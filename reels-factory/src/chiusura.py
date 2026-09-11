"""Dove finisce la clip: su un ragionamento chiuso, non su un respiro.

Lorenzo, 11/09, guardando il Reel uscito quella mattina:

    "ha una conclusione sbagliata, nel senso che lascia in sospeso: dice
     'da lì a credere a un dio che ha delle regole della Bibbia eccetera
     eccetera' e poi si ferma improvvisamente. Il Reel dev'essere un
     discorso completo, comprensibile e finito in sé stesso."

Aveva ragione alla lettera. Quel Reel finiva cosi:

    "...mi rendo conto che pero da li a scegliere il cristianesimo, un dio
     specifico con un nome, una storia, delle regole"

e basta: la frase non si chiude mai.

Il motivo stava nel codice. La fine della clip veniva decisa da
`snap_to_sentences`, e li "frase" non vuol dire quello che sembra: si
chiude sulla punteggiatura di Whisper, che nel parlato salta quasi sempre,
oppure su una pausa di 0.75 secondi. Una pausa e un respiro. Quindi la
clip finiva dove Lorenzo aveva preso fiato — che non ha niente a che
vedere con la fine di un discorso.

Qui si cambia il criterio, con lo stesso schema usato per l'apertura: il
codice ELENCA tutti i punti in cui la clip potrebbe finire, scarta quelli
che non possono chiudere una frase, e il modello SCEGLIE quello in cui il
ragionamento si e chiuso. Il vincolo sta in come nascono le opzioni, non
in una raccomandazione dentro un prompt.
"""

import re

from . import aggancio

# Una pausa piu corta di quella che Whisper considera fine frase: qui non si
# cerca "la fine di una frase", si cerca un punto in cui la voce si ferma
# abbastanza da poter tagliare senza che si senta il taglio.
RESPIRO = 0.28

# Il massimo di punti da mettere davanti al modello. Piu di cosi il prompt
# diventa lungo e la scelta peggiora, non migliora.
MAX_PUNTI = 14

# Parole con cui un discorso NON puo finire: dopo di loro ci si aspetta
# qualcos'altro, e chi guarda sente il vuoto. Sono le legature dell'apertura
# piu quelle che reggono solo guardando avanti.
SOSPESE = aggancio.LEGATURE | {
    "ma", "pero", "però", "perche", "perché", "quando", "mentre", "quindi",
    "allora", "dunque", "invece", "finche", "finché", "affinche", "affinché",
    "cui", "chi", "quale", "quali", "molto", "piu", "più", "meno", "tanto",
    "cosi", "così", "sempre", "mai", "non", "ogni", "ogni", "un", "uno",
    "una", "il", "i", "del", "dei", "nei", "sui", "tra", "fra", "verso",
    "sotto", "sopra", "dentro", "fuori", "senza", "durante", "essere",
    "avere", "fare", "dire", "voler", "poter", "dover",
}


def _pulita(parola: str) -> str:
    return re.sub(r"[^\w'àèéìòùÀÈÉÌÒÙ]", "", parola.lower()).strip("'")


def punti_finali(words: list[dict], start: float, *,
                 min_seconds: float, max_seconds: float) -> list[dict]:
    """I punti in cui la clip puo finire, dal piu presto al piu tardi.

    Un punto e buono se: sta dentro la durata ammessa, la voce ci si ferma
    (una pausa, o una punteggiatura forte di Whisper quando c'e), e l'ultima
    parola non e una di quelle che lasciano la frase appesa.

    Ognuno porta con se le ultime parole, che sono quelle su cui il modello
    dovra giudicare se il discorso e chiuso.
    """
    primo, ultimo = start + min_seconds, start + max_seconds
    dentro = [w for w in words if w["start"] >= start - 0.5 and w["end"] <= ultimo + 0.5]
    if len(dentro) < 4:
        return []

    fuori: list[dict] = []
    for i, w in enumerate(dentro):
        if not (primo <= w["end"] <= ultimo):
            continue
        testo = w["word"].strip()
        forte = bool(set(testo) & set(".?!"))
        pausa = (dentro[i + 1]["start"] - w["end"]) if i + 1 < len(dentro) else 99.0
        if not forte and pausa < RESPIRO:
            continue
        if _pulita(testo) in SOSPESE:
            continue
        coda = aggancio.ricuci(" ".join(x["word"] for x in dentro[max(0, i - 11):i + 1]))
        fuori.append({"fine": w["end"], "coda": coda.strip(),
                      "pausa": min(pausa, 9.9), "forte": forte})

    # Due punti a mezzo secondo l'uno dall'altro sono lo stesso punto: si
    # tiene quello con la pausa piu larga, che e il taglio piu pulito.
    fuori.sort(key=lambda p: p["fine"])
    diradati: list[dict] = []
    for p in fuori:
        if diradati and p["fine"] - diradati[-1]["fine"] < 0.9:
            if p["pausa"] > diradati[-1]["pausa"]:
                diradati[-1] = p
            continue
        diradati.append(p)

    # Se sono troppi si tengono i piu tardi: una clip che chiude tardi ha
    # detto piu cose, e il minimo di durata e gia garantito da `primo`.
    return diradati[-MAX_PUNTI:]


SCELTA_FINALE = """Questo e il parlato di un Reel per Instagram. Chi lo guarda \
non ha visto altro e non vedra altro: il Reel deve essere un discorso intero, \
che si capisce da solo e che FINISCE.

Argomento della clip: {argomento}

Il parlato, con i punti in cui posso tagliare segnati cosi ⟦1⟧ ⟦2⟧ ⟦3⟧:

{testo}

Scegli il numero del punto in cui il discorso SI CHIUDE. Il punto giusto e \
quello dopo il quale chi guarda non resta ad aspettare il seguito:
- l'ultima frase e finita — non si interrompe a meta, non lascia un "pero", \
un "da li a", un elenco aperto;
- il ragionamento ha una conclusione: si e detto il punto, non solo la \
premessa o l'esempio;
- se subito dopo il taglio arrivasse il silenzio, avrebbe senso.

Meglio una clip piu corta che chiude, che una piu lunga che si spegne a meta \
frase. Ma non scegliere un punto cosi presto da non aver detto niente.

Rispondi SOLO col numero. Se NESSUNO dei punti chiude il discorso, rispondi 0."""


def _testo_segnato(words: list[dict], start: float, punti: list[dict]) -> str:
    """Il parlato dall'inizio della clip, coi punti di taglio numerati."""
    fine = punti[-1]["fine"]
    pezzi: list[str] = []
    prossimo = 0
    for w in words:
        if not (start - 0.5 <= w["start"] and w["end"] <= fine + 0.5):
            continue
        pezzi.append(w["word"].strip())
        while prossimo < len(punti) and w["end"] >= punti[prossimo]["fine"] - 0.01:
            pezzi.append(f"⟦{prossimo + 1}⟧")
            prossimo += 1
    return aggancio.ricuci(" ".join(pezzi))


def scegli_finale(words: list[dict], start: float, *, argomento: str,
                  model: str, min_seconds: float, max_seconds: float) -> float | None:
    """Il secondo in cui far finire la clip, scelto fra i punti possibili.

    Torna None se non ci sono punti o se il modello non ne approva nessuno:
    in quel caso chi chiama tiene la fine che aveva.
    """
    punti = punti_finali(words, start, min_seconds=min_seconds,
                         max_seconds=max_seconds)
    if not punti:
        print("      ⚠️ Nessun punto di chiusura utile: la clip finisce dov'era")
        return None
    if len(punti) == 1:
        print(f"      🔚 Un solo finale possibile, a {punti[0]['fine']:.0f}s")
        return punti[0]["fine"]

    testo = _testo_segnato(words, start, punti)
    prompt = SCELTA_FINALE.format(argomento=argomento or "(non indicato)",
                                  testo=testo)
    for tentativo in (1, 2, 3):
        try:
            r = aggancio._cliente().messages.create(
                model=model, max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:                       # noqa: BLE001
            print(f"      ⚠️ Scelta del finale, tentativo {tentativo}: {e}")
            continue
        risposta = "".join(b.text for b in r.content if b.type == "text")
        numeri = re.findall(r"\d+", risposta)
        if not numeri:
            print(f"      ⚠️ Scelta del finale senza numero "
                  f"(stop_reason={r.stop_reason}, testo={risposta[:40]!r})")
            break
        k = int(numeri[0])
        if k == 0:
            # NESSUNO CHIUDE. Non si tiene la fine di prima: quella era una
            # pausa qualsiasi, e il Reel dell'11/09 e uscito cosi. Si prende
            # il punto piu tardi fra quelli che almeno non finiscono su una
            # parola appesa — e il meno peggio, e resta dentro il tetto.
            scelto = max(punti, key=lambda p: (p["forte"], p["pausa"]))
            print(f"      🔚 Nessun finale chiude davvero: prendo la pausa piu "
                  f"larga, a {scelto['fine']:.0f}s")
            return scelto["fine"]
        if 1 <= k <= len(punti):
            scelto = punti[k - 1]
            print(f"      🔚 La clip chiude su «{scelto['coda'][-60:]}» "
                  f"({scelto['fine']:.0f}s)")
            return scelto["fine"]
        print(f"      ⚠️ Finale fuori elenco ({k} su {len(punti)})")
        break
    return None

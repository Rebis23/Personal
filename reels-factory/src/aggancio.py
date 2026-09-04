"""L'aggancio: la frase corta che si legge a schermo E si sente per prima.

Lorenzo, guardando il Reel del 3/09 (4/09):

    "l'hook scritto e lunghissimo e non attrae, perche quando ti trovi una
     sbrodolata di testo del genere e chiaro che non ti fermerai a guardare.
     [...] in questo caso un hook perfetto e breve era «Pensare e roba da
     stupidi», che e la frase piu d'impatto che c'e dentro questo reel. E
     anche i primi secondi del video sono sbagliati, perche bastava iniziare
     dicendo «Pensare e roba da stupidi» e poi partire."

Due difetti, una causa sola: il banner e il parlato erano scollegati. Il
modello scriveva una frase riassuntiva lunga, e la clip partiva dove
cominciava il ragionamento — quindi chi guardava leggeva quattro righe e
sentiva una premessa.

Qui la frase corta diventa il perno: si accorcia l'aggancio fino a una riga
prendendolo DENTRO le parole gia scritte, poi si cerca dove quelle parole
vengono pronunciate e la clip parte da li. Banner e voce dicono la stessa
cosa, nello stesso istante.

Le due regole sono meccaniche, non raccomandazioni nel prompt: quello diceva
gia "max 12 parole" e "apri sull'hook", e sono usciti agganci da 27 parole
che partivano dieci secondi prima. Un vincolo che il codice non verifica non
e un vincolo.
"""

import json
import re

import anthropic


# Una riga sola su Instagram, a corpo grande, sono cinque o sei parole. Sette
# e il tetto oltre il quale si va a capo e si perde l'impatto.
MAX_PAROLE = 7


def parole(testo: str) -> list[str]:
    """Solo le parole, senza punteggiatura e senza accenti di comodo."""
    return [p for p in re.findall(r"[0-9a-zàèéìòóùç']+", testo.lower()) if p]


def quante(testo: str) -> int:
    return len(parole(testo))


def e_contiguo(frammento: str, intero: str) -> bool:
    """Vero se `frammento` e un pezzo consecutivo di `intero`.

    Serve a impedire che l'accorciamento diventi una riscrittura: il modello
    puo solo TAGLIARE, non inventare parole nuove. Cosi il banner resta una
    frase che nel video si sente davvero.
    """
    f, i = parole(frammento), parole(intero)
    if not f or len(f) > len(i):
        return False
    return any(i[k:k + len(f)] == f for k in range(len(i) - len(f) + 1))


def trova_nel_parlato(words: list[dict], frase: str,
                      da: float, a: float) -> float | None:
    """A che secondo si comincia a pronunciare `frase`, fra `da` e `a`.

    `words` sono le parole con i tempi (da Whisper). Il confronto e sulle
    parole nude: la trascrizione scrive "perche", il banner "perché", e
    devono combaciare lo stesso.

    Tolleranza: bastano i primi tre quarti delle parole della frase, in
    ordine e consecutive. Whisper ogni tanto attacca o stacca una parola, e
    pretendere il calco esatto farebbe fallire il rilevamento proprio sulle
    frasi lunghe, che sono quelle che ne hanno piu bisogno.
    """
    cercate = parole(frase)
    if not cercate:
        return None

    dentro = [(w, parole(w["word"])) for w in words if da - 0.5 <= w["start"] <= a]
    piatte: list[tuple[str, float]] = []
    for w, pp in dentro:
        for p in pp:
            piatte.append((p, w["start"]))
    if not piatte:
        return None

    testo = [p for p, _ in piatte]
    minimo = max(3, int(len(cercate) * 0.75))
    # Si prova prima con la frase intera, poi accorciandola dalla coda: il
    # principio della frase e la parte che conta, ed e quella su cui la clip
    # deve aprirsi.
    for lunghezza in range(len(cercate), minimo - 1, -1):
        pezzo = cercate[:lunghezza]
        for k in range(len(testo) - lunghezza + 1):
            if testo[k:k + lunghezza] == pezzo:
                return piatte[k][1]
    return None


PROMPT = """Questi sono gli agganci di alcuni Reel: la frase che compare \
scritta a schermo sopra la testa di chi parla, e che deve fermare lo scroll.

Sono troppo lunghi. A schermo diventano quattro righe di testo, e chi scorre \
non si ferma a leggere un paragrafo: si ferma su UNA RIGA che colpisce.

Per ognuno, estrai il frammento piu forte che c'e gia dentro, al massimo \
{max_parole} parole.

REGOLE FERREE:
- Puoi solo TAGLIARE. Ogni parola che scrivi deve essere presa dall'aggancio \
originale, nello stesso ordine e consecutive. Non aggiungere, non cambiare, \
non riordinare, non coniugare diversamente.
- Scegli il pezzo che colpisce di piu, non il primo che capita: quello che \
contraddice, che nomina la cosa concreta, che fa male. Di solito NON e la \
premessa: e quello che viene dopo i due punti, dopo la virgola, dopo il "ma".
- Deve reggersi da solo per chi non ha visto niente.
- Niente virgolette, niente punto finale.

Esempio del criterio, con le parole di chi lo ha chiesto:
  originale: "selezionando quale comportamento mi e utile e a quel punto \
basta eseguirlo ed e li che pensare diventa roba da stupidi"
  giusto:    "pensare diventa roba da stupidi"

AGGANCI:
{elenco}

Rispondi SOLO con un oggetto JSON {{"numero": "frammento"}}, usando i numeri \
qui sopra. Nessun'altra parola."""


def accorcia(hooks: dict[int, str], *, model: str,
             max_parole: int = MAX_PAROLE) -> dict[int, str]:
    """Riduce a una riga gli agganci troppo lunghi, tagliando e basta.

    Torna solo quelli effettivamente accorciati e verificati. Un frammento
    che non risulta contiguo all'originale viene scartato: meglio tenere
    l'aggancio lungo che metterne a schermo uno che nel video non si sente.
    """
    lunghi = {i: h for i, h in hooks.items() if quante(h) > max_parole}
    if not lunghi:
        return {}

    elenco = "\n".join(f"{i}. {h}" for i, h in sorted(lunghi.items()))
    try:
        risposta = anthropic.Anthropic().messages.create(
            model=model,
            max_tokens=1200,
            messages=[{"role": "user", "content": PROMPT.format(
                max_parole=max_parole, elenco=elenco)}],
        )
    except Exception as e:                      # noqa: BLE001
        print(f"      ⚠️ Accorciamento non riuscito ({e}): tengo gli agganci lunghi")
        return {}

    testo = "".join(b.text for b in risposta.content if b.type == "text")
    inizio, fine = testo.find("{"), testo.rfind("}")
    if inizio < 0 or fine < 0:
        print("      ⚠️ Accorciamento senza risposta leggibile")
        return {}
    try:
        grezzo = json.loads(testo[inizio:fine + 1])
    except json.JSONDecodeError:
        print("      ⚠️ Accorciamento con JSON rotto")
        return {}

    buoni: dict[int, str] = {}
    for chiave, frammento in grezzo.items():
        try:
            i = int(chiave)
        except (TypeError, ValueError):
            continue
        if i not in lunghi or not isinstance(frammento, str):
            continue
        frammento = frammento.strip().strip('"').rstrip(".")
        if not frammento:
            continue
        if quante(frammento) > max_parole:
            print(f"      ⚠️ Frammento ancora lungo, scartato: «{frammento}»")
            continue
        if not e_contiguo(frammento, lunghi[i]):
            # Questo e il controllo che conta: senza, il modello "accorcia"
            # riscrivendo, e il banner torna a dire cose che nel video non
            # si sentono — cioe esattamente il difetto di partenza.
            print(f"      ⚠️ Frammento riscritto invece che tagliato, scartato: "
                  f"«{frammento}»")
            continue
        buoni[i] = frammento[0].upper() + frammento[1:]
    return buoni

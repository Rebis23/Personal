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
import os
import re
import time

import anthropic


# Il segreto va SEMPRE passato con .strip(). Quando si incolla una chiave nei
# GitHub Secrets ci resta attaccato un a-capo, e un a-capo dentro un header
# HTTP e illegale: la richiesta non parte nemmeno, e la libreria lo riporta
# come "Connection error." — che sembra la rete e invece e questa riga.
#
# Il 4 e il 5 settembre ho perso due giorni dietro a questo. Avevo scritto
# anthropic.Anthropic() senza chiave in tre punti nuovi, mentre brain.py la
# passava gia con .strip() dal primo giorno. Risultato: le chiamate vecchie
# funzionavano, le mie no, sempre, e io davo la colpa alla rete e a WARP.
# Tre tentativi su tre fallivano perche il guasto era deterministico.
def _cliente() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


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


# Dove una frase italiana si spezza naturalmente. I due punti per primi:
# nella lingua parlata quello che viene dopo i due punti e quasi sempre la
# frase forte, e la premessa sta davanti.
SEPARATORI = r"[:;–—]|,|\s+\bma\b\s+|\s+\bpero\b\s+|\s+\bperò\b\s+|\s+\bquindi\b\s+"


def spezza(intero: str, max_parole: int = MAX_PAROLE) -> str | None:
    """Ritaglia meccanicamente il pezzo migliore, senza chiedere a nessuno.

    E l'ultima rete quando il modello, invece di tagliare, riscrive: il 4/09
    su quattro agganci lunghi ne ha accorciato bene uno solo, e gli altri tre
    erano parafrasi respinte da e_contiguo. La guardia faceva il suo mestiere,
    ma il risultato era comunque un banner lungo.

    Qui non c'e niente da riscrivere: si spezza la frase dove si spezza da
    sola — due punti, punto e virgola, virgola, "ma" — e si tiene il tratto
    che sta nel limite. A parita di lunghezza vince quello piu avanti, perche
    in italiano la premessa sta davanti e la frase che fa male viene dopo.

    Torna None se nessun tratto regge: meglio un aggancio lungo che un
    moncone di due parole che non vuol dire niente.
    """
    # Si spezza tenendo da parte i separatori, perche SERVE sapere quale
    # pezzo viene subito dopo i due punti: e quasi sempre quello buono.
    parti = re.split(f"({SEPARATORI})", intero)
    pezzi: list[str] = []
    dopo_i_due_punti: list[bool] = []
    due_punti_visti = False
    for k, grezzo in enumerate(parti):
        if grezzo is None:
            continue
        if k % 2 == 1:                      # e un separatore
            if ":" in grezzo:
                due_punti_visti = True
            continue
        testo = grezzo.strip(" ,;:—–")
        if testo:
            pezzi.append(testo)
            dopo_i_due_punti.append(due_punti_visti)
    if len(pezzi) < 2:
        return None

    migliore = None
    voto_migliore = (-1, 1, -1)
    for i in range(len(pezzi)):
        for j in range(i + 1, len(pezzi) + 1):
            tratto = " ".join(pezzi[i:j])
            n = quante(tratto)
            # Sotto le tre parole non e una frase, e sopra il limite non e
            # una riga: in mezzo si sceglie.
            if not (3 <= n <= max_parole):
                continue
            # Deve restare un pezzo consecutivo dell'originale, come tutto
            # il resto del meccanismo.
            if not e_contiguo(tratto, intero):
                continue
            # L'ORDINE DI PREFERENZA, corretto il 4/09 dopo averlo visto
            # sbagliare: prima quello che sta DOPO i due punti (in italiano
            # la premessa sta davanti e la frase che fa male viene dopo),
            # poi il PIU VICINO ai due punti — non l'ultimo. Con la regola
            # vecchia, su «...a 25 anni: quello studio e falso, i
            # partecipanti avevano al massimo 20 anni» sceglieva la coda
            # («i partecipanti avevano...») invece del pugno («quello studio
            # e falso»). A parita, il tratto piu lungo porta piu contesto.
            voto = (1 if dopo_i_due_punti[i] else 0, -i, n)
            if voto > voto_migliore:
                voto_migliore, migliore = voto, tratto
    if migliore is None:
        return None
    return migliore[0].upper() + migliore[1:]


def candidati(intero: str, max_parole: int = MAX_PAROLE,
              minimo: int = 4) -> list[str]:
    """Tutti i tratti consecutivi di 4-7 parole dentro l'aggancio.

    E il cambio di impostazione del 5/09. Finora si CHIEDEVA al modello di
    tagliare e poi si controllava se aveva obbedito: su quattro agganci veri
    ne ha tagliati bene uno, gli altri tre erano parafrasi e sono stati
    respinti. Chiedere e controllare e una lotta.

    Qui il taglio lo genera il codice — tutte le finestre possibili — e al
    modello resta solo la cosa che sa fare davvero: dire quale delle frasi
    gia pronte colpisce di piu. Cosi la contiguita non e piu una regola da
    far rispettare: e una proprieta di come le opzioni sono nate. Nessuna
    puo essere una riscrittura, perche nessuna e stata scritta.

    Copre anche i casi senza punteggiatura, dove spezza() alza le mani: su
    «...allena il tuo cervello a fare lo spettatore invece del protagonista»
    non c'e nessun due punti, ma «il tuo cervello a fare lo spettatore» e li
    dentro e si regge.
    """
    # Si lavora sulle parole con la loro punteggiatura attaccata, cosi il
    # tratto scelto si puo restituire leggibile invece che spellato.
    pezzi = intero.split()
    # Nessun tratto puo SCAVALCARE un due punti o un punto fermo. Fra le 62
    # opzioni offerte per l'aggancio sui 25 anni ce n'erano di questo tipo:
    # «di svilupparsi a 25 anni: quello studio» — meta premessa e meta
    # pugno, incollate. Come banner non vogliono dire niente, e offrirle
    # significa dare al modello la possibilita di sceglierne una. La virgola
    # invece si attraversa: «nebbia mentale, ansia, libido a zero» e una
    # riga sola e funziona.
    MURI = set(".:;?!—–")
    muro_dopo = [bool(MURI & set(w)) for w in pezzi]
    fuori: list[str] = []
    visti: set[str] = set()
    for i in range(len(pezzi)):
        for n in range(minimo, max_parole + 1):
            if i + n > len(pezzi):
                break
            if any(muro_dopo[i:i + n - 1]):
                break                       # oltre il muro non si va
            tratto = " ".join(pezzi[i:i + n]).strip(" ,;:—–.")
            if not (minimo <= quante(tratto) <= max_parole):
                continue
            chiave = " ".join(parole(tratto))
            if chiave in visti:
                continue
            visti.add(chiave)
            fuori.append(tratto)
    return fuori


SCELTA = """Devo mettere UNA RIGA di testo sopra la testa di chi parla in un \
Reel: la frase che ferma lo scroll. L'aggancio che ho e troppo lungo, quindi \
ho gia ritagliato tutti i pezzi possibili e ora devo scegliere.

AGGANCIO INTERO:
{intero}

PEZZI FRA CUI SCEGLIERE:
{elenco}

Scegli il numero del pezzo che:
- si regge DA SOLO per chi non ha visto niente e non legge il resto;
- colpisce di piu — contraddice qualcosa, nomina una cosa concreta, fa male. \
Di solito NON e la premessa;
- comincia e finisce dove comincerebbe e finirebbe una frase, non a meta di \
un'espressione ("a fare lo" no, "il tuo cervello a fare lo spettatore" si).

Rispondi SOLO col numero. Se nessun pezzo si regge da solo, rispondi 0: \
meglio un aggancio lungo che un moncone senza senso."""


def scegli_tratto(intero: str, *, model: str,
                  max_parole: int = MAX_PAROLE) -> str | None:
    """Fa scegliere al modello UNO dei tratti gia ritagliati dal codice."""
    opzioni = candidati(intero, max_parole)
    if not opzioni:
        return None
    elenco = "\n".join(f"{k + 1}. {o}" for k, o in enumerate(opzioni))
    for tentativo in (1, 2, 3):
        try:
            r = _cliente().messages.create(
                model=model, max_tokens=200,
                messages=[{"role": "user", "content": SCELTA.format(
                    intero=intero, elenco=elenco)}],
            )
            testo = "".join(b.text for b in r.content if b.type == "text")
            numeri = re.findall(r"\d+", testo)
            if not numeri:
                return None
            k = int(numeri[0])
            if k == 0 or k > len(opzioni):
                return None
            scelto = opzioni[k - 1]
            # Cintura e bretelle: e nato da un taglio, ma si verifica lo stesso.
            if not e_contiguo(scelto, intero):
                return None
            return scelto[0].upper() + scelto[1:]
        except Exception as e:                          # noqa: BLE001
            print(f"      ⚠️ Scelta del tratto, tentativo {tentativo}/3 ({e})")
            if tentativo < 3:
                time.sleep(tentativo * 4)
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

    # Si riprova. Il 4/09 una singola "Connection error." ha fatto uscire
    # tutti e cinque gli agganci lunghi — 20, 28, 23, 22 parole — cioe
    # esattamente il difetto che Lorenzo aveva appena chiesto di togliere.
    # Un inciampo di rete non deve costare la correzione: questo passaggio
    # non e un ornamento, e la regola.
    risposta = None
    for tentativo in (1, 2, 3):
        try:
            risposta = _cliente().messages.create(
                model=model,
                max_tokens=1200,
                messages=[{"role": "user", "content": PROMPT.format(
                    max_parole=max_parole, elenco=elenco)}],
            )
            break
        except Exception as e:                  # noqa: BLE001
            print(f"      ⚠️ Accorciamento, tentativo {tentativo}/3 fallito ({e})")
            if tentativo < 3:
                time.sleep(tentativo * 4)
    # Qui non si esce MAI in anticipo. Il 5/09 il modello ha risposto senza
    # graffe, questa funzione ha fatto "return {}" e i tre agganci lunghi
    # sono usciti lunghi — 17, 16 e 20 parole. Le due reti scritte apposta
    # sotto (scegli fra i tratti pronti, taglia sui due punti) non sono
    # nemmeno state sfiorate: erano irraggiungibili proprio nel caso in cui
    # servivano. Una rete di sicurezza dopo un return non e una rete.
    grezzo: dict = {}
    if risposta is None:
        print("      ⛔ Accorciamento: nessuna risposta dopo 3 tentativi, "
              "passo alle reti")
    else:
        testo = "".join(b.text for b in risposta.content if b.type == "text")
        inizio, fine = testo.find("{"), testo.rfind("}")
        if inizio < 0 or fine < 0:
            print(f"      ⚠️ Accorciamento senza graffe ({testo[:60]!r}), "
                  f"passo alle reti")
        else:
            try:
                letto = json.loads(testo[inizio:fine + 1])
                grezzo = letto if isinstance(letto, dict) else {}
            except json.JSONDecodeError:
                print("      ⚠️ Accorciamento con JSON rotto, passo alle reti")

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

    # ULTIMA RETE. Quello che il modello non ha saputo tagliare — perche ha
    # riscritto, o perche non ha risposto per quella riga — lo si taglia a
    # mano, spezzando la frase dove si spezza da sola. Non risolve tutto:
    # sui quattro agganci veri del 4/09 sera ne recupera uno (quello coi due
    # punti) e lascia stare gli altri due, che non hanno un punto di rottura.
    # E' una rete, non una soluzione, e va detto invece che vantato.
    for i, intero in lunghi.items():
        if i in buoni:
            continue
        # Secondo giro, con le carte in tavola: invece di chiedere di
        # tagliare, si mostrano i tagli gia fatti e si chiede solo di
        # scegliere. Cosi una riscrittura non e nemmeno possibile.
        tratto = scegli_tratto(intero, model=model, max_parole=max_parole)
        if tratto:
            print(f"      ✂️ Scelto fra i tratti pronti: «{tratto}»")
            buoni[i] = tratto
            continue
        # Terzo giro, senza chiedere niente a nessuno.
        tratto = spezza(intero, max_parole)
        if tratto:
            print(f"      ✂️ Tagliato a mano sui due punti: «{tratto}»")
            buoni[i] = tratto
    ancora_lunghi = [i for i in lunghi if i not in buoni]
    if ancora_lunghi:
        print(f"      ⚠️ {len(ancora_lunghi)} agganci restano lunghi: non c'e "
              f"un punto dove spezzarli senza mutilarli")
    return buoni

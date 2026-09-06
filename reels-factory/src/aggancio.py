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


def ricuci(testo: str) -> str:
    """Rimette insieme le elisioni spezzate da Whisper.

    Whisper italiano restituisce le parole una per una e ogni tanto stacca
    l'elisione: "l" e "'effetto" arrivano separate, e unendole con uno
    spazio esce «l 'effetto». Il 6/09 e finito cosi su un banner vero, in
    cima a un Reel: «Cervello sotto l 'effetto prolungato di pornografia».
    In italiano l'apostrofo non ha spazi ne prima ne dopo.
    """
    testo = re.sub(r"\s+'", "'", testo)
    testo = re.sub(r"'\s+", "'", testo)
    return re.sub(r"\s{2,}", " ", testo).strip()


def parole(testo: str) -> list[str]:
    """Solo le parole, senza punteggiatura e senza accenti di comodo."""
    return [p for p in re.findall(r"[0-9a-zàèéìòóùç']+", testo.lower()) if p]


def quante(testo: str) -> int:
    return len(parole(testo))


# Parole troppo comuni per dire qualcosa sull'argomento: se l'unica cosa in
# comune fra banner e argomento e "la", il banner non nomina niente.
VUOTE = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "l", "dell",
    "di", "del", "della", "dei", "delle", "a", "al", "alla", "ai", "alle",
    "da", "dal", "dalla", "in", "nel", "nella", "con", "su", "sul", "sulla",
    "per", "tra", "fra", "e", "ed", "o", "ma", "che", "chi", "cui", "come",
    "non", "piu", "più", "sono", "essere", "fare", "cosa", "cose", "tuo",
    "tua", "tuoi", "tue", "mio", "mia", "si", "ti", "ci", "se", "quando",
}


def _radice(p: str) -> str:
    """Taglia la desinenza: «pornografia» e «pornografico» devono combaciare."""
    return p[:6] if len(p) > 7 else p


def nomina_argomento(hook: str, argomento: str) -> bool:
    """Il banner nomina l'argomento della clip, o parla d'altro?

    LA REGOLA CHE MANCAVA. Il 6/09 e uscito un Reel sulla religione col
    titolo «Zanzara che depone le uova negli occhi». La zanzara nel video
    c'e — e l'esempio che porta il discorso — ma chi scorre legge il titolo
    e non capisce di cosa si parla, quindi non si ferma. Lorenzo: "un hook
    perfetto sarebbe stato «Perché Dio permette il male sugli animali?»".

    Il controllo e grezzo di proposito: basta una parola piena in comune fra
    banner e argomento. Non sa riconoscere i sinonimi, quindi ogni tanto
    boccia un banner buono — e per questo un "no" non butta via niente, fa
    solo riscrivere. Ma il caso che conta lo prende: fra «zanzara ... occhi»
    e «la fede in Dio» non c'e una parola in comune, e si vede subito.
    """
    if not argomento.strip():
        return True                     # senza argomento non c'e niente da verificare
    dette = {_radice(x) for x in parole(hook) if x not in VUOTE}
    cercate = {_radice(x) for x in parole(argomento) if x not in VUOTE}
    return bool(dette & cercate)


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
            # IL BUDGET NON E' LA LUNGHEZZA DELLA RISPOSTA. Chiedere "dimmi
            # solo un numero" non vuol dire che bastino pochi token: prima
            # della risposta il modello ragiona, e quel ragionamento consuma
            # il budget. Con 200 la risposta usciva VUOTA con
            # stop_reason=max_tokens — il modello veniva tagliato mentre
            # pensava e non arrivava mai a dire il numero. Il 5/09 questo ha
            # spento in silenzio due passaggi su tre della catena.
            r = _cliente().messages.create(
                model=model, max_tokens=3000,
                messages=[{"role": "user", "content": SCELTA.format(
                    intero=intero, elenco=elenco)}],
            )
            testo = "".join(b.text for b in r.content if b.type == "text")
            numeri = re.findall(r"\d+", testo)
            if not numeri:
                # Prima si tornava None e basta: il passaggio spariva dal
                # log e sembrava non essere mai stato scritto.
                print(f"      ⚠️ Scelta del tratto senza numero "
                      f"(stop_reason={r.stop_reason}, testo={testo[:40]!r})")
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


# ---------------------------------------------------------------------------
# IL BANNER PRESO DAL PARLATO
#
# Il 5/09, su cinque clip su cinque, il log diceva "L'aggancio non si ritrova
# nel parlato". Non era un caso sfortunato: era garantito. Il banner nasce
# come frase SCRITTA dal modello (e poi riscritta, se la prova a freddo la
# boccia), e accorcia() ne ritaglia un pezzo — ma un pezzo di una frase
# scritta resta una frase scritta. Cercarla nel sonoro non poteva funzionare.
#
# Quindi la si prende dall'altra parte. Le righe candidate sono pezzi di
# parlato veri, con dentro il secondo esatto in cui vengono pronunciate: al
# modello resta solo da dire quale ferma lo scroll. Banner e voce non
# possono divergere, perche sono la stessa cosa.
#
# Lorenzo, 4/09: «bastava iniziare dicendo "pensare e roba da stupidi" e poi
# partire». Quella frase lui l'ha presa dal video, non l'ha inventata.
# ---------------------------------------------------------------------------

# Un muro non si attraversa e apre una proposizione nuova.
MURI = ".:;?!—–"
# Dopo una virgola si puo tirare dritto, ma li comincia anche una riga buona.
VIRGOLE = ","
# Nel parlato la punteggiatura di Whisper salta; il silenzio no.
PAUSA = 0.45
# Parole con cui una riga NON puo cominciare: sono legature, e chi le legge
# da sole sente che manca qualcosa prima. Tutto il resto va bene, anche in
# mezzo a un periodo — la riga che Lorenzo voleva, "pensare diventa roba da
# stupidi", sta esattamente in mezzo a un periodo senza virgole ne pause.
LEGATURE = {"e", "ed", "che", "di", "del", "della", "dei", "delle", "a", "al",
            "alla", "ai", "alle", "da", "dal", "dalla", "in", "nel", "nella",
            "con", "su", "sul", "sulla", "per", "come", "se", "o", "oppure",
            "cioe", "cioè", "ecco", "poi", "anche", "gia", "già", "li", "lì",
            "ci", "ne", "lo", "la", "le", "gli", "mi", "ti", "si", "vi"}


def tratti_parlati(words: list[dict], da: float, a: float, *,
                   max_parole: int = MAX_PAROLE, minimo: int = 4,
                   gia_usati: frozenset[str] = frozenset()) -> list[dict]:
    """Le righe da 4-7 parole realmente pronunciate fra `da` e `a`.

    Ognuna comincia dove comincia una proposizione — inizio frase, dopo una
    virgola o un due punti, dopo una pausa, dopo un "ma" — perche una riga
    che parte a meta sintagma, letta o sentita, suona monca. E ognuna porta
    il secondo in cui parte: e quello il punto da cui far partire la clip.
    """
    dentro = [w for w in words if da - 0.5 <= w["start"] <= a]
    if len(dentro) < minimo:
        return []

    testi = [w["word"].strip() for w in dentro]
    muro = [bool(set(t) & set(MURI)) for t in testi]
    virgola = [t.endswith(tuple(VIRGOLE)) for t in testi]

    # Una riga puo cominciare quasi ovunque. Il primo tentativo la faceva
    # partire solo dopo una virgola, una pausa o un "ma", e su
    # «...ed e li che pensare diventa roba da stupidi» offriva quattro sole
    # opzioni, tutte dentro la premessa: la riga che Lorenzo aveva indicato
    # come quella giusta non era nemmeno fra le scelte. Il parlato continuo
    # non ha punteggiatura, e legare i tagli alla punteggiatura significava
    # non trovarli mai. Si taglia dappertutto e si scarta solo cio che
    # comincia con una legatura.
    inizi = [i for i, t in enumerate(testi)
             if not (parole(t) and parole(t)[0] in LEGATURE)]
    if 0 not in inizi:
        inizi.insert(0, 0)

    fuori: list[dict] = []
    visti: set[str] = set()
    for i in inizi:
        for n in range(minimo, max_parole + 1):
            if i + n > len(testi):
                break
            if any(muro[i:i + n - 1]):
                break                       # oltre il muro non si va
            testo = ricuci(" ".join(testi[i:i + n]).strip(" ,;:—–."))
            if not (minimo <= quante(testo) <= max_parole):
                continue
            chiave = " ".join(parole(testo))
            if chiave in visti or chiave in gia_usati:
                continue
            visti.add(chiave)
            fuori.append({"testo": testo, "start": dentro[i]["start"]})
    return fuori


DAL_PARLATO = """Devo mettere UNA RIGA di testo sopra la testa di chi parla in \
un Reel — la frase che ferma lo scroll — e il video deve PARTIRE esattamente \
da quella frase. Quindi la riga non posso scriverla: devo pescarla fra le \
cose che nel video vengono dette davvero.

Qui sotto ci sono tutte le righe pronunciate in questa clip, gia ritagliate. \
Scegline UNA.

Di cosa parla la clip: {tema}

RIGHE PRONUNCIATE:
{elenco}

Scegli quella che:
- si regge DA SOLA per chi non ha visto niente e non sa nulla del video;
- colpisce di piu: contraddice qualcosa che si da per scontato, nomina una \
cosa concreta, fa male. Di solito NON e la premessa;
- funziona come PRIMA COSA che si sente, non come conclusione di un \
ragionamento (niente "quindi", "ecco perche", "come dicevo").

Esempio del criterio, con le parole di chi lo ha chiesto: in un video che \
diceva "selezionando quale comportamento mi e utile e a quel punto basta \
eseguirlo ed e li che pensare diventa roba da stupidi", la riga giusta era \
"pensare diventa roba da stupidi".

Se NESSUNA regge da sola davanti a uno che non ha contesto, rispondi \
NESSUNA: meglio niente che una riga che non vuol dire niente.

Rispondi SOLO col numero, oppure NESSUNA. Nessun'altra parola."""


def scegli_parlato(tratti: list[dict], *, tema: str, model: str) -> dict | None:
    """Fa scegliere al modello quale riga pronunciata diventa il banner."""
    if not tratti:
        return None
    elenco = "\n".join(f"{i}. {t['testo']}" for i, t in enumerate(tratti))
    for tentativo in (1, 2, 3):
        try:
            # 3000, dopo due tentativi sbagliati nella stessa serata.
            # Prima 16, pensando "tanto deve dire solo un numero": risposta
            # vuota su cinque clip su cinque (run 101). Poi 200: ancora
            # vuota su quattro su cinque (run 104), e stavolta lo
            # stop_reason l'ha detto — max_tokens. Il modello non veniva
            # tagliato mentre scriveva la risposta: veniva tagliato mentre
            # RAGIONAVA, prima di arrivare a scriverla. Il budget non e la
            # lunghezza della risposta, e tutto cio che serve per produrla.
            r = _cliente().messages.create(
                model=model, max_tokens=3000,
                messages=[{"role": "user", "content": DAL_PARLATO.format(
                    tema=tema, elenco=elenco)}],
            )
            testo = "".join(b.text for b in r.content if b.type == "text").strip()
            if not testo:
                # Il motivo dello stop e l'unica cosa che distingue "il
                # modello non ha risposto" da "l'ho tagliato io": senza,
                # si ricomincia a indovinare.
                print(f"      ⚠️ Scelta dal parlato: risposta vuota "
                      f"(stop_reason={r.stop_reason})")
                return None
            if "NESSUN" in testo.upper():
                print("      ▶️ Nessuna riga pronunciata regge da sola: "
                      "tengo il banner scritto")
                return None
            numeri = re.findall(r"\d+", testo)
            if numeri and 0 <= int(numeri[0]) < len(tratti):
                return tratti[int(numeri[0])]
            print(f"      ⚠️ Scelta dal parlato illeggibile ({testo[:40]!r})")
            return None
        except Exception as e:                  # noqa: BLE001
            print(f"      ⚠️ Scelta dal parlato, tentativo {tentativo}/3 ({e})")
            if tentativo < 3:
                time.sleep(tentativo * 4)
    return None


def dal_parlato(words: list[dict], da: float, a: float, *, tema: str,
                model: str, max_parole: int = MAX_PAROLE,
                gia_usati: frozenset[str] = frozenset()) -> dict | None:
    """La riga del banner, presa dalle parole davvero pronunciate.

    Torna {"testo", "start"} — la frase e il secondo in cui parte — oppure
    None, e allora si tiene il banner scritto e la clip parte dov'era.
    """
    # `gia_usati` sono i banner gia assegnati alle altre clip di questo
    # video. Il 6/09 le clip 3 e 4 sono uscite col banner identico — «perdi
    # la voglia di fare letteralmente tutto» tutte e due — perche le loro
    # finestre si sovrapponevano e la frase migliore era la stessa. Due Reel
    # di fila con lo stesso titolo in cima sembrano un errore, e lo sono.
    tratti = tratti_parlati(words, da, a, max_parole=max_parole,
                            gia_usati=gia_usati)
    if not tratti:
        print("      ⚠️ Nessuna riga pronunciata abbastanza corta da fare banner")
        return None
    return scegli_parlato(tratti, tema=tema, model=model)

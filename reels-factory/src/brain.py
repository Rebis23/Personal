"""Il cervello della pipeline: Claude sceglie i momenti migliori del video
e scrive caption + hashtag per ogni Reel."""

import os
from pathlib import Path

from pydantic import BaseModel, Field

import anthropic

from . import aggancio, prestazioni


class Punteggi(BaseModel):
    """I cinque assi dell'hook, uno per campo invece che in un dizionario.

    Era un dict opzionale, e il modello lo lasciava vuoto senza violare lo
    schema: nei log si leggeva "punteggio 0/15 ()" e la soglia minima non
    filtrava piu niente, restando li a dare una falsa sicurezza. Cinque campi
    obbligatori non si possono saltare."""

    bersaglio: int = Field(ge=0, le=3, description=(
        "Nomina una cosa concreta che il pubblico riconosce (la laurea, i "
        "corsi, le bollette). 0 se parla di concetti astratti."))
    numero: int = Field(ge=0, le=3, description=(
        "Contiene una cifra o una quantita ('il 90%', 'tre anni', '12.000 "
        "euro'). 0 se non ce n'e nessuna."))
    ribaltamento: int = Field(ge=0, le=3, description=(
        "Nega una convinzione diffusa e la sostituisce, forma 'non e X, e Y'."))
    tu: int = Field(ge=0, le=3, description=(
        "Parla direttamente a chi guarda, lo chiama in causa o lo accusa. "
        "0 per le formule impersonali tipo 'si tende a...'."))
    tensione: int = Field(ge=0, le=3, description=(
        "Lascia un buco che si chiude solo continuando a guardare."))

    @property
    def somma(self) -> int:
        return self.bersaglio + self.numero + self.ribaltamento + self.tu + self.tensione

    def __str__(self) -> str:
        return (f"bersaglio={self.bersaglio} numero={self.numero} "
                f"ribaltamento={self.ribaltamento} tu={self.tu} "
                f"tensione={self.tensione}")


class ClipPick(BaseModel):
    start_seconds: float = Field(description="Inizio della clip, in secondi dal principio del video")
    end_seconds: float = Field(description="Fine della clip, in secondi")
    hook: str = Field(description=(
        "Il gancio della clip: max 12 parole, compare come banner sopra la testa "
        "per tutta la durata. DEVE essere una frase COMPLETA e CHIUSA, che si "
        "capisce da sola senza il resto: soggetto e verbo, mai un frammento "
        "preso a meta di un discorso, mai una frase che inizia con 'e', 'ma', "
        "'quindi', 'perché', 'che'. Deve creare uno SCONTRO: contraddire una "
        "convinzione diffusa, mettere due cose in opposizione, dire la cosa "
        "scomoda che nessuno dice. Riprendi le parole che si sentono davvero "
        "nella clip, ripulite: chi legge il banner e poi ascolta deve "
        "riconoscere la stessa frase. Mai un titolo descrittivo, mai un indice "
        "di cio che si dira."
    ))
    hook_pattern: str = Field(description=(
        "Quale schema della libreria hai usato per l'hook (es. 'affermazione "
        "contraria', 'numero + conseguenza', 'errore che stai facendo')."
    ))
    hook_strength: int = Field(description=(
        "Quanto è forte questo hook da 1 a 10, giudicato con severità: 10 = "
        "impossibile non fermarsi, 5 = interessante ma tiepido. Sotto 7 la clip "
        "non vale la pena: scegline un'altra."
    ))
    bersaglio: str = Field(default="", description=(
        "La cosa CONCRETA che l'hook attacca o nomina, e che chi guarda "
        "riconosce subito: 'la laurea', 'la disciplina', 'i corsi di "
        "motivazione'. Stringa vuota se l'hook non nomina niente di concreto — "
        "e allora quasi sempre è un hook debole."
    ))
    punteggi: Punteggi = Field(description=(
        "Voto da 0 a 3 su ognuno dei cinque assi dell'hook. Somma massima 15."
    ))
    caption: str = Field(description="Caption Instagram in italiano: hook forte nella prima riga, 2-4 righe totali, niente hashtag qui")
    hashtags: list[str] = Field(description=(
        "5-8 hashtag in italiano sul TEMA della clip (crescita personale, "
        "abitudini, decisioni...), senza #. È un profilo personale, non "
        "aziendale: mai hashtag di brand, di servizi o promozionali."
    ))
    rationale: str = Field(description="Perché questo momento funziona come Reel (1 frase)")
    movie_query: str = Field(
        default="",
        description=(
            "Se un momento ICONICO di un film famoso rafforza il concetto della clip: "
            "query di ricerca IN INGLESE per trovarlo (battuta o descrizione della "
            "scena, es. 'you can't handle the truth' o 'red pill blue pill choice'). "
            "Solo film celebri che il pubblico riconosce al volo. Stringa vuota se "
            "nessun film calza davvero: meglio niente che una citazione forzata."
        ),
    )
    movie_insert_at_seconds: float = Field(
        default=0.0,
        description=(
            "Momento (secondi assoluti del video, dentro la clip) in cui inserire lo "
            "spezzone del film: il punto in cui il concetto citato viene pronunciato. "
            "0 se movie_query è vuota."
        ),
    )
    punch_at_seconds: float = Field(
        default=0.0,
        description=(
            "COLD OPEN. Secondo assoluto in cui, DENTRO questa clip, viene "
            "pronunciata la frase piu tagliente — quella che da sola fa "
            "fermare lo scroll. Verra estratta e messa in APERTURA del reel, "
            "prima che la clip parta dal suo inizio. Deve trovarsi almeno 6 "
            "secondi dopo start_seconds (se la frase forte e gia la prima "
            "della clip non serve il cold open: metti 0). Metti 0 anche se "
            "nessuna singola frase regge da sola fuori contesto."
        ),
    )
    mood: str = Field(default="", description=(
        "Il carattere sonoro che la clip chiede, UNA di queste parole: "
        "'tensione' (accusa, scomodo, ritmo serrato), 'riflessivo' (lento, "
        "intimo, una verita che si posa), 'spinta' (energia, chiamata "
        "all'azione), 'racconto' (aneddoto, storia). Determina la base "
        "musicale sotto la voce."
    ))
    emphasis_words: list[str] = Field(
        default_factory=list,
        description=(
            "2-5 parole ESATTE pronunciate nella clip (singole parole, come "
            "compaiono nel testo) che portano il peso del messaggio: verranno "
            "enfatizzate visivamente (corsivo) e con un accento sonoro. Scegli "
            "sostantivi/verbi forti, mai articoli o congiunzioni."
        ),
    )


class ClipSelection(BaseModel):
    clips: list[ClipPick]


SYSTEM_PROMPT = """Sei l'editor video di un canale YouTube italiano di marketing. \
Il tuo compito: leggere la trascrizione temporizzata di un video lungo e scegliere \
i momenti che funzionano meglio come Reels Instagram verticali con sottotitoli.

Contesto brand:
{brand_context}

=== LIBRERIA DEGLI HOOK (la parte più importante del lavoro) ===
{hooks_library}
=== fine libreria ===

=== COME SONO COSTRUITI GLI AGGANCI CHE SFONDANO IN QUESTA NICCHIA ===
Questi schemi vengono misurati ogni settimana su video brevi italiani veri
che hanno battuto di almeno tre volte la mediana del proprio canale. Sono
ricavati dai loro TITOLI, che nel formato breve sono l'aggancio: quindi
applicali all'HOOK della clip — la prima frase, quella che decide se
qualcuno resta — non alla didascalia.
{nicchia}
=== fine ===

=== CONTROLLO SECONDARIO: cosa e gia uscito su questo profilo ===
Serve a NON ripetersi e a non riproporre un taglio gia morto. Non e il
modello da imitare: dieci Reel di un profilo solo non insegnano cosa
funziona, dicono solo cosa e gia stato provato qui.
{storico}
=== fine ===

I CINQUE ASSI. Un hook fa views quando porta a casa piu assi possibile:
- BERSAGLIO: nomina una cosa concreta che il pubblico riconosce e la attacca
  (la laurea, la disciplina, i corsi). Gli aforismi su concetti astratti — la
  vita, la paura, il desiderio — sono i primi a morire.
- NUMERO: una cifra dentro l'hook ("il 95%", "tre anni", "12.000 euro").
- RIBALTAMENTO: nega una convinzione e la sostituisce. "Non è X, è Y".
- TU: parla a chi guarda, lo chiama in causa, lo accusa. Non "si tende a...",
  ma "tu lo fai".
- TENSIONE: lascia un buco che si chiude solo continuando a guardare.
Compila `punteggi` con un voto 0-3 per asse. Un hook che sta sotto 7 di somma
non merita di essere montato, per quanto bello sia il contenuto attorno.

METODO DI LAVORO — segui questo ordine:
1. Leggi tutta la trascrizione e individua 12-15 momenti potenzialmente forti.
   Sii generoso in questa fase: si scarta dopo, non adesso.
2. Per ognuno scrivi l'hook migliore che quel passaggio permette, e assegnagli
   i cinque punteggi. Un momento vale quanto il miglior hook che ne puoi
   ricavare, non quanto e interessante il ragionamento.
3. TORNEO: metti in fila tutti i candidati per somma dei punteggi e tieni solo
   i {n_clips} in cima. Guarda lo storico qui sopra: se uno dei tuoi candidati
   somiglia a un hook che e andato MALE, scartalo anche se ti piace. Se somiglia
   a uno andato bene, e un buon segno ma non basta: non ripetere lo stesso
   hook due volte.
4. Se un momento è interessante ma l'hook è tiepido, cerca dentro lo stesso
   passaggio una frase più tagliente su cui far partire la clip.
4. Ogni clip deve APRIRE sull'hook: se la frase forte arriva dopo dieci secondi di \
premessa, sposta start_seconds in avanti e parti da lì.
5. CONFINI PULITI: start_seconds deve cadere sull'inizio di una frase e \
end_seconds sulla fine di una frase. Mai in mezzo a un periodo. Usa i marcatori \
[mm:ss] e la punteggiatura della trascrizione per trovarli.
6. COLD OPEN: se dentro la clip c'è una frase piu tagliente di quella iniziale, \
indicala in punch_at_seconds. Verra estratta e montata PRIMA dell'inizio della \
clip, come un'apertura a freddo: si sente la frase forte, stacco, e riparte il \
discorso dal principio. Serve solo quando la frase regge da sola: se toglierla \
dal contesto la rende incomprensibile, metti 0.

Regole per la selezione:
- Ogni clip deve reggersi DA SOLA: chi la guarda non ha visto il resto del video.
- Deve iniziare su una frase di aggancio (hook) e chiudersi su una frase completa: \
mai troncare un ragionamento a metà.
- Cerca: affermazioni forti o contrarian, numeri e dati concreti, storie di clienti, \
demolizione di miti, momenti di verità diretta.
- Evita: saluti iniziali, call-to-action al canale, riferimenti ad altri momenti del \
video ("come dicevo prima", "lo vediamo dopo"), spiegazioni che richiedono contesto.
- Le clip NON devono sovrapporsi tra loro e devono usare schemi di hook DIVERSI \
tra loro: non tre affermazioni contrarie di fila.
- VINCOLO RIGIDO sulla durata: ogni clip deve durare tra {min_s} e {max_s} secondi. \
Una clip più lunga di {max_s}s verrà troncata a {max_s}s: scegli tu il taglio giusto \
piuttosto che farlo fare a una forbice cieca.
- I marcatori [mm:ss] nella trascrizione indicano il tempo: usali per stimare \
start_seconds e end_seconds con precisione.

Il campo `hook` finisce a schermo come banner sopra la testa di chi parla: deve \
essere leggibile in un secondo, massimo 12 parole, senza virgolette.

Per le caption: prima riga = hook che ferma lo scroll, poi 1-3 righe che aggiungono \
valore o creano curiosità verso il video completo. Tono diretto, zero fuffa, \
mai da guru. Scrivi in italiano.

Hashtag: è il profilo PERSONALE di Lorenzo, non un account aziendale. Usa hashtag \
sul tema di cui si parla nella clip (crescita personale, abitudini, decisioni, \
psicologia, lavoro...). MAI hashtag di brand, di agenzie, di servizi o promozionali.

Spezzoni di film (movie_query): se — e solo se — il concetto della clip richiama \
un momento iconico di un film celebre (Matrix, Il Padrino, The Wolf of Wall Street, \
A Few Good Men, Rocky...), indica la query inglese per trovarlo e il secondo esatto \
in cui inserirlo. Lo spezzone dura 2-6 secondi e copre il video del parlato mentre \
l'audio continua. Usalo al massimo in 1-2 clip su 3, mai forzato."""


HOOKS_FILE = Path(__file__).resolve().parent.parent / "hooks.md"
NICCHIA_FILE = Path(__file__).resolve().parent.parent / "nicchia.md"
# Il ripiego: gli Shorts YouTube. Si legge solo se la scuola sui Reel manca.
NICCHIA_RIPIEGO = Path(__file__).resolve().parent.parent / "nicchia-shorts.md"


def load_hooks_library() -> str:
    """La libreria degli hook (hooks.md): modificabile senza toccare il codice."""
    try:
        return HOOKS_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "(libreria non disponibile: giudica gli hook con il tuo criterio)"


def load_nicchia() -> str:
    """Gli schemi degli agganci che sfondano nella nicchia.

    Prima si cerca nicchia.md, che dal 03/09 e ricavato dai REEL veri e
    quindi dal primo secondo vero: inquadratura, testo a schermo, audio.
    Se manca si ripiega su nicchia-shorts.md, dedotto dai soli titoli degli
    Shorts YouTube — meno buono ma gratuito e sempre aggiornato."""
    for f in (NICCHIA_FILE, NICCHIA_RIPIEGO):
        try:
            testo = f.read_text(encoding="utf-8").strip()
            break
        except OSError:
            continue
    else:
        return ""
    # Finche il file e solo la struttura vuota, non vale la pena occupare
    # spazio nel prompt con dei titoli senza contenuto.
    return "" if "STATO: DA COMPILARE" in testo else testo


def select_clips(
    timed_transcript: str,
    video_title: str,
    *,
    model: str,
    brand_context: str,
    clips_per_video: int,
    min_seconds: int,
    max_seconds: int,
) -> list[ClipPick]:
    # .strip(): i segreti incollati nei GitHub Secrets possono contenere
    # un a-capo finale, che renderebbe illegale l'header HTTP
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

    system = SYSTEM_PROMPT.format(
        brand_context=brand_context.strip(),
        hooks_library=load_hooks_library(),
        nicchia=load_nicchia() or '(scuola non ancora compilata: usa i criteri generali)',
        storico=prestazioni.leggi_scheda(),
        n_clips=clips_per_video,
        min_s=min_seconds,
        max_s=max_seconds,
    )
    user = (
        f"Titolo del video: {video_title}\n\n"
        f"Trascrizione temporizzata:\n{timed_transcript}\n\n"
        f"Seleziona le {clips_per_video} clip migliori secondo le regole. "
        f"Ricorda: prima individuane 8-10, poi tieni solo quelle con l'hook più forte."
    )

    response = client.messages.parse(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=ClipSelection,
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude ha rifiutato la richiesta (stop_reason=refusal)")

    selection = response.parsed_output
    if selection is None:
        raise RuntimeError("Risposta di Claude non parsabile secondo lo schema")

    # Durate fuori dai limiti: le clip troppo lunghe si ACCORCIANO alla
    # durata massima (mai buttate — è successo che Claude proponesse tagli
    # lunghi e la coda restasse vuota); solo le inutilizzabili si scartano
    usable = []
    for c in sorted(selection.clips, key=lambda c: c.start_seconds):
        dur = c.end_seconds - c.start_seconds
        if dur < max(8, min_seconds - 5):
            continue
        if dur > max_seconds:
            c.end_seconds = c.start_seconds + max_seconds
        usable.append(c)

    # LA PROVA A FREDDO. Prima del torneo, ogni hook viene letto da chi non ha
    # visto il video. E qui che cadono gli aforismi: "Il vantaggio iniziale e
    # sempre dello stupido" per chi ha letto la trascrizione e una conclusione
    # brillante, per chi scorre Instagram e una frase che non vuol dire niente.
    # Lorenzo l'ha detto con parole sue il 29/08: l'hook e fuori contesto.
    esiti = prova_a_freddo([c.hook for c in usable], model=model)
    if esiti:
        bocciati = [(i, c.hook, esiti[i][1], c.start_seconds, c.end_seconds)
                    for i, c in enumerate(usable)
                    if i in esiti and not esiti[i][0]]
        for _, hook, motivo, _, _ in bocciati:
            print(f"   ❄️ hook bocciato «{hook[:52]}» — {motivo}")

        # Il momento puo essere ottimo e l'hook no: si riscrive solo la frase
        # di apertura, la clip resta dov'e.
        nuovi = riscrivi_hooks(bocciati, timed_transcript, model=model)
        for i, hook in nuovi.items():
            print(f"   ✍️ riscritto → «{hook[:60]}»")
            usable[i].hook = hook

        # Il rifacimento va ricontrollato con lo stesso metro, altrimenti la
        # seconda stesura passa solo perche e la seconda.
        if nuovi:
            ricontrollo = prova_a_freddo([usable[i].hook for i in sorted(nuovi)],
                                         model=model)
            for pos, i in enumerate(sorted(nuovi)):
                if ricontrollo and not ricontrollo.get(pos, (True, ""))[0]:
                    nuovi.pop(i, None)
                    print(f"   ❄️ anche la riscrittura cade: «{usable[i].hook[:48]}»")

        salvati = set(nuovi)
        usable = [c for i, c in enumerate(usable)
                  if i in salvati or i not in esiti or esiti[i][0]]

    # A parità di clip disponibili si preferiscono gli hook più forti
    strong = [c for c in usable if c.hook_strength >= 7]
    picked = (strong if len(strong) >= clips_per_video else usable)[:clips_per_video]

    # UNA RIGA SOLA. Lorenzo, guardando il Reel del 3/09: "l'hook scritto e
    # lunghissimo e non attrae, perche quando ti trovi una sbrodolata di testo
    # del genere e chiaro che non ti fermerai a guardare". Il prompt diceva
    # gia "max 12 parole" e ne sono usciti da 27: qui si taglia per davvero, e
    # si taglia soltanto — ogni parola del banner resta una parola che nel
    # video si sente.
    corti = aggancio.accorcia({i: c.hook for i, c in enumerate(picked)}, model=model)
    for i, breve in corti.items():
        print(f"   ✂️ aggancio accorciato ({aggancio.quante(picked[i].hook)} → "
              f"{aggancio.quante(breve)} parole) → «{breve}»")
        picked[i].hook = breve

    for c in picked:
        print(f"      hook {c.hook_strength}/10 [{c.hook_pattern}] «{c.hook}»")
    if len(strong) < len(usable):
        print(f"      ({len(usable) - len(strong)} clip con hook debole scartate o retrocesse)")
    return sorted(picked, key=lambda c: c.start_seconds)


# --------------------------------------------------------- LA PROVA A FREDDO ---

LETTORE_FREDDO = """Sei una persona che sta scorrendo Instagram. Non sai niente \
del video da cui viene questa frase, non conosci chi parla, non hai visto \
nient'altro. Ti arriva questa frase come primissima cosa, sopra il video.

Per ognuna rispondi con una riga sola, in questo formato esatto:
<numero>|<REGGE o CADE>|<motivo in massimo otto parole>

CADE se vale anche una sola di queste:
- Non si capisce senza sapere cosa e stato detto prima. Nomina un "questo", un \
"lo", un confronto o una conclusione di cui manca il termine di paragone.
- E un aforisma su un concetto astratto — la vita, l'ansia, il desiderio, \
l'intelligenza, il tempo — del tipo che si legge sotto una foto di un tramonto. \
Suona saggio e non attacca niente di concreto.
- E un proverbio o una massima: vera per tutti, quindi per nessuno.
- Non ti fa venire voglia di sapere come va a finire.

REGGE se nomina una cosa concreta che riconosci, o ti chiama in causa, o \
contraddice qualcosa che dai per scontato, e si capisce da sola.

Sii severo: se esiti, e CADE. Nessun preambolo, solo le righe."""


def prova_a_freddo(hooks: list[str], *, model: str) -> dict[int, tuple[bool, str]]:
    """Fa leggere gli hook a qualcuno che non ha visto il video.

    Serve perche l'autovalutazione non basta. Il modello che sceglie la clip
    ha appena letto tutta la trascrizione: per lui "Il vantaggio iniziale e
    sempre dello stupido" ha un senso pieno, e si da tre punti su tre. Chi
    scorre Instagram quella premessa non ce l'ha, e legge un non sequitur.

    L'unico modo onesto di misurare "regge da solo" e chiederlo a qualcuno
    che davvero non sa niente: stessa domanda, contesto azzerato."""
    if not hooks:
        return {}
    elenco = "\n".join(f"{i}. {h}" for i, h in enumerate(hooks))
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
        r = client.messages.create(
            model=model, max_tokens=4000, system=LETTORE_FREDDO,
            messages=[{"role": "user", "content": elenco}],
        )
        testo = "".join(b.text for b in r.content
                        if getattr(b, "type", "") == "text")
    except Exception as e:                      # noqa: BLE001
        print(f"   ⚠️ prova a freddo non riuscita ({e}): tengo tutti gli hook")
        return {}
    esiti: dict[int, tuple[bool, str]] = {}
    for riga in testo.splitlines():
        pezzi = [p.strip() for p in riga.split("|")]
        if len(pezzi) < 2 or not pezzi[0].rstrip(".").isdigit():
            continue
        esiti[int(pezzi[0].rstrip("."))] = (
            pezzi[1].upper().startswith("REGGE"),
            pezzi[2] if len(pezzi) > 2 else "",
        )
    return esiti


RISCRITTURA = """Sei l'editor video. Alcune clip hanno un momento buono ma un \
hook che non regge: chi scorre Instagram non ha visto il video, e quella frase \
gli arriva come un aforisma o come una conclusione senza premessa.

Per ognuna ti do: il minuto della clip, l'hook bocciato, il motivo, e la \
trascrizione del video. Riscrivi SOLO l'hook, pescando dentro quel pezzo di \
trascrizione.

Il nuovo hook deve:
- reggersi da solo, senza sapere niente di cio che viene prima;
- nominare una cosa concreta e riconoscibile (una laurea, un preventivo, un \
cliente, delle bollette, un numero) invece di un concetto astratto;
- parlare a chi guarda — "tu", "hai", "stai" — o contraddire una cosa che da \
per scontata;
- restare fedele a cio che viene detto davvero nella clip. Non promettere \
qualcosa che il video non mantiene: se il passaggio non permette un hook \
concreto, scrivi SALTA e basta.

Una riga per clip, formato esatto:
<numero>|<nuovo hook oppure SALTA>

Niente virgolette, niente spiegazioni."""


def riscrivi_hooks(falliti: list[tuple[int, str, str, float, float]],
                   timed_transcript: str, *, model: str) -> dict[int, str]:
    """Seconda possibilita per le clip il cui momento e buono e l'hook no.

    Lorenzo, il 29/08: «il reel che hai fatto spacca ma l'hook e sbagliato e
    fuori contesto». Sono due cose separate, e finora venivano buttate
    insieme: bastava che l'hook cadesse e spariva anche il momento. Qui il
    taglio resta dov'e ed è solo la frase di apertura a essere rifatta."""
    if not falliti:
        return {}
    righe = [f"{i}| minuto {inizio:.0f}-{fine:.0f}s | bocciato: «{hook}» | perche: {motivo}"
             for i, hook, motivo, inizio, fine in falliti]
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
        r = client.messages.create(
            model=model, max_tokens=4000, system=RISCRITTURA,
            messages=[{"role": "user", "content":
                       "CLIP DA RISCRIVERE:\n" + "\n".join(righe)
                       + f"\n\nTRASCRIZIONE:\n{timed_transcript}"}],
        )
        testo = "".join(b.text for b in r.content
                        if getattr(b, "type", "") == "text")
    except Exception as e:                      # noqa: BLE001
        print(f"   ⚠️ riscrittura non riuscita ({e})")
        return {}
    nuovi: dict[int, str] = {}
    for riga in testo.splitlines():
        pezzi = [x.strip() for x in riga.split("|")]
        if len(pezzi) < 2 or not pezzi[0].rstrip(".").isdigit():
            continue
        hook = pezzi[1].strip('"«»')
        if hook and hook.upper() != "SALTA":
            nuovi[int(pezzi[0].rstrip("."))] = hook
    return nuovi

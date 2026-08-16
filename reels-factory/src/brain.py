"""Il cervello della pipeline: Claude sceglie i momenti migliori del video
e scrive caption + hashtag per ogni Reel."""

import os
from pathlib import Path

from pydantic import BaseModel, Field

import anthropic


class ClipPick(BaseModel):
    start_seconds: float = Field(description="Inizio della clip, in secondi dal principio del video")
    end_seconds: float = Field(description="Fine della clip, in secondi")
    hook: str = Field(description=(
        "Il gancio della clip: max 12 parole, compare come banner sopra la testa "
        "per tutta la durata. Deve fermare lo scroll da solo — affermazione "
        "contraria, numero secco, errore da evitare, verità scomoda. Mai un titolo "
        "descrittivo, mai un indice di ciò che si dirà."
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

METODO DI LAVORO — segui questo ordine:
1. Leggi tutta la trascrizione e individua 8-10 momenti potenzialmente forti.
2. Per ognuno chiediti: "se questa frase fosse scritta sopra la testa di chi \
parla, uno smetterebbe di scrollare?". Scarta senza pietà quelli che non superano \
la prova.
3. Tieni SOLO i {n_clips} migliori. Ogni hook deve valere almeno 7/10 secondo la \
libreria qui sopra. Se un momento è interessante ma l'hook è tiepido, cerca dentro \
lo stesso passaggio una frase più tagliente su cui far partire la clip.
4. Ogni clip deve APRIRE sull'hook: se la frase forte arriva dopo dieci secondi di \
premessa, sposta start_seconds in avanti e parti da lì.

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


def load_hooks_library() -> str:
    """La libreria degli hook (hooks.md): modificabile senza toccare il codice."""
    try:
        return HOOKS_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "(libreria non disponibile: giudica gli hook con il tuo criterio)"


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

    # A parità di clip disponibili si preferiscono gli hook più forti, ma non
    # si scarta mai tutto: meglio un hook da 6 che una coda vuota
    strong = [c for c in usable if c.hook_strength >= 7]
    picked = (strong if len(strong) >= clips_per_video else usable)[:clips_per_video]
    for c in picked:
        print(f"      hook {c.hook_strength}/10 [{c.hook_pattern}] «{c.hook}»")
    if len(strong) < len(usable):
        print(f"      ({len(usable) - len(strong)} clip con hook debole scartate o retrocesse)")
    return sorted(picked, key=lambda c: c.start_seconds)

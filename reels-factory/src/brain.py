"""Il cervello della pipeline: Claude sceglie i momenti migliori del video
e scrive caption + hashtag per ogni Reel."""

import os
from pydantic import BaseModel, Field

import anthropic


class ClipPick(BaseModel):
    start_seconds: float = Field(description="Inizio della clip, in secondi dal principio del video")
    end_seconds: float = Field(description="Fine della clip, in secondi")
    hook: str = Field(description="Il gancio della clip in max 8 parole (usato come titolo interno)")
    caption: str = Field(description="Caption Instagram in italiano: hook forte nella prima riga, 2-4 righe totali, niente hashtag qui")
    hashtags: list[str] = Field(description="5-8 hashtag pertinenti in italiano, senza #")
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


class ClipSelection(BaseModel):
    clips: list[ClipPick]


SYSTEM_PROMPT = """Sei l'editor video di un canale YouTube italiano di marketing. \
Il tuo compito: leggere la trascrizione temporizzata di un video lungo e scegliere \
i momenti che funzionano meglio come Reels Instagram verticali con sottotitoli.

Contesto brand:
{brand_context}

Regole per la selezione:
- Ogni clip deve durare tra {min_s} e {max_s} secondi.
- Ogni clip deve reggersi DA SOLA: chi la guarda non ha visto il resto del video.
- Deve iniziare su una frase di aggancio (hook) e chiudersi su una frase completa: \
mai troncare un ragionamento a metà.
- Cerca: affermazioni forti o contrarian, numeri e dati concreti, storie di clienti, \
demolizione di miti, momenti di verità diretta.
- Evita: saluti iniziali, call-to-action al canale, riferimenti ad altri momenti del \
video ("come dicevo prima", "lo vediamo dopo"), spiegazioni che richiedono contesto.
- Le clip NON devono sovrapporsi tra loro.
- I marcatori [mm:ss] nella trascrizione indicano il tempo: usali per stimare \
start_seconds e end_seconds con precisione.

Per le caption: prima riga = hook che ferma lo scroll, poi 1-3 righe che aggiungono \
valore o creano curiosità verso il video completo. Tono diretto, zero fuffa, \
mai da guru. Scrivi in italiano.

Spezzoni di film (movie_query): se — e solo se — il concetto della clip richiama \
un momento iconico di un film celebre (Matrix, Il Padrino, The Wolf of Wall Street, \
A Few Good Men, Rocky...), indica la query inglese per trovarlo e il secondo esatto \
in cui inserirlo. Lo spezzone dura 2-6 secondi e copre il video del parlato mentre \
l'audio continua. Usalo al massimo in 1-2 clip su 3, mai forzato."""


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
        min_s=min_seconds,
        max_s=max_seconds,
    )
    user = (
        f"Titolo del video: {video_title}\n\n"
        f"Trascrizione temporizzata:\n{timed_transcript}\n\n"
        f"Seleziona le {clips_per_video} clip migliori secondo le regole."
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

    # Filtro di sicurezza sulle durate, poi ordino per posizione nel video
    valid = [
        c for c in selection.clips
        if (max_seconds + 10) >= (c.end_seconds - c.start_seconds) >= (min_seconds - 5)
    ]
    valid.sort(key=lambda c: c.start_seconds)
    return valid[:clips_per_video]

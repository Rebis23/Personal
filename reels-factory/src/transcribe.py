"""Trascrizione del video: Scribe di ElevenLabs, con Whisper come rete.

Dal 23/09 la strada principale e Scribe (vedi scribe.py). Whisper resta
installato e resta la rete di sicurezza: se la chiave manca, se ElevenLabs
risponde male o se la rete cade, la lavorazione prosegue con una
trascrizione peggiore invece di fermarsi. Un Reel mediocre esce; un Reel
che non esiste no.

Sostituisce i sottotitoli automatici di YouTube: timing parola-per-parola
(essenziale per il karaoke) e nessuna attesa che YouTube li generi.
"""

from pathlib import Path

from . import scribe

# Whisper e Scribe chiamano le lingue in modo diverso: "it" contro "ita".
# Tradurre qui evita di dover cambiare tutti i punti che chiamano.
ISO3 = {"it": "ita", "en": "eng", "es": "spa", "fr": "fra", "de": "deu"}


def transcribe_words(video_path: Path, model_size: str = "small",
                     language: str = "it", *,
                     scribe_model: str = scribe.MODELLO,
                     usa_scribe: bool = True) -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, stessa forma di parse_json3."""
    if usa_scribe and scribe.disponibile():
        parole = scribe.trascrivi(video_path,
                                  language=ISO3.get(language, language),
                                  model=scribe_model)
        if parole:
            return parole
        print("  ↩️ Scribe non ha funzionato: passo a Whisper")

    return _con_whisper(video_path, model_size, language)


def _con_whisper(video_path: Path, model_size: str, language: str) -> list[dict]:
    from faster_whisper import WhisperModel  # import pigro: pacchetto pesante

    print(f"  🎙️ Trascrizione con Whisper ({model_size}, {language})...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    words: list[dict] = []
    for segment in segments:
        for w in segment.words or []:
            text = w.word.strip()
            if text:
                words.append({"word": text, "start": round(w.start, 3), "end": round(w.end, 3)})
    print(f"  🎙️ Trascrizione completata: {len(words)} parole")
    return words

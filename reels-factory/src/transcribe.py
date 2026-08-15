"""Trascrizione del video con faster-whisper (in locale sul runner, gratis).

Sostituisce i sottotitoli automatici di YouTube: timing parola-per-parola
più preciso (essenziale per il karaoke) e nessuna attesa che YouTube li
generi — il video è processabile appena pubblicato.
"""

from pathlib import Path


def transcribe_words(video_path: Path, model_size: str = "small",
                     language: str = "it") -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, stessa forma di transcript.parse_json3."""
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

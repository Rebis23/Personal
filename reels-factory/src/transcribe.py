"""Trascrizione del video: Whisper grande in casa, Scribe se non punteggia.

L'ordine e cambiato tre volte, e ogni volta per un motivo misurato.

Fino al 23/09 era Whisper `small` sul runner. Gratis, e con un difetto: la
punteggiatura andava e veniva. Nel tratto del Reel dell'11 settembre non
c'era UN segno (94 parole, zero punti, zero virgole), e senza segni
sentences() spezzava sulle pause di 0,75 secondi — cioe sui respiri. Da li i
Reel chiusi a meta frase.

Attenzione a non raccontarselo male, come ho fatto io il 28/09 per mezz'ora:
`small` NON e un modello che non punteggia. Misurato su 68 secondi di audio
vero fa 10,6 punti fermi al minuto. Il difetto e l'intermittenza — "smette di
mettere la punteggiatura per minuti interi", era gia scritto nel config di
agosto — e un tratto muto in mezzo a un video puntato bene basta a rovinare
la clip che ci casca dentro.

Dal 23/09 la strada principale e diventata Scribe di ElevenLabs, che
punteggia. Ha risolto i tagli, e costa: 330 crediti al minuto di audio,
~5.800 crediti per un video da 17 minuti, ~$22 al mese di abbonamento.

Dal 28/09 il repo e pubblico e i minuti del runner sono gratis e illimitati.
Quello che rendeva attraente Scribe — la velocita, perche i minuti si
pagavano — non e piu una valuta. Quindi si riprova Whisper, ma col modello
GRANDE: la punteggiatura mancava al modello piccolo, non a Whisper.

E qui la parte che conta: nessuno garantisce che il modello grande punteggi
in modo continuo. Ne la documentazione di faster-whisper ne quella di Groq
promettono niente sulla punteggiatura. Quindi non si spera — si conta.
Whisper large gira gratis, poi punteggiatura.py guarda due cose: quanti segni
ci sono in tutto, e quanto e lungo il tratto peggiore senza nessun segno. La
seconda e quella che serve davvero: una media buona puo nascondere un buco di
due minuti, e la clip che ci finisce dentro viene tagliata sul respiro come
l'11 settembre. Solo se una delle due misure e fuori si paga Scribe.

Misurato il 28/09 su 68s di audio vero: large-v3 fa 11,5 punti/min con un
vuoto massimo di 13,0s; small 10,6 e 14,5s. Il limite del vuoto e 40s, cioe
tre volte piu largo. Su quel pezzo il gratis basta.

Se cadono tutte e due resta comunque la trascrizione di Whisper: un Reel
tagliato male esce, un Reel che non esiste no.

Sostituisce i sottotitoli automatici di YouTube: timing parola-per-parola
(essenziale per il karaoke) e nessuna attesa che YouTube li generi.
"""

from pathlib import Path

from . import punteggiatura, scribe

# Whisper e Scribe chiamano le lingue in modo diverso: "it" contro "ita".
# Tradurre qui evita di dover cambiare tutti i punti che chiamano.
ISO3 = {"it": "ita", "en": "eng", "es": "spa", "fr": "fra", "de": "deu"}


def transcribe_words(video_path: Path, model_size: str = "large-v3",
                     language: str = "it", *,
                     scribe_model: str = scribe.MODELLO,
                     usa_scribe: bool = True) -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, stessa forma di parse_json3."""
    parole = _con_whisper(video_path, model_size, language)

    if parole and punteggiatura.abbastanza(parole):
        print(f"  ✅ Punteggiatura sufficiente "
              f"({punteggiatura.densita(parole):.1f} punti/min): "
              f"non servono servizi a pagamento")
        return parole

    if parole:
        print(f"  ⚠️ Punteggiatura troppo scarsa "
              f"({punteggiatura.densita(parole):.1f} punti/min, "
              f"serve {punteggiatura.SOGLIA}): senza segni si taglierebbe "
              f"sui respiri")

    if usa_scribe and scribe.disponibile():
        print("  💳 Passo a Scribe, che punteggia")
        da_scribe = scribe.trascrivi(video_path,
                                     language=ISO3.get(language, language),
                                     model=scribe_model)
        if da_scribe:
            return da_scribe
        print("  ↩️ Scribe non ha funzionato")

    if parole:
        print("  ⚠️ Tengo la trascrizione di Whisper cosi com'e: i tagli "
              "saranno meno precisi, ma il Reel esce")
    return parole


def _con_whisper(video_path: Path, model_size: str, language: str) -> list[dict]:
    from faster_whisper import WhisperModel  # import pigro: pacchetto pesante

    print(f"  🎙️ Trascrizione con Whisper ({model_size}, {language})...")
    try:
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
                    words.append({"word": text,
                                  "start": round(w.start, 3),
                                  "end": round(w.end, 3)})
    except Exception as e:                       # noqa: BLE001
        # Il modello grande pesa ~3 GB: se il disco del runner non ce la fa,
        # o il download cade, non si porta giu tutta la lavorazione — c'e
        # ancora Scribe dopo.
        print(f"  ⚠️ Whisper non ha funzionato: {e}")
        return []

    print(f"  🎙️ Trascrizione completata: {len(words)} parole")
    return words

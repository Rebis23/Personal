"""Trascrizione con Scribe di ElevenLabs.

Lorenzo, 21/09: "voglio che per le prossime trascrizioni ed editing usi
eleven labs. Sempre."

Perche conta piu di quanto sembri. Whisper small, che girava sul runner,
sbaglia in un modo che si propaga: stacca gli apostrofi («l 'effetto»),
inventa parole («cegliele» per «sceglierlo»), e soprattutto smette di
mettere la punteggiatura per minuti interi. Quell'ultima cosa e la causa
di meta dei guasti riparati a settembre — il finale che si spegneva a
meta frase, la clip che partiva dal punto sbagliato — perche il codice
usava la punteggiatura per capire dove finiscono le frasi, e quando non
c'e ripiega sulle pause, cioe sul respiro.

Una trascrizione migliore non ripara quei difetti a valle: li toglie a
monte.

Due scelte di costruzione:

· Si manda SOLO L'AUDIO, non il video. ffmpeg tira fuori una traccia mono
  a 16 kHz: un video da venticinque minuti passa da centinaia di megabyte
  a cinque o sei. La trascrizione e identica e l'invio dura secondi.

· Se qualcosa va storto si torna None, non si solleva. Chi chiama ripiega
  su Whisper e la lavorazione continua: una trascrizione peggiore e molto
  meglio di un video che non esce.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests

URL = "https://api.elevenlabs.io/v1/speech-to-text"

# L'elenco dei modelli non e enumerato nella documentazione: l'esempio
# ufficiale usa scribe_v2. Sta in config.yaml cosi si cambia senza toccare
# il codice, e se il nome fosse sbagliato il corpo dell'errore finisce nel
# log invece di sparire in un fallback muto.
MODELLO = "scribe_v2"


def disponibile() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())


def _solo_audio(video: Path, dove: Path) -> Path | None:
    """La traccia audio, mono e leggera. Il video non serve a trascrivere."""
    fuori = dove / "audio.mp3"
    esito = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-b:a", "32k", str(fuori)],
        capture_output=True, text=True, timeout=900,
    )
    if esito.returncode != 0 or not fuori.is_file():
        print(f"  ⚠️ Non riesco a estrarre l'audio: {esito.stderr[-200:]}")
        return None
    return fuori


def _parole(dati: dict) -> list[dict]:
    """Da come risponde ElevenLabs a come le vuole la fabbrica.

    ATTENZIONE AL CAMPO `type`. L'elenco non contiene solo parole: ci sono
    anche gli spazi («spacing») e i rumori riconosciuti («audio_event»).
    Se entrassero nella lista diventerebbero parole finte con un loro
    tempo, e finirebbero nei sottotitoli e nei conteggi.
    """
    fuori = []
    for w in dati.get("words") or []:
        if w.get("type") != "word":
            continue
        testo = (w.get("text") or "").strip()
        if not testo:
            continue
        fuori.append({"word": testo,
                      "start": round(float(w["start"]), 3),
                      "end": round(float(w["end"]), 3)})
    return fuori


def trascrivi(video: Path, *, language: str = "ita",
              model: str = MODELLO) -> list[dict] | None:
    """[{word, start, end}] dalla voce, o None se non si puo fare."""
    if not disponibile():
        return None

    with tempfile.TemporaryDirectory() as tmp:
        audio = _solo_audio(video, Path(tmp))
        if audio is None:
            return None
        peso = audio.stat().st_size / 1_048_576
        print(f"  🎙️ Trascrizione con Scribe ({model}, {language}) — "
              f"{peso:.1f} MB di audio")

        for tentativo in (1, 2, 3):
            try:
                with audio.open("rb") as f:
                    r = requests.post(
                        URL,
                        headers={"xi-api-key":
                                 os.environ["ELEVENLABS_API_KEY"].strip()},
                        data={"model_id": model,
                              "language_code": language,
                              "timestamps_granularity": "word",
                              "diarize": "false"},
                        files={"file": (audio.name, f, "audio/mpeg")},
                        timeout=900,
                    )
            except requests.RequestException as e:
                print(f"  ⚠️ Scribe, tentativo {tentativo}/3: {e}")
                if tentativo < 3:
                    time.sleep(tentativo * 5)
                continue

            if r.status_code == 200:
                parole = _parole(r.json())
                if not parole:
                    print("  ⚠️ Scribe non ha restituito parole")
                    return None
                print(f"  🎙️ Trascrizione completata: {len(parole)} parole")
                return parole

            # IL CORPO DELL'ERRORE SI STAMPA SEMPRE. Un 401 (chiave
            # sbagliata o senza il permesso Speech to Text) e un 422
            # (model_id inesistente) si distinguono solo leggendolo, e
            # senza si passerebbe a Whisper senza sapere perche.
            print(f"  ⚠️ Scribe ha risposto {r.status_code}: {r.text[:300]}")
            if r.status_code < 500:
                return None                 # colpa nostra: riprovare e inutile
            if tentativo < 3:
                time.sleep(tentativo * 5)
    return None

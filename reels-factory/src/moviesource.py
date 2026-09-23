"""Spezzoni di film GRATIS: ricerca della scena sui canali movie-clips di
YouTube, download via Apify (già usato per i video del canale), individuazione
del momento esatto della battuta con Whisper.

Serve solo il secret YOUTUBE_API_KEY: chiave gratuita della YouTube Data API
(Google Cloud Console → APIs → YouTube Data API v3 → credenziali). La quota
gratuita copre ~100 ricerche al giorno: qui ne servono 1-3.

Alternativa premium senza questo modulo: clip.cafe (vedi clipcafe.py).
"""

import os
import re
from pathlib import Path

import requests

from . import apify

SEARCH_API = "https://www.googleapis.com/youtube/v3/search"
# Canali affidabili di scene di film: Movieclips e simili
PREFERRED = re.compile(r"movieclips|moviescenes|screen\s?bites|fandango", re.I)


def _key() -> str:
    return os.environ.get("YOUTUBE_API_KEY", "").strip()


def is_configured() -> bool:
    return bool(_key())


def search_scene(query: str) -> str | None:
    """Cerca la scena su YouTube. Ritorna il video_id migliore o None."""
    try:
        resp = requests.get(SEARCH_API, params={
            "key": _key(),
            "part": "snippet",
            "q": f"{query} movie scene",
            "type": "video",
            "videoDuration": "short",   # < 4 minuti
            "maxResults": 8,
            "safeSearch": "none",
        }, timeout=60)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return None
        # Preferisci i canali di movie clips ufficiali, poi il primo risultato
        for it in items:
            if PREFERRED.search(it["snippet"]["channelTitle"]):
                return it["id"]["videoId"]
        return items[0]["id"]["videoId"]
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"  ⚠️ Ricerca YouTube fallita: {e}")
        return None


def _match_offset(words: list[dict], query: str, span: float) -> float | None:
    """Trova l'inizio della finestra di `span` secondi che meglio copre le
    parole della query (match testuale scorrevole sulla trascrizione)."""
    tokens = {t for t in re.findall(r"[a-z']+", query.lower()) if len(t) > 2}
    if not tokens or not words:
        return None
    best_score, best_start = 0, None
    for i, w in enumerate(words):
        t0 = w["start"]
        score = sum(
            1 for x in words[i:]
            if x["start"] < t0 + span
            and re.sub(r"[^a-z']", "", x["word"].lower()) in tokens
        )
        if score > best_score:
            best_score, best_start = score, t0
    # Servono almeno 2 parole della battuta nella finestra per fidarsi
    return best_start if best_score >= 2 else None


def find_clip(query: str, workdir: Path, *, max_seconds: int = 5) -> dict | None:
    """Cerca e scarica lo spezzone. Ritorna {path, src_offset, duration} o None.

    Mai un'eccezione: lo spezzone è un di più, non deve bloccare la clip.
    """
    try:
        vid = search_scene(query)
        if not vid:
            print("  🎞️ YouTube: nessuna scena trovata")
            return None
        print(f"  🎞️ Scena candidata: https://youtu.be/{vid} — scarico via Apify...")
        path = apify.download_video(vid, workdir / "movie", quality="720p")
        if path is None:
            return None

        # Trova il momento esatto della battuta nella scena
        from . import transcribe
        offset = None
        try:
            # usa_scribe=False: questo e uno spezzone di film usa e getta,
            # spesso scartato. Non ha senso pagarne la trascrizione.
            words = transcribe.transcribe_words(path, model_size="small",
                                                language="en",
                                                usa_scribe=False)
            offset = _match_offset(words, query, float(max_seconds))
        except Exception as e:  # noqa: BLE001 — il fallback è comunque valido
            print(f"  ⚠️ Trascrizione scena fallita ({e}), uso il centro")
        if offset is None:
            # Fallback: il cuore della scena (mai i primi secondi, spesso loghi)
            offset = 8.0
        else:
            # Un attimo di respiro prima della battuta
            offset = max(0.0, offset - 0.4)
        print(f"  🎞️ Spezzone: da {offset:.1f}s per {max_seconds}s")
        return {"path": path, "src_offset": offset, "duration": float(max_seconds)}
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ Spezzone YouTube fallito: {e}")
        return None

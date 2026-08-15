"""Spezzoni di film pertinenti via Clip.cafe (https://clip.cafe).

Claude suggerisce per ogni clip un momento cinematografico famoso in tema;
qui lo cerchiamo nel database Clip.cafe (ricerca semantica nelle battute)
e scarichiamo il file video da sovraimporre come cutaway.

Richiede l'abbonamento PRO di Clip.cafe e il secret CLIPCAFE_API_KEY.
Se la chiave manca, la pipeline funziona normalmente senza spezzoni.
"""

import os
from pathlib import Path

import requests

API = "https://api.clip.cafe/"


def _key() -> str:
    return os.environ.get("CLIPCAFE_API_KEY", "").strip()


def is_configured() -> bool:
    return bool(_key())


def find_clip(query: str, *, min_seconds: int = 2, max_seconds: int = 8) -> dict | None:
    """Cerca lo spezzone più adatto: {slug, download_key, duration, title, movie}.

    Ritorna None se non c'è nulla di utilizzabile (mai un'eccezione:
    lo spezzone è un di più, non deve bloccare la clip).
    """
    try:
        resp = requests.get(API, params={
            "api_key": _key(),
            "captions": query,
            "duration": f"{min_seconds}-{max_seconds}",
            "size": 5,
        }, timeout=60)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        for h in hits:
            src = h.get("_source", {})
            slug = src.get("slug", "")
            # Il nome del campo con la chiave di download non è documentato
            # in modo univoco: proviamo i nomi plausibili
            dl_key = (src.get("download") or src.get("download_key")
                      or src.get("downloadKey") or src.get("key") or "")
            duration = float(src.get("duration") or 0)
            if slug and dl_key and duration:
                return {
                    "slug": slug,
                    "download_key": dl_key,
                    "duration": duration,
                    "title": src.get("title", ""),
                    "movie": src.get("movie_title", ""),
                }
        if hits:
            known = sorted(hits[0].get("_source", {}).keys())
            print(f"  🎞️ Clip.cafe: risultati senza chiave di download; campi: {known}")
        return None
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"  ⚠️ Clip.cafe ricerca fallita: {e}")
        return None


def download(found: dict, out_path: Path) -> Path | None:
    """Scarica lo spezzone trovato da find_clip. None se fallisce."""
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(API, params={
            "api_key": _key(),
            "slug": found["slug"],
            "key": found["download_key"],
        }, stream=True, timeout=120) as r:
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "json" in ctype or "html" in ctype:
                print(f"  ⚠️ Clip.cafe download: risposta inattesa ({ctype})")
                return None
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        size_mb = out_path.stat().st_size / 1e6
        if size_mb < 0.05:
            print("  ⚠️ Clip.cafe download: file troppo piccolo, lo ignoro")
            return None
        print(f"  🎞️ Spezzone film scaricato: «{found['title']}» "
              f"({found.get('movie', '?')}, {found['duration']:.0f}s, {size_mb:.0f} MB)")
        return out_path
    except (requests.RequestException, OSError) as e:
        print(f"  ⚠️ Clip.cafe download fallito: {e}")
        return None

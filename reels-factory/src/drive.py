"""Sorgente video da Google Drive (piano B, il più affidabile).

Quando YouTube blocca tutti i download, il file master ce l'abbiamo comunque:
chi monta il video lo trascina nella cartella Drive dedicata (condivisa
"chiunque con il link") e la pipeline lo prende da lì con una semplice
API key Google — Drive non blocca mai.

Convenzione: un file per video, il più recente non ancora usato.
"""

import os
from pathlib import Path

import requests

API = "https://www.googleapis.com/drive/v3/files"


def _env() -> tuple[str, str] | None:
    key = os.environ.get("GDRIVE_API_KEY", "").strip()
    folder = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    return (key, folder) if key and folder else None


def is_configured() -> bool:
    return _env() is not None


def find_new_file(used_file_ids: list[str]) -> dict | None:
    """Il video più recente nella cartella non ancora usato: {id, name, size}."""
    env = _env()
    if env is None:
        return None
    key, folder = env
    resp = requests.get(API, params={
        "q": f"'{folder}' in parents and trashed=false and mimeType contains 'video/'",
        "orderBy": "createdTime desc",
        "fields": "files(id,name,size,createdTime,mimeType)",
        "pageSize": 20,
        "key": key,
    }, timeout=60)
    resp.raise_for_status()
    for f in resp.json().get("files", []):
        if f["id"] not in used_file_ids:
            return f
    return None


def download_file(file_id: str, out_path: Path) -> Path:
    key, _ = _env()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(f"{API}/{file_id}", params={"alt": "media", "key": key},
                      stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    size_mb = out_path.stat().st_size / 1e6
    print(f"  ⬇️ Video scaricato da Google Drive ({size_mb:.0f} MB)")
    return out_path

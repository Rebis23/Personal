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


def _somiglianza(nome: str, titolo: str) -> float:
    """Quanto il nome del file assomiglia al titolo del video, contando le
    parole in comune. Serve per non accoppiare il file sbagliato al video
    sbagliato quando nella cartella ce n'e piu di uno."""
    import re
    pulisci = lambda t: {w for w in re.findall(r"[a-z0-9]{4,}", t.lower())}
    a, b = pulisci(nome), pulisci(titolo)
    return len(a & b) / len(b) if b else 0.0


def find_new_file(used_file_ids: list[str], *, video_id: str = "",
                  titolo: str = "") -> dict | None:
    """Il file da usare per QUESTO video: {id, name, size}.

    Con Apify a secco e YouTube che blocca, la cartella Drive e diventata la
    via principale, non piu l'ultima spiaggia: accoppiare il file sbagliato al
    video sbagliato non e piu un rischio teorico. Quindi si cerca in ordine:
      1. un file che contiene l'id del video nel nome (accoppiamento certo)
      2. un file il cui nome somiglia al titolo per almeno meta delle parole
      3. il piu recente non ancora usato, ma solo se ce n'e UNO solo: con due
         file in attesa la scelta sarebbe una scommessa, meglio fermarsi
    """
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
    liberi = [f for f in resp.json().get("files", [])
              if f["id"] not in used_file_ids]
    if not liberi:
        return None

    if video_id:
        for f in liberi:
            if video_id in f["name"]:
                print(f"  📁 File accoppiato per id: {f['name']}")
                return f

    if titolo:
        migliore = max(liberi, key=lambda f: _somiglianza(f["name"], titolo))
        punteggio = _somiglianza(migliore["name"], titolo)
        if punteggio >= 0.5:
            print(f"  📁 File accoppiato per titolo ({punteggio:.0%}): {migliore['name']}")
            return migliore

    if len(liberi) == 1:
        print(f"  📁 Unico file in attesa: {liberi[0]['name']}")
        return liberi[0]

    print(f"  ⚠️ {len(liberi)} file in attesa e nessuno riconducibile a questo "
          f"video: rinomina il file mettendoci l'id ({video_id}) o il titolo")
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

"""Download dei video tramite Apify (actor memo23/youtube-video-downloader).

YouTube blocca i download dagli IP dei datacenter (GitHub Actions incluso):
l'actor fa il download sulla sua infrastruttura con proxy residenziali e ci
restituisce un link al file, scaricabile senza blocchi. Costo: pochi centesimi
a video, coperti dai 5 $/mese di crediti del piano gratuito Apify.
"""

import os
import time
from pathlib import Path

import requests

ACTOR = "memo23~youtube-video-downloader"
BASE = "https://api.apify.com/v2"


class ApifyError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        raise ApifyError("Secret APIFY_TOKEN mancante")
    return token


def _run_actor(actor_input: dict, timeout_minutes: int = 20) -> list[dict]:
    """Avvia l'actor, attende la fine e ritorna le righe del dataset."""
    resp = requests.post(
        f"{BASE}/acts/{ACTOR}/runs",
        params={"token": _token()},
        json=actor_input,
        timeout=60,
    )
    resp.raise_for_status()
    run = resp.json()["data"]
    run_id, dataset_id = run["id"], run["defaultDatasetId"]
    print(f"  ☁️ Apify run {run_id} avviato...")

    deadline = time.time() + timeout_minutes * 60
    while True:
        status = requests.get(
            f"{BASE}/actor-runs/{run_id}", params={"token": _token()}, timeout=60
        ).json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise ApifyError(f"Apify run {run_id} terminato con stato {status}")
        if time.time() > deadline:
            raise ApifyError(f"Apify run {run_id}: timeout dopo {timeout_minutes} min")
        time.sleep(10)

    items = requests.get(
        f"{BASE}/datasets/{dataset_id}/items", params={"token": _token()}, timeout=60
    ).json()
    if not items:
        raise ApifyError("Apify: dataset vuoto")
    row = items[0]
    if row.get("error"):
        raise ApifyError(f"Apify: {row['error']}")
    return items


def get_duration(video_id: str) -> int | None:
    """Durata del video in secondi (solo metadati, costa una frazione di centesimo)."""
    try:
        row = _run_actor({
            "videoUrls": [f"https://www.youtube.com/watch?v={video_id}"],
            "metadataOnly": True,
        }, timeout_minutes=5)[0]
        return int(row.get("durationSec") or 0) or None
    except (ApifyError, requests.RequestException, ValueError) as e:
        print(f"  ⚠️ Apify metadati falliti: {e}")
        return None


# Insistere nella stessa sessione peggiora le cose: YouTube stringe le
# maglie a chi ritenta subito. Meglio pochi tentativi e ben distanziati —
# il vero "riprova" è affidato alle esecuzioni successive della giornata
# (vedi i cron in .github/workflows/reels-ingest.yml).
RETRY_WAITS = (90,)


def download_video(video_id: str, workdir: Path, quality: str = "1080p") -> Path | None:
    """Scarica il video via Apify. Ritorna il percorso del file mp4 o None."""
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / f"{video_id}.mp4"
    total = len(RETRY_WAITS) + 1
    for attempt in range(1, total + 1):
        # Al secondo tentativo si chiede una qualità più bassa: i flussi 720p
        # a volte passano quando i 1080p sono bloccati
        q = quality if attempt == 1 else "720p"
        try:
            row = _run_actor({
                "videoUrls": [f"https://www.youtube.com/watch?v={video_id}"],
                "quality": q,
                "format": "mp4",
            })[0]
            url = row.get("downloadUrl")
            if not url:
                raise ApifyError("nessun downloadUrl nella risposta")
            # Il file sta nel key-value store privato dell'account: senza
            # autenticazione risponde 403
            headers = {}
            if "api.apify.com" in url:
                headers["Authorization"] = f"Bearer {_token()}"
            with requests.get(url, headers=headers, stream=True, timeout=180) as r:
                r.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            size_mb = out.stat().st_size / 1e6
            print(f"  ⬇️ Video scaricato via Apify ({size_mb:.0f} MB, {q})")
            return out
        except (ApifyError, requests.RequestException) as e:
            print(f"  ⚠️ Apify download fallito (tentativo {attempt}/{total}, {q}): {e}")
            if attempt <= len(RETRY_WAITS):
                wait = RETRY_WAITS[attempt - 1]
                print(f"     ⏳ riprovo tra {wait}s...")
                time.sleep(wait)
    return None

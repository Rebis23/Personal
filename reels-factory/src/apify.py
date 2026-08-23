"""Download dei video tramite Apify.

YouTube blocca i download dagli IP dei datacenter (GitHub Actions incluso):
gli actor Apify fanno il download sulla loro infrastruttura con proxy
residenziali e ci restituiscono un link al file, scaricabile senza blocchi.
Costo: pochi centesimi a video, coperti dai crediti mensili del piano Apify.

Un solo actor non basta. Il 18 agosto memo23 ha iniziato a fallire in modo
sistematico (YouTube stringe le maglie a ondate, actor per actor) e la
fabbrica si e fermata per cinque giorni. Ora si prova una fila di actor
diversi: quando uno viene bloccato, gli altri di solito passano ancora.
Il 23/08 memo23 e fallito di nuovo e streamers ha scaricato al primo
colpo: da li l'ordine attuale.
"""

import os
import time
from pathlib import Path

import requests

BASE = "https://api.apify.com/v2"

# Actor per i metadati (durata): leggero, non scarica il file
META_ACTOR = "memo23~youtube-video-downloader"

# Fila degli actor per il download vero, in ordine di preferenza. Ognuno ha
# il suo schema di input: la funzione riceve (url, qualita) e ritorna il JSON.
STREAMERS = (
    "streamers~youtube-video-downloader",
    lambda url, q: {
        "videos": [{"url": url}],
        "preferredQuality": q,
        "preferredFormat": "mp4",
        "storeInKVStore": True,
    },
)
MEMO23 = (
    "memo23~youtube-video-downloader",
    lambda url, q: {"videoUrls": [url], "quality": q, "format": "mp4"},
)
EPCTEX = (
    "epctex~youtube-video-downloader",
    lambda url, q: {"startUrls": [url], "quality": q.rstrip("p"), "storageType": "apify"},
)

PROVIDERS = [STREAMERS, MEMO23, EPCTEX]


class ApifyError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        raise ApifyError("Secret APIFY_TOKEN mancante")
    return token


def _run_actor(actor: str, actor_input: dict, timeout_minutes: int = 20) -> dict:
    """Avvia l'actor, attende la fine, ritorna {items, run_id, kv_store_id}."""
    resp = requests.post(
        f"{BASE}/acts/{actor}/runs",
        params={"token": _token()},
        json=actor_input,
        timeout=60,
    )
    resp.raise_for_status()
    run = resp.json()["data"]
    run_id, dataset_id = run["id"], run["defaultDatasetId"]
    kv_store_id = run.get("defaultKeyValueStoreId", "")
    print(f"  ☁️ Apify run {run_id} avviato ({actor})...")

    deadline = time.time() + timeout_minutes * 60
    while True:
        status = requests.get(
            f"{BASE}/actor-runs/{run_id}", params={"token": _token()}, timeout=60
        ).json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise ApifyError(f"run {run_id} terminato con stato {status}")
        if time.time() > deadline:
            raise ApifyError(f"run {run_id}: timeout dopo {timeout_minutes} min")
        time.sleep(10)

    items = requests.get(
        f"{BASE}/datasets/{dataset_id}/items", params={"token": _token()}, timeout=60
    ).json()
    if items and isinstance(items[0], dict) and items[0].get("error"):
        raise ApifyError(str(items[0]["error"]))
    return {"items": items, "run_id": run_id, "kv_store_id": kv_store_id}


VIDEO_EXTS = (".mp4", ".m4v", ".webm", ".mkv", ".mov")


def _walk(node, key=""):
    """Scorre dizionari e liste annidati restituendo coppie (chiave, stringa)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v, key)
    elif isinstance(node, str):
        yield key, node


def _pick_download_url(items: list) -> str:
    """Trova il link al file scaricato, qualunque nome gli dia l'actor.

    Ogni actor ha il suo schema (downloadUrl, output.url, videoUrl...): invece
    di inseguirli uno per uno si cerca il candidato migliore per punteggio.
    """
    best, best_score = "", 0
    for key, value in _walk(items):
        if not value.startswith("http"):
            continue
        low_url, low_key = value.lower(), key.lower()
        # L'input viene spesso ripetuto nell'output: non e il file scaricato
        if "youtube.com" in low_url or "youtu.be" in low_url:
            continue
        score = 0
        if "download" in low_key:
            score += 3
        if low_key in ("url", "link", "fileurl", "videourl", "mediaurl", "location"):
            score += 2
        if any(low_url.split("?")[0].endswith(e) for e in VIDEO_EXTS):
            score += 3
        if "key-value-stores" in low_url or "/records/" in low_url:
            score += 2
        if score > best_score:
            best, best_score = value, score
    if best_score < 2:
        raise ApifyError("nessun link al file nella risposta")
    return best


def _kv_store_url(kv_store_id: str) -> str:
    """Ultima spiaggia: pesca il file direttamente dallo store del run."""
    if not kv_store_id:
        raise ApifyError("nessun key-value store da ispezionare")
    keys = requests.get(
        f"{BASE}/key-value-stores/{kv_store_id}/keys",
        params={"token": _token(), "limit": 100},
        timeout=60,
    ).json().get("data", {}).get("items", [])
    for item in keys:
        name = item.get("key", "")
        if name.lower().endswith(VIDEO_EXTS):
            return f"{BASE}/key-value-stores/{kv_store_id}/records/{name}"
    raise ApifyError("nessun file video nel key-value store")


def get_duration(video_id: str) -> int | None:
    """Durata del video in secondi (solo metadati, costa una frazione di centesimo)."""
    try:
        rows = _run_actor(META_ACTOR, {
            "videoUrls": [f"https://www.youtube.com/watch?v={video_id}"],
            "metadataOnly": True,
        }, timeout_minutes=5)["items"]
        return int(rows[0].get("durationSec") or 0) or None
    except (ApifyError, requests.RequestException, ValueError, IndexError, KeyError) as e:
        print(f"  ⚠️ Apify metadati falliti: {e}")
        return None


def _fetch(url: str, out: Path) -> Path:
    # I file stanno nel key-value store privato dell'account: senza
    # autenticazione rispondono 403
    headers = {}
    if "api.apify.com" in url:
        headers["Authorization"] = f"Bearer {_token()}"
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    if out.stat().st_size < 100_000:
        out.unlink(missing_ok=True)
        raise ApifyError("file scaricato troppo piccolo: non e un video")
    return out


# Insistere con lo STESSO actor peggiora le cose: YouTube stringe le maglie a
# chi ritenta subito. Si cambia actor invece di ripetere, con una pausa in
# mezzo; il vero "riprova" resta affidato alle esecuzioni successive della
# giornata (vedi i cron in .github/workflows/reels-ingest.yml).
PAUSE_BETWEEN_PROVIDERS = 45


def _attempts(quality: str) -> list[tuple]:
    """Coppie (actor, qualita) da provare, in ordine.

    Il primo actor ha due chance: la qualita richiesta e poi 720p, che e la
    combinazione gia vista funzionare. Solo dopo si cambia fornitore.
    """
    plan = [(STREAMERS, quality)]
    if quality != "720p":
        plan.append((STREAMERS, "720p"))
    plan += [(p, quality) for p in PROVIDERS[1:]]
    return plan


def download_video(video_id: str, workdir: Path, quality: str = "1080p") -> Path | None:
    """Scarica il video provando gli actor in fila. Ritorna il percorso o None."""
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / f"{video_id}.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"
    plan = _attempts(quality)
    total = len(plan)

    for attempt, ((actor, build_input), q) in enumerate(plan, start=1):
        try:
            run = _run_actor(actor, build_input(url, q))
            try:
                file_url = _pick_download_url(run["items"])
            except ApifyError:
                file_url = _kv_store_url(run["kv_store_id"])
            _fetch(file_url, out)
            size_mb = out.stat().st_size / 1e6
            print(f"  ⬇️ Video scaricato via Apify ({size_mb:.0f} MB, {q}, {actor})")
            return out
        except (ApifyError, requests.RequestException) as e:
            short = actor.split("~")[0]
            print(f"  ⚠️ Apify fallito (actor {attempt}/{total}, {short}, {q}): {e}")
            if attempt < total:
                print(f"     ⏳ provo un altro actor tra {PAUSE_BETWEEN_PROVIDERS}s...")
                time.sleep(PAUSE_BETWEEN_PROVIDERS)
    return None

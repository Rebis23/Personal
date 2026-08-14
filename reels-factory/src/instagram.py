"""Pubblicazione Reels tramite Instagram Graph API (account business/creator).

Flusso in 3 passi:
  1. POST /{ig-user-id}/media          → crea il "container" del Reel
  2. GET  /{container-id}?fields=...   → attende che Instagram processi il video
  3. POST /{ig-user-id}/media_publish  → pubblica

Limite API: max 25 post pubblicati via API ogni 24h (qui ne facciamo 1-3 al giorno).
"""

import os
import time

import requests

GRAPH_VERSION = os.environ.get("IG_GRAPH_API_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class InstagramError(RuntimeError):
    pass


def _token() -> str:
    return os.environ["IG_ACCESS_TOKEN"]


def _user_id() -> str:
    return os.environ["IG_USER_ID"]


def _check(resp: requests.Response) -> dict:
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or "error" in data:
        raise InstagramError(f"Graph API {resp.status_code}: {data.get('error', data)}")
    return data


def publish_reel(video_url: str, caption: str, timeout_minutes: int = 15) -> dict:
    """Pubblica un Reel. Ritorna {ig_media_id, permalink}."""
    # 1. Container
    data = _check(requests.post(
        f"{BASE}/{_user_id()}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": _token(),
        },
        timeout=60,
    ))
    container_id = data["id"]
    print(f"  📦 Container creato: {container_id}")

    # 2. Attesa processamento
    deadline = time.time() + timeout_minutes * 60
    while True:
        status = _check(requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": _token()},
            timeout=60,
        ))
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise InstagramError(f"Processamento fallito: {status.get('status')}")
        if time.time() > deadline:
            raise InstagramError(f"Timeout processamento ({timeout_minutes} min), stato: {code}")
        print(f"  ⏳ Stato container: {code} — attendo 15s...")
        time.sleep(15)

    # 3. Pubblicazione
    published = _check(requests.post(
        f"{BASE}/{_user_id()}/media_publish",
        data={"creation_id": container_id, "access_token": _token()},
        timeout=60,
    ))
    media_id = published["id"]

    permalink = ""
    try:
        info = _check(requests.get(
            f"{BASE}/{media_id}",
            params={"fields": "permalink", "access_token": _token()},
            timeout=60,
        ))
        permalink = info.get("permalink", "")
    except InstagramError:
        pass  # il permalink è solo informativo

    return {"ig_media_id": media_id, "permalink": permalink}

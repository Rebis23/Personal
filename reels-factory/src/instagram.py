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

GRAPH_VERSION = os.environ.get("IG_GRAPH_API_VERSION", "v23.0").strip()
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class InstagramError(RuntimeError):
    pass


# .strip(): i segreti incollati nei GitHub Secrets possono avere un a-capo finale

def _token() -> str:
    return os.environ["IG_ACCESS_TOKEN"].strip()


def _user_id() -> str:
    return os.environ["IG_USER_ID"].strip()


def _check(resp: requests.Response) -> dict:
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or "error" in data:
        raise InstagramError(f"Graph API {resp.status_code}: {data.get('error', data)}")
    return data


def check_connection() -> str:
    """Interroga l'account senza pubblicare: dice se l'API risponde davvero.
    Usato nelle prove a vuoto per accorgersi in anticipo di token scaduti o
    restrizioni sull'app Meta."""
    try:
        info = _check(requests.get(
            f"{BASE}/{_user_id()}",
            params={"fields": "username,followers_count,media_count",
                    "access_token": _token()},
            timeout=60,
        ))
        return (f"🔗 Instagram raggiungibile: @{info.get('username')} "
                f"({info.get('followers_count')} follower, "
                f"{info.get('media_count')} contenuti)")
    except (InstagramError, requests.RequestException, KeyError) as e:
        return f"⛔ Instagram NON raggiungibile: {e}"


def diagnose() -> str:
    """Interroga Meta su token, permessi e quota per capire PERCHE la
    pubblicazione e stata rifiutata. Il sottocodice 2207085 ("Generic Internal
    Error") non dice niente da solo: puo essere un guasto passeggero oppure un
    blocco vero e proprio, e senza questi tre dati non si distinguono.
    Non pubblica e non modifica nulla: e solo lettura."""
    righe = ["🩺 Diagnosi del collegamento Instagram:"]

    try:
        tok = _check(requests.get(
            f"{BASE}/debug_token",
            params={"input_token": _token(), "access_token": _token()},
            timeout=60,
        )).get("data", {})
        scadenza = tok.get("expires_at")
        righe.append(
            f"   token: valido={tok.get('is_valid')} tipo={tok.get('type')} "
            f"app={tok.get('application')} "
            f"scadenza={'mai' if scadenza == 0 else scadenza}")
        permessi = tok.get("scopes", [])
        ha_publish = "instagram_content_publish" in permessi
        righe.append(f"   permesso di pubblicare: {'SI' if ha_publish else 'NO — e questo il problema'}")
    except (InstagramError, requests.RequestException, KeyError) as e:
        righe.append(f"   token: impossibile verificarlo ({e})")

    try:
        limite = _check(requests.get(
            f"{BASE}/{_user_id()}/content_publishing_limit",
            params={"fields": "config,quota_usage", "access_token": _token()},
            timeout=60,
        )).get("data", [{}])[0]
        usati = limite.get("quota_usage")
        totale = limite.get("config", {}).get("quota_total")
        righe.append(f"   quota 24h: {usati}/{totale} usati")
    except (InstagramError, requests.RequestException, IndexError, KeyError) as e:
        righe.append(f"   quota 24h: non leggibile ({e})")

    righe.append("   " + check_connection())
    return "\n".join(righe)


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
    # Il 26/08 questa chiamata e tornata 400 con sottocodice 2207085 ("Generic
    # Internal Error ... please try again later"): il video era gia stato
    # elaborato, si e perso solo l'ultimo passo e la giornata e saltata.
    # Sono errori del lato Meta, non nostri: si riprova qualche volta.
    TRANSITORI = (2207085, 2207001, 2207032)
    published = None
    for tentativo in (1, 2, 3):
        try:
            published = _check(requests.post(
                f"{BASE}/{_user_id()}/media_publish",
                data={"creation_id": container_id, "access_token": _token()},
                timeout=60,
            ))
            break
        except InstagramError as e:
            transitorio = any(str(c) in str(e) for c in TRANSITORI) or "500" in str(e)
            if not transitorio or tentativo == 3:
                raise
            attesa = 30 * tentativo
            print(f"  ⚠️ Instagram ha risposto con un errore interno "
                  f"(tentativo {tentativo}/3), riprovo tra {attesa}s: {e}")
            time.sleep(attesa)
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

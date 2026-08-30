"""YouTube: rilevamento nuovi video (feed RSS, zero API key) e download via yt-dlp."""

import json
import os
import subprocess
import time
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

_cookie_file: Path | None = None


def _cookie_args() -> list[str]:
    """YouTube blocca gli IP dei datacenter (GitHub Actions incluso) con
    "Sign in to confirm you're not a bot". Il secret YT_COOKIES (contenuto di
    un cookies.txt esportato dal browser) sblocca il download."""
    global _cookie_file
    cookies = os.environ.get("YT_COOKIES", "").strip()
    if not cookies:
        return []
    if _cookie_file is None:
        f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        f.write(cookies + "\n")
        f.close()
        _cookie_file = Path(f.name)
    return ["--cookies", str(_cookie_file)]


def _proxy_args() -> list[str]:
    """Secret YT_PROXY (es. http://utente:password@host:porta): fa uscire il
    traffico da una connessione residenziale invece che dall'IP del runner.
    È la via che rende il download diretto affidabile senza intermediari."""
    proxy = os.environ.get("YT_PROXY", "").strip()
    return ["--proxy", proxy] if proxy else []


# YouTube applica un controllo anti-bot legato al "client" che chiede il
# video, e non tutti i client lo prendono allo stesso modo. Misurato il
# 30/08 sullo stesso video, uno per uno:
#
#   tv, tv_embedded, android_vr, default  →  "Sign in to confirm you're not
#                                            a bot": muro, la richiesta muore
#   web_safari, mweb, web_embedded, ios   →  passano il controllo e falliscono
#                                            piu avanti, su cose risolvibili
#
# La catena aveva "tv" per primo, quindi sbatteva sul muro e non arrivava mai
# a provare quelli che passano. Ora ci sono solo i tre che passano.
#
# "ios" resta fuori apposta: passa il controllo ma i suoi flussi vogliono un
# GVS PO token che il provider bgutil non sa generare, quindi restano solo
# le anteprime.
#
# Dopo il controllo restano due ostacoli, e per entrambi il pezzo necessario
# e gia sul runner: la sfida JavaScript (la risolve deno, installato dal
# workflow) e il PO token con i suoi Visitor Data (li da il provider bgutil,
# avviato dal workflow). In locale la sfida JS si e risolta appena installato
# deno, e l'ultimo errore rimasto era il 429 da IP consumato dalle prove.
CLIENT_ARGS = ["--extractor-args", "youtube:player_client=web_safari,mweb,web_embedded"]


def _net_args() -> list[str]:
    args = _cookie_args() + _proxy_args()
    # I cookie autenticano diversamente dal client tv: accostarli invalida la
    # sessione, quindi si scelgono i client alternativi solo senza cookie
    if not os.environ.get("YT_COOKIES", "").strip():
        args += CLIENT_ARGS
    return args


def fetch_recent_videos(channel_id: str) -> list[dict]:
    """Legge il feed RSS del canale. Ritorna [{video_id, title, published}] dal più recente.

    Il feed ogni tanto risponde 404 o va in timeout per qualche secondo: si
    riprova un paio di volte invece di far fallire l'intera esecuzione.
    """
    url = RSS_URL.format(channel_id=channel_id)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (reels-factory)"})
    # Il 26/08 il feed ha risposto 404 per piu di un minuto e i tre tentativi
    # distanziati 15s si sono esauriti tutti dentro l'intoppo: la lavorazione
    # e stata saltata pur essendoci lavoro da fare. Attese piu larghe.
    xml_data = None
    attese = (20, 60, 120)
    for attempt in range(1, len(attese) + 2):
        try:
            with urlopen(req, timeout=30) as resp:
                xml_data = resp.read()
            break
        except Exception as e:  # noqa: BLE001 — qualsiasi intoppo di rete
            print(f"  ⚠️ Feed del canale non raggiungibile "
                  f"(tentativo {attempt}/{len(attese) + 1}): {e}")
            if attempt <= len(attese):
                time.sleep(attese[attempt - 1])
    if xml_data is None:
        print("  ⏭️ Feed non raggiungibile: riprovo alla prossima esecuzione")
        return []
    root = ET.fromstring(xml_data)
    videos = []
    for entry in root.findall("atom:entry", NS):
        vid = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS)
        published = entry.findtext("atom:published", namespaces=NS)
        if vid:
            videos.append({"video_id": vid, "title": title or "", "published": published or ""})
    return videos


def video_age_hours(published_iso: str) -> float:
    try:
        published = datetime.fromisoformat(published_iso)
    except ValueError:
        return 0.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - published).total_seconds() / 3600


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    print("  $", " ".join(cmd[:6]), "...")
    return subprocess.run(cmd, capture_output=True, text=True)


def get_video_info(video_id: str) -> dict | None:
    """Metadati del video (durata inclusa) senza scaricarlo."""
    proc = _run(["yt-dlp", *_net_args(), "--dump-json", "--no-download",
                 f"https://www.youtube.com/watch?v={video_id}"])
    if proc.returncode != 0:
        print(f"  ⚠️ yt-dlp info fallito per {video_id}: {proc.stderr[-500:]}")
        return None
    return json.loads(proc.stdout)


def download_video(video_id: str, workdir: Path) -> Path | None:
    """Scarica il video (max 1080p, mp4). Ritorna il percorso del file o None."""
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / f"{video_id}.mp4"
    proc = _run([
        "yt-dlp", *_net_args(),
        "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b",
        "--merge-output-format", "mp4",
        "--retries", "5",
        "-o", str(out),
        f"https://www.youtube.com/watch?v={video_id}",
    ])
    if proc.returncode != 0 or not out.exists():
        print(f"  ⚠️ download fallito per {video_id}: {proc.stderr[-800:]}")
        return None
    return out


def download_auto_subs(video_id: str, workdir: Path, lang: str = "it") -> Path | None:
    """Scarica i sottotitoli automatici in formato json3 (timing parola per parola).

    Ritorna il percorso del file .json3 oppure None se non ancora disponibili.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    base = workdir / f"{video_id}.subs"
    proc = _run([
        "yt-dlp", *_net_args(),
        "--skip-download",
        "--write-auto-subs", "--write-subs",
        "--sub-langs", f"{lang},{lang}-orig",
        "--sub-format", "json3",
        "-o", str(base),
        f"https://www.youtube.com/watch?v={video_id}",
    ])
    if proc.returncode != 0:
        print(f"  ⚠️ yt-dlp sottotitoli fallito: {proc.stderr[-500:]}")
    matches = sorted(workdir.glob(f"{video_id}.subs*.json3"))
    return matches[0] if matches else None

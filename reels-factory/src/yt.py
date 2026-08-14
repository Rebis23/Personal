"""YouTube: rilevamento nuovi video (feed RSS, zero API key) e download via yt-dlp."""

import json
import os
import subprocess
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


def fetch_recent_videos(channel_id: str) -> list[dict]:
    """Legge il feed RSS del canale. Ritorna [{video_id, title, published}] dal più recente."""
    url = RSS_URL.format(channel_id=channel_id)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (reels-factory)"})
    with urlopen(req, timeout=30) as resp:
        xml_data = resp.read()
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
    proc = _run(["yt-dlp", *_cookie_args(), "--dump-json", "--no-download",
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
        "yt-dlp", *_cookie_args(),
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
        "yt-dlp", *_cookie_args(),
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

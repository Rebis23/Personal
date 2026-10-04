"""YouTube: rilevamento nuovi video (feed RSS, zero API key) e download via yt-dlp."""

import json
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

from . import tunnel

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


# Come si passa il controllo anti-bot di YouTube, misurato il 30/08 e
# finalmente riuscito (run 33341525826):
#
#   1. il tunnel WARP, che cambia l'indirizzo di uscita (lo alza il workflow)
#   2. questa catena di client, che parte da "web" invece che sbatterci
#   3. --remote-components ejs:github, che scarica il risolutore della
#      sfida JavaScript: deno da solo non basta, lo script va chiesto
#
# Servono tutti e tre insieme. Tolto uno qualsiasi si torna a "Sign in to
# confirm you're not a bot", e ci sono voluti cinque giri per capirlo
# perche ogni giro ne provava due su tre.
# DUE COSE DIVERSE, TENUTE SEPARATE DAL 4/10.
#
# Stavano in un elenco solo, e il 4/10 Lorenzo ha messo i cookie: il blocco
# anti-bot e sparito davvero — nel log si vede `yt-dlp --cookies /tmp/...` e
# nessun "Sign in to confirm you're not a bot" — ma lo scarico e fallito
# cosi:
#
#     WARNING: n challenge solving failed: ... Ensure you have a supported
#              JavaScript runtime and challenge solver script installed
#     ERROR:   The page needs to be reloaded.
#
# Perche con i cookie _net_args() smetteva di passare TUTTO l'elenco, e
# dentro c'era anche il risolutore JavaScript. I due pezzi hanno ragioni
# opposte di esistere:
#
#   il risolutore JS  serve SEMPRE — YouTube firma gli indirizzi dei file
#                     con del codice da eseguire, e senza eseguirlo non si
#                     scarica niente, con o senza cookie
#   i client alternativi  servono SOLO senza cookie — autenticano in un modo
#                     che coi cookie va in conflitto e invalida la sessione
#
# Messi nella stessa lista si escludevano a vicenda sbagliando: i cookie
# risolvevano un problema e ne riaprivano un altro. Il difetto era latente
# da sempre e si e visto solo adesso, perche YT_COOKIES non era mai stato
# impostato: un ramo che nessuno ha mai percorso non e codice funzionante,
# e solo codice non ancora smentito.
RISOLUTORE_JS = ["--remote-components", "ejs:github"]
CLIENT_ARGS = [
    "--extractor-args", "youtube:player_client=web,tv,mweb,web_safari",
]


def _net_args() -> list[str]:
    args = _cookie_args() + _proxy_args() + RISOLUTORE_JS
    # I client alternativi autenticano diversamente dai cookie: accostarli
    # invalida la sessione, quindi si usano solo quando i cookie non ci sono.
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


# Tutte le chiamate a yt-dlp passano di qui: e l'unico punto in cui serve
# il tunnel, ed e per questo che il tunnel si accende solo qui invece che
# per tutto il lavoro (vedi src/tunnel.py per il perche).
#
# E hanno un tetto di tempo. Prima non ce l'avevano: uno scarico appeso
# avrebbe tenuto il tunnel su a oltranza, cioe esattamente la condizione
# che stiamo togliendo di mezzo.
def _run(cmd: list[str], *, tetto: int = 900) -> subprocess.CompletedProcess:
    print("  $", " ".join(cmd[:6]), "...")
    with tunnel.acceso():
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=tetto)
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ yt-dlp oltre i {tetto // 60} minuti: interrotto")
            return subprocess.CompletedProcess(cmd, 1, "", f"timeout dopo {tetto}s")


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


def fetch_intero_catalogo(channel_id: str, *, tetto: int = 200) -> list[dict]:
    """TUTTI i video del canale, non solo gli ultimi quindici.

    Il feed RSS che usa fetch_recent_videos() e tagliato a 15 voci da
    YouTube: non e una scelta di configurazione, e un limite del feed. Per
    la pubblicazione quotidiana bastava — un video nuovo compare sempre fra
    i primi quindici. Ma per pescare dall'archivio no: il 25/09, coi conti
    a due Reel al giorno, si e visto che la fabbrica credeva di avere sei
    video di riserva quando il canale ne ha molti di piu. Sedici giorni di
    autonomia invece di mesi, per un limite che nessuno aveva scelto.

    Qui si chiede l'elenco vero a yt-dlp, senza scaricare niente: --flat-
    playlist legge solo i titoli e gli identificativi.

    Torna la stessa forma di fetch_recent_videos(), dal piu recente. In caso
    di guaio torna [] e chi chiama ripiega sul feed: meglio quindici video
    che nessuno.
    """
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    esito = _run(["yt-dlp", "--flat-playlist", "--dump-json",
                  "--playlist-end", str(tetto), url], tetto=600)
    if esito.returncode != 0:
        print(f"  ⚠️ Catalogo intero non leggibile: {esito.stderr[-200:]}")
        return []

    fuori = []
    for riga in esito.stdout.splitlines():
        riga = riga.strip()
        if not riga:
            continue
        try:
            v = json.loads(riga)
        except json.JSONDecodeError:
            continue
        vid = v.get("id")
        if not vid:
            continue
        # --flat-playlist non da la data di pubblicazione. L'ordine pero e
        # quello del canale, dal piu recente: chi chiama usa l'ordine, non
        # la data, e per i video d'archivio la data non serve a niente.
        fuori.append({"video_id": vid,
                      "title": v.get("title") or "",
                      "published": "",
                      "durata": v.get("duration") or 0})
    print(f"  📚 Catalogo del canale: {len(fuori)} video")
    return fuori

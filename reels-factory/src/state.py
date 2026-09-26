"""Stato persistente della pipeline (file JSON committato nel repo).

Struttura di state/queue.json:
  processed_videos: video già ingeriti (o saltati) — non vengono riprocessati
  queue:            clip pronte, caricate su R2, in attesa di pubblicazione
  published:        storico delle clip pubblicate su Instagram
"""

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state" / "queue.json"

EMPTY_STATE = {
    "processed_videos": [],  # [{video_id, title, status, processed_at, clips}]
    "queue": [],             # [{clip_id, video_id, video_title, media_url, caption, created_at}]
    "published": [],         # [{clip_id, ig_media_id, permalink, published_at}]
}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return json.loads(json.dumps(EMPTY_STATE))
    with open(STATE_PATH, encoding="utf-8") as f:
        state = json.load(f)
    for key in EMPTY_STATE:
        state.setdefault(key, [])
    return state


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Uno stato che significa "sta nell'elenco ma va rifatto". Serve quando le
# clip erano tecnicamente a posto e sbagliate nella sostanza — hook fuori
# contesto, stile bocciato — e il video va ritagliato da capo.
DA_RIFARE = "da_rifare"


def is_processed(state: dict, video_id: str) -> bool:
    return any(v["video_id"] == video_id and v.get("status") != DA_RIFARE
               for v in state["processed_videos"])


def nostri_caricamenti(state: dict) -> set[str]:
    """Gli id YouTube dei video caricati da NOI come Shorts.

    Dal 25/09 la fabbrica pubblica i Reel anche su YouTube. Quei
    caricamenti compaiono nel feed del canale come video nuovi di zecca —
    il feed non sa distinguere un video di Lorenzo da un Reel che gli
    abbiamo messo noi. Senza questo filtro l'ingest li prende per "il
    video nuovo del giorno", scopre che sono corti, li scarta e chiude la
    corsa; e siccome un video nuovo c'era, l'archivio non viene nemmeno
    interrogato.

    Il conto del 26/09: quattro Shorts caricati al giorno contro tre
    ingest al giorno, e ogni ingest ne smaltisce uno solo
    (MAX_VIDEOS_PER_RUN = 1). La fabbrica perde un video al giorno e non
    torna piu indietro: la coda Instagram non si riempirebbe mai piu.

    Torna un insieme, cosi chi chiama fa `in` senza pensarci. Le voci
    vecchie di shorts_done erano semplici stringhe (il clip_id, non l'id
    YouTube): quelle non dicono niente su cosa c'e sul canale e vengono
    ignorate senza far rumore.
    """
    fuori = set()
    for voce in state.get("shorts_done") or []:
        if isinstance(voce, dict) and voce.get("youtube_id"):
            fuori.add(voce["youtube_id"])
    return fuori


def da_saltare(state: dict, video_id: str) -> bool:
    """Vero se la fabbrica non deve toccare questo video del canale.

    Due motivi, e conviene tenerli sotto un nome solo perche i posti che
    scelgono un video sono due (il feed dei nuovi e il pescaggio
    dall'archivio) e il 25/09 si e visto cosa succede quando uno dei due
    ha un filtro e l'altro no: basta la falla di uno per fermare tutto.

      - l'abbiamo gia lavorato (o scartato apposta)
      - l'abbiamo caricato noi, ed e un nostro stesso Reel
    """
    return is_processed(state, video_id) or video_id in nostri_caricamenti(state)

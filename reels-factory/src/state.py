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

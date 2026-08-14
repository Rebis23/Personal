"""Parsing dei sottotitoli automatici YouTube (formato json3) in parole temporizzate."""

import json
from pathlib import Path


def parse_json3(path: Path) -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, ordinato nel tempo."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    words: list[dict] = []
    for event in data.get("events", []):
        t_start = event.get("tStartMs")
        if t_start is None or "segs" not in event:
            continue
        duration = event.get("dDurationMs", 0)
        for seg in event["segs"]:
            text = (seg.get("utf8") or "").strip()
            if not text or text == "\n":
                continue
            start_ms = t_start + seg.get("tOffsetMs", 0)
            words.append({"word": text, "start": start_ms / 1000.0, "end": None,
                          "_event_end": (t_start + duration) / 1000.0})

    words.sort(key=lambda w: w["start"])
    # La fine di ogni parola è l'inizio della successiva (limitata alla fine
    # dell'evento), così l'evidenziazione karaoke resta fluida.
    for i, w in enumerate(words):
        next_start = words[i + 1]["start"] if i + 1 < len(words) else w["_event_end"]
        w["end"] = min(max(next_start, w["start"] + 0.08), w["start"] + 3.0)
        del w["_event_end"]
    return words


def to_timed_text(words: list[dict], marker_every: float = 10.0) -> str:
    """Trascrizione testuale con marcatori [mm:ss] ogni ~10s, per Claude."""
    if not words:
        return ""
    parts: list[str] = []
    next_marker = 0.0
    for w in words:
        if w["start"] >= next_marker:
            m, s = divmod(int(w["start"]), 60)
            parts.append(f"\n[{m:02d}:{s:02d}]")
            next_marker = w["start"] + marker_every
        parts.append(w["word"])
    return " ".join(parts).strip()


def snap_to_words(words: list[dict], start: float, end: float) -> tuple[float, float]:
    """Aggancia i confini della clip ai confini reali delle parole, con un
    piccolo margine, così non si taglia una parola a metà."""
    in_range = [w for w in words if w["start"] >= start - 1.5 and w["end"] <= end + 1.5]
    if not in_range:
        return start, end
    first = min(in_range, key=lambda w: abs(w["start"] - start))
    last = max((w for w in in_range if w["end"] <= end + 1.5), key=lambda w: w["end"])
    snapped_start = max(0.0, first["start"] - 0.25)
    snapped_end = last["end"] + 0.45
    return snapped_start, snapped_end


def words_in_clip(words: list[dict], start: float, end: float) -> list[dict]:
    """Parole della clip, con tempi RELATIVI all'inizio della clip."""
    out = []
    for w in words:
        if w["start"] >= start - 0.05 and w["end"] <= end + 0.3:
            out.append({
                "word": w["word"],
                "start": max(0.0, w["start"] - start),
                "end": max(0.0, w["end"] - start),
            })
    return out

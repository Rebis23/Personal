"""Orchestratore Reels Factory.

Comandi:
  python -m src.main ingest   → controlla nuovi video, taglia le clip, le mette in coda
  python -m src.main publish  → pubblica su Instagram la prossima clip in coda
  python -m src.main status   → riepilogo dello stato

Eseguito da GitHub Actions (vedi .github/workflows/reels-*.yml), ma funziona
anche in locale se hai ffmpeg, yt-dlp e le variabili d'ambiente configurate.
"""

import os
import sys
from pathlib import Path

import yaml

from . import apify, brain, drive, instagram, state as state_mod, storage, subtitles, transcribe, transcript, video, yt

ROOT = Path(__file__).resolve().parent.parent
WORKDIR = ROOT / "work"
MAX_VIDEOS_PER_RUN = 1  # limita la durata di ogni esecuzione


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dry_run() -> bool:
    return os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


# ----------------------------------------------------------------- INGEST ---

def cmd_ingest() -> int:
    cfg = load_config()
    st = state_mod.load_state()
    channel_id = cfg["youtube"]["channel_id"]
    if not channel_id or channel_id.startswith("INSERISCI"):
        print("❌ config.yaml: youtube.channel_id non configurato")
        return 1

    print(f"🔎 Controllo feed del canale {channel_id}...")
    videos = yt.fetch_recent_videos(channel_id)
    print(f"   {len(videos)} video nel feed")

    max_age_h = cfg["youtube"]["max_age_days"] * 24
    candidates = [
        v for v in videos
        if not state_mod.is_processed(st, v["video_id"])
        and yt.video_age_hours(v["published"]) <= max_age_h
    ]
    if not candidates:
        print("✅ Nessun nuovo video da processare")
        return 0

    processed_count = 0
    for v in candidates:
        if processed_count >= MAX_VIDEOS_PER_RUN:
            print("⏭️ Limite video per esecuzione raggiunto, il resto alla prossima")
            break
        if _process_video(v, cfg, st):
            processed_count += 1
        state_mod.save_state(st)
    return 0


def _mark(st: dict, v: dict, status: str, clips: list | None = None) -> None:
    st["processed_videos"].append({
        "video_id": v["video_id"],
        "title": v["title"],
        "status": status,
        "processed_at": state_mod.now_iso(),
        "clips": clips or [],
    })


def _process_video(v: dict, cfg: dict, st: dict) -> bool:
    """Ritorna True se il video è stato processato (in qualsiasi esito definitivo)."""
    vid = v["video_id"]
    print(f"\n🎬 Video: {v['title']} ({vid})")

    # Durata: prima la via gratuita (yt-dlp, funziona se YouTube non blocca),
    # poi Apify come fallback affidabile
    info = yt.get_video_info(vid)
    duration = (info or {}).get("duration") or apify.get_duration(vid) or 0
    # Con durata ignota si prosegue comunque: se c'è un file (es. da Drive)
    # il video è certamente uno vero, non uno Short
    if 0 < duration < cfg["youtube"]["min_duration_seconds"]:
        print(f"   ⏭️ Troppo corto ({duration}s): probabilmente uno Short, salto")
        _mark(st, v, "skipped_short")
        return True

    # Download del video, a cascata: yt-dlp gratis → Apify → cartella Google
    # Drive (il file master caricato dal team: la via che funziona sempre)
    vdir = WORKDIR / vid
    drive_file_id = None
    source = yt.download_video(vid, vdir)
    if source is None:
        source = apify.download_video(vid, vdir, quality=cfg["apify"]["video_quality"])
    if source is None and drive.is_configured():
        used = st.get("used_drive_files", [])
        f = drive.find_new_file(used)
        if f is not None:
            print(f"  📁 Uso il file da Google Drive: {f['name']}")
            source = drive.download_file(f["id"], vdir / f"{vid}.mp4")
            drive_file_id = f["id"]
        else:
            print("  📁 Nessun nuovo file nella cartella Drive")
    if source is None:
        print("   Download impossibile: carica il file del video nella cartella "
              "Drive dedicata, riprovo alla prossima esecuzione")
        return False
    if drive_file_id:
        st.setdefault("used_drive_files", []).append(drive_file_id)

    # Trascrizione con Whisper: parola-per-parola, nessuna dipendenza dai
    # sottotitoli automatici di YouTube
    words = transcribe.transcribe_words(source, model_size=cfg["whisper"]["model"])
    if len(words) < 50:
        print("   ⏭️ Trascrizione troppo scarna, salto")
        _mark(st, v, "skipped_no_transcript")
        return True

    clip_cfg = cfg["clips"]
    picks = brain.select_clips(
        transcript.to_timed_text(words),
        v["title"],
        model=cfg["claude"]["model"],
        brand_context=cfg["claude"]["brand_context"],
        clips_per_video=clip_cfg["per_video"],
        min_seconds=clip_cfg["min_seconds"],
        max_seconds=clip_cfg["max_seconds"],
    )
    if not picks:
        print("   ⚠️ Claude non ha trovato clip valide, salto")
        _mark(st, v, "no_clips_found")
        return True
    print(f"   🧠 Claude ha scelto {len(picks)} clip")

    sub_cfg = cfg["subtitles"]
    queued = []
    for n, pick in enumerate(picks, start=1):
        clip_id = f"{vid}-{n}"
        print(f"   ✂️ Clip {n}: [{pick.start_seconds:.0f}s → {pick.end_seconds:.0f}s] «{pick.hook}»")
        start, end = transcript.snap_to_words(words, pick.start_seconds, pick.end_seconds)
        clip_words = transcript.words_in_clip(words, start, end)

        ass_file = subtitles.build_ass(
            clip_words, vdir / f"{clip_id}.ass",
            font=sub_cfg["font"], font_size=sub_cfg["font_size"],
            highlight_color=sub_cfg["highlight_color"], base_color=sub_cfg["base_color"],
            words_per_line=sub_cfg["words_per_line"],
            vertical_position=sub_cfg["vertical_position"],
        )
        out_mp4 = vdir / f"{clip_id}.mp4"
        video.render_clip(
            source, ass_file, out_mp4,
            start=start, end=end, vertical_mode=cfg["clips"]["vertical_mode"],
        )

        r2_key = f"reels/{vid}/{clip_id}.mp4"
        media_url = storage.upload_clip(out_mp4, r2_key)
        print(f"   ☁️ Caricata su R2: {r2_key}")

        caption = _build_caption(pick, cfg)
        st["queue"].append({
            "clip_id": clip_id,
            "video_id": vid,
            "video_title": v["title"],
            "hook": pick.hook,
            "r2_key": r2_key,
            "media_url": media_url,
            "caption": caption,
            "created_at": state_mod.now_iso(),
        })
        queued.append(clip_id)

    _mark(st, v, "done", queued)
    print(f"   ✅ {len(queued)} clip in coda di pubblicazione")
    return True


def _build_caption(pick: brain.ClipPick, cfg: dict) -> str:
    ig = cfg["instagram"]
    parts = [pick.caption.strip()]
    if ig.get("caption_footer"):
        parts.append(ig["caption_footer"].strip())
    tags = " ".join(f"#{t.lstrip('#')}" for t in pick.hashtags)
    if ig.get("default_hashtags"):
        tags = (tags + " " + ig["default_hashtags"].strip()).strip()
    if tags:
        parts.append(tags)
    return "\n\n".join(p for p in parts if p)[:2150]


# ---------------------------------------------------------------- PUBLISH ---

def cmd_publish() -> int:
    cfg = load_config()
    st = state_mod.load_state()

    if not st["queue"]:
        print("✅ Coda vuota: niente da pubblicare")
        return 0

    clip = st["queue"][0]
    print(f"📤 Prossima clip in coda: {clip['clip_id']} — «{clip.get('hook', '')}»")

    if _dry_run() or not cfg["instagram"].get("auto_publish", True):
        print("🧪 DRY RUN / auto_publish disattivato — non pubblico. Caption prevista:")
        print(clip["caption"])
        return 0

    media_url = storage.refresh_url(clip["r2_key"])
    result = instagram.publish_reel(media_url, clip["caption"])

    st["queue"].pop(0)
    st["published"].append({
        "clip_id": clip["clip_id"],
        "video_id": clip["video_id"],
        "hook": clip.get("hook", ""),
        "ig_media_id": result["ig_media_id"],
        "permalink": result["permalink"],
        "published_at": state_mod.now_iso(),
    })
    state_mod.save_state(st)
    print(f"✅ Pubblicato! {result['permalink'] or result['ig_media_id']}")
    return 0


# ----------------------------------------------------------------- STATUS ---

def cmd_status() -> int:
    st = state_mod.load_state()
    print(f"Video processati: {len(st['processed_videos'])}")
    print(f"Clip in coda:     {len(st['queue'])}")
    print(f"Reels pubblicati: {len(st['published'])}")
    for c in st["queue"]:
        print(f"  ⏳ {c['clip_id']} — {c.get('hook', '')}")
    for p in st["published"][-5:]:
        print(f"  ✅ {p['clip_id']} — {p.get('permalink', '')}")
    return 0


def main() -> int:
    commands = {"ingest": cmd_ingest, "publish": cmd_publish, "status": cmd_status}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Uso: python -m src.main [{'|'.join(commands)}]")
        return 1
    return commands[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())

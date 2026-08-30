"""Orchestratore Reels Factory.

Comandi:
  python -m src.main ingest   → controlla nuovi video, taglia le clip, le mette in coda
  python -m src.main publish  → pubblica su Instagram la prossima clip in coda
  python -m src.main status   → riepilogo dello stato

Eseguito da GitHub Actions (vedi .github/workflows/reels-*.yml), ma funziona
anche in locale se hai ffmpeg, yt-dlp e le variabili d'ambiente configurate.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import apify, brain, ricerca_nicchia, scuola, clipcafe, drive, instagram, moviesource, musica, prestazioni, remotion_render, state as state_mod, storage, subtitles, transcribe, transcript, video, yt

ROOT = Path(__file__).resolve().parent.parent
WORKDIR = ROOT / "work"
FONTS_DIR = ROOT / "assets" / "fonts"
AUDIO_DIR = ROOT / "assets" / "audio"
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

    archive_pick = None
    max_age_h = cfg["youtube"]["max_age_days"] * 24
    candidates = [
        v for v in videos
        if not state_mod.is_processed(st, v["video_id"])
        and yt.video_age_hours(v["published"]) <= max_age_h
    ]
    if not candidates:
        v = _archive_candidate(videos, cfg, st)
        if v is None:
            print("✅ Nessun nuovo video da processare")
            return 0
        print(f"📚 Nessun video nuovo: pesco dall'archivio → {v['title']}")
        candidates = [v]
        archive_pick = v["video_id"]

    processed_count = 0
    for v in candidates:
        if processed_count >= MAX_VIDEOS_PER_RUN:
            print("⏭️ Limite video per esecuzione raggiunto, il resto alla prossima")
            break
        ok = _process_video(v, cfg, st)
        if ok:
            processed_count += 1
            # Il video d'archivio si considera speso solo ora: se il download
            # era fallito, alla prossima esecuzione si riprova
            if archive_pick == v["video_id"]:
                st.setdefault("archive_done", []).append(archive_pick)
                st["last_archive_at"] = state_mod.now_iso()
        state_mod.save_state(st)
    return 0


def _batch_force() -> bool:
    """BATCH_FORCE_ARCHIVE=1 ignora l'attesa fra un video d'archivio e l'altro
    e la soglia sulla coda. Serve alle infornate lanciate a mano; le esecuzioni
    programmate non lo impostano mai, quindi la cadenza normale resta intatta."""
    return os.environ.get("BATCH_FORCE_ARCHIVE", "").strip() == "1"


def _archive_candidate(videos: list[dict], cfg: dict, st: dict) -> dict | None:
    """Quando non escono video nuovi, ripesca dai video passati del canale.

    Vincoli: al massimo `max_videos` video d'archivio in tutto, uno solo ogni
    `min_days_between` giorni, e solo se la coda si sta svuotando — così
    l'archivio riempie i buchi senza inondare il profilo.
    """
    arc = cfg.get("archive", {})
    if not arc.get("enabled"):
        return None

    forza = _batch_force()

    if not forza and len(st.get("queue", [])) > arc.get("queue_below", 1):
        return None

    done = len(st.get("archive_done", []))
    if done >= arc.get("max_videos", 5):
        return None

    last = st.get("last_archive_at")
    if last and not forza:
        try:
            elapsed_h = (datetime.now(timezone.utc)
                         - datetime.fromisoformat(last.replace("Z", "+00:00"))
                         ).total_seconds() / 3600
        except ValueError:
            elapsed_h = 1e9
        if elapsed_h < arc.get("min_days_between", 7) * 24:
            rest = arc["min_days_between"] * 24 - elapsed_h
            print(f"📚 Archivio: prossimo video tra {rest / 24:.1f} giorni")
            return None

    # Il più recente tra quelli mai processati (i vecchi vengono dopo i nuovi).
    # NON viene segnato qui: si registra solo a lavoro riuscito, altrimenti un
    # download fallito brucerebbe il video e farebbe partire l'attesa di giorni
    done_ids = set(st.get("archive_done", []))
    for v in videos:
        if not state_mod.is_processed(st, v["video_id"]) and v["video_id"] not in done_ids:
            return v
    return None


def _mark(st: dict, v: dict, status: str, clips: list | None = None) -> None:
    voce = {
        "video_id": v["video_id"],
        "title": v["title"],
        "status": status,
        "processed_at": state_mod.now_iso(),
        "clips": clips or [],
    }
    # Si sostituisce invece di accodare: un video segnato "da_rifare" viene
    # rilavorato, e senza questo si ritroverebbe due volte nell'elenco con
    # due esiti diversi.
    for i, vecchia in enumerate(st["processed_videos"]):
        if vecchia["video_id"] == v["video_id"]:
            st["processed_videos"][i] = voce
            return
    st["processed_videos"].append(voce)


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
        f = drive.find_new_file(used, video_id=vid, titolo=v["title"])
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

    clip_cfg = dict(cfg["clips"])
    if os.environ.get("BATCH_CLIPS", "").strip().isdigit():
        clip_cfg["per_video"] = int(os.environ["BATCH_CLIPS"])
        print(f"   📦 Infornata: {clip_cfg['per_video']} clip da questo video")
    # Prima di scegliere, aggiorna la scheda dei risultati veri: Claude deve
    # vedere quali hook hanno fatto views su QUESTO profilo e quali sono morti.
    # Senza, sceglie al buio applicando regole generali.
    try:
        righe = prestazioni.raccogli(st["published"])
        prestazioni.scrivi_scheda(righe)
        print(f"   📊 Storico aggiornato: numeri veri di {len(righe)} Reel")
    except Exception as e:                      # noqa: BLE001
        # Instagram irraggiungibile non deve fermare la lavorazione: si
        # sceglie con la scheda di ieri, o senza.
        print(f"   ⚠️ Storico non aggiornato ({e}): uso quello precedente")

    picks = brain.select_clips(
        transcript.to_timed_text(words),
        v["title"],
        model=cfg["claude"]["model"],
        brand_context=cfg["claude"]["brand_context"],
        clips_per_video=clip_cfg["per_video"],
        min_seconds=clip_cfg["min_seconds"],
        max_seconds=clip_cfg["max_seconds"],
    )
    # Soglia dura sul punteggio. Il prompt la chiede, ma chiederla non basta:
    # meglio pubblicare tre clip forti che sei di cui due tiepide. Se un video
    # non ha momenti abbastanza buoni, e giusto che ne esca meno del massimo.
    soglia = int(clip_cfg.get("punteggio_minimo", 7))
    scartate = [p for p in picks if p.punteggi and sum(p.punteggi.values()) < soglia]
    for p in scartate:
        print(f"   🚫 Scartata ({sum(p.punteggi.values())}/15, sotto {soglia}): «{p.hook}»")
    picks = [p for p in picks if not (p.punteggi and sum(p.punteggi.values()) < soglia)]

    if not picks:
        print("   ⚠️ Claude non ha trovato clip valide, salto")
        _mark(st, v, "no_clips_found")
        return True
    print(f"   🧠 Tenute {len(picks)} clip su {len(picks) + len(scartate)} candidate")

    sub_cfg = cfg["subtitles"]
    queued = []
    for n, pick in enumerate(picks, start=1):
        clip_id = f"{vid}-{n}"
        somma = sum(pick.punteggi.values()) if pick.punteggi else 0
        assi = " ".join(f"{k}={v}" for k, v in (pick.punteggi or {}).items())
        print(f"   ✂️ Clip {n}: [{pick.start_seconds:.0f}s → {pick.end_seconds:.0f}s] «{pick.hook}»")
        print(f"      punteggio {somma}/15 ({assi})"
              + (f" · bersaglio: {pick.bersaglio}" if pick.bersaglio else " · nessun bersaglio"))
        start, end = transcript.snap_to_sentences(
            words, pick.start_seconds, pick.end_seconds,
            min_seconds=clip_cfg["min_seconds"], max_seconds=clip_cfg["max_seconds"],
        )

        # Cold open: la frase piu tagliente estratta e montata in apertura.
        # Deve stare dentro la clip e almeno 6s dopo il suo inizio, altrimenti
        # si sentirebbe due volte di fila.
        punch = None
        if clip_cfg.get("cold_open", True) and pick.punch_at_seconds > 0:
            t = pick.punch_at_seconds
            if start + 6.0 <= t <= end:
                punch = transcript.sentence_around(
                    words, t,
                    max_seconds=float(clip_cfg.get("cold_open_max_seconds", 6)),
                )
                if punch is not None:
                    ptxt = " ".join(w["word"] for w in words
                                    if punch[0] <= w["start"] <= punch[1])
                    print(f"      ⚡ Cold open ({punch[1]-punch[0]:.1f}s): «{ptxt}»")
        clip_words = transcript.words_for_clip(words, start, end, punch)
        total_len = (end - start) + ((punch[1] - punch[0]) if punch else 0.0)

        # Spezzone di film (facoltativo): se Claude l'ha proposto e almeno una
        # sorgente è configurata. Qualsiasi problema qui NON blocca la clip.
        cutaway, cut_at, cut_dur, cut_src = None, 0.0, 0.0, 0.0
        mv_cfg = cfg.get("movies", {})
        if mv_cfg.get("enabled") and pick.movie_query.strip():
            max_s = mv_cfg.get("max_seconds", 5)
            for src_name in mv_cfg.get("sources", ["clipcafe", "youtube"]):
                if src_name == "clipcafe" and clipcafe.is_configured():
                    found = clipcafe.find_clip(pick.movie_query, max_seconds=max_s)
                    if found and clipcafe.download(found, vdir / f"{clip_id}-film.mp4"):
                        cutaway = vdir / f"{clip_id}-film.mp4"
                        cut_dur = min(found["duration"], max_s)
                        break
                elif src_name == "youtube" and moviesource.is_configured():
                    found = moviesource.find_clip(pick.movie_query, vdir,
                                                  max_seconds=max_s)
                    if found:
                        cutaway = found["path"]
                        cut_dur = found["duration"]
                        cut_src = found["src_offset"]
                        break
        if cutaway is not None:
            # Dentro la clip: mai nei primi 2s (l'hook è sacro), mai oltre la fine
            offset = (punch[1] - punch[0]) if punch else 0.0
            rel = pick.movie_insert_at_seconds - start + offset
            cut_at = min(max(rel, offset + 2.0),
                         max(offset + 2.0, total_len - cut_dur - 1.0))

        # Sound design: base musicale (scelta stabile per clip) + whoosh + pop
        # sulle parole enfatizzate da Claude
        audio_cfg = cfg.get("audio", {})
        music = whoosh = pop = None
        if audio_cfg.get("music", True):
            # La base non si tira piu a sorte: Claude dice che carattere ha la
            # clip (tensione, riflessivo, spinta, racconto) e si prende la
            # traccia di quel carattere.
            #
            # Il ripiego cerca "bed-*-*.mp3", con due trattini, e non e un
            # dettaglio: prende solo le basi costruite da musica.py, di cui
            # conosciamo autore e licenza. Le tre vecchie (bed-futuristica,
            # bed-hiphop, bed-piano) hanno un solo trattino e restano fuori,
            # perche di quelle non sappiamo da dove vengano — e roba che
            # finisce su un profilo pubblico.
            mood = (getattr(pick, "mood", "") or "").strip().lower()
            beds = sorted(AUDIO_DIR.glob(f"bed-{mood}-*.mp3")) if mood else []
            if not beds:
                beds = sorted(AUDIO_DIR.glob("bed-*-*.mp3"))
                if mood:
                    print(f"   🎵 Nessuna traccia per '{mood}': uso il fondo generico")
            if beds:
                music = beds[int(hashlib.md5(clip_id.encode()).hexdigest(), 16)
                             % len(beds)]
                print(f"   🎵 Base musicale: {music.name}"
                      + (f" (carattere: {mood})" if mood else ""))
        if audio_cfg.get("whoosh_on_cutaway", True):
            wf = AUDIO_DIR / "sfx-whoosh.wav"
            whoosh = wf if wf.is_file() else None

        emph = {"".join(c for c in w.lower() if c.isalnum())
                for w in pick.emphasis_words}
        pop_times: list[float] = []
        if audio_cfg.get("pop_on_emphasis", True) and emph:
            pf = AUDIO_DIR / "sfx-pop.wav"
            if pf.is_file():
                pop = pf
                pop_times = remotion_render.emphasis_times(clip_words, emph)

        render_common = dict(
            start=start, end=end,
            punch_start=punch[0] if punch else 0.0,
            punch_end=punch[1] if punch else 0.0,
            vertical_mode=cfg["clips"]["vertical_mode"],
            cutaway=cutaway, cutaway_at=cut_at, cutaway_duration=cut_dur,
            cutaway_src_offset=cut_src,
            corner_radius=cfg["clips"].get("corner_radius", 96),
            zoom=cfg["clips"].get("zoom", 0),
            music=music,
            music_gain_db=audio_cfg.get("music_gain_db", -20),
            ducking=audio_cfg.get("ducking", True),
            whoosh=whoosh, pop=pop, pop_times=pop_times,
        )

        out_mp4 = vdir / f"{clip_id}.mp4"
        rendered = False
        if cfg["clips"].get("renderer", "remotion") == "remotion":
            try:
                base_mp4 = vdir / f"{clip_id}-base.mp4"
                video.render_clip(source, None, base_mp4, **render_common)
                pages = remotion_render.build_pages(
                    clip_words, emph,
                    words_per_screen=sub_cfg["words_per_line"],
                )
                remotion_render.render(
                    base_mp4, out_mp4,
                    pages=pages, duration=total_len,
                    font_size=sub_cfg["font_size"],
                    vertical_position=sub_cfg["vertical_position"],
                    uppercase=sub_cfg.get("uppercase", False),
                    hook_text=pick.hook if cfg["clips"].get("hook_card", True) else "",
                    hook_seconds=float(cfg["clips"].get("hook_card_seconds", 0)),
                )
                rendered = True
            except Exception as e:  # noqa: BLE001 — il fallback ASS tiene viva la pipeline
                print(f"   ⚠️ Remotion fallito, uso il renderer classico: {e}")
        if not rendered:
            ass_file = subtitles.build_ass(
                clip_words, vdir / f"{clip_id}.ass",
                font=sub_cfg["font"], font_size=sub_cfg["font_size"],
                highlight_color=sub_cfg["highlight_color"],
                base_color=sub_cfg["base_color"],
                words_per_line=sub_cfg["words_per_line"],
                vertical_position=sub_cfg["vertical_position"],
                style=sub_cfg.get("style", "word"),
                uppercase=sub_cfg.get("uppercase", False),
            )
            video.render_clip(
                source, ass_file, out_mp4,
                fonts_dir=FONTS_DIR if FONTS_DIR.is_dir() else None,
                **render_common,
            )

        r2_key = f"reels/{vid}/{clip_id}.mp4"
        media_url = storage.upload_clip(out_mp4, r2_key)
        print(f"   ☁️ Caricata su R2: {r2_key}")

        caption = _build_caption(pick, cfg, con_musica=music is not None)
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


def _build_caption(pick: brain.ClipPick, cfg: dict, *, con_musica: bool = False) -> str:
    ig = cfg["instagram"]
    parts = [pick.caption.strip()]
    if ig.get("caption_footer"):
        parts.append(ig["caption_footer"].strip())

    # Hashtag di Claude + quelli fissi, senza ripetizioni (Claude propone
    # spesso gli stessi che abbiamo già in coda) e mantenendo l'ordine
    raw = list(pick.hashtags) + (ig.get("default_hashtags") or "").split()
    seen, tags = set(), []
    for t in raw:
        tag = t.strip().lstrip("#")
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(f"#{tag}")
    if tags:
        parts.append(" ".join(tags))
    # La licenza della musica chiede la citazione dell'autore. Va in fondo,
    # dopo gli hashtag, dove non toglie niente al messaggio — e ci va solo se
    # una base c'e davvero.
    if con_musica:
        parts.append(musica.credito())
    return "\n\n".join(p for p in parts if p)[:2150]



def _ora_italiana() -> int:
    """L'ora corrente a Roma. Con zoneinfo l'ora legale è gestita da sola;
    se i dati dei fusi non ci fossero sul runner, si ripiega su UTC+2, che
    d'estate è l'offset giusto e d'inverno sbaglia di un'ora — abbastanza per
    un controllo che serve solo a distinguere il giorno dalla notte."""
    from datetime import timedelta
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Rome")).hour
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=2)).hour


# ---------------------------------------------------------------- PUBLISH ---

def cmd_publish() -> int:
    cfg = load_config()
    st = state_mod.load_state()

    if not st["queue"]:
        print("✅ Coda vuota: niente da pubblicare")
        return 0

    # Una sola pubblicazione al giorno, anche se il workflow parte piu volte.
    # Gli orari di riserva servono solo a coprire i ritardi di GitHub (il 27/08
    # l'esecuzione delle 09:30 e arrivata alle 19:55, il 28/08 non e arrivata):
    # non devono trasformarsi in tre Reel nello stesso giorno.
    forzato = os.environ.get("PUBLISH_FORCE", "").strip().lower() in ("1", "true", "yes")
    if st["published"] and not forzato:
        ultima = st["published"][-1].get("published_at", "")[:10]
        if ultima == state_mod.now_iso()[:10]:
            print(f"✅ Gia pubblicato oggi ({ultima}): non ne esce un secondo")
            return 0

    # Fuori dall'orario buono non si pubblica: meglio saltare un turno che
    # bruciare una clip alle 3 di notte (successo il 29/08, con l'esecuzione
    # delle 19:30 consegnata da GitHub sette ore e mezza dopo).
    finestra = cfg["instagram"].get("ore_pubblicazione")
    if finestra and not forzato:
        ora_it = _ora_italiana()
        if not (finestra[0] <= ora_it < finestra[1]):
            print(f"🌙 Sono le {ora_it}:xx in Italia, fuori dalla finestra "
                  f"{finestra[0]}-{finestra[1]}: non pubblico, ci pensa il turno dopo")
            return 0

    clip = st["queue"][0]
    print(f"📤 Prossima clip in coda: {clip['clip_id']} — «{clip.get('hook', '')}»")

    if _dry_run() or not cfg["instagram"].get("auto_publish", True):
        print("🧪 DRY RUN / auto_publish disattivato — non pubblico. Caption prevista:")
        print(clip["caption"])
        # Verifica del collegamento a Instagram senza pubblicare nulla:
        # serve a sapere in anticipo se l'account risponde
        print(instagram.check_connection())
        return 0

    media_url = storage.refresh_url(clip["r2_key"])
    try:
        result = instagram.publish_reel(media_url, clip["caption"])
    except instagram.InstagramError:
        # Il 26/08 la pubblicazione ha smesso di funzionare restituendo sempre
        # lo stesso errore generico. Da solo non dice niente: stampiamo subito
        # token, permessi e quota, cosi il log dice se e un blocco vero.
        print(instagram.diagnose())
        raise

    registrazione = {
        "clip_id": clip["clip_id"],
        "video_id": clip["video_id"],
        "hook": clip.get("hook", ""),
        "ig_media_id": result["ig_media_id"],
        "permalink": result["permalink"],
        "published_at": state_mod.now_iso(),
    }

    # La ricevuta viene scritta PRIMA dello stato. Il 28/08 il Reel e uscito
    # ma il salvataggio dello stato e stato rifiutato (nel frattempo la
    # lavorazione aveva scritto sul repo): il sistema credeva la clip ancora
    # in coda e l'avrebbe ripubblicata il giorno dopo. Con la ricevuta su
    # disco il passo di commit puo riapplicare la modifica sullo stato
    # aggiornato, quante volte serve.
    RICEVUTA.write_text(json.dumps(registrazione, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    _registra(st, registrazione)
    state_mod.save_state(st)
    print(f"✅ Pubblicato! {result['permalink'] or result['ig_media_id']}")
    return 0


# --------------------------------------------------- REGISTRA PUBBLICAZIONE ---

RICEVUTA = Path(__file__).resolve().parent.parent / "state" / "ultima-pubblicazione.json"


def _registra(st: dict, reg: dict) -> bool:
    """Toglie la clip dalla coda e la mette tra le pubblicate. Idempotente:
    richiamarla due volte sulla stessa ricevuta non cambia niente."""
    gia = any(p["clip_id"] == reg["clip_id"] for p in st["published"])
    prima = len(st["queue"])
    st["queue"] = [c for c in st["queue"] if c["clip_id"] != reg["clip_id"]]
    if not gia:
        st["published"].append(reg)
    return not gia or len(st["queue"]) != prima


def cmd_registra() -> int:
    """Riapplica l'ultima ricevuta di pubblicazione sullo stato corrente.
    Serve al passo di commit: se il salvataggio viene rifiutato perche un'altra
    esecuzione ha scritto nel frattempo, si riparte dallo stato aggiornato e si
    riapplica solo questa modifica, invece di perdere il Reel gia pubblicato."""
    if not RICEVUTA.exists():
        print("Nessuna ricevuta da registrare")
        return 0
    reg = json.loads(RICEVUTA.read_text(encoding="utf-8"))
    st = state_mod.load_state()
    if _registra(st, reg):
        state_mod.save_state(st)
        print(f"📝 Registrata la pubblicazione di {reg['clip_id']}")
    else:
        print(f"📝 {reg['clip_id']} era gia registrata")
    return 0


# ---------------------------------------------------------------- NICCHIA ---

def cmd_nicchia() -> int:
    """Va a vedere come sono costruiti i video brevi che sfondano nella
    nicchia, e ne scrive gli schemi. Nessun intervento umano, nessuna chiave
    da procurarsi, nessun servizio a pagamento: solo gli elenchi pubblici di
    YouTube, letti con yt-dlp.

    Perche gli Shorts e non i Reel: stesso formato, stesso pubblico, stesse
    regole di aggancio — ma leggibili senza chiedere niente a nessuno,
    mentre per i Reel ogni strada passa da uno scraper a pagamento."""
    cfg = load_config()
    ric = cfg.get("nicchia", {})
    query = ric.get("ricerche") or []
    if not query:
        print("⚠️ Nessuna ricerca configurata (chiave nicchia.ricerche)")
        return 1

    print(f"🎓 Cerco i video brevi forti su {len(query)} filoni")
    try:
        video = scuola.outlier(
            query,
            model=cfg["claude"]["model"],
            per_ricerca=int(ric.get("per_ricerca", 25)),
            scarto_minimo=float(ric.get("scarto_minimo", 3.0)),
            canali_max=int(ric.get("canali_max", 20)),
            shorts_per_canale=int(ric.get("shorts_per_canale", 30)),
            mediana_minima=int(ric.get("mediana_minima", 500)),
            views_minime=int(ric.get("views_minime", 5000)),
            per_canale_max=int(ric.get("per_canale_max", 4)),
            # Il canale di casa si esclude: la scuola serve a imparare cosa
            # fanno gli ALTRI, non a rispecchiare quello che facciamo gia.
            escludi={cfg["youtube"]["channel_id"]},
        )
    except scuola.ScuolaError as e:
        print(f"⛔ {e}")
        return 1

    # La vendemmia di oggi si somma a quelle passate: la nicchia italiana e
    # piccola e un giro solo non basta a distinguere uno schema da un caso.
    video = scuola.accumula(video, per_canale_max=int(ric.get("per_canale_max", 4)))

    if len(video) < 10:
        print(f"   ⚠️ Solo {len(video)} video nello storico: troppo pochi per "
              "estrarre schemi affidabili. Lascio la scheda precedente.")
        return 0

    for v in video[:8]:
        print(f"      {v['scarto']:>5}x  {v['views']:>9,} views  {v['titolo'][:58]}")

    schemi = scuola.distilla(video, model=cfg["claude"]["model"])
    scuola.scrivi_scheda(video, schemi, query)
    print(f"   🎓 nicchia.md riscritto su {len(video)} video")
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


def cmd_musica() -> int:
    """Ricostruisce la libreria musicale in assets/audio.

    Si lancia a mano e di rado: i file finiscono nel repository, quindi ogni
    montaggio se li trova gia li senza scaricare niente. Serve quando si
    vuole cambiare aria — altre basi per gli stessi quattro caratteri."""
    fatti = musica.costruisci()
    if not fatti:
        print("⛔ Nessuna base scaricata")
        return 1
    print(f"   🎵 {fatti} basi pronte in assets/audio")
    return 0


def main() -> int:
    commands = {"ingest": cmd_ingest, "publish": cmd_publish,
                "registra": cmd_registra, "nicchia": cmd_nicchia,
                "musica": cmd_musica, "status": cmd_status}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"Uso: python -m src.main [{'|'.join(commands)}]")
        return 1
    return commands[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())

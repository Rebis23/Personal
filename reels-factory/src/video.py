"""Montaggio con ffmpeg: taglio della clip, conversione 9:16, sottotitoli
impressi, eventuale spezzone di film in sovraimpressione (cutaway)."""

import subprocess
from pathlib import Path

SQUARE_Y = 420  # il quadrato 1080x1080 parte qui sulla tela 1080x1920


def _vertical_filter(mode: str, duration: float, zoom: float,
                     src: str = "[0:v]") -> str:
    if mode == "crop":
        # Ritaglio centrale 9:16 a piena altezza
        return f"{src}crop=ih*9/16:ih,scale=1080:1920,setsar=1[vmain]"
    if mode == "square":
        # Stile Modern Wisdom: video ritagliato quadrato (persona al centro)
        # su tela nera 9:16, con un lento push-in per dare vita all'inquadratura
        push = ""
        if zoom > 0:
            rate = zoom / max(1.0, duration * 30)
            push = (
                f",zoompan=z='1+{rate:.7f}*in'"
                ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                ":d=1:s=1080x1080:fps=30"
            )
        return (
            f"{src}crop=ih:ih,scale=1080:1080,setsar=1{push},"
            f"pad=1080:1920:0:{SQUARE_Y}:black[vmain]"
        )
    # Default "blur": video intero centrato su sfondo sfocato
    return (
        f"{src}split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=24,eq=brightness=-0.08[bgb];"
        "[fg]scale=1080:-2[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[vmain]"
    )


def _corner_mask(radius: int, out_path: Path) -> Path:
    """PNG 1080x1920 trasparente con gli angoli del quadrato coperti di nero:
    sovrapposto al video, arrotonda gli angoli del riquadro (lo sfondo è nero).
    Antialias tramite disegno a 4x e ridimensionamento."""
    from PIL import Image, ImageDraw, ImageOps

    s = 4
    mask = Image.new("L", (1080 * s, 1080 * s), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle(
        [0, 0, 1080 * s - 1, 1080 * s - 1], radius=radius * s, fill=255,
    )
    mask = mask.resize((1080, 1080), Image.LANCZOS)

    corners = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    black = Image.new("RGBA", (1080, 1080), (0, 0, 0, 255))
    black.putalpha(ImageOps.invert(mask))
    corners.paste(black, (0, SQUARE_Y), black)
    corners.save(out_path)
    return out_path


def render_clip(
    source: Path,
    ass_file: Path | None,
    out_path: Path,
    *,
    start: float,
    end: float,
    punch_start: float = 0.0,
    punch_end: float = 0.0,
    vertical_mode: str = "square",
    fonts_dir: Path | None = None,
    cutaway: Path | None = None,
    cutaway_at: float = 0.0,
    cutaway_duration: float = 0.0,
    cutaway_src_offset: float = 0.0,
    corner_radius: int = 96,
    zoom: float = 0.0,
    music: Path | None = None,
    music_gain_db: float = -20.0,
    ducking: bool = True,
    whoosh: Path | None = None,
    pop: Path | None = None,
    pop_times: list[float] | None = None,
) -> Path:
    """Taglia [start, end], converte in 1080x1920 e imprime i sottotitoli.

    Se `cutaway` è indicato, lo spezzone (muto) viene mostrato al posto del
    video del parlato da `cutaway_at` (secondi dall'inizio della clip) per
    `cutaway_duration` secondi; l'audio del parlato continua sotto.

    Sound design: `music` è la base musicale in sottofondo (in loop, con
    dissolvenza finale; se `ducking` è attivo si abbassa da sola quando c'è
    la voce); `whoosh` è l'effetto riprodotto all'ingresso del cutaway.
    """
    duration = max(1.0, end - start)
    # Cold open: il momento piu forte della clip viene mostrato per primo, poi
    # parte la clip dall'inizio (richiesta di Lorenzo, 25/08). E lo stesso file
    # aperto due volte con due punti di partenza: si concatena prima di tutto
    # il resto, cosi la grafica e il sound design lavorano sull'insieme.
    punch_duration = max(0.0, punch_end - punch_start)
    has_punch = punch_duration >= 1.0
    total = duration + (punch_duration if has_punch else 0.0)

    # Senza file .ass i sottotitoli non vengono impressi qui (li disegna
    # Remotion in un secondo passaggio)
    ass_arg = None
    if ass_file is not None:
        ass_arg = f"ass={ass_file.name}"
        if fonts_dir is not None:
            ass_arg += f":fontsdir={fonts_dir}"

    inputs: list[str] = []
    parts: list[str] = []
    if has_punch:
        inputs += ["-ss", f"{punch_start:.3f}", "-t", f"{punch_duration:.3f}",
                   "-i", str(source)]
    inputs += ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source)]
    n_inputs = 2 if has_punch else 1

    if has_punch:
        parts.append(
            "[0:v]fps=30,setsar=1,setpts=PTS-STARTPTS[cv0];"
            "[1:v]fps=30,setsar=1,setpts=PTS-STARTPTS[cv1];"
            "[cv0][cv1]concat=n=2:v=1:a=0[vsrc]"
        )
        parts.append(
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            "asetpts=PTS-STARTPTS[ca0];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            "asetpts=PTS-STARTPTS[ca1];"
            "[ca0][ca1]concat=n=2:v=0:a=1[asrc]"
        )
        vsrc, asrc = "[vsrc]", "[asrc]"
    else:
        vsrc, asrc = "[0:v]", "[0:a]"

    parts.append(_vertical_filter(vertical_mode, total, zoom, src=vsrc))
    last = "[vmain]"

    if cutaway is not None and cutaway_duration > 0.25:
        # -ss prima dell'input: lo spezzone parte dal momento giusto della scena
        if cutaway_src_offset > 0:
            inputs += ["-ss", f"{cutaway_src_offset:.3f}"]
        inputs += ["-i", str(cutaway)]
        idx = n_inputs
        n_inputs += 1
        t1, t2 = cutaway_at, cutaway_at + cutaway_duration
        parts.append(
            f"[{idx}:v]crop=ih:ih,scale=1080:1080,setsar=1,fps=30,"
            f"trim=duration={cutaway_duration:.3f},"
            f"setpts=PTS-STARTPTS+{t1:.3f}/TB[cut]"
        )
        parts.append(
            f"{last}[cut]overlay=(W-w)/2:{SQUARE_Y}:eof_action=pass"
            f":enable='between(t,{t1:.3f},{t2:.3f})'[vover]"
        )
        last = "[vover]"

    if vertical_mode == "square" and corner_radius > 0:
        aux_dir = ass_file.parent if ass_file is not None else out_path.parent
        mask_png = _corner_mask(corner_radius, aux_dir / "corners.png")
        inputs += ["-loop", "1", "-i", str(mask_png)]
        idx = n_inputs
        n_inputs += 1
        parts.append(f"{last}[{idx}:v]overlay=0:0:shortest=1[vcorn]")
        last = "[vcorn]"

    parts.append(f"{last}{ass_arg}[vout]" if ass_arg else f"{last}null[vout]")

    # ------------------------------------------------------- sound design ---
    audio_map = ["-map", "[asrc]"] if has_punch else ["-map", "0:a?"]
    mix_srcs: list[str] = []
    has_whoosh = (whoosh is not None and cutaway is not None
                  and cutaway_duration > 0.25)
    pop_times = [t for t in (pop_times or []) if 0.3 < t < total - 0.5][:4]
    has_pops = pop is not None and len(pop_times) > 0
    if music is not None or has_whoosh or has_pops:
        parts.append(f"{asrc}aformat=sample_rates=44100:channel_layouts=stereo[voice]")

    if music is not None:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        m_idx = n_inputs
        n_inputs += 1
        fade_start = max(0.0, total - 1.2)
        parts.append(
            f"[{m_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"atrim=duration={total:.3f},volume={music_gain_db:.1f}dB,"
            f"afade=t=out:st={fade_start:.3f}:d=1.2[mus]"
        )
        if ducking:
            parts.append("[voice]asplit=2[v1][v2]")
            parts.append(
                "[mus][v2]sidechaincompress=threshold=0.05:ratio=8"
                ":attack=20:release=500[musd]"
            )
            voice_lbl, music_lbl = "[v1]", "[musd]"
        else:
            voice_lbl, music_lbl = "[voice]", "[mus]"
        mix_srcs = [voice_lbl, music_lbl]
    elif has_whoosh or has_pops:
        mix_srcs = ["[voice]"]

    if has_pops:
        # Colpo soft in corrispondenza delle parole enfatizzate
        inputs += ["-i", str(pop)]
        p_idx = n_inputs
        n_inputs += 1
        n = len(pop_times)
        parts.append(
            f"[{p_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume=-12dB,asplit={n}" + "".join(f"[pp{i}]" for i in range(n))
        )
        for i, t in enumerate(pop_times):
            ms = int(t * 1000)
            parts.append(f"[pp{i}]adelay={ms}|{ms}[pd{i}]")
            mix_srcs.append(f"[pd{i}]")

    if has_whoosh:
        inputs += ["-i", str(whoosh)]
        w_idx = n_inputs
        n_inputs += 1
        delay_ms = max(0, int((cutaway_at - 0.25) * 1000))
        parts.append(
            f"[{w_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms},volume=-8dB[wh]"
        )
        mix_srcs.append("[wh]")

    if len(mix_srcs) == 1:
        # Una sola sorgente: niente da miscelare, ma [asrc] e gia stato
        # consumato da [voice] — si mappa quella
        audio_map = ["-map", mix_srcs[0]]
    if len(mix_srcs) > 1:
        parts.append(
            f"{''.join(mix_srcs)}amix=inputs={len(mix_srcs)}"
            ":duration=first:normalize=0,alimiter=limit=0.97[aout]"
        )
        audio_map = ["-map", "[aout]"]

    filter_complex = ";".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", *audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
        str(out_path),
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # cwd = cartella del file .ass, così il filtro "ass=" non ha problemi
    # di escaping del percorso
    workdir = ass_file.parent if ass_file is not None else out_path.parent
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"ffmpeg fallito:\n{proc.stderr[-1500:]}")
    return out_path

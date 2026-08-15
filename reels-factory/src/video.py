"""Montaggio con ffmpeg: taglio della clip, conversione 9:16, sottotitoli
impressi, eventuale spezzone di film in sovraimpressione (cutaway)."""

import subprocess
from pathlib import Path


def _vertical_filter(mode: str) -> str:
    if mode == "crop":
        # Ritaglio centrale 9:16 a piena altezza
        return "[0:v]crop=ih*9/16:ih,scale=1080:1920,setsar=1[vmain]"
    if mode == "square":
        # Stile Modern Wisdom: video ritagliato quadrato (persona al centro)
        # su tela nera 9:16
        return (
            "[0:v]crop=ih:ih,scale=1080:1080,setsar=1,"
            "pad=1080:1920:0:420:black[vmain]"
        )
    # Default "blur": video intero centrato su sfondo sfocato
    return (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=24,eq=brightness=-0.08[bgb];"
        "[fg]scale=1080:-2[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[vmain]"
    )


def render_clip(
    source: Path,
    ass_file: Path,
    out_path: Path,
    *,
    start: float,
    end: float,
    vertical_mode: str = "square",
    fonts_dir: Path | None = None,
    cutaway: Path | None = None,
    cutaway_at: float = 0.0,
    cutaway_duration: float = 0.0,
) -> Path:
    """Taglia [start, end], converte in 1080x1920 e imprime i sottotitoli.

    Se `cutaway` è indicato, lo spezzone (muto) viene mostrato al posto del
    video del parlato da `cutaway_at` (secondi dall'inizio della clip) per
    `cutaway_duration` secondi; l'audio del parlato continua sotto.
    """
    duration = max(1.0, end - start)

    ass_arg = f"ass={ass_file.name}"
    if fonts_dir is not None:
        ass_arg += f":fontsdir={fonts_dir}"

    inputs = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(source)]
    parts = [_vertical_filter(vertical_mode)]

    if cutaway is not None and cutaway_duration > 0.25:
        inputs += ["-i", str(cutaway)]
        t1, t2 = cutaway_at, cutaway_at + cutaway_duration
        parts.append(
            "[1:v]crop=ih:ih,scale=1080:1080,setsar=1,fps=30,"
            f"trim=duration={cutaway_duration:.3f},"
            f"setpts=PTS-STARTPTS+{t1:.3f}/TB[cut]"
        )
        parts.append(
            f"[vmain][cut]overlay=(W-w)/2:(H-h)/2:eof_action=pass"
            f":enable='between(t,{t1:.3f},{t2:.3f})'[vover]"
        )
        last = "[vover]"
    else:
        last = "[vmain]"

    parts.append(f"{last}{ass_arg}[vout]")
    filter_complex = ";".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
        str(out_path),
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # cwd = cartella del file .ass, così il filtro "ass=" non ha problemi
    # di escaping del percorso
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ass_file.parent)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"ffmpeg fallito:\n{proc.stderr[-1500:]}")
    return out_path

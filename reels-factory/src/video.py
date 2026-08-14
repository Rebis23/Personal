"""Montaggio con ffmpeg: taglio della clip, conversione 9:16, sottotitoli impressi."""

import subprocess
from pathlib import Path


def _vertical_filter(mode: str) -> str:
    if mode == "crop":
        # Ritaglio centrale 9:16 a piena altezza
        return "[0:v]crop=ih*9/16:ih,scale=1080:1920,setsar=1[vmain]"
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
    vertical_mode: str = "blur",
) -> Path:
    """Taglia [start, end], converte in 1080x1920 e imprime i sottotitoli."""
    duration = max(1.0, end - start)
    filter_complex = (
        f"{_vertical_filter(vertical_mode)};"
        f"[vmain]ass={ass_file.name}[vout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(source),
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

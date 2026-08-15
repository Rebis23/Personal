"""Montaggio con ffmpeg: taglio della clip, conversione 9:16, sottotitoli
impressi, eventuale spezzone di film in sovraimpressione (cutaway)."""

import subprocess
from pathlib import Path

SQUARE_Y = 420  # il quadrato 1080x1080 parte qui sulla tela 1080x1920


def _vertical_filter(mode: str, duration: float, zoom: float) -> str:
    if mode == "crop":
        # Ritaglio centrale 9:16 a piena altezza
        return "[0:v]crop=ih*9/16:ih,scale=1080:1920,setsar=1[vmain]"
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
            f"[0:v]crop=ih:ih,scale=1080:1080,setsar=1{push},"
            f"pad=1080:1920:0:{SQUARE_Y}:black[vmain]"
        )
    # Default "blur": video intero centrato su sfondo sfocato
    return (
        "[0:v]split=2[bg][fg];"
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
    corner_radius: int = 48,
    zoom: float = 0.06,
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
    parts = [_vertical_filter(vertical_mode, duration, zoom)]
    last = "[vmain]"
    n_inputs = 1

    if cutaway is not None and cutaway_duration > 0.25:
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
        mask_png = _corner_mask(corner_radius, ass_file.parent / "corners.png")
        inputs += ["-loop", "1", "-i", str(mask_png)]
        idx = n_inputs
        n_inputs += 1
        parts.append(f"{last}[{idx}:v]overlay=0:0:shortest=1[vcorn]")
        last = "[vcorn]"

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

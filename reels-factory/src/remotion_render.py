"""Ponte verso Remotion: il motore che disegna le caption animate premium
(stile Williamson) sopra il video base già montato da ffmpeg.

Flusso: ffmpeg produce il video base (taglio, quadrato su nero, angoli,
cutaway, audio completo) → qui Remotion ci renderizza sopra le caption
(pop-in a molla, ombra diffusa, parole enfatizzate in corsivo) e la
hook card iniziale.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = ROOT / "remotion"


def is_available() -> bool:
    return (REMOTION_DIR / "node_modules" / ".bin" / "remotion").exists() or \
        shutil.which("npx") is not None


def build_pages(words: list[dict], emphasis: set[str],
                words_per_screen: int = 3) -> list[dict]:
    """Raggruppa le parole in pagine da 2-3, spezzando sulle pause naturali.
    `emphasis` = parole (minuscole, senza punteggiatura) da enfatizzare."""
    def norm(w: str) -> str:
        return "".join(c for c in w.lower() if c.isalnum())

    groups: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (len(cur) >= words_per_screen
                    or w["start"] - cur[-1]["end"] > 0.7):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    pages = []
    for i, g in enumerate(groups):
        start = g[0]["start"]
        if i + 1 < len(groups):
            end = min(groups[i + 1][0]["start"], g[-1]["end"] + 0.8)
        else:
            end = g[-1]["end"] + 0.4
        pages.append({
            "start": round(max(0.0, start), 3),
            "end": round(max(start + 0.15, end), 3),
            "words": [
                {"text": w["word"].strip(), "em": norm(w["word"]) in emphasis}
                for w in g
            ],
        })
    return pages


def emphasis_times(words: list[dict], emphasis: set[str]) -> list[float]:
    """Istanti (secondi dall'inizio clip) in cui parte una parola enfatizzata."""
    def norm(w: str) -> str:
        return "".join(c for c in w.lower() if c.isalnum())
    return [w["start"] for w in words if norm(w["word"]) in emphasis]


def render(base_video: Path, out_path: Path, *, pages: list[dict],
           duration: float, font_size: int, vertical_position: float,
           uppercase: bool, hook_text: str = "", hook_seconds: float = 0.0,
           timeout_minutes: int = 25) -> Path:
    """Renderizza la clip finale con Remotion. Solleva RuntimeError se fallisce."""
    public_input = REMOTION_DIR / "public" / "input.mp4"
    shutil.copyfile(base_video, public_input)

    props = {
        "video": "input.mp4",
        "durationSeconds": round(duration, 3),
        "pages": pages,
        "fontSize": font_size,
        "verticalPosition": vertical_position,
        "uppercase": uppercase,
        "hookText": hook_text,
        "hookSeconds": round(hook_seconds, 3),
    }
    props_file = REMOTION_DIR / "props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render", "src/index.ts", "Reel", str(out_path),
        f"--props={props_file}",
        "--codec=h264",
        "--audio-codec=aac",
        "--log=error",
    ]
    env = dict(os.environ)
    proc = subprocess.run(
        cmd, cwd=REMOTION_DIR, capture_output=True, text=True,
        timeout=timeout_minutes * 60, env=env,
    )
    public_input.unlink(missing_ok=True)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(
            f"Remotion fallito:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}"
        )
    return out_path

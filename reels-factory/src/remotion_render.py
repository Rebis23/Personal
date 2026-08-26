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
    """Caption karaoke secondo il playbook "Riflettendo Edit".

    Regole (Sezione SHORTS del playbook, applicate alla lettera):
    - blocchi di 2-3 parole; blocco nuovo a pausa >= 0.45s oppure su
      punteggiatura
    - visibile da blocco.start - 0.04 fino a blocco_successivo.start - 0.04,
      cosi non ci sono mai due caption insieme
    - ogni parola porta il suo istante: compare quando viene pronunciata

    `emphasis` = parole da enfatizzare (corsivo e alone, come approvato).
    """
    def norm(w: str) -> str:
        return "".join(c for c in w.lower() if c.isalnum())

    def chiude(w: str) -> bool:
        return w.strip().endswith((".", ",", "!", "?", ";", ":", "…"))

    PAUSA = 0.45
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (len(cur) >= words_per_screen
                    or w["start"] - cur[-1]["end"] >= PAUSA
                    or chiude(cur[-1]["word"])):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    # Una virgola puo lasciare una parola sola a schermo ("felice,"): le
    # parole isolate si riuniscono al blocco vicino, purche non si superino
    # le tre parole
    fusi: list[list[dict]] = []
    for g in groups:
        if (len(g) == 1 and fusi
                and len(fusi[-1]) + 1 <= words_per_screen
                and g[0]["start"] - fusi[-1][-1]["end"] < PAUSA):
            fusi[-1].extend(g)
        else:
            fusi.append(g)
    # Chi non ha trovato posto nel blocco precedente prova con il successivo
    uniti: list[list[dict]] = []
    i = 0
    while i < len(fusi):
        g = fusi[i]
        seguente = fusi[i + 1] if i + 1 < len(fusi) else None
        if (len(g) == 1 and seguente
                and len(seguente) + 1 <= words_per_screen
                and seguente[0]["start"] - g[-1]["end"] < PAUSA):
            uniti.append(g + seguente)
            i += 2
            continue
        uniti.append(g)
        i += 1
    groups = uniti

    ANTICIPO = 0.04
    pages = []
    for i, g in enumerate(groups):
        start = max(0.0, g[0]["start"] - ANTICIPO)
        if i + 1 < len(groups):
            end = max(start + 0.12, groups[i + 1][0]["start"] - ANTICIPO)
        else:
            end = g[-1]["end"] + 0.4
        parole = [
            # lstrip: Whisper a volte produce parole tipo "'attenzione"
            {"text": w["word"].strip().lstrip("'\u2019"),
             "em": norm(w["word"]) in emphasis}
            for w in g
        ]
        pages.append({"start": round(start, 3), "end": round(end, 3),
                      "words": parole})
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

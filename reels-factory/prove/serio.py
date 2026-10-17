"""Lo stile serio: fotografia fredda e banner bianco su nero.

Lorenzo, 17/10, mandando lo screenshot di uno Short — «Renowned
Neuroscientist ON GOD», bianco su nero con le ultime due parole in blu:

> «voglio fare in modo che alcuni dei video che magari sono quelli un po'
> più filosofici, un po' più profondi [...] metteci un hook di questo tipo
> con una scritta seria [...] metteci magari anche un filter un pochino
> gray, una color correction per farlo sembrare cinematic, ci sono tutti
> questi piccoli trucchi qua che lo fanno sentire premium come una cosa
> importante da ascoltare»

Tre pezzi, e stanno in tre posti diversi: il tono lo sceglie Claude clip
per clip (brain.ClipPick.tono), la fotografia la fa ffmpeg prima
(video.GRADO_SERIO), la grafica la fa Remotion dopo (Reel.tsx). Questa
prova verifica che siano collegati, perche e li che si rompono: un campo
che nessuno legge e il difetto che ho gia fatto due volte questa settimana.

    python prove/serio.py
"""
import subprocess
import sys
import tempfile
import types
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import video as V

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


print("— la fotografia —")
serio = V._vertical_filter("carta", 60.0, 0.0, src="[0:v]", mask="1:v",
                           grado=V.GRADO_SERIO)
normale = V._vertical_filter("carta", 60.0, 0.0, src="[0:v]", mask="1:v")
check("i colori si spengono", "saturation=0.78" in serio)
check("il contrasto chiude i neri", "contrast=1.10" in serio)
check("e c'e un soffio di freddo", "colorbalance" in serio and "bs=0.05" in serio)
check("senza tono serio non cambia niente",
      "saturation=0.78" not in normale and "colorbalance" not in normale)

print("\n— e si applica PRIMA dello split —")
# Se si gradasse solo il quadrato, lo sfondo sfocato resterebbe caldo e si
# vedrebbe il bordo fra due fotografie diverse.
check("il grado viene prima di split",
      serio.index("saturation=0.78") < serio.index("split=2"))
check("quindi lo sfondo sfocato e gradato quanto il quadrato",
      serio.count("saturation=0.78") == 1)

print("\n— vale per tutte le modalita, non solo per 'carta' —")
for modo in ("square", "blur", "crop"):
    g = V._vertical_filter(modo, 30.0, 0.0, grado=V.GRADO_SERIO)
    check(f"«{modo}» prende il grado", "saturation=0.78" in g)

print("\n— il montaggio deve ancora FINIRE —")
# Stessa lezione del 15/10: un filtro nuovo nel grafo e un modo nuovo di
# non terminare. Si rende senza imporre la durata.
lavoro = Path(tempfile.mkdtemp(prefix="prove-serio-"))
sorgente = lavoro / "sorgente.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                "-i", "testsrc2=size=1920x1080:rate=30:duration=4",
                "-pix_fmt", "yuv420p", str(sorgente)],
               check=True, capture_output=True)
maschera = V._mask_carta(48, lavoro / "m.png")
grafo = V._vertical_filter("carta", 4.0, 0.0, src="[0:v]", mask="1:v",
                           grado=V.GRADO_SERIO)
try:
    reso = subprocess.run(
        ["ffmpeg", "-y", "-i", str(sorgente), "-loop", "1", "-i", str(maschera),
         "-filter_complex", grafo, "-map", "[vmain]",
         "-c:v", "libx264", "-preset", "ultrafast", str(lavoro / "out.mp4")],
        capture_output=True, timeout=120)
    finito, codice = True, reso.returncode
except subprocess.TimeoutExpired:
    finito, codice = False, -1
check("quattro secondi si montano e finiscono", finito and codice == 0)
if finito and codice == 0:
    durata = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(lavoro / "out.mp4")],
        capture_output=True, text=True).stdout.strip()
    check(f"e durano quanto la sorgente ({durata}s)",
          abs(float(durata) - 4.0) < 0.5)

print("\n— e si vede davvero, non solo nel grafo —")
# La prova che conta: due fotogrammi, uno gradato e uno no, e la
# saturazione misurata. Un filtro che c'e nella stringa e non nell'immagine
# e il modo piu facile di credersi a posto.
def satura(grado: str, nome: str) -> float:
    fuori = lavoro / nome
    g = V._vertical_filter("square", 4.0, 0.0, grado=grado)
    subprocess.run(["ffmpeg", "-y", "-i", str(sorgente), "-filter_complex", g,
                    "-map", "[vmain]", "-frames:v", "1", str(fuori)],
                   check=True, capture_output=True)
    from PIL import Image
    im = Image.open(fuori).convert("HSV")
    # Media di un pezzo di immagine, ridotto a un pixel: e il modo piu
    # corto di chiedere "quanto e satura questa zona".
    return im.crop((300, 800, 780, 1200)).resize((1, 1)).getpixel((0, 0))[1]

s_serio = satura(V.GRADO_SERIO, "serio.png")
s_norm = satura("", "normale.png")
check(f"la clip seria e meno satura ({s_serio:.0f} contro {s_norm:.0f})",
      s_serio < s_norm * 0.92)

print("\n— i collegamenti, che sono la parte che si rompe —")
import inspect
corpo = inspect.getsource(V.render_clip)
check("render_clip accetta il tono", "tono: str" in corpo)
check("e lo passa al filtro",
      'grado=GRADO_SERIO if tono == "serio" else ""' in corpo)

principale = (RADICE / "src" / "main.py").read_text(encoding="utf-8")
check("main.py legge il tono scelto da Claude",
      'getattr(pick, "tono", "") == "serio"' in principale)
check("lo passa a ffmpeg", "tono=tono," in principale)
check("e anche a Remotion", "tono=tono,\n                )" in principale)

from src import brain as B
check("ClipPick ha il campo tono", "tono" in B.ClipPick.model_fields)
descrizione = B.ClipPick.model_fields["tono"].description
check("e la descrizione dice quando usarlo",
      "riflessiva" in descrizione and "Nel dubbio" in descrizione)

reel = (RADICE / "remotion" / "src" / "Reel.tsx").read_text(encoding="utf-8")
check("Reel.tsx riceve il tono", "tono={props.tono}" in reel)
check("in serio la pillola bianca sparisce",
      "backgroundColor: serio ? 'transparent' : 'white'" in reel)
check("il testo diventa bianco", "color: serio ? 'white' : 'black'" in reel)
check("e la coda va a colore", "CODA_BLU" in reel)

print("\n— e le due scelte che vanno con il tono —")
check("la musica va sul riflessivo", 'if tono == "serio":\n                mood = "riflessivo"' in principale)
check("e la fascia di foto sparisce",
      'if tono == "serio" and img_cfg.get("attive"):' in principale)
check("il corpo del banner si adatta al testo", "corpoSerio" in reel)
check("e la coda blu non si spezza mai", "whiteSpace: 'nowrap'" in reel)

print("\n— la coda a colore —")
# spezzaCoda vive in TypeScript; qui si prova la regola, che e la cosa che
# puo sbagliare: dove cade il taglio sui banner veri.
def spezza(t: str):
    pz = t.split()
    if len(pz) < 3:
        return t, ""
    quante = 1 if len(pz) <= 4 else 2
    return " ".join(pz[:-quante]), " ".join(pz[-quante:])

check("«La tua mente inconscia comanda il 95%» → coda «il 95%»",
      spezza("La tua mente inconscia comanda il 95%")[1] == "il 95%")
check("«Perché per un ricco 2.000 euro sono pochi» → coda «sono pochi»",
      spezza("Perché per un ricco 2.000 euro sono pochi")[1] == "sono pochi")
check("un banner corto resta intero", spezza("Giapponese in 30 giorni")[1] == "giorni")
check("due parole non si spezzano", spezza("Basta reel")[1] == "")
check("e la regola nel tsx e la stessa",
      "pz.length <= 4 ? 1 : 2" in reel and "pz.length < 3" in reel)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

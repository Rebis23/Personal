"""Il quadrato sullo sfocato, con gli angoli che lasciano vedere lo sfondo.

Lorenzo, 15/10, mandando uno Short di Tom Youngs: «bello questo stile di
editing». Quel montaggio e il quadrato di 'square' posato sullo sfondo
sfocato di 'blur' — due cose che la fabbrica aveva gia da settembre, ma in
due modalita che si escludevano a vicenda.

LA TRAPPOLA, ed e il motivo per cui questo file esiste: gli angoli tondi di
'square' si ottengono dipingendo gli angoli di NERO con un velo sopra il
risultato. Funziona perche sotto c'e il nero. Sopra lo sfocato lascerebbe
quattro tacche nere agli angoli della cartolina, visibilissime. Qui la
maschera entra invece come canale alpha del quadrato (alphamerge) prima che
venga posato sullo sfondo.

    python prove/carta.py
"""
import sys
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


carta = V._vertical_filter("carta", 60.0, 0.0, src="[0:v]", mask="1:v")
square = V._vertical_filter("square", 60.0, 0.0, src="[0:v]")

print("— la cartolina —")
check("lo sfondo e sfocato, non nero", "gblur" in carta)
check("ed e anche scurito, se no ruba l'occhio", "eq=brightness=-0.08" in carta)
check("il quadrato e ritagliato dal centro", "crop=ih:ih,scale=1080:1080" in carta)
check(f"e posato a {V.SQUARE_Y}, dove stava prima",
      f"overlay=0:{V.SQUARE_Y}" in carta)
check("gli angoli passano dall'alpha, non da una vernice nera",
      "alphamerge" in carta)
check("senza maschera non si inventa un alphamerge a vuoto",
      "alphamerge" not in V._vertical_filter("carta", 60.0, 0.0, mask=None))

print("\n— la trappola degli angoli neri —")
# Il velo nero di 'square' si applica DOPO, sopra tutto: su uno sfondo
# sfocato dipingerebbe quattro tacche. Deve restare legato a 'square'.
sorgente = (RADICE / "src" / "video.py").read_text(encoding="utf-8")
velo = sorgente.split("_corner_mask(corner_radius")[0].split("\n")[-2:]
check("il velo nero si applica solo in modalita 'square'",
      'vertical_mode == "square" and corner_radius > 0' in sorgente)
check("la cartolina ha una sua maschera, in scala di grigi",
      "_mask_carta" in sorgente)
check("e la maschera entra PRIMA del filtro, non dopo",
      sorgente.index("_mask_carta(corner_radius")
      < sorgente.index("_vertical_filter(vertical_mode"))

print("\n— il push-in resta uguale alle due modalita —")
con_spinta = V._vertical_filter("carta", 60.0, 0.06, mask="1:v")
check("con zoom la cartolina ha lo zoompan", "zoompan" in con_spinta)
check("e anche 'square' ce l'ha, dalla stessa formula",
      "zoompan" in V._vertical_filter("square", 60.0, 0.06))
check("senza zoom non c'e", "zoompan" not in carta and "zoompan" not in square)

print("— il montaggio deve FINIRE —")
# La prova che conta, e quella che mancava. La maschera entra con -loop 1,
# cioe un flusso infinito: senza shortest=1 alphamerge continua a produrre
# fotogrammi dopo la fine del video. Il 15/10 la prima corsa vera e rimasta
# un'ora e 56 su una clip sola finche il tetto dei 150 minuti ha ucciso il
# job, e la coda e rimasta vuota per un altro giorno.
#
# La prima versione di questa prova passava lo stesso, perche la rendevo con
# -t 20: misuravo una cosa che in produzione non esiste. Qui NON si impone
# nessuna durata — e l'unico modo di accorgersene.
import subprocess
import tempfile
import time

lavoro = Path(tempfile.mkdtemp(prefix="prove-carta-render-"))
sorgente = lavoro / "sorgente.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                "-i", "testsrc2=size=1920x1080:rate=30:duration=6",
                "-pix_fmt", "yuv420p", str(sorgente)],
               check=True, capture_output=True)
maschera = V._mask_carta(48, lavoro / "m.png")
grafo = V._vertical_filter("carta", 6.0, 0.0, src="[0:v]", mask="1:v")
inizio = time.time()
try:
    reso = subprocess.run(
        ["ffmpeg", "-y", "-i", str(sorgente), "-loop", "1", "-i", str(maschera),
         "-filter_complex", grafo, "-map", "[vmain]",
         "-c:v", "libx264", "-preset", "ultrafast", str(lavoro / "out.mp4")],
        capture_output=True, timeout=120)
    finito, codice = True, reso.returncode
except subprocess.TimeoutExpired:
    finito, codice = False, -1
check(f"sei secondi di clip si montano e FINISCONO ({time.time()-inizio:.0f}s)",
      finito and codice == 0)
if finito and codice == 0:
    durata = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(lavoro / "out.mp4")],
        capture_output=True, text=True).stdout.strip()
    check(f"e durano quanto la sorgente, non all'infinito ({durata}s)",
          abs(float(durata) - 6.0) < 0.5)
check("shortest=1 e nel grafo, non solo nei commenti",
      "alphamerge=shortest=1" in grafo)

print("\n— la maschera —")
import tempfile
fuori = Path(tempfile.mkdtemp(prefix="prove-carta-")) / "m.png"
V._mask_carta(48, fuori)
from PIL import Image
m = Image.open(fuori)
check("e 1080x1080 come il quadrato", m.size == (1080, 1080))
check("in scala di grigi: diventa alpha", m.mode == "L")
check("bianca al centro (il video si vede)", m.getpixel((540, 540)) == 255)
check("nera nell'angolo (lo sfondo si vede)", m.getpixel((1, 1)) == 0)
# Il bordo si cerca nell'angolo tutto, non su un pixel scelto a mano: la
# prima versione sondava (14,14), cioe la diagonale esatta, dove la
# transizione cade FRA due pixel e si legge 0 poi 255. Sembrava seghettata
# e non lo era — riga y=5: 0, 1, 3, 98, 211, 255.
angolo = [m.getpixel((x, y)) for x in range(70) for y in range(70)]
check("e il bordo e sfumato, non seghettato",
      sum(1 for v in angolo if 0 < v < 255) > 20)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

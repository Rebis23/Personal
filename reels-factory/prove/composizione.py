"""Foto e banner devono stare fuori dalla zona che Instagram copre.

Il 6/09 Lorenzo ha mandato lo screenshot di un Reel dicendo "le immagini
sono tagliate". Non erano tagliate dal montaggio — nel file erano intere —
erano COPERTE: la fascia partiva a 42 px dall'alto e l'interfaccia di
Instagram, nome del profilo e riga dell'audio, arriva fin verso i 230.

Questa prova legge i numeri veri dal codice del montaggio e verifica che
niente di leggibile finisca nelle due zone che Instagram si prende.

    python prove/composizione.py
"""
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ALTEZZA = 1920

# Misurate sullo screenshot di Lorenzo del 6/09, in px sui 1920 del frame.
IG_ALTO = 230       # nome del profilo + riga dell'audio
IG_BASSO = 1500     # da qui in giu: didascalia e tasti

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


def numero(testo: str, schema: str) -> int:
    m = re.search(schema, testo, re.M)
    assert m, f"non trovo {schema}"
    return int(m.group(1))


video_py = (RADICE / "src" / "video.py").read_text(encoding="utf-8")
reel_tsx = (RADICE / "remotion" / "src" / "Reel.tsx").read_text(encoding="utf-8")

square_y = numero(video_py, r"^SQUARE_Y = (\d+)")
fascia_top = numero(reel_tsx, r"top: (\d+),\n          display: 'flex'")
fascia_h = numero(reel_tsx, r"const altezza = (\d+);")
banner_top = numero(reel_tsx, r"top: sottoFascia \? (\d+)")
banner_h = 190          # due righe a 58px con l'imbottitura: misura generosa

print(f"  fascia  {fascia_top} → {fascia_top + fascia_h}")
print(f"  banner  {banner_top} → {banner_top + banner_h}")
print(f"  video   {square_y} → {square_y + 1080}\n")

prova("la fascia comincia sotto l'interfaccia di Instagram",
      fascia_top >= IG_ALTO, f"parte a {fascia_top}, il limite e {IG_ALTO}")
prova("il banner comincia dopo la fascia",
      banner_top >= fascia_top + fascia_h,
      f"banner a {banner_top}, la fascia finisce a {fascia_top + fascia_h}")
prova("il banner finisce prima della didascalia",
      banner_top + banner_h <= IG_BASSO)
prova("il video comincia dopo il banner",
      square_y >= banner_top + banner_h,
      f"video a {square_y}, il banner finisce a {banner_top + banner_h}")
prova("il video sta dentro il frame", square_y + 1080 <= ALTEZZA,
      f"finirebbe a {square_y + 1080}")

# Il nero sprecato: prima erano 420 px sotto il video, un quinto del Reel.
nero_sotto = ALTEZZA - (square_y + 1080)
prova("sotto il video non resta un buco nero", nero_sotto <= 200,
      f"{nero_sotto} px di nero")

print(f"\n{verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

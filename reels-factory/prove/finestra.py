"""La clip che esce deve essere il momento che Claude ha votato.

L'11/09 tre clip su sei sono uscite da un punto del video diverso da quello
valutato, e due di quelle tre sono uscite IDENTICHE fra loro. Il motivo:
snap_to_sentences allarga la finestra quando Whisper non mette un punto per
minuti interi, e la riga d'apertura si andava a pescare in tutto quello
spazio — anche due minuti dopo il momento scelto.

Questa prova usa i numeri veri di quel run.

    python prove/finestra.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.aggancio import limite_apertura, stesso_spezzone   # noqa: E402

MIN, MAX = 20.0, 75.0
verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- I sei casi veri del run 129 ---------------------------------------
# (clip, start dopo lo snap, end dopo lo snap, fine votata, riga scelta)
# Gli `end` allargati sono ricostruiti dai tempi misurati sui file usciti.
CASI = [
    (1, 0.0,   51.0,  51.0,  0.0,   True),    # era gia giusta
    (2, 204.0, 303.0, 265.0, 265.0, False),   # usciva da [265-303]
    (3, 275.0, 572.0, 316.0, 395.0, False),   # usciva da [395-470]
    (4, 380.0, 471.0, 439.0, 396.0, True),    # dentro il votato: va bene
    (5, 774.0, 814.0, 814.0, 781.0, True),
    (6, 846.0, 890.0, 884.0, 848.0, True),
]

print("  finestra in cui si cerca la riga d'apertura:\n")
for n, start, end, votato, scelta, era_buona in CASI:
    lim = limite_apertura(start, end, votato, min_seconds=MIN, max_seconds=MAX)
    ammessa = scelta <= lim
    print(f"    clip {n}: [{start:.0f} … {lim:.0f}]  la riga era a {scelta:.0f}s")
    prova(f"clip {n}: la riga a {scelta:.0f}s {'passa' if era_buona else 'viene esclusa'}",
          ammessa == era_buona,
          f"limite {lim:.0f}s, ammessa={ammessa}")

print()
# La finestra non puo mai sfondare il tetto ne uscire dal momento votato.
for n, start, end, votato, _s, _b in CASI:
    lim = limite_apertura(start, end, votato, min_seconds=MIN, max_seconds=MAX)
    prova(f"clip {n}: la finestra resta dentro il momento votato",
          lim <= max(start + 1.0, votato), f"limite {lim:.0f} vs votato {votato:.0f}")
    prova(f"clip {n}: la clip non puo sfondare il tetto",
          lim - start <= MAX, f"{lim - start:.0f}s di rincorsa")

print()
# --- Le due clip gemelle del run 129 ------------------------------------
prova("le clip 3 e 4 dell'11/09 sono riconosciute come lo stesso spezzone",
      stesso_spezzone((395.0, 470.0), (396.0, 471.0)))
prova("due clip lontane non sono lo stesso spezzone",
      not stesso_spezzone((0.0, 47.0), (265.0, 303.0)))
prova("due clip che si sfiorano non sono lo stesso spezzone",
      not stesso_spezzone((100.0, 140.0), (135.0, 175.0)))
prova("una clip dentro l'altra e lo stesso spezzone",
      stesso_spezzone((100.0, 175.0), (110.0, 140.0)))

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

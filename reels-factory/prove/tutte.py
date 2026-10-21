"""Lancia tutte le prove e conta bene.

Finche si contava a mano con un grep, il numero era sbagliato: alcune
prove stampano «25 verdi, 0 rotti» con due spazi davanti e altre senza, e
il filtro ancorato a inizio riga saltava le prime. Il 21/10 ho riferito
694 quando erano 850 — nessuna prova rotta, solo un conto sbagliato, ma
un numero sbagliato detto con sicurezza vale meno di nessun numero.

    python prove/tutte.py          tutte
    python prove/tutte.py inizio   solo quelle che contengono "inizio"
"""
import re
import subprocess
import sys
import time
from pathlib import Path

QUI = Path(__file__).resolve().parent
RIGA = re.compile(r"^\s*(\d+)\s+verdi,\s+(\d+)\s+rotti", re.M)

filtro = sys.argv[1] if len(sys.argv) > 1 else ""
file = sorted(p for p in QUI.glob("*.py")
              if p.name != "tutte.py" and filtro in p.name)
if not file:
    print(f"nessuna prova corrisponde a «{filtro}»")
    raise SystemExit(1)

verdi = rotti = 0
caduti: list[str] = []
inizio = time.time()

for p in file:
    esito = subprocess.run([sys.executable, str(p)], capture_output=True,
                           text=True, timeout=900)
    uscita = esito.stdout + esito.stderr
    trovato = RIGA.findall(uscita)
    if trovato:
        v, r = trovato[-1]
        verdi += int(v)
        rotti += int(r)
    if esito.returncode != 0:
        caduti.append(p.name)
        print(f"ROTTA  {p.name}")
        for r in uscita.splitlines():
            if "ROTTO" in r or "Error" in r or "Traceback" in r:
                print(f"       {r.strip()[:120]}")
    elif not trovato:
        # Una prova che esce bene senza dire quanti controlli ha fatto non
        # si puo contare, e una prova che non si conta e una prova che
        # domani sparisce senza che nessuno se ne accorga.
        caduti.append(p.name)
        print(f"MUTA   {p.name}: esce a posto ma non dice quanti controlli "
              f"ha fatto")

quante = len(file)
print(f"\n{verdi} verdi, {rotti} rotti su {quante} file "
      f"({time.time() - inizio:.0f}s)")
if caduti:
    print(f"da guardare: {', '.join(caduti)}")
raise SystemExit(1 if caduti or rotti else 0)

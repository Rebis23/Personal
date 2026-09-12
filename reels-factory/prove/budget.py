"""La guardia contro il budget troppo stretto.

Il 5/09 ho spento in silenzio due passaggi su tre della catena che
accorcia gli agganci, per un numero. Avevo scritto max_tokens=16 su una
chiamata pensando "tanto deve rispondere solo un numero", e max_tokens=200
su un'altra per lo stesso motivo. Tutte e due tornavano una risposta VUOTA,
sempre, con stop_reason=max_tokens.

Il ragionamento sta DENTRO il budget. Il modello non veniva tagliato mentre
scriveva la risposta: veniva tagliato prima di arrivarci. Quindi "la
risposta e corta" non dice niente su quanto budget serve — e chiedere una
risposta corta e semmai il caso in cui e piu facile sbagliarsi, perche
sembra ovvio che basti poco.

Questa prova legge il codice e boccia qualunque max_tokens sotto la soglia.
Non serve rete, non serve chiave.

    python prove/budget.py
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# Sotto questa soglia il ragionamento non ci sta e la risposta esce vuota.
# Alzata da 600 a 1000 il 12/09: il giudizio sulle foto stava esattamente a
# 600, passava questa prova, e tornava comunque vuoto — cinque volte fra il
# 6 e l'11 settembre. Guardare dodici immagini costa piu ragionamento di
# quanto costi leggere del testo, e 600 non bastavano.
MINIMO = 1000

trovati = 0
colpevoli: list[str] = []
for f in sorted(SRC.glob("*.py")):
    for n, riga in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if riga.lstrip().startswith("#"):
            continue
        m = re.search(r"max_tokens\s*=\s*(\d+)", riga)
        if not m:
            continue
        trovati += 1
        if int(m.group(1)) < MINIMO:
            colpevoli.append(f"{f.name}:{n}  max_tokens={m.group(1)}  {riga.strip()}")

print(f"{trovati} chiamate al modello, soglia {MINIMO} token")
if colpevoli:
    print("\nBUDGET TROPPO STRETTI — la risposta rischia di uscire vuota:")
    for c in colpevoli:
        print("  ", c)
    print("\nIl ragionamento sta dentro il budget: una risposta corta non "
          "vuol dire che basti poco.")
    sys.exit(1)
print("nessun budget sotto soglia")

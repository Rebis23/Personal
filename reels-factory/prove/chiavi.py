"""La guardia contro l'errore che mi e costato due giorni.

Il 4 e il 5 settembre la fabbrica ha prodotto banner lunghi e fasce di foto
scelte a caso, e nei log si leggeva "Connection error." su ogni chiamata.
Ho dato la colpa alla rete, poi a WARP, poi al carico del runner. Non era
niente di tutto questo: in tre punti nuovi avevo scritto

    anthropic.Anthropic()

invece di

    anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())

Senza .strip() la chiave arriva con l'a-capo che i GitHub Secrets attaccano
in fondo, e un a-capo dentro un header HTTP e illegale: la richiesta non
parte proprio, e la libreria lo riporta come errore di connessione. Sembra
la rete. E' una riga di codice.

Questa prova cerca la costruzione sbagliata in tutto src/. Non serve rete,
non serve chiave: si legge il codice. Da lanciare prima di ogni commit che
tocca una chiamata al modello.

    python prove/chiavi.py
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# Va bene solo la forma che passa la chiave ripulita.
SBAGLIATA = re.compile(r"anthropic\.Anthropic\(\s*\)")
GIUSTA = re.compile(r'anthropic\.Anthropic\(\s*api_key\s*=\s*os\.environ\[\s*'
                    r'["\']ANTHROPIC_API_KEY["\']\s*\]\s*\.strip\(\)\s*\)')

colpevoli: list[str] = []
buone = 0
for f in sorted(SRC.glob("*.py")):
    testo = f.read_text(encoding="utf-8")
    for n, riga in enumerate(testo.splitlines(), 1):
        if "anthropic.Anthropic(" not in riga:
            continue
        if riga.lstrip().startswith("#"):
            continue
        if GIUSTA.search(riga):
            buone += 1
        elif SBAGLIATA.search(riga):
            colpevoli.append(f"{f.name}:{n}  {riga.strip()}")
        else:
            colpevoli.append(f"{f.name}:{n}  forma non riconosciuta: {riga.strip()}")

print(f"{buone} costruzioni corrette del client Anthropic")
if colpevoli:
    print("\nCOSTRUZIONI SBAGLIATE — la chiave arriverebbe con l'a-capo:")
    for c in colpevoli:
        print("  ", c)
    print("\nUsare: anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'].strip())")
    sys.exit(1)

print("nessuna costruzione sbagliata")

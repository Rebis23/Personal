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

# UNA sola deroga, e va motivata sulla riga stessa. Esiste perche il 27/09 e
# nata una chiamata in cui la risposta non serve davvero: cervello_pronto()
# chiede un token al modello solo per sapere se l'API accetta le nostre
# richieste — se torna vuota va benissimo, la si butta. Senza deroga l'unico
# modo di far passare quella riga sarebbe stato abbassare la soglia per
# tutti, che e il contrario di quello che serve.
#
# La deroga pretende un motivo scritto: `# risposta-non-usata: <perche>`.
# Senza motivo non vale, cosi non diventa un interruttore per zittire la
# guardia quando da fastidio.
DEROGA = re.compile(r"#\s*risposta-non-usata:\s*\S+")

trovati = 0
derogate = 0
colpevoli: list[str] = []
for f in sorted(SRC.glob("*.py")):
    for n, riga in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if riga.lstrip().startswith("#"):
            continue
        m = re.search(r"max_tokens\s*=\s*(\d+)", riga)
        if not m:
            continue
        trovati += 1
        if DEROGA.search(riga):
            derogate += 1
            continue
        if int(m.group(1)) < MINIMO:
            colpevoli.append(f"{f.name}:{n}  max_tokens={m.group(1)}  {riga.strip()}")

# IL PUNTO CIECO. Il 1/10 ho scritto `max_tokens=budget` — una variabile, non
# un numero — e questa prova ha smesso di vedere quella chiamata: le chiamate
# contate sono passate da 12 a 11 senza che nulla diventasse rosso. Una
# guardia che perde di vista cio che deve guardare e peggio di nessuna
# guardia, perche intanto dice "nessun budget sotto soglia".
#
# Quindi due controlli in piu. Primo: le costanti che contengono i budget
# vanno guardate nei loro valori. Secondo: un `max_tokens=<nome>` deve
# riferirsi a una costante che questa prova sa controllare — se qualcuno
# inventa una variabile nuova, qui diventa rosso e non silenzioso.
import importlib                                            # noqa: E402

sys.path.insert(0, str(SRC.parent))

# Un import che non riesce NON si salta in silenzio. La prima versione di
# questo blocco faceva `except: continue`, il percorso dei moduli non era
# impostato, e la prova stampava "costanti controllate: {}" seguito da
# "nessun budget sotto soglia": non guardava niente e diceva che andava
# tutto bene. E' lo stesso errore che la prova esiste per impedire, commesso
# dalla prova stessa.
CONTROLLATE = {}
MODULI = ("aggancio", "brain", "chiusura", "immagini")
for nome_mod in MODULI:
    try:
        mod = importlib.import_module(f"src.{nome_mod}")
    except Exception as e:                                   # noqa: BLE001
        colpevoli.append(f"src/{nome_mod}.py non si importa ({type(e).__name__}: "
                         f"{e}): i suoi budget restano NON controllati")
        continue
    for attr in dir(mod):
        if "BUDGET" not in attr:
            continue
        valori = getattr(mod, attr)
        valori = valori if isinstance(valori, (tuple, list)) else [valori]
        CONTROLLATE[attr] = [v for v in valori if isinstance(v, int)]

for attr, valori in sorted(CONTROLLATE.items()):
    bassi = [v for v in valori if v < MINIMO]
    if bassi:
        colpevoli.append(f"costante {attr}: valori sotto soglia {bassi}")

# I max_tokens che puntano a un nome invece che a un numero.
NOMI_NOTI = set(CONTROLLATE) | {"budget"}   # `budget` cicla su una costante nota
per_nome = 0
for f in sorted(SRC.glob("*.py")):
    for n, riga in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if riga.lstrip().startswith("#"):
            continue
        m = re.search(r"max_tokens\s*=\s*([A-Za-z_][A-Za-z_0-9]*)", riga)
        if not m:
            continue
        per_nome += 1
        if m.group(1) not in NOMI_NOTI:
            colpevoli.append(
                f"{f.name}:{n}  max_tokens={m.group(1)} — nome che questa "
                f"prova non sa controllare: aggiungilo a NOMI_NOTI e fai in "
                f"modo che i suoi valori siano verificabili")

print(f"{trovati} chiamate col numero scritto, {per_nome} con un nome, "
      f"soglia {MINIMO} token"
      + (f" ({derogate} in deroga, motivate)" if derogate else ""))
print(f"costanti di budget controllate: "
      f"{ {k: v for k, v in sorted(CONTROLLATE.items())} }")
if not CONTROLLATE:
    colpevoli.append("nessuna costante di budget trovata: o sono state "
                     "rinominate senza 'BUDGET' nel nome, o questa prova "
                     "non sta piu guardando dove deve")
if colpevoli:
    print("\nBUDGET TROPPO STRETTI — la risposta rischia di uscire vuota:")
    for c in colpevoli:
        print("  ", c)
    print("\nIl ragionamento sta dentro il budget: una risposta corta non "
          "vuol dire che basti poco.")
    sys.exit(1)
print("nessun budget sotto soglia")

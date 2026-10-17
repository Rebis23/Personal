"""Un nome usato prima di esistere: il guasto del 17/10, e nessuna prova lo vedeva.

Quel giorno la prima rilavorazione col metodo nuovo e morta cosi, dopo 35
minuti di lavoro e con le clip gia scelte:

    File ".../src/main.py", line 622, in _process_video
      mood = (getattr(pick, "mood", "") or "").strip().lower()
    UnboundLocalError: cannot access local variable 'tono'

Avevo messo `tono` accanto a render_common, in fondo, e lo leggevo molto
prima — nella scelta della musica e nella fascia di foto. Tutte le righe
giuste, nell'ordine sbagliato.

E prove/serio.py era VERDE, perche cercava quelle righe nel sorgente: le
trovava tutte e dichiarava il collegamento a posto. Una prova che legge il
testo del codice non sa in che ordine gira. E' un intero genere di difetti
che le mie prove non possono vedere — e per quel genere esiste uno
strumento che costa un secondo.

pyflakes su tutto il progetto, zero tolleranza. Quando l'ho provato sul
file rotto ha detto:

    src/main.py:629:16: undefined name 'tono'

Zero tolleranza si puo permettere perche il progetto e pulito: il giorno
che l'ho acceso, in tutto src/ e prove/, c'erano quattro segnalazioni in
croce — questa piu due import inutili e una f-string senza nulla dentro.
Tenerlo a zero costa meno che decidere ogni volta quali ignorare.

    python prove/lint.py
"""
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


file = sorted((RADICE / "src").glob("*.py")) + sorted((RADICE / "prove").glob("*.py"))
print(f"— pyflakes su {len(file)} file —")

try:
    esito = subprocess.run([sys.executable, "-m", "pyflakes", *map(str, file)],
                           capture_output=True, text=True, timeout=120)
    disponibile = "No module named" not in esito.stderr
except (OSError, subprocess.TimeoutExpired) as e:
    esito, disponibile = None, False
    print(f"  ({e})")

# UNA PROVA SALTATA IN SILENZIO E' PEGGIO DI UNA PROVA CHE NON C'E: chi
# legge il verde crede che il controllo sia passato. Se pyflakes manca,
# questo file e ROSSO e dice cosa installare.
if not disponibile:
    print("  ROTTO pyflakes non e installato: questo controllo NON ha girato")
    print("        pip install pyflakes   (sta in requirements.txt)")
    sys.exit(1)

righe = [r for r in (esito.stdout or "").splitlines() if r.strip()]
for r in righe:
    print(f"  →  {r}")
check(f"zero segnalazioni ({len(righe)} trovate)", not righe)

print("\n— e deve prendere il caso che ci e costato il run —")
# Si ricostruisce il difetto vero in un file finto e si pretende che lo
# veda. Senza questo, un domani qualcuno allenta il controllo e la prova
# resta verde lo stesso.
import tempfile
finto = Path(tempfile.mkdtemp(prefix="prove-lint-")) / "rotto.py"
finto.write_text(
    "def gira(picks):\n"
    "    for pick in picks:\n"
    "        if tono == 'serio':\n"          # usato qui
    "            print('serio')\n"
    "        tono = 'normale'\n",            # definito dopo
    encoding="utf-8")
prova = subprocess.run([sys.executable, "-m", "pyflakes", str(finto)],
                       capture_output=True, text=True)
check("un nome usato prima di essere definito viene visto",
      "tono" in prova.stdout)

print("\n— e sta nei requisiti, se no domani non c'e —")
req = (RADICE / "requirements.txt").read_text(encoding="utf-8")
check("pyflakes e in requirements.txt", "pyflakes" in req)

print("\n— e gira PRIMA di spendere, non dopo —")
# Il punto non e avere il controllo: e averlo prima del download e della
# trascrizione. Il 17/10 il guasto si e visto dopo 35 minuti di lavoro
# gia pagato.
flusso = (RADICE.parent / ".github" / "workflows" / "reels-ingest.yml"
          ).read_text(encoding="utf-8")
check("l'ingest passa dal linter", "python -m pyflakes src/*.py" in flusso)
# Il messaggio va a capo nel YAML: si cerca un pezzo che sta su una
# riga sola, se no la prova fallisce su un workflow giusto.
check("e si ferma se trova qualcosa",
      "fermo qui, prima di spendere" in flusso and "exit 1" in flusso)
# Prima di TUTTA la trafila del tunnel, non solo del download: quella
# da sola a volte ci mette minuti, e non ha senso farla per poi morire
# su una riga di Python.
check("prima del tunnel, non dentro l'ingest",
      flusso.index("python -m pyflakes") < flusso.index("wg-quick up warp"))
check("ed e un passo suo, con un nome che si legge nel riepilogo",
      "- name: Il codice sta in piedi?" in flusso)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

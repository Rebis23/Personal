"""Il conto dei token, e la guardia che chi lo usa sappia importarlo.

PERCHE IL CONTO. Dal 25/09 Lorenzo chiede quanto costa un video e ogni volta
gli ho dato una divisione: «venti dollari hanno coperto tre lavorazioni,
quindi sei-sette l'una». Aritmetica su un dato solo, e che non risponde alla
domanda che conta — QUALE chiamata costa. Senza quello, scegliere dove
mettere un modello piu economico e indovinare: si rischia di spostare le tre
che costano un centesimo e lasciare su Opus quella che costa un dollaro.

PERCHE LA GUARDIA. Collegando il conto ho aggiunto `conto.segna(...)` dentro
una funzione di chiusura.py e dimenticato l'import. `import src.chiusura`
passava — importare un modulo compila, non esegue — quindi il controllo che
avevo fatto diceva "tutti i moduli importano" ed era vero e inutile:
l'errore sarebbe uscito in produzione, dentro una lavorazione da 50 minuti,
come NameError a meta strada. Qui si guarda il testo: chi chiama conto deve
importarlo.

    python prove/conto.py
"""
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from src.conto import PREZZI, Conto                            # noqa: E402

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


class FintoUsage:
    def __init__(self, dentro, fuori):
        self.input_tokens = dentro
        self.output_tokens = fuori


print("\n— chi usa conto.segna deve importare conto —")
# La guardia che mi serviva un'ora fa.
for f in sorted((RADICE / "src").glob("*.py")):
    testo = f.read_text(encoding="utf-8")
    if "conto.segna" not in testo and "conto.azzera" not in testo:
        continue
    importa = ("from . import conto" in testo
               or "from .conto import" in testo
               or ", conto" in testo.split("def ")[0]
               or "conto," in testo.split("def ")[0])
    check(f"{f.name} chiama conto e lo importa", importa)

print("\n— il conto somma —")
c = Conto()
c.segna("scelta clip", FintoUsage(8000, 4000))
c.segna("scelta clip", FintoUsage(2000, 1000))
check("due chiamate sulla stessa voce si sommano",
      c.voci["scelta clip"] == [2, 10000, 5000])
atteso = 10000 / 1e6 * 5.0 + 5000 / 1e6 * 25.0
check(f"i dollari tornano ({atteso:.4f})",
      abs(c.dollari("scelta clip", "claude-opus-5") - atteso) < 1e-9)

print("\n— la voce piu cara sta in cima, perche e quella su cui decidere —")
c2 = Conto()
c2.segna("briciola", FintoUsage(100, 50))
for _ in range(5):
    c2.segna("giudizio foto", FintoUsage(15000, 1200))
righe = c2.scheda("claude-opus-5").splitlines()
check("la prima voce elencata e la piu cara", "giudizio foto" in righe[1])
check("e la briciola sta sotto", "briciola" in righe[2])
check("c'e il totale", "TOTALE" in righe[-1])

print("\n— nessun prezzo inventato —")
c3 = Conto()
c3.segna("x", FintoUsage(1000, 1000))
check("un modello fuori tabella non produce dollari",
      c3.dollari("x", "modello-mai-visto") is None)
check("e nemmeno un totale", c3.totale("modello-mai-visto") is None)
check("ma i token si vedono comunque",
      "1000" in c3.scheda("modello-mai-visto"))
check("e lo dice in chiaro",
      "nessun dollaro inventato" in c3.scheda("modello-mai-visto"))

print("\n— un contatore non deve mai rompere una lavorazione —")
from src import conto as C                                     # noqa: E402
C.azzera()
C.segna("strana", object())          # usage senza i campi attesi
check("un usage inatteso non esplode", True)
C.segna("buona", FintoUsage(10, 20))
check("e la misura buona viene registrata comunque",
      C.CORRENTE.voci.get("buona") == [1, 10, 20])
C.azzera()
check("azzera svuota il conto", C.CORRENTE.voci == {})

print("\n— i prezzi sono quelli dei modelli che usiamo —")
check("il modello del config e in tabella",
      "claude-opus-5" in PREZZI)
check("e ci sono le alternative economiche da valutare",
      "claude-sonnet-5" in PREZZI and "claude-haiku-4-5" in PREZZI)
check("sonnet costa meno di opus",
      PREZZI["claude-sonnet-5"] < PREZZI["claude-opus-5"])

print("\n— la voce vuota non finge —")
check("un conto senza chiamate lo dice",
      "Nessuna chiamata" in Conto().scheda("claude-opus-5"))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

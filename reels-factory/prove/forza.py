"""La quota non deve vincere sulla qualita.

Lorenzo, 13/10, guardando i Reel usciti: «non prendi gli spezzoni migliori
del video, li prendi un pochino a caso». Aveva ragione, e il posto era una
riga sola:

    strong = [c for c in usable if c.hook_strength >= 7]
    picked = (strong if len(strong) >= clips_per_video else usable)[:n]

C'era una soglia di qualita, ma quando le clip forti non bastavano a
riempire la quota la soglia non si abbassava: si SPEGNEVA. E `usable` e in
ordine di tempo nel video, quindi il ramo di scorta prendeva le prime n —
non le n migliori. Con dieci spezzoni di forza [4, 5, 9, 8, 3, …] teneva il
4 e il 5 e buttava il 9 e l'8, solo perche venivano prima nel video.

Due cose rendevano il difetto invisibile:
  - nel log si leggeva «(2 clip con hook debole scartate o retrocesse)»,
    che suona come un filtro che funziona;
  - config.yaml diceva «se un video non ne ha 6 sopra soglia, ne escono
    meno» — e descriveva un codice che non c'era: ne uscivano sempre 6.

    python prove/forza.py
"""
import inspect
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# anthropic non serve: piu_forti() non chiama l'API.
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import brain as B

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


class Clip:
    """Una clip finta: conta solo la forza e l'ordine nel video."""

    def __init__(self, forza, secondo):
        self.hook_strength = forza
        self.start_seconds = secondo
        self.hook = f"hook da {forza}/10 a {secondo}s"

    def __repr__(self):
        return f"{self.hook_strength}@{self.start_seconds}s"


def video(*forze):
    """Clip in ordine di tempo, una ogni 60 secondi — come arrivano davvero."""
    return [Clip(f, i * 60) for i, f in enumerate(forze)]


print("— il caso che Lorenzo ha visto —")
DIECI = video(4, 5, 9, 8, 3, 6, 9, 2, 7, 5)
scelte = B.piu_forti(DIECI, 6)
forze = [c.hook_strength for c in scelte]
check(f"le sei scelte sono le sei piu forti: {forze}",
      sorted(forze, reverse=True) == [9, 9, 8, 7, 6, 5])
check("il 9 che stava in settima posizione c'e", 9 in forze)
check("il 4 che stava primo non c'e piu", 4 not in forze)
# Il comportamento di prima, per confronto: le prime sei in ordine di tempo.
prima = [c.hook_strength for c in DIECI[:6]]
check(f"prima uscivano queste: {prima} — due sotto il 5",
      prima == [4, 5, 9, 8, 3, 6])

print("\n— quando le clip forti bastano —")
TANTE = video(8, 9, 3, 7, 9, 2, 8)
scelte = B.piu_forti(TANTE, 4)
check("si prendono solo quelle sopra soglia",
      all(c.hook_strength >= B.FORZA_MINIMA for c in scelte))
check("e restano nell'ordine del video, non riordinate per forza",
      [c.start_seconds for c in scelte] == sorted(c.start_seconds for c in scelte))

print("\n— i casi ai bordi —")
check("niente clip, niente scelte", B.piu_forti([], 6) == [])
check("meno clip della quota: escono tutte",
      len(B.piu_forti(video(3, 4), 6)) == 2)
check("esattamente quante ne serve sopra soglia",
      [c.hook_strength for c in B.piu_forti(video(7, 7, 2), 2)] == [7, 7])
check("tutte sotto soglia: escono comunque le piu forti, in ordine",
      [c.hook_strength for c in B.piu_forti(video(2, 6, 4), 2)] == [6, 4])
check("quota a zero non restituisce niente", B.piu_forti(DIECI, 0) == [])

print("\n— la soglia deve restare collegata —")
# Il difetto non era una soglia sbagliata: era una soglia che in un ramo
# non veniva piu guardata. Se qualcuno riscrive piu_forti() smettendo di
# usarla, o select_clips() smette di chiamare piu_forti(), qui cade.
corpo = inspect.getsource(B.piu_forti)
check("piu_forti() usa la soglia", "soglia" in corpo)
check("e il suo valore di partenza e FORZA_MINIMA",
      inspect.signature(B.piu_forti).parameters["soglia"].default == B.FORZA_MINIMA)
check("FORZA_MINIMA vale 7", B.FORZA_MINIMA == 7)
scelta = inspect.getsource(B.select_clips)
check("select_clips() passa da piu_forti()", "piu_forti(" in scelta)
check("e non ricostruisce la scelta a mano",
      "[:clips_per_video]" not in scelta.split("piu_forti(")[0].split("strong =")[-1])

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

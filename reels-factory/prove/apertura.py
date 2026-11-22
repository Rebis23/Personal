"""Senza riga d'apertura, la clip non si monta.

Il 21/11 alle 17:37 e uscito su Instagram «La vita e peggiorata». Nel log
della sua lavorazione, due righe una sotto l'altra:

    ⚠️ «nell'ultimo anno, piu o meno, ho smesso, in un» non si ritrova
       nell'audio
    ▶️ Nessuna riga d'apertura scelta: la clip parte dove l'ha tagliata
       Claude

Il controllo sull'inizio si era arreso, e il codice tirava dritto col taglio
grezzo. Era la terza volta — 15/11, 20/11, 21/11 — e la prima in cui il Reel
e arrivato davvero al profilo: il turno di pubblicazione passa prima del
controllo del mattino, quindi le prime due le avevo fermate a mano e questa
no.

Ci sono TRE esiti, e vanno tenuti distinti:

  scarta=True   «qui dentro non c'e un Reel»          → non si monta
  una riga      «parte da qui»                        → si monta
  None          «non si e riusciti a trovarla»        → ?

Il terzo non e «va bene»: e «non lo so». E pubblicare un non-so come se
fosse un si non e una possibilita che qualcuno ha scelto — e quello che il
codice faceva in mancanza d'altro.

    python prove/apertura.py
"""
import ast
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SORGENTE = (RADICE / "src" / "main.py").read_text(encoding="utf-8")

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


# Non basta cercare delle stringhe: il 20/10 una prova era verde mentre la
# produzione moriva, perche guardava il TESTO del codice e non l'ordine in
# cui gira. Qui si legge l'albero sintattico e si guarda il ramo else vero.
albero = ast.parse(SORGENTE)


def trova_ramo_else():
    """Il ramo `else` dell'`if detta:` che decide da dove parte la clip."""
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.If):
            continue
        prova = nodo.test
        if isinstance(prova, ast.Name) and prova.id == "detta" and nodo.orelse:
            # Quello giusto ha `start = ...` nel ramo positivo.
            corpo = ast.dump(ast.Module(body=nodo.body, type_ignores=[]))
            if "inizio_pulito" in corpo:
                return nodo.orelse
    return None


ramo = trova_ramo_else()
print("— il ramo che decide cosa fare quando l'inizio non si trova —")
check("il ramo else esiste ancora", ramo is not None)

if ramo is not None:
    tipi = [type(n).__name__ for n in ramo]
    # `continue` salta il resto del giro: niente montaggio, niente R2,
    # niente coda. E' lo stesso gesto del ramo `scarta`.
    check("finisce con un continue, cioe la clip non viene montata",
          "Continue" in tipi)
    testo = ast.dump(ast.Module(body=ramo, type_ignores=[]))
    check("e prima lo dice nel log", "Call" in tipi or "Expr" in tipi)
    check("il messaggio spiega che non si sa da dove parte",
          "non si e ritrovata nell'audio" in SORGENTE
          or "non si ritrova" in SORGENTE)
    # Se un domani qualcuno rimette il montaggio qui dentro, questa cade.
    check("nel ramo non si assegna piu uno start",
          "start" not in testo or "Assign" not in tipi)

print("\n— l'altro esito, quello che c'era gia, non e stato toccato —")
check("scarta=True continua a buttare la clip",
      'detta.get("scarta")' in SORGENTE
      and "scartata: nessun inizio che si regga" in SORGENTE)
# I due motivi devono restare leggibili separatamente nel log: uno dice
# «non c'era un Reel», l'altro «non ho saputo trovarlo». Confonderli
# vorrebbe dire non sapere piu quale dei due sta crescendo.
check("e i due messaggi restano diversi",
      "scartata: nessun inizio che si regga" in SORGENTE
      and "non montata" in SORGENTE)

print("\n— e il ramo buono funziona come prima —")
check("quando la riga c'e, si usa", "inizio_pulito(words, detta[" in SORGENTE)
check("e si ricorda per non ripeterla", "banner_usati.add(" in SORGENTE)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

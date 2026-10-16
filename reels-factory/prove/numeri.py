"""«2.000» e una parola sola, e quel punto non e un punto fermo.

Il 16/10 il controllo del mattino ha trovato in coda un banner sopra il
limite: «Perché per un ricco 2.000 euro sono pochi». Otto parole a occhio,
nove secondo il codice, sette il massimo. Fin qui sarebbe un conteggio
sbagliato in un rapporto. Il guaio e che il conteggio non resta nel
rapporto: e il conteggio con cui si DECIDE.

Misurato prima di toccare niente, sul banner vero:

    quante()     9
    candidati()  «Perché per un ricco», «Perché per un ricco 2.000»,
                 «per un ricco 2.000»

Tre mutilazioni, e nessuna delle due righe che si reggono in piedi — «Per
un ricco 2.000 euro sono pochi», «2.000 euro sono pochi». Il modello le ha
rifiutate tutte e tre, e ha fatto bene: il prompt dice "se nessun pezzo si
regge da solo, rispondi 0". Cosi il banner e uscito lungo.

Due errori dallo stesso punto:

    parole()    il separatore delle migliaia spezzava il numero in due
    il muro     quel punto valeva come punto fermo, e nessun tratto poteva
                attraversarlo — ecco perche tutte le opzioni morivano li

    python prove/numeri.py
"""
import sys
import types
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import aggancio as A

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


VERO = "Perché per un ricco 2.000 euro sono pochi"

print("— il conteggio —")
check(f"«{VERO}» sono 8 parole, non 9", A.quante(VERO) == 8)
check("«2.000» resta intero", "2.000" in A.parole(VERO))
check("le migliaia col punto: «1.500 euro» sono due parole",
      A.quante("1.500 euro") == 2)
check("i decimali con la virgola: «3,5 milioni» sono due parole",
      A.quante("3,5 milioni") == 2)
check("i milioni a tre gruppi: «1.250.000» e una parola",
      A.quante("1.250.000") == 1)
check("un numero liscio resta una parola", A.quante("Giapponese in 30 giorni") == 4)
check("la percentuale non cambia niente",
      A.quante("La tua mente inconscia comanda il 95%") == 7)

print("\n— e la punteggiatura vera continua a contare —")
check("il punto fermo separa ancora", A.quante("Basta. Funziona") == 2)
check("le parole con apostrofo non si spezzano", A.parole("l'ego") == ["l'ego"])
check("una parola con dentro una cifra resta una", A.parole("H2O") == ["h2o"])

print("\n— il muro —")
check("«2.000» non e un muro", not A.ha_muro("2.000"))
check("«3,5» nemmeno", not A.ha_muro("3,5"))
check("«pochi.» si", A.ha_muro("pochi."))
check("«davvero?» si", A.ha_muro("davvero?"))
# «2.» resta un muro: la' il punto non sta fra due cifre, e puo benissimo
# essere la fine di una frase che finisce con un numero. Nel dubbio si
# ferma: un taglio in piu e un banner corto, un taglio in meno e un banner
# che attraversa due frasi.
check("«2.» resta un muro, e va bene cosi", A.ha_muro("2."))

print("\n— quello che cambia davvero: i tagli offerti —")
tagli = A.candidati(VERO)
check(f"adesso sono {len(tagli)}, non 3", len(tagli) > 3)
check("c'e «per un ricco 2.000 euro sono pochi» (7 parole)",
      any(A.parole(t) == A.parole("per un ricco 2.000 euro sono pochi")
          for t in tagli))
check("e c'e «2.000 euro sono pochi»",
      any(A.parole(t) == A.parole("2.000 euro sono pochi") for t in tagli))
check("nessun taglio supera il limite",
      all(A.quante(t) <= A.MAX_PAROLE for t in tagli))
check("e nessuno resta sotto le 4 parole",
      all(A.quante(t) >= 4 for t in tagli))

print("\n— il parlato: un numero non apre una frase nuova —")
# Stesso errore nell'altra strada, quella che decide DA DOVE parte la clip:
# un «2.000» pronunciato valeva come muro, e un muro e la prova piu forte
# che li cominci una proposizione. La clip sarebbe partita da «euro».
def parla(*testi, passo=0.4):
    return [{"word": t, "start": round(i * passo, 3),
             "end": round(i * passo + passo * 0.9, 3)}
            for i, t in enumerate(testi)]


NUM = parla("Senti.", "Per", "un", "ricco", "2.000", "euro", "sono", "pochi")
check("dopo «2.000» non comincia niente",
      A._attacco(NUM, 5, pausa=A.PAUSA) == "")
check("mentre dopo un punto vero si", A._attacco(NUM, 1, pausa=A.PAUSA) == "muro")
# Qui le righe devono USCIRE davvero: una prova che passa perche l'input
# non produce niente non e una prova. Per questo la sequenza comincia con
# un punto — senza, in questo parlato finto non c'e nessun attacco e la
# lista e vuota qualunque cosa faccia il codice.
tratti = A.tratti_parlati(NUM, 0.0, 10.0)
check(f"le righe escono: {len(tratti)}", len(tratti) == 4)
check("e la piu lunga attraversa il numero fino in fondo",
      any(t["testo"] == "Per un ricco 2.000 euro sono pochi" for t in tratti))

print("\n— il conto e il muro vengono dallo stesso posto —")
import inspect
check("candidati() usa ha_muro()", "ha_muro(" in inspect.getsource(A.candidati))
check("e anche tratti_parlati()", "ha_muro(" in inspect.getsource(A.tratti_parlati))
check("nessuno dei due si rifa' la sua lista di muri",
      "set(MURI)" not in inspect.getsource(A.candidati)
      and "set(MURI)" not in inspect.getsource(A.tratti_parlati))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

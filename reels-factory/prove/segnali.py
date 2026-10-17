"""Il metro con cui si misura un motore di trascrizione.

Lorenzo, 15/10, su ElevenLabs: «bisognerebbe stimare quanto ci servirebbe
in termini di crediti e quanto ne vale la pena». Per rispondere con un
numero serve un metro che dia lo stesso risultato sui due motori, e che
misuri la cosa giusta: non quante parole indovina, ma quanti PUNTI DI
PARTENZA mette sul tavolo. Il testo di Whisper, su quelle dieci clip, era
buono; i tagli no.

Qui si prova il metro, non i motori: due trascrizioni finte, una piena di
silenzi e una tutta incollata, e il metro deve distinguerle.

    python prove/segnali.py
"""
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from src import segnali as S

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


def parla(*coppie, passo=0.4):
    """(testo, silenzio_prima) → parole con i tempi, come le da un motore."""
    fuori, t = [], 0.0
    for testo, prima in coppie:
        t += prima
        fuori.append({"word": testo, "start": round(t, 3),
                      "end": round(t + passo, 3)})
        t += passo
    return fuori


print("— una trascrizione INCOLLATA, come quella di Whisper —")
# E' la forma misurata il 17/10: tempi attaccati, un segno in 34 secondi.
INCOLLATA = parla(("non", 0), ("ho", 0), ("tempo", 0), ("per", 0),
                  ("fare", 0), ("contenuti", 0), ("mi", 0), ("dicono", 0))
m = S.misura(INCOLLATA)
check(f"tutti gli stacchi a zero ({m['zeri']}/{m['stacchi']})",
      m["zeri"] == m["stacchi"] == 7)
check("nessuna pausa utile", m["pause"] == 0 and m["pause_forti"] == 0)
check("nessun segno di punteggiatura", m["segni"] == 0)
check("quindi zero attacchi offerti", m["attacchi"] == 0)

print("\n— una con i silenzi, come dovrebbe essere —")
CON_PAUSE = parla(("Basta.", 0), ("Non", 1.2), ("ho", 0), ("tempo", 0),
                  ("per", 0), ("fare", 0.6), ("contenuti,", 0), ("dicono", 0.5))
m = S.misura(CON_PAUSE)
check(f"le pause si vedono ({m['pause']} sopra {S.PAUSA}s)", m["pause"] == 3)
check(f"e quella lunga si distingue ({m['pause_forti']} sopra "
      f"{S.PAUSA_FORTE}s)", m["pause_forti"] == 1)
# «Basta.» e un muro, «contenuti,» una virgola: due prove diverse, contate
# separate. La prima versione di questa riga le sommava in «segni» e
# pretendeva 2 — e il metro ignorava le virgole del tutto.
check("il muro si conta", m["segni"] == 1)
check("e la virgola si conta a parte", m["virgole"] == 1)
check(f"attacchi offerti: {m['attacchi']} (1 muro + 1 virgola + 3 pause)",
      m["attacchi"] == 5)
check("lo stacco piu lungo e quello giusto", abs(m["stacco_max"] - 1.2) < 0.01)

print("\n— le svolte vivono nel testo, non nei tempi —")
# E' la prova che resta quando pause e punteggiatura non ci sono: l'11/09
# le dodici candidate venivano tutte da qui.
SVOLTE = parla(("io", 0), ("credo", 0), ("ma", 0), ("invece", 0),
               ("pero", 0), ("basta", 0))
m = S.misura(SVOLTE)
check(f"ne trova {m['svolte']}", m["svolte"] == 3)
check("e le conta fra gli attacchi anche senza un solo silenzio",
      m["attacchi"] == 3 and m["pause"] == 0)
check("«pero» e «però» valgono uguale",
      S.misura(parla(("x", 0), ("però", 0)))["svolte"] == 1)
check("una svolta con la virgola attaccata si riconosce",
      S.misura(parla(("x", 0), ("ma,", 0)))["svolte"] == 1)

print("\n— i bordi —")
check("lista vuota: zero, senza esplodere", S.misura([])["attacchi"] == 0)
check("una parola sola: zero stacchi", S.misura(parla(("sola", 0)))["stacchi"] == 0)
check("le parole vuote non contano",
      S.misura([{"word": "  ", "start": 0, "end": 1}] + INCOLLATA)["parole"] == 8)
check("la densita di punteggiatura e al minuto, non assoluta",
      abs(S.misura(CON_PAUSE)["segni_min"]
          - 1 / (S.misura(CON_PAUSE)["durata"] / 60)) < 0.01)

print("\n— il confronto deve dire la cosa giusta —")
testo = S.confronto(("Whisper", S.misura(INCOLLATA)),
                    ("Scribe", S.misura(CON_PAUSE)))
check("mette i due numeri in fila", "0 con Whisper, 5 con Scribe" in testo)
check("e dice quanti punti in piu si guadagnano", "ne offre 5 in piu" in testo)
pari = S.confronto(("Whisper", S.misura(INCOLLATA)),
                   ("Scribe", S.misura(INCOLLATA)))
check("se nessuno dei due offre niente, lo dice chiaro",
      "nessuno dei due da un punto da cui partire" in pari)

print("\n— le soglie sono quelle che usa la fabbrica, non altre —")
# Un metro con soglie sue misurerebbe un'altra cosa e darebbe un verdetto
# che non vale per il codice vero.
import types
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import aggancio as A
check("PAUSA e la stessa di aggancio.py", S.PAUSA == A.PAUSA)
check("PAUSA_FORTE pure", S.PAUSA_FORTE == A.PAUSA_FORTE)
check("i muri sono gli stessi", set(S.MURI) == set(A.MURI))
check("le virgole pure", set(S.VIRGOLE) == set(A.VIRGOLE))
check("e le svolte pure", S.SVOLTE == A.SVOLTE)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

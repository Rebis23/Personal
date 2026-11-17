"""Una risposta troncata non deve portarsi via la lavorazione.

Il 12 e il 17/11, a cinque giorni di distanza, due corse sono morte nello
stesso punto — la scelta delle clip — dopo 52 e 41 minuti di lavoro gia
fatto. Stesso errore tutte e due le volte:

    pydantic_core.ValidationError: 1 validation error for ClipSelection
      Invalid JSON: EOF while parsing a string at line 1 column 5420
      input_value='{"clips":[{"start_second...movie_query":"","movie_'

e la seconda volta tagliata prima, alla colonna 3052, su «"emphasis».

Il 12 avevo riferito che era un colpo singolo. Era vero di quello che si
sapeva allora e falso cinque giorni dopo: due volte non e un caso, e una
prova che lo dice vale piu di una frase in un rapporto.

Il difetto peggiore non e il JSON rotto: e che l'eccezione non era gestita,
quindi una risposta sbagliata costava 45 minuti di runner e un giorno di
pubblicazioni. E che client.messages.parse() valida PRIMA di restituire,
quindi il codice che legge stop_reason — l'unico numero che dice perche la
risposta si e fermata — non veniva mai raggiunto. Due guasti, zero numeri.

    python prove/troncata.py
"""
import inspect
import sys
import types
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
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


class RispostaFinta:
    def __init__(self):
        self.stop_reason = "end_turn"
        self.usage = types.SimpleNamespace(input_tokens=10, output_tokens=20)
        self.parsed_output = object()
        self.content = [types.SimpleNamespace(text='{"clips":[]}')]


class ClienteFinto:
    """Un client che cade un numero dato di volte e poi risponde."""

    def __init__(self, cadute, errore=None):
        self.cadute = cadute
        self.errore = errore or ValueError(
            "Invalid JSON: EOF while parsing a string at line 1 column 3052")
        self.chiamate = 0
        self.diagnosi = 0
        self.messages = self

    def parse(self, **_kw):
        self.chiamate += 1
        if self.chiamate <= self.cadute:
            raise self.errore
        return RispostaFinta()

    def create(self, **_kw):
        self.diagnosi += 1
        return RispostaFinta()


print("— la rete regge —")
c = ClienteFinto(cadute=1)
r = B._scelta_con_rete(c, model="m", system="s", user="u", attesa=0)
check("una caduta e la seconda volta passa", r is not None and c.chiamate == 2)

c = ClienteFinto(cadute=2)
r = B._scelta_con_rete(c, model="m", system="s", user="u", attesa=0)
check("due cadute e la terza passa", r is not None and c.chiamate == 3)

print("\n— ma non nasconde un guasto vero —")
c = ClienteFinto(cadute=99)
caduto = False
try:
    B._scelta_con_rete(c, model="m", system="s", user="u", attesa=0)
except ValueError:
    caduto = True
check("se cadono tutti i tentativi, rilancia", caduto)
check(f"e i tentativi sono stati 3, non infiniti ({c.chiamate})",
      c.chiamate == 3)
# Una corsa che fallisce in silenzio sembra una corsa riuscita a vuoto, e
# il controllo del mattino la riferirebbe come «nessun video nuovo».
check("non ritorna None di nascosto",
      "raise ultimo" in inspect.getsource(B._scelta_con_rete))

print("\n— e ogni caduta lascia il numero che spiega perche —")
c = ClienteFinto(cadute=1)
B._scelta_con_rete(c, model="m", system="s", user="u", attesa=0)
check("a ogni caduta si chiede stop_reason senza schema",
      c.diagnosi == 1)
diag = inspect.getsource(B._perche_si_e_fermata)
check("la diagnosi stampa stop_reason", "stop_reason=" in diag)
check("e quanto era lungo il testo davvero", "caratteri" in diag)
check("e quanti token sono usciti, col tetto accanto",
      "output_tokens" in diag and "BUDGET_SCELTA" in diag)
check("usa create(), non parse(): senza schema non c'e niente da validare",
      ".create(" in diag and ".parse(" not in diag)
check("la diagnosi non puo far cadere la rete: e dentro un try",
      "except Exception" in diag)
check("e quello che spende lo segna sul conto",
      "conto.segna('scelta clip (diagnosi)'" in diag)

print("\n— il tetto NON e stato alzato —")
# Nelle corse riuscite la scelta clip esce a 9.776, 10.294, 11.390, 11.589
# e 13.149 token su 16.000. Il taglio del 17/11 e arrivato a 3.052
# CARATTERI: un decimo del tetto. Alzare un limite mai raggiunto e
# ripararla a caso, ed e la cosa che Lorenzo ha chiesto di non fare.
check(f"resta 16000 ({B.BUDGET_SCELTA})", B.BUDGET_SCELTA == 16000)
rete = inspect.getsource(B._scelta_con_rete)
check("e il perche sta scritto accanto, coi numeri",
      "3.052" in rete and "ripararla a caso" in rete)

print("\n— la rete e davvero sulla strada principale —")
sorgente = inspect.getsource(B.select_clips)
check("select_clips passa dalla rete", "_scelta_con_rete(" in sorgente)
check("e non chiama piu parse() per conto suo",
      "client.messages.parse(" not in sorgente)
check("il controllo su refusal resta dopo", 'stop_reason == "refusal"' in sorgente)
check("e il conto si segna ancora", "conto.segna('scelta clip'" in sorgente)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

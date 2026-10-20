"""Chiedere prima di spendere, e dire cosa fare.

Il 25 e il 26/09 sei corse di ingest hanno fatto la stessa cosa sei volte:

    19:56  video scaricato via Apify (201 MB, cinque minuti)
    20:01  trascritto con Scribe, 3142 parole
    20:02  «Your credit balance is too low to access the Anthropic API»

Sette minuti e due servizi a pagamento, tre volte al giorno, per scoprire
una cosa che si sapeva prima di cominciare. Il codice era giusto: quello
che mancava era l'ordine delle domande — si pagava per lo scarico e poi si
andava a vedere se il cervello rispondeva.

E il messaggio conta quanto il momento. Nel traceback i tre guasti
possibili si somigliano, ma non si somigliano per niente in cio che va
fatto: il credito si risolve pagando, la chiave rigenerandola, il limite
di frequenza aspettando. Un errore che non dice quale dei tre e costringe
a leggere il log per indovinare.

    python prove/cervello.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import brain as B

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


# Il testo vero, copiato dal log della corsa 177 del 26/09 alle 22:28.
VERO = ("Error code: 400 - {'type': 'error', 'error': {'type': "
        "'invalid_request_error', 'message': 'Your credit balance is too low "
        "to access the Anthropic API. Please go to Plans & Billing to upgrade "
        "or purchase credits.'}, 'request_id': 'req_011CfSqeHZzNYzR2nLGapdrT'}")

print("\n— il guasto vero del 26/09 —")
detto = B.leggi_guasto(Exception(VERO))
check("riconosce il credito esaurito", "credito Anthropic esaurito" in detto)
check("dice dove si ricarica", "Plans & Billing" in detto)
check("dice che non e un bug da riparare", "codice" in detto)
check("non sputa il traceback addosso a chi legge", "request_id" not in detto)

print("\n— gli altri due, che si curano in modo diverso —")
chiave = B.leggi_guasto(Exception(
    "Error code: 401 - {'error': {'type': 'authentication_error', "
    "'message': 'invalid x-api-key'}}"))
check("la chiave rifiutata si riconosce", "chiave" in chiave)
check("e non viene confusa col credito",
      "credito Anthropic esaurito" not in chiave)

freq = B.leggi_guasto(Exception(
    "Error code: 429 - {'error': {'type': 'rate_limit_error'}}"))
check("il limite di frequenza si riconosce", "frequenza" in freq)
check("e dice che passa da solo", "riprova" in freq)
check("e non viene confuso col credito",
      "credito Anthropic esaurito" not in freq)

print("\n— un guasto mai visto —")
ignoto = B.leggi_guasto(Exception("overloaded_error: the engine is busy"))
check("non inventa una diagnosi", "credito" not in ignoto and "chiave" not in ignoto)
check("riporta comunque il testo originale", "overloaded_error" in ignoto)
lungo = B.leggi_guasto(Exception("x" * 5000))
check("e non allaga il log", len(lungo) <= 300)

print("\n— l'ordine delle domande —")
# cervello_pronto() va chiamato PRIMA dello scarico, non dopo: e' tutto il
# punto. Qui si controlla che in cmd_ingest venga prima del feed.
codice = (Path(__file__).resolve().parent.parent / "src" / "main.py").read_text()
corpo = codice.split("def cmd_ingest")[1].split("\ndef ")[0]
check("cervello_pronto() e' dentro cmd_ingest",
      "cervello_pronto" in corpo)
check("e viene prima di guardare il feed",
      corpo.index("cervello_pronto") < corpo.index("fetch_recent_videos"))
check("senza cervello la corsa finisce male (esce 1, cosi arriva la mail)",
      "return 1" in corpo[corpo.index("cervello_pronto"):][:400])


print("\n— e si riprova, se il guasto e di quelli che passano —")
# Il 18 e il 19/10 due corse sono morte qui su «Request timed out», con la
# chiave viva e il credito pieno. Un controllo nato per non sprecare una
# lavorazione ne stava buttando una al giorno da solo.
check("un timeout si riprova", B.passeggero("Request timed out or interrupted"))
check("una connessione caduta pure", B.passeggero("Connection error."))
check("un 503 pure", B.passeggero("503 overloaded_error"))
check("il credito finito NO: aspettare non lo ricarica",
      not B.passeggero("credito Anthropic esaurito — serve una ricarica"))
check("la chiave rifiutata nemmeno",
      not B.passeggero("authentication_error: invalid x-api-key"))
check("e un guasto mai visto non si riprova a caso",
      not B.passeggero("qualcosa di mai visto"))


class Finto:
    """Risponde male le prime N volte, poi bene."""

    def __init__(self, quanti, errore="Request timed out or interrupted"):
        self.rimasti, self.errore, self.chiamate = quanti, errore, 0

    def __call__(self, **kw):
        self.chiamate += 1
        if self.rimasti > 0:
            self.rimasti -= 1
            raise RuntimeError(self.errore)
        return object()


def gira(finto):
    import os
    import types as t
    vecchio = B.anthropic.Anthropic
    B.anthropic.Anthropic = lambda **_: t.SimpleNamespace(
        messages=t.SimpleNamespace(create=finto))
    os.environ.setdefault("ANTHROPIC_API_KEY", "prova")
    try:
        return B.cervello_pronto("m", attesa=0.0)
    finally:
        B.anthropic.Anthropic = vecchio


f = Finto(2)
vivo, _ = gira(f)
check(f"due timeout e poi passa: vivo ({f.chiamate} tentativi)",
      vivo and f.chiamate == 3)

f = Finto(99)
vivo, guasto = gira(f)
check(f"ma non si riprova per sempre ({f.chiamate} tentativi)",
      not vivo and f.chiamate == 3)
check("e dice quante volte ha provato", "dopo 3 tentativi" in guasto)

f = Finto(99, errore=B.CREDITO_ESAURITO)
vivo, guasto = gira(f)
check(f"col credito finito si esce al primo colpo ({f.chiamate})",
      not vivo and f.chiamate == 1)
check("e il messaggio dice cosa fare, non cosa e successo",
      "ricarica" in guasto)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

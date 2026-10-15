"""La trascrizione non deve viaggiare due volte.

Lorenzo, 15/10, mandando il prompt «token-saver» di Blatchford: applicalo
all'editing, anche ai video lunghi. Il punto 1 di quel prompt — «trova i
compiti dove spendi piu token» — da noi era gia fatto e misurato da
conto.py. Il punto 2 — «puo farlo la macchina gratis prima che il modello
legga?» — aveva gia incassata la risposta piu grossa il 9 ottobre: Whisper
in locale al posto di ElevenLabs.

Quello che l'audit ha trovato di nuovo e spreco puro: la trascrizione
INTERA partiva due volte a ogni lavorazione. Una per scegliere le clip, e
una dentro riscrivi_hooks() per rifare i banner bocciati. Ma per riscrivere
il banner di una clip servono le parole di QUELLA clip:

    video dell'11/10    ~6.300 token rispediti per niente
    video da 40 minuti  ~19.000

Il taglio si appoggia ai marcatori [mm:ss] che to_timed_text() mette gia
ogni 10 secondi: nessuna macchina nuova, solo smettere di spedire.

    python prove/doppia.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import transcript as T

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


# Mezz'ora di parlato, una parola al secondo: come un video vero.
PAROLE = [{"word": f"p{i}", "start": float(i), "end": i + 0.9}
          for i in range(1800)]
INTERO = T.to_timed_text(PAROLE)

print("— quanto si risparmia —")
f = T.finestra(INTERO, 600.0, 660.0)
quota = 100 * len(f) / len(INTERO)
check(f"su mezz'ora, una clip da un minuto costa il {quota:.0f}% del testo",
      quota < 15)

print("\n— e c'e dentro quello che serve —")
check("le parole della clip ci sono tutte",
      all(f"p{i}" in f for i in range(600, 660)))
check("con un po' di contorno prima", "p585" in f)
check("e dopo", "p675" in f)
check("ma non il resto del video", "p100" not in f and "p1700" not in f)
check("i marcatori restano: servono al modello per orientarsi",
      "[10:00]" in f)

print("\n— i casi ai bordi —")
check("una finestra all'inizio non va sotto zero",
      T.finestra(INTERO, 0.0, 30.0).startswith("[00:00]"))
check("una finestra alla fine non esplode",
      "p1795" in T.finestra(INTERO, 1780.0, 1800.0))
check("trascrizione vuota: finestra vuota", T.finestra("", 10.0, 20.0) == "")
check("finestra fuori dal video: niente, non tutto",
      T.finestra(INTERO, 5000.0, 5100.0) == "")

print("\n— il collegamento, che e la parte che si rompe —")
# Una finestra perfetta serve a zero se riscrivi_hooks continua a spedire
# tutto. Qui si guarda il punto di consumo, non solo l'attrezzo.
import inspect
import types

if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import brain as B

corpo = inspect.getsource(B.riscrivi_hooks)
check("riscrivi_hooks() usa transcript.finestra()",
      "transcript.finestra(" in corpo)
check("e non spedisce piu la trascrizione intera",
      "TRASCRIZIONE:" not in corpo)
check("se le finestre non si trovano si ripiega sull'intero, invece di "
      "mandare il vuoto", "or timed_transcript" in corpo)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

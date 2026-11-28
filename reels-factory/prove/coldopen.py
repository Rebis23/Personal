"""Il cold open passa gli stessi controlli di tutto il resto.

Il cold open e la frase piu tagliente della clip, staccata e rimontata in
testa. L'idea e buona. Il guaio e che veniva assemblato DOPO i controlli,
quindi li scavalcava — e ha fatto danni tre volte, sempre per quel motivo:

  11/11  clip uscita a 51 secondi col tetto a 50: taglio 47,8s + 3,2s di
         cold open. Il tetto si verificava su end-start.
  20/11  la prima cosa che si sentiva era «E' chiaro che e una battaglia
         che fai molta fatica a vincere, perche il tuo cervello vede.» La
         riga d'apertura verificata era un'altra: il cold open le stava
         davanti.
  28/11  «Finisco per odiarmi per aver sprecato tempo che non tornera mai.
         E» — si ferma su «E», e la stessa frase si risente nella clip
         trenta secondi dopo.

Il commento in main.py diceva gia «deve stare almeno 6s dopo l'inizio,
altrimenti si sentirebbe due volte di fila»: il problema era visto, ma la
distanza non basta, perche la frase puo ricomparire piu avanti.

Chi non passa non si usa, e la clip esce senza cold open. Il contenuto non
si butta: il difetto sta nella decorazione.

    python prove/coldopen.py
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


def parla(frase, da=0.0, passo=0.5):
    parole, t = [], da
    for w in frase.split():
        parole.append({"word": w, "start": round(t, 3),
                       "end": round(t + passo, 3)})
        t += passo
    return parole


print("— i secondi del cold open si contano nel tetto —")
# Il caso dell'11/11, coi numeri veri: 47,8s di clip + 3,2s di cold open
# = 51, col tetto a 50.
W = parla("uno due tre quattro cinque sei sette otto nove dieci", da=0.0)
va, perche = T.cold_open_valido(W, (0.0, 3.2), 0.0, 47.8, 50.0)
check(f"47,8 + 3,2 oltre 50 non passa ({perche[:40]})", not va)
check("e il motivo dice i due pezzi",
      "di clip" in perche and "di cold open" in perche)
va, _ = T.cold_open_valido(W, (0.0, 3.2), 0.0, 40.0, 50.0)
check("40 + 3,2 dentro 50 passa", va)

print("\n— non si chiude su una parola orfana —")
# Il caso del 28/11: punto fermo, e poi una parola appesa dopo.
ORFANA = parla("Finisco per odiarmi per aver sprecato tempo che non tornerà mai. È")
# La finestra del punch deve coprire le parole e nient'altro: con (0, 99)
# il cold open risultava da 99 secondi e scattava il tetto, non il
# controllo che volevo provare. La prova era sbagliata, non il codice.
FINE_ORFANA = ORFANA[-1]["end"]
va, perche = T.cold_open_valido(ORFANA, (0.0, FINE_ORFANA), 0.0, 20.0, 50.0)
check(f"«... mai. È» non passa ({perche[:44]})", not va)
check("e il motivo mostra le due parole", "«mai. È»" in perche)
PULITA = parla("Finisco per odiarmi per aver sprecato tempo che non tornerà mai.")
va, _ = T.cold_open_valido(PULITA, (0.0, PULITA[-1]["end"]), 0.0, 20.0, 50.0)
check("la stessa frase senza la parola appesa passa", va)

print("\n— non si dice due volte —")
# Il cold open sta nei primi secondi; la stessa frase torna piu avanti
# nella clip. Il controllo della distanza (6s) non la vedeva.
DOPPIA = parla("la mia mente è cibo spazzatura", da=0.0)
DOPPIA += parla("poi parlo di altre cose per un po", da=10.0)
DOPPIA += parla("la mia mente è cibo spazzatura", da=20.0)
va, perche = T.cold_open_valido(DOPPIA, (0.0, 2.9), 0.0, 30.0, 50.0)
check(f"la frase ripetuta non passa ({perche[:38]})", not va)
UNICA = parla("la mia mente è cibo spazzatura", da=0.0)
UNICA += parla("poi parlo di altre cose per un bel po di tempo", da=10.0)
va, _ = T.cold_open_valido(UNICA, (0.0, 2.9), 0.0, 30.0, 50.0)
check("se si dice una volta sola, passa", va)
# La punteggiatura di Whisper va e viene: il confronto deve ignorarla, se
# no basta una virgola in piu e il doppione non si vede.
VIRGOLA = parla("la mia mente è cibo spazzatura", da=0.0)
VIRGOLA += parla("e poi di nuovo, la mia, mente è cibo spazzatura!", da=10.0)
va, _ = T.cold_open_valido(VIRGOLA, (0.0, 2.9), 0.0, 30.0, 50.0)
check("e una virgola in mezzo non nasconde il doppione", not va)

print("\n— un cold open buono passa, e torna il suo testo —")
BUONO = parla("Le tue cattive abitudini non sono il problema vero.", da=0.0)
BUONO += parla("adesso ti spiego come funziona la faccenda nel dettaglio", da=12.0)
va, testo = T.cold_open_valido(BUONO, (0.0, 4.5), 0.0, 25.0, 50.0)
check("passa", va)
check("e il secondo valore e il testo, non un motivo",
      va and "cattive abitudini" in testo)

print("\n— i casi vuoti non esplodono —")
va, _ = T.cold_open_valido([], (0.0, 3.0), 0.0, 30.0, 50.0)
check("senza parole non passa", not va)
va, _ = T.cold_open_valido(W, (900.0, 903.0), 0.0, 30.0, 50.0)
check("un tratto fuori dal parlato non passa", not va)

print("\n— ed e collegato davvero —")
principale = (RADICE / "src" / "main.py").read_text(encoding="utf-8")
check("main.py chiama il controllo",
      "transcript.cold_open_valido(" in principale)
check("e se non passa mette punch a None",
      "Cold open scartato" in principale and "punch = None" in principale)
# Se il controllo fallisce, la clip deve uscire comunque: il contenuto e
# buono, era la decorazione a essere rotta.
sorgente = inspect.getsource(T.cold_open_valido)
check("il controllo non butta la clip, torna solo un verdetto",
      "return False, " in sorgente and "continue" not in sorgente)
check("il tetto che usa e quello di config, non un numero scritto a mano",
      'float(clip_cfg["max_seconds"])' in principale)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

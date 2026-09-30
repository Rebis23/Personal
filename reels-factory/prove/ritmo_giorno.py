"""Il secondo Reel non deve diventare impossibile per una regola.

IL 29/09 dovevano uscire due Reel e ne e uscito uno. Nessun errore: il
codice ha fatto quello che c'era scritto. I sette turni di publish sono
stati consegnati da GitHub cosi:

    18:49 UTC (20:49 italiane)  -> pubblica
    20:08 UTC (22:08 italiane)  -> fuori finestra
    21:30 UTC (23:30 italiane)  -> fuori finestra
    23:04 UTC (01:04 italiane)  -> fuori finestra

Undici ore di ritardo sul primo turno. Uno solo su sette e atterrato dentro
la finestra 7-22, e con la distanza minima fissa a 5 ore un turno solo fa un
Reel solo: cinque ore dopo le 20:49 e l'1:49 di notte.

La distanza di 5 ore era corretta a 1 Reel al giorno — serviva a impedire che
due turni arretrati consegnati insieme sparassero due Reel nello stesso
minuto. A 2 al giorno e diventata il tappo.

Adesso la distanza si calcola dal tempo che resta. Questa prova tiene
insieme le due cose che devono restare vere allo stesso tempo: che a fine
giornata il Reel esca comunque, e che a inizio giornata i Reel restino
distanziati — perche rilassare la regola sempre vorrebbe dire riportare il
guaio del 31/08, due Reel a un minuto di distanza.

    python prove/ritmo_giorno.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ritmo_giorno import MINIMO_ASSOLUTO, distanza_richiesta

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


def d(ora, usciti, *, piena=5.0, fine=22, tetto=2):
    return distanza_richiesta(distanza_piena=piena, ora_adesso=ora,
                              fine_finestra=fine, gia_usciti=usciti,
                              tetto=tetto)


print("\n— il 29/09, rigiocato —")
# 20:49 italiane, zero Reel usciti, due da piazzare entro le 22.
richiesta = d(20, 0)
check(f"la distanza scende a {richiesta:.1f}h invece di 5", richiesta < 5.0)
check("quindi il secondo Reel torna possibile", richiesta <= 2.0)
check("ma non escono attaccati", richiesta >= MINIMO_ASSOLUTO)

print("\n— la mattina la regola resta larga —")
check(f"alle 9:00 con 2 da piazzare serve ancora il massimo ({d(9, 0):.1f}h)",
      d(9, 0) == 5.0)
check(f"alle 12:00 idem ({d(12, 0):.1f}h)", d(12, 0) == 5.0)
check("alle 16:00 comincia a stringere", d(16, 0) < 5.0)

print("\n— piu tardi e piu strettamente si sta —")
serie = [(h, d(h, 0)) for h in (9, 14, 17, 19, 20, 21)]
for h, v in serie:
    print(f"      {h}:00 -> {v:.2f}h")
check("la distanza non cresce mai andando avanti nel tempo",
      all(a[1] >= b[1] for a, b in zip(serie, serie[1:])))

print("\n— non si scende mai sotto la mezz'ora —")
check("alle 21:45 con uno da piazzare", d(21, 1) >= MINIMO_ASSOLUTO)
check("nemmeno all'ultimo minuto utile", d(22, 1) >= MINIMO_ASSOLUTO)
check("nemmeno con un tetto assurdo", d(20, 0, tetto=10) >= MINIMO_ASSOLUTO)

print("\n— il tetto del giorno raggiunto —")
check("se sono usciti tutti, torna la distanza piena (decide il tetto)",
      d(20, 2) == 5.0)
check("e anche se ne sono usciti di piu", d(20, 3) == 5.0)

print("\n— fuori finestra decide l'orario, non questa regola —")
check("a mezzanotte torna la distanza piena", d(0, 0) == 5.0)
check("dopo la fine della finestra idem", d(23, 0) == 5.0)

print("\n— un tetto a 1 si comporta come prima —")
check("con un Reel al giorno e mattina, distanza piena",
      d(9, 0, tetto=1) == 5.0)
check("e a fine giornata stringe pure lui", d(21, 0, tetto=1) < 5.0)

print("\n— finestre diverse —")
check("con finestra fino alle 20 stringe prima",
      d(17, 0, fine=20) < d(17, 0, fine=23))
check("una finestra larghissima resta al tetto",
      d(9, 0, fine=24) == 5.0)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

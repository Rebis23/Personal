"""Un momento che e gia un Reel non si rifa.

Lorenzo, 17/10: «Per le vecchie clip, pubblica 6 e 7, poi riedita le altre
con il nuovo metodo». Cioe: dello stesso video lungo, due clip restano e
le altre si rifanno da capo.

Qui si rompeva. `montate` — la lista degli spezzoni gia usati — nasceva
vuota a ogni lavorazione: il controllo valeva DENTRO la corsa e dimenticava
tutto appena finita. La corsa nuova avrebbe riproposto gli stessi due
momenti migliori (sono i migliori, per questo erano stati scelti), e sul
profilo sarebbero usciti due Reel identici a un giorno di distanza.

Il controllo sui tempi c'era gia dall'11/09, quando due clip sono uscite a
0.78 secondi l'una dall'altra con banner diversi e audio identico. Era
giusto e aveva la memoria corta.

    python prove/gemelle.py
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
from src import aggancio as A
from src import main as M

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


print("— il confronto sui tempi, che c'era gia —")
check("due clip sullo stesso minuto sono la stessa clip",
      A.stesso_spezzone((100.0, 160.0), (105.0, 165.0)))
check("due clip lontane no", not A.stesso_spezzone((100.0, 160.0), (300.0, 360.0)))
check("un contatto di pochi secondi non basta",
      not A.stesso_spezzone((100.0, 160.0), (155.0, 215.0)))
# La soglia e esatta: serve PIU di meta della clip piu corta. Due clip da
# 60s che se ne dividono 29 sono due clip, 31 sono la stessa. La prima
# versione di questa riga chiedeva 29 e dava ROTTO su un codice giusto.
check("oltre la meta e la stessa clip (31s su 60)",
      A.stesso_spezzone((100.0, 160.0), (129.0, 189.0)))
check("sotto la meta sono due clip (29s su 60)",
      not A.stesso_spezzone((100.0, 160.0), (131.0, 191.0)))

print("\n— la memoria fra una corsa e l'altra —")
corpo = inspect.getsource(M._process_video)
check("montate si riempie con le clip gia in coda",
      'st.get("queue", [])' in corpo and "montate.append" in corpo)
check("e con quelle gia pubblicate", 'st.get("published", [])' in corpo)
check("solo per QUESTO video, non per tutti",
      'c.get("video_id") == vid' in corpo)
check("usa inizio/fine quando ci sono",
      '"inizio" in vecchia and "fine" in vecchia' in corpo)
check("e ritrova il testo quando non ci sono",
      "aggancio.trova_nel_parlato(" in corpo)
check("dove non si ritrova lo DICE, invece di far finta di niente",
      "potrebbe essere riproposta" in corpo)

print("\n— e i nomi non si ripetono —")
# Stessa occasione, difetto diverso e peggiore: la corsa nuova numerava
# le clip da 1, quindi avrebbe sfornato un "lReO_BD_fS4-2" mentre in coda
# ce n'era gia uno DIVERSO con quel nome. published e shorts_done
# identificano le clip per nome: avrebbero scambiato l'una per l'altra, e
# un Reel nuovo non sarebbe uscito perche "risulta gia uscito".
check("il numero riparte da dopo l'ultima clip di quel video",
      'scarto = max(usati) if usati else 0' in corpo
      and 'clip_id = f"{vid}-{scarto + n}"' in corpo)
check("si guarda sia la coda sia i pubblicati",
      'st.get("queue", []) + st.get("published", [])' in corpo)
check("e solo i numeri di QUESTO video",
      "testa == vid and coda.isdigit()" in corpo)


def prossimo(vid, esistenti):
    """La stessa regola di main.py, per provarla sui casi veri."""
    usati = []
    for cid in esistenti:
        testa, _, coda = cid.rpartition("-")
        if testa == vid and coda.isdigit():
            usati.append(int(coda))
    return (max(usati) if usati else 0) + 1


check("col caso di oggi la prossima e la 4",
      prossimo("lReO_BD_fS4", ["lReO_BD_fS4-2", "lReO_BD_fS4-3"]) == 4)
check("su un video mai lavorato si riparte da 1",
      prossimo("nuovo123", ["lReO_BD_fS4-2"]) == 1)
check("le clip di altri video non spostano il numero",
      prossimo("abc", ["xyz-9", "abc-1"]) == 2)
check("un identificativo strano non fa esplodere niente",
      prossimo("abc", ["abc-film", "abc-2"]) == 3)

print("\n— il ritrovamento nel parlato —")
# E' il caso vero di oggi: le due clip che restano sono state montate
# prima che la fabbrica salvasse i secondi, quindi hanno solo il testo.
def parla(frase, da=0.0, passo=0.4):
    return [{"word": w, "start": round(da + i * passo, 3),
             "end": round(da + i * passo + passo * 0.9, 3)}
            for i, w in enumerate(frase.split())]


PARLATO = parla("prima di tutto parliamo di una cosa Noi siamo nella nostra "
                "mente conscia il 5% del tempo il restante 95% e guidato "
                "dalla mente inconscia e qui si trovano i paradigmi")
quando = A.trova_nel_parlato(PARLATO, "Noi siamo nella nostra mente conscia",
                             0.0, 1e9)
check(f"la clip 6 si ritrova nel parlato (a {quando}s)", quando is not None)
check("ed e il punto giusto, non l'inizio del video", quando and quando > 2.0)
check("una frase che non c'e torna None, non zero",
      A.trova_nel_parlato(PARLATO, "una frase che non si sente mai",
                          0.0, 1e9) is None)

print("\n— e serve a questo: non rifare quello che e gia uscito —")
gia = (quando, quando + 60.0)
check("una clip nuova sullo stesso punto viene saltata",
      A.stesso_spezzone((quando + 3.0, quando + 63.0), gia))
check("una clip su un altro punto del video passa",
      not A.stesso_spezzone((quando + 400.0, quando + 460.0), gia))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

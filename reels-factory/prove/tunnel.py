"""Il tunnel non deve MAI restare su dopo lo scarico.

E' tutto il senso del cambiamento: l'esposizione passa da cinquanta minuti
a tre. Se una strada lascia il tunnel alzato — un'eccezione, una chiamata
annidata, uno scarico andato male — si torna al guasto di partenza, con la
differenza che stavolta sembrerebbe risolto.

    python prove/tunnel.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import tunnel                                        # noqa: E402

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


mosse: list[str] = []
tunnel.disponibile = lambda: True
tunnel._wg = lambda azione: (mosse.append(azione), True)[1]


def su() -> int:
    return mosse.count("up") - mosse.count("down")


with tunnel.acceso():
    prova("dentro il blocco il tunnel e su", su() == 1, str(mosse))
prova("all'uscita e giu", su() == 0, str(mosse))
prova("una salita e una discesa", mosse == ["up", "down"], str(mosse))

# Un'eccezione non deve lasciarlo acceso.
mosse.clear()
try:
    with tunnel.acceso():
        raise RuntimeError("scarico esploso")
except RuntimeError:
    pass
prova("anche con un'eccezione resta giu", su() == 0, str(mosse))

# Chiamate annidate: si alza una volta sola e si smonta all'ultima uscita.
mosse.clear()
with tunnel.acceso():
    with tunnel.acceso():
        prova("annidato: sempre e solo una salita", mosse.count("up") == 1, str(mosse))
    prova("l'uscita interna NON lo smonta", su() == 1, str(mosse))
prova("lo smonta l'ultimo che esce", su() == 0, str(mosse))

# Se non si alza, si va avanti lo stesso: lo scarico fallira dicendo perche.
mosse.clear()
tunnel._wg = lambda azione: (mosse.append(azione), azione != "up")[1]
arrivato = False
with tunnel.acceso() as vivo:
    arrivato = True
    prova("se non si alza lo dice", vivo is False)
prova("se non si alza si va avanti lo stesso", arrivato)

# Senza profilo non si tocca niente.
mosse.clear()
tunnel.disponibile = lambda: False
with tunnel.acceso() as vivo:
    pass
prova("senza profilo non si chiama wg-quick", mosse == [] and vivo is False, str(mosse))

# LA DOMANDA A CUI NON SI PUO' RISPONDERE. /etc/wireguard e di root e mode
# 0700: chiedergli "esiste questo file?" solleva PermissionError invece di
# dire no. Il 5/09 questo ha fatto morire l'ingest alla prima chiamata a
# yt-dlp, dentro il codice scritto apposta per rendere le cose piu sicure.
import importlib                                               # noqa: E402
import os                                                     # noqa: E402

from src import tunnel as T                                   # noqa: E402

importlib.reload(T)                 # si ricarica: sopra e stato manomesso
os.environ.pop(T.PRONTO, None)


class ConfVietata:
    """Finge /etc/wireguard/warp.conf: di root, mode 0700, guai a guardarlo."""
    def is_file(self):
        raise PermissionError(13, "Permission denied")


T.CONF = ConfVietata()
try:
    risposta = T.disponibile()
    prova("un file che non si puo guardare non fa esplodere niente", True)
    prova("e la risposta e un si/no", isinstance(risposta, bool), repr(risposta))
except PermissionError as e:
    prova("un file che non si puo guardare non fa esplodere niente", False, str(e))
    prova("e la risposta e un si/no", False)

# Il workflow ha l'ultima parola: se dice che non c'e, non si guarda nemmeno.
os.environ[T.PRONTO] = "0"
prova("WARP_PRONTO=0 vince sul file", T.disponibile() is False)
os.environ[T.PRONTO] = "1"
prova("WARP_PRONTO=1 vince sul file", T.disponibile() is True)
os.environ.pop(T.PRONTO, None)

print(f"\n{verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

"""Il tunnel WARP acceso solo quando serve davvero.

Serve a una cosa sola: passare il muro anti-bot di YouTube. Provato il
5/09 lanciando l'ingest senza — "Sign in to confirm you're not a bot", e
nessuna delle altre tre strade (Apify, Drive, cookie) e configurata. Quindi
il tunnel serve.

Il guaio e che restava acceso per tutti i cinquanta minuti del lavoro,
mentre lo scarico ne occupa tre. E per tutti quei minuti Cloudflare poteva
tagliare fuori il runner da GitHub — successo quattro volte in due giorni:
78 minuti appesi, un runner tolto di mezzo a meta lavoro, due volte
mezz'ora e passa di silenzio.

Contro quel guasto i tetti di tempo non possono niente, e la ragione e
istruttiva: a rompersi non e il comando, e il canale con cui il runner
racconta a GitHub cosa sta facendo. Un timeout scritto dentro il runner ha
bisogno di qualcuno che lo faccia rispettare, e quel qualcuno e dall'altra
parte del taglio.

L'unica difesa vera e restare esposti per meno tempo. Qui il tunnel si
alza prima di ogni chiamata a yt-dlp e si smonta subito dopo: da cinquanta
minuti di esposizione a tre. Durante trascrizione, montaggio, caricamento
su R2 e push, il runner sta sulla sua rete di sempre e nessuno puo
isolarlo.
"""

import os
import shutil
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path

CONF = Path("/etc/wireguard/warp.conf")

# Il workflow lo mette a 1 quando il profilo e pronto, a 0 quando nessun
# dispositivo ha retto. E' il modo pulito di saperlo: /etc/wireguard esiste
# apposta per non farsi leggere da nessuno tranne root.
PRONTO = "WARP_PRONTO"

# Piu chiamate a yt-dlp possono annidarsi: si conta chi e dentro, e si
# smonta solo quando esce l'ultimo. Senza, la prima uscita spegnerebbe il
# tunnel a un'altra chiamata ancora in corso.
_dentro = 0
_chiave = threading.Lock()


def disponibile() -> bool:
    """C'e un profilo WARP da alzare?

    Prima qui c'era solo CONF.is_file(), e il 5/09 ha fatto morire l'ingest
    alla prima chiamata a yt-dlp con "PermissionError: /etc/wireguard/
    warp.conf". Quella cartella e di root e mode 0700: guardarci dentro non
    e permesso, e is_file() su un errore di permessi non risponde "no", ti
    solleva un'eccezione in faccia. Chiedere "esiste?" a un file che non
    hai il diritto di guardare non e una domanda a cui si possa rispondere.
    """
    segnale = os.environ.get(PRONTO)
    if segnale in ("0", "1"):
        return segnale == "1"
    try:
        return CONF.is_file()
    except OSError:
        # Non poter guardare non vuol dire che non ci sia. Si prova ad
        # alzarlo: se non c'e, wg-quick fallisce e si tira avanti senza.
        return shutil.which("wg-quick") is not None


def _wg(azione: str) -> bool:
    """su o giu, con un tetto che non dipende dalla rete."""
    try:
        p = subprocess.run(["sudo", "timeout", "60", "wg-quick", azione, "warp"],
                           capture_output=True, text=True, timeout=90)
        return p.returncode == 0
    except Exception:                                   # noqa: BLE001
        return False


@contextmanager
def acceso():
    """Tunnel su per il tempo del blocco, giu comunque vada.

    Se non si alza si va avanti lo stesso: senza tunnel yt-dlp fallira sul
    muro anti-bot, e un fallimento chiaro e meglio di un lavoro fermo.
    """
    global _dentro
    if not disponibile():
        yield False
        return

    alzato = False
    with _chiave:
        if _dentro == 0:
            alzato = _wg("up")
            if not alzato:
                print("      ⚠️ Tunnel non alzato: provo lo stesso senza")
        _dentro += 1
    try:
        yield alzato or _dentro > 1
    finally:
        with _chiave:
            _dentro -= 1
            if _dentro == 0:
                _wg("down")

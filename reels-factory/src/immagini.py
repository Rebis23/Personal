"""La fascia di immagini in alto: foto vere prese da Pinterest.

Lorenzo, 4/09, mandando come riferimento un Reel con tre foto in cima
(Muhammad Ali, Verstappen, Steve Jobs) sopra il titolo:

    "graficamente vorrei avere tre immagini nel mio stile con una paletta di
     colori sensata, che permetta di attrarre visivamente il pubblico che
     desidero. Voglio foto reali, prese da Pinterest. Le voglio aesthetic."

Aveva anche insistito che una strada per Pinterest doveva esistere — e
aveva ragione. Non l'API ufficiale (da accesso solo ai TUOI pin) e non
xjdeng/pinterest-image-scraper che lui aveva proposto (fermo al 2020, e
prende solo le board): gallery-dl, che e mantenuto e fa anche le ricerche.

Misurato prima di costruirci sopra, perche con Instagram la stessa cosa
sembrava funzionare e poi dai runner GitHub dava 429 alla prima richiesta.
Sonda prova-pinterest.yml del 4/09, dai server di GitHub: 5 pin trovati
senza VPN, 3 file scaricati davvero, 5 pin anche sotto WARP. Passa.

Regola di sopravvivenza: qualunque cosa vada storta qui, la clip esce lo
stesso senza fascia. Le immagini sono un ornamento, il Reel e il lavoro.
"""

import base64
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import anthropic

from . import conto

# Il segreto va SEMPRE passato con .strip(). Quando si incolla una chiave nei
# GitHub Secrets ci resta attaccato un a-capo, e un a-capo dentro un header
# HTTP e illegale: la richiesta non parte nemmeno, e la libreria lo riporta
# come "Connection error." — che sembra la rete e invece e questa riga.
#
# Il 4 e il 5 settembre ho perso due giorni dietro a questo. Avevo scritto
# anthropic.Anthropic() senza chiave in tre punti nuovi, mentre brain.py la
# passava gia con .strip() dal primo giorno. Risultato: le chiamate vecchie
# funzionavano, le mie no, sempre, e io davo la colpa alla rete e a WARP.
# Tre tentativi su tre fallivano perche il guasto era deterministico.
def _cliente() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())


# Sotto questa misura sul lato corto l'immagine sgrana appena viene
# ingrandita nella fascia: si scarta invece di metterci una foto sfocata.
LATO_MINIMO = 400

# Pinterest serve anche video e gif animate: nella fascia ci vanno fotografie.
ESTENSIONI = {".jpg", ".jpeg", ".png", ".webp"}


def disponibile() -> bool:
    return shutil.which("gallery-dl") is not None


def _url_ricerca(query: str) -> str:
    from urllib.parse import quote
    return f"https://www.pinterest.com/search/pins/?q={quote(query)}"


def _lato_corto(f: Path) -> int:
    """Il lato corto in pixel, letto dall'intestazione del file."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(f)],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        w, h = (int(x) for x in out.split("x")[:2])
        return min(w, h)
    except Exception:                                   # noqa: BLE001
        return 0


def cerca(query: str, *, quante: int, dove: Path, stile: str = "",
          timeout: int = 90) -> list[Path]:
    """Scarica fino a `quante` fotografie per una ricerca su Pinterest.

    `stile` e la parola che tiene insieme il colpo d'occhio fra una clip e
    l'altra ("aesthetic", "editorial", "film grain"...): viene appesa a ogni
    ricerca, cosi le immagini di Reel diversi sembrano della stessa mano.
    """
    if not disponibile():
        print("      ⚠️ gallery-dl non installato: niente fascia di immagini")
        return []

    intera = f"{query} {stile}".strip()
    dove.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(
                ["gallery-dl", "-q", "--range", f"1-{quante * 3}", "-D", tmp,
                 _url_ricerca(intera)],
                capture_output=True, text=True, timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"      ⚠️ Pinterest non risponde per «{intera}»")
            return []

        # Si chiedono il triplo delle immagini che servono perche fra i
        # risultati ci finiscono video, gif e miniature piccole: la selezione
        # avviene qui, non sperando che i primi tre siano buoni.
        candidati = sorted(p for p in Path(tmp).iterdir()
                           if p.suffix.lower() in ESTENSIONI)
        tenuti: list[Path] = []
        for p in candidati:
            if len(tenuti) >= quante:
                break
            if _lato_corto(p) < LATO_MINIMO:
                continue
            finale = dove / f"{len(tenuti)}{p.suffix.lower()}"
            shutil.copyfile(p, finale)
            tenuti.append(finale)

    if not tenuti:
        print(f"      ⚠️ Nessuna immagine utile per «{intera}»")
    return tenuti


GIUDICE = """Queste sono foto pescate da Pinterest per la fascia in cima a un \
Reel di Instagram. Il Reel parla di: {tema}

Devo tenerne {quante}, e le altre le butto. Scegli quelle che REGGONO in cima \
a un Reel, guardandole davvero.

SCARTA SENZA PIETA:
- qualunque immagine con SCRITTE, parole, loghi o filigrane sopra. In cima al \
Reel c'e gia un banner di testo: una foto con dentro altre parole fa a botte \
con quello. Questo e il motivo di scarto piu importante.
- collage, griglie di piu foto, schermate, meme
- disegni, illustrazioni, rendering 3D, immagini fatte al computer: servono \
FOTOGRAFIE di cose e persone reali
- roba sgranata, sfocata, con bordi bianchi o colori slavati
- immagini troppo simili fra loro: tre foto quasi uguali valgono come una

TIENI:
- fotografie vere, pulite, con un soggetto riconoscibile a colpo d'occhio \
anche in un riquadro piccolo
- che abbiano a che fare con l'argomento del Reel
- che stiano bene insieme: colori e atmosfera coerenti fra le tre

Rispondi SOLO con un elenco JSON dei numeri scelti, in ordine di come le \
metteresti da sinistra a destra: ad esempio [3, 0, 7]. Se non ce ne sono \
abbastanza che meritano, dammene meno invece di riempire con gli scarti."""


def _miniatura(f: Path, lato: int = 320) -> tuple[str, str] | None:
    """Riduce l'immagine per mandarla al giudice: si decide sul colpo
    d'occhio, che e esattamente come la vedra chi scorre."""
    try:
        from PIL import Image
        with Image.open(f) as im:
            im = im.convert("RGB")
            im.thumbnail((lato, lato))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=82)
        return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    except Exception:                                   # noqa: BLE001
        return None


def scegli(candidate: list[Path], *, quante: int, tema: str,
           model: str) -> list[Path]:
    """Guarda le foto e tiene solo quelle che reggono.

    Serve perche la ricerca di Pinterest, da sola, restituisce di tutto: al
    primo giro di prova sono uscite una trama astratta in bianco e nero e un
    collage con su scritto "morning routine" — sopra un banner che e gia
    testo. Un filtro sui pixel non puo accorgersene: bisogna guardarle.

    Se il giudizio non arriva si tengono le prime, cosi la fascia esce
    comunque: e un ornamento, non deve mai bloccare la clip.
    """
    if len(candidate) <= quante:
        return candidate

    blocchi: list[dict] = []
    validi: list[Path] = []
    for p in candidate:
        mini = _miniatura(p)
        if mini is None:
            continue
        blocchi.append({"type": "text", "text": f"Immagine {len(validi)}:"})
        blocchi.append({"type": "image", "source": {
            "type": "base64", "media_type": mini[1], "data": mini[0]}})
        validi.append(p)
    if len(validi) <= quante:
        return validi[:quante]

    blocchi.append({"type": "text",
                    "text": GIUDICE.format(tema=tema, quante=quante)})
    risposta = None
    for tentativo in (1, 2, 3):
        try:
            # 600 sembravano tanti per una risposta tipo "[0, 4, 9]", e
            # infatti passavano la prova sul budget. Ma qui il modello deve
            # prima GUARDARE dodici immagini e ragionarci sopra, e quel
            # ragionamento sta dentro il budget: il 6/09 due giudizi e
            # l'11/09 altri tre sono tornati completamente vuoti. Non
            # "illeggibili": vuoti, stringa di zero caratteri. Il segno e
            # sempre lo stesso, stop_reason=max_tokens, e adesso si legge.
            risposta = _cliente().messages.create(
                model=model, max_tokens=3000,
                messages=[{"role": "user", "content": blocchi}],
            )
            conto.segna('giudizio foto', risposta.usage)
            break
        except Exception as e:                          # noqa: BLE001
            print(f"      ⚠️ Giudizio sulle foto, tentativo {tentativo}/3 ({e})")
            if tentativo < 3:
                time.sleep(tentativo * 4)
    if risposta is None:
        print("      ⚠️ Giudizio saltato: tengo le prime, controllare a mano")
        return validi[:quante]

    testo = "".join(b.text for b in risposta.content if b.type == "text")

    # Si legge la risposta in due modi, perche il 5/09 tre giudizi su cinque
    # sono finiti in "Giudizio illeggibile": la chiamata riusciva e il
    # modello rispondeva bene, ma senza parentesi quadre — "0, 4, 9" invece
    # di "[0, 4, 9]" — e il mio lettore cercava solo la forma con le
    # parentesi. Buttavo via una risposta giusta per una questione di
    # punteggiatura, e tenevo le prime foto a caso.
    scelti: list | None = None
    a, z = testo.find("["), testo.rfind("]")
    if a >= 0 and z > a:
        try:
            scelti = json.loads(testo[a:z + 1])
        except json.JSONDecodeError:
            scelti = None
    if scelti is None:
        # Ripiego: i numeri nudi, nell'ordine in cui compaiono.
        numeri = re.findall(r"\d+", testo)
        if numeri:
            scelti = [int(n) for n in numeri[:quante]]
    if not scelti:
        print(f"      ⚠️ Giudizio illeggibile ({testo[:60]!r}, "
              f"stop_reason={risposta.stop_reason}): tengo le prime")
        return validi[:quante]

    fuori = [validi[i] for i in scelti
             if isinstance(i, int) and 0 <= i < len(validi)][:quante]
    print(f"      🖼️ Foto: {len(validi)} candidate → {len(fuori)} tenute")
    return fuori


def per_clip(query_list: list[str], *, quante: int, dove: Path, tema: str,
             model: str, stile: str = "", per_ricerca: int = 4) -> list[Path]:
    """La fascia di una clip: si pesca largo, poi si guarda e si sceglie.

    Claude propone due o tre chiavi di ricerca a partire da cio che la clip
    dice. Da ognuna si scaricano quattro foto — non una — perche la prima
    che Pinterest restituisce non e affatto la migliore, e la selezione la
    fa poi il giudice a vista.
    """
    candidate: list[Path] = []
    for i, q in enumerate(query_list[:4]):
        candidate += cerca(q, quante=per_ricerca, dove=dove / f"q{i}",
                           stile=stile)
    if not candidate:
        return []
    return scegli(candidate, quante=quante, tema=tema, model=model)

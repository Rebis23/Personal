"""La libreria musicale: una base sonora per ogni carattere di clip.

Il montaggio sa gia mettere una base sotto la voce, e il cervello sa gia dire
che carattere ha la clip — 'tensione', 'riflessivo', 'spinta', 'racconto'.
Mancava solo la musica: c'erano tre basi generiche senza carattere, quindi la
scelta cadeva sempre sul ripiego e il carattere non serviva a niente.

Da dove viene. Instagram non lascia agganciare via API un brano della sua
libreria — quella strada e chiusa e non si apre — quindi la musica va messa
DENTRO il file mentre lo si monta, e allora deve essere musica che si puo
usare. Il catalogo di Kevin MacLeod (incompetech.com) e millequattrocento
brani con carattere, bpm e strumenti dichiarati, leggibile da un programma
senza chiavi ne account. Licenza CC BY 4.0: si usa per qualsiasi scopo,
compreso commerciale, a patto di citare l'autore. La citazione la mette da
sola `credito()` in fondo alla didascalia.

Perche non "la musica in trend di Instagram": quella e sotto licenza e non e
scaricabile in nessun modo legittimo. Questo catalogo non da il brano del
momento, da il SUONO giusto sotto la voce — che e cio che serve davvero,
perche in un Reel parlato la musica non e il contenuto, e il pavimento.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

CATALOGO = "https://incompetech.com/music/royalty-free/pieces.json"
SCARICO = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"
AUDIO = Path(__file__).resolve().parent.parent / "assets" / "audio"

CREDITO = ("🎵 Kevin MacLeod – incompetech.com · CC BY 4.0")

# Quanto dura la base salvata. Le clip stanno sotto il minuto e il montaggio
# taglia da solo; ottanta secondi coprono tutto senza portarsi dietro cinque
# minuti di mp3 dentro il repository.
DURATA = 80

# Strumenti che in un Reel parlato di crescita personale suonano sbagliati:
# fanno "documentario", "fantasy" o "comico" invece di stare sotto una voce.
VIETATI = ("tuba", "harp", "celesta", "marimba", "steel drum", "banjo",
           "accordion", "choir", "french horn", "flute", "bassoon", "trumpet",
           "sax", "harpsichord", "organ", "recorder", "lute", "ukulele",
           "whistle", "fiddle", "log drum", "shaker", "oboe", "clarinet",
           "mandolin", "sitar", "bagpipe", "kazoo", "vibraphone", "xylophone",
           "santur")
MODERNI = ("synth", "drum", "bass", "percussion", "piano", "guitar", "cello",
           "string", "kit", "ep")
CARATTERI_NO = {"Humorous", "Epic", "Mystical", "Eerie", "Unnerving",
                "Ren Faire", "Medieval", "Suspenseful", "Mysterious"}

# Per ogni carattere: quali "feel" deve avere, in che giro di bpm, e il bpm
# ideale attorno a cui ordinare. I nomi dei caratteri sono gli stessi che
# sceglie brain.py, altrimenti la corrispondenza non scatta.
RICETTE = {
    "tensione":   ({"Dark"}, {"Driving", "Intense", "Action"}, (90, 135), 110),
    "riflessivo": ({"Calming", "Relaxed", "Somber", "Calm"}, set(), (55, 95), 75),
    "spinta":     ({"Driving", "Uplifting"}, {"Bright", "Grooving"}, (105, 150), 125),
    "racconto":   ({"Grooving"}, {"Bright", "Bouncy", "Relaxed"}, (80, 120), 100),
}


def credito(mood: str = "") -> str:
    """La riga da mettere in fondo alla didascalia quando c'e una base.

    Non e cortesia: la licenza CC BY la richiede, e usare musica altrui senza
    citarla sarebbe esattamente il tipo di scorciatoia che questo brand dice
    di non prendere."""
    return CREDITO


def _bpm(p: dict) -> int:
    b = (p.get("bpm") or "").strip()
    return int(b) if b.isdigit() else 0


def _feel(p: dict) -> set[str]:
    return {f.strip() for f in (p.get("feel") or "").split(",") if f.strip()}


def _secondi(p: dict) -> int:
    try:
        pezzi = [int(x) for x in (p.get("length") or "").split(":")]
    except ValueError:
        return 0
    while len(pezzi) < 3:
        pezzi.insert(0, 0)
    return pezzi[0] * 3600 + pezzi[1] * 60 + pezzi[2]


def _adatto(p: dict) -> bool:
    strumenti = (p.get("instruments") or "").lower()
    return (not any(v in strumenti for v in VIETATI)
            and any(m in strumenti for m in MODERNI)
            and not CARATTERI_NO & _feel(p)
            and _secondi(p) >= 90
            and "waltz" not in (p.get("title") or "").lower())


def scegli(catalogo: list[dict], *, per_carattere: int = 3) -> dict[str, list[dict]]:
    """I brani migliori per ogni carattere, ordinati per vicinanza al bpm ideale."""
    fuori: dict[str, list[dict]] = {}
    for mood, (obbligatori, secondari, (lo, hi), ideale) in RICETTE.items():
        buoni = [p for p in catalogo if _adatto(p)
                 and obbligatori & _feel(p)
                 and (not secondari or secondari & _feel(p))
                 and lo <= _bpm(p) <= hi]
        buoni.sort(key=lambda p: abs(_bpm(p) - ideale))
        fuori[mood] = buoni[:per_carattere]
    return fuori


def _porta_a_casa(brano: dict, destinazione: Path) -> None:
    """Scarica, taglia a DURATA secondi, sfuma in coda e pareggia il volume.

    Il pareggio serve piu di quanto sembri: le tracce del catalogo hanno
    volumi molto diversi, e senza normalizzare una base coprirebbe la voce e
    quella dopo non si sentirebbe."""
    grezzo = destinazione.with_suffix(".grezzo.mp3")
    url = SCARICO + urllib.parse.quote(brano["filename"])
    with urllib.request.urlopen(url, timeout=120) as r, open(grezzo, "wb") as f:
        f.write(r.read())
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(grezzo),
         "-t", str(DURATA),
         "-af", f"afade=t=out:st={DURATA - 3}:d=3,loudnorm=I=-20:TP=-2",
         "-ac", "2", "-b:a", "128k", str(destinazione)],
        check=True, capture_output=True)
    grezzo.unlink(missing_ok=True)


def costruisci(*, per_carattere: int = 3) -> int:
    """Riempie assets/audio con una base per ogni carattere. Si lancia a mano
    quando serve rinfrescare la libreria; i file poi vivono nel repository,
    cosi ogni montaggio non riscarica niente."""
    with urllib.request.urlopen(CATALOGO, timeout=120) as r:
        catalogo = json.loads(r.read())
    print(f"📚 catalogo: {len(catalogo)} brani")

    AUDIO.mkdir(parents=True, exist_ok=True)
    fatti = 0
    for mood, brani in scegli(catalogo, per_carattere=per_carattere).items():
        if not brani:
            print(f"   ⚠️ nessun brano per '{mood}': la ricetta e troppo stretta")
            continue
        for n, brano in enumerate(brani, 1):
            dest = AUDIO / f"bed-{mood}-{n}.mp3"
            try:
                _porta_a_casa(brano, dest)
            except Exception as e:               # noqa: BLE001
                print(f"   ⚠️ {brano['title']}: {e}")
                continue
            fatti += 1
            print(f"   🎵 {mood:<11} {_bpm(brano):>3}bpm  {brano['title'][:34]:<34} "
                  f"→ {dest.name}")
    return fatti

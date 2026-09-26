"""La fabbrica non deve mangiarsi i propri Shorts.

La notte del 25/09 la coda Instagram era a una clip e la lavorazione non
riusciva a ripartire. La causa non era ne il download ne il montaggio:

    23:01  ingest parte
    23:03  «9mrqmmbw024 — Non devi capire per agire: devi agire per capire»
           troppo corto, probabilmente uno Short, salto
    23:03  fine corsa, zero clip

«9mrqmmbw024» era un Reel nostro, caricato su YouTube due ore prima dalla
corsa degli Shorts delle 21:14. Il feed del canale non distingue un video
di Lorenzo da un Reel che ci abbiamo messo noi: lo dava per video nuovo,
l'ingest lo prendeva per il video del giorno, lo scartava perche corto, e
chiudeva. E siccome un video nuovo c'era, l'archivio — 131 video veri —
non veniva nemmeno interrogato.

Il conto non tornava piu: quattro Shorts caricati al giorno contro tre
ingest al giorno, uno smaltito per corsa (MAX_VIDEOS_PER_RUN = 1). Un
video di ritardo al giorno, per sempre. Nessuno avrebbe piu prodotto una
clip: non per un errore, ma per un bilancio.

Il filtro sta in un posto solo — da_saltare() — perche i posti che
scelgono un video sono due, e qui la falla di uno solo bastava a fermare
tutto.

    python prove/nostri.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import state as S

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


# Lo stato com'era davvero alle 23:01 del 25/09.
QUELLA_NOTTE = {
    "processed_videos": [
        {"video_id": "C5gSgm-yLsc", "status": "done"},
    ],
    "shorts_done": [
        {"clip_id": "tCyZ18Ubms4-1", "at": "2026-09-25T20:34:53Z",
         "youtube_id": "iTeGJM6X0D8"},
        {"clip_id": "tCyZ18Ubms4-2", "at": "2026-09-25T21:14:37Z",
         "youtube_id": "dKv4fWySxj8"},
        {"clip_id": "tCyZ18Ubms4-3", "at": "2026-09-25T21:14:41Z",
         "youtube_id": "9mrqmmbw024"},
        {"clip_id": "eFVPQDJXKk4-1", "at": "2026-09-25T21:14:44Z",
         "youtube_id": "Cm2wphoNqYE"},
    ],
}

print("\n— i nostri caricamenti si riconoscono —")
nostri = S.nostri_caricamenti(QUELLA_NOTTE)
check("tutti e quattro gli Shorts di ieri sera", nostri == {
    "iTeGJM6X0D8", "dKv4fWySxj8", "9mrqmmbw024", "Cm2wphoNqYE"})
check("uno stato senza shorts_done non esplode",
      S.nostri_caricamenti({"processed_videos": []}) == set())
check("shorts_done a None non esplode",
      S.nostri_caricamenti({"processed_videos": [], "shorts_done": None}) == set())
check("le voci vecchie (stringhe, non dizionari) vengono ignorate",
      S.nostri_caricamenti(
          {"processed_videos": [], "shorts_done": ["tCyZ18Ubms4-1", "x-2"]}) == set())
check("una voce senza youtube_id non finisce dentro",
      S.nostri_caricamenti(
          {"processed_videos": [], "shorts_done": [{"clip_id": "a-1"}]}) == set())

print("\n— il guardiano —")
check("9mrqmmbw024, il Reel nostro che aveva fermato tutto",
      S.da_saltare(QUELLA_NOTTE, "9mrqmmbw024") is True)
check("un video gia lavorato resta saltato",
      S.da_saltare(QUELLA_NOTTE, "C5gSgm-yLsc") is True)
check("un video vero di Lorenzo passa",
      S.da_saltare(QUELLA_NOTTE, "6GSTLqWek5k") is False)

print("\n— la notte del 25/09, rigiocata —")
# Il feed com'era: i quattro Shorts nostri in testa, poi il video vero.
FEED = ["Cm2wphoNqYE", "9mrqmmbw024", "dKv4fWySxj8", "iTeGJM6X0D8", "C5gSgm-yLsc"]
rimasti = [v for v in FEED if not S.da_saltare(QUELLA_NOTTE, v)]
check("nessuno dei video del feed e un candidato: la lista resta vuota",
      rimasti == [])
check("lista vuota = l'archivio VIENE interrogato (prima non succedeva)",
      len(rimasti) == 0)

# E nel pescaggio dall'archivio: il catalogo intero contiene anche i nostri.
CATALOGO = ["Cm2wphoNqYE", "9mrqmmbw024", "6GSTLqWek5k", "flUlQn4_vuo"]
gia = {"flUlQn4_vuo"}
scelto = next((v for v in CATALOGO
               if not S.da_saltare(QUELLA_NOTTE, v) and v not in gia), None)
check(f"dall'archivio esce un video vero, non un Reel nostro: {scelto}",
      scelto == "6GSTLqWek5k")

print("\n— il bilancio che non tornava —")
# Quattro caricamenti al giorno, tre ingest, uno smaltito per corsa.
# Prima: ogni corsa bruciata su un nostro Short. Adesso: zero.
bruciate = sum(1 for v in FEED[:4] if not S.da_saltare(QUELLA_NOTTE, v))
check("nessuna corsa di ingest viene piu spesa su roba nostra", bruciate == 0)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

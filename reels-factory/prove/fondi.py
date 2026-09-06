"""La fusione dello stato non deve buttare via un rifacimento.

Gli id delle clip sono "<video>-<numero>", quindi rifare un video produce
id identici a quelli gia pubblicati. Il 6/09 in coda c'erano
NlnJgTd3tC8-1 e -2 rifatti da zero mentre i vecchi, con lo stesso id, erano
gia su Instagram. La regola di prima — "questo id e gia uscito, si salta" —
li avrebbe cancellati in silenzio, e proprio nel caso peggiore: dopo averli
rifatti apposta perche i primi erano sbagliati.

    python prove/fondi.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


def clip(cid, quando, hook="x"):
    return {"clip_id": cid, "hook": hook, "created_at": quando,
            "video_id": cid.rsplit("-", 1)[0]}


def fondi(origine: dict, nostro: dict) -> dict:
    """Lancia il comando vero, come lo lancia il workflow."""
    with tempfile.TemporaryDirectory() as tmp:
        stato = RADICE / "state" / "queue.json"
        salvato = stato.read_text(encoding="utf-8")
        try:
            stato.write_text(json.dumps(origine, ensure_ascii=False), encoding="utf-8")
            mio = Path(tmp) / "nostro.json"
            mio.write_text(json.dumps(nostro, ensure_ascii=False), encoding="utf-8")
            r = subprocess.run([sys.executable, "-m", "src.main", "fondi", str(mio)],
                               cwd=RADICE, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            return json.loads(stato.read_text(encoding="utf-8"))
        finally:
            stato.write_text(salvato, encoding="utf-8")


VUOTO = {"queue": [], "published": [], "processed_videos": [], "archive_done": []}

# 1. Il caso vero del 6/09: id gia pubblicato, ma la clip in coda e piu nuova.
origine = dict(VUOTO, published=[
    {"clip_id": "A-1", "published_at": "2026-09-04T16:38:31Z", "ig_media_id": "111"}])
nostro = dict(VUOTO, queue=[clip("A-1", "2026-09-06T01:30:00Z", "rifatta")])
fuso = fondi(origine, nostro)
prova("il rifacimento sopravvive alla fusione",
      [c["clip_id"] for c in fuso["queue"]] == ["A-1"],
      str(fuso["queue"]))
prova("ed e proprio quella nuova",
      fuso["queue"] and fuso["queue"][0]["hook"] == "rifatta")

# 2. Ma la clip GIA' pubblicata, quella vecchia, non deve rientrare in coda.
nostro_vecchio = dict(VUOTO, queue=[clip("A-1", "2026-09-03T10:00:00Z", "vecchia")])
prova("la clip gia uscita non torna in coda",
      fondi(origine, nostro_vecchio)["queue"] == [], )

# 3. Le pubblicazioni di origine comandano sempre.
prova("le pubblicazioni restano intatte",
      len(fondi(origine, nostro)["published"]) == 1)

# 4. Nessun doppione se e gia in coda su origine.
origine2 = dict(VUOTO, queue=[clip("B-1", "2026-09-06T01:00:00Z")])
fuso2 = fondi(origine2, dict(VUOTO, queue=[clip("B-1", "2026-09-06T01:00:00Z")]))
prova("una clip presente da entrambe le parti non si sdoppia",
      len(fuso2["queue"]) == 1, str(fuso2["queue"]))

print(f"\n{verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

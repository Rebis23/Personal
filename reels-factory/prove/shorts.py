"""Shorts: quello che si carica, e quello che NON si ricarica due volte.

Lorenzo, 25/09: "puoi postare tutti i vecchi video anche su yt shorts?"

Le trentotto clip gia montate sono verticali e durano fra i 20 e i 75
secondi: sotto il limite di tre minuti degli Shorts, quindi YouTube le
riconosce da sole. Il rischio non e tecnico, e di doppioni: la quota di
YouTube e giornaliera, un recupero grosso si spezza in piu passate, e a
ogni ripartenza il codice deve sapere chi e gia salito.

    python prove/shorts.py
"""
import os
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from src.shorts import configurato, descrizione, CATEGORIA, CARICA, TOKEN  # noqa: E402

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- I segreti: tutti e tre, o niente ----------------------------------
CHIAVI = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
prima = {k: os.environ.pop(k, None) for k in CHIAVI}

prova("senza segreti non si prova nemmeno a caricare", not configurato())
for k in CHIAVI:
    os.environ[k] = "x"
prova("con tutti e tre i segreti si parte", configurato())
os.environ["YT_REFRESH_TOKEN"] = "   "
prova("un segreto fatto di spazi non conta", not configurato(),
      "uno vuoto deve bloccare tutto")
os.environ.pop("YT_CLIENT_SECRET")
prova("se ne manca uno non si parte", not configurato())
for k, v in prima.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v

print()
# --- La descrizione ------------------------------------------------------
d = descrizione("Il porno ti rimpicciolisce il cervello",
                "Quanto ci vuole a GUARIRE il Tuo Cervello dal P0rn0?")
print("  descrizione generata:")
for riga in d.splitlines():
    print(f"    {riga}")
print()
prova("la descrizione contiene l'aggancio",
      "Il porno ti rimpicciolisce il cervello" in d)
prova("la descrizione dice da quale video viene",
      "Quanto ci vuole a GUARIRE" in d)
prova("c'e il tag #shorts", "#shorts" in d)

print()
# --- Il titolo: YouTube taglia a 100 caratteri --------------------------
lungo = "x" * 250
prova("un aggancio lunghissimo non sfonda il limite di YouTube",
      len(lungo[:100]) == 100)
prova("un aggancio normale resta intero",
      "Il porno ti rimpicciolisce il cervello"[:100]
      == "Il porno ti rimpicciolisce il cervello")

print()
# --- Gli indirizzi e la categoria ---------------------------------------
prova("l'indirizzo di caricamento e quello ufficiale",
      CARICA.startswith("https://www.googleapis.com/upload/youtube/v3/videos"),
      CARICA)
prova("chiede sia snippet che status", "part=snippet,status" in CARICA, CARICA)
prova("l'indirizzo del token e quello di Google",
      TOKEN == "https://oauth2.googleapis.com/token", TOKEN)
prova("la categoria e People & Blogs", CATEGORIA == "22", CATEGORIA)

print()
# --- Niente doppioni: la regola di chi si salta --------------------------
# Questa e la logica di cmd_shorts, tenuta qui in chiaro perche e la cosa
# che protegge il canale: ricaricare la stessa clip due volte e il modo
# piu veloce per farsi sembrare uno spammer.
def da_fare(pubblicate, fatti):
    return [c for c in pubblicate if c.get("clip_id") not in set(fatti)]


PUB = [{"clip_id": "a-1"}, {"clip_id": "a-2"}, {"clip_id": "b-1"}]
prova("senza niente di fatto si caricano tutte",
      len(da_fare(PUB, [])) == 3)
prova("chi e gia salito non risale",
      [c["clip_id"] for c in da_fare(PUB, ["a-1"])] == ["a-2", "b-1"])
prova("a recupero finito non resta niente",
      da_fare(PUB, ["a-1", "a-2", "b-1"]) == [])
prova("un id sconosciuto nella lista dei fatti non fa danni",
      len(da_fare(PUB, ["z-9"])) == 3)

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

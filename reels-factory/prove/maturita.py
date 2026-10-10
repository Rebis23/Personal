"""La scheda dei risultati non deve bocciare un Reel per la sua eta.

prestazioni.py nasce con questa riga in cima:

    # Sotto questa soglia i numeri non si sono ancora assestati: un Reel di
    # due ore fa non e "andato male", e solo giovane.
    ORE_MINIME = 24

e per tre settimane nessuno l'ha letta: raccogli() prendeva tutti i Reel
pubblicati, giovani compresi. Il conto di cosa succedeva:

    09/10 11:55  esce «Il tuo stipendio decide che auto guidi»
    09/10 14:19  parte una lavorazione, la scheda si aggiorna
                 → quel Reel ha 2 ore e 24 minuti, fa 180 views
                 → ultima riga della tabella, sotto tutti
    prompt:      «Studia cosa distingue i primi dagli ultimi PRIMA di
                  scegliere» — e gli ultimi erano i piu giovani

La scheda scritta per insegnare a Claude quali hook funzionano stava
insegnando il contrario, e il giorno dopo si correggeva da sola: il Reel
risaliva, e dell'errore non restava traccia da nessuna parte. Nessun
guasto, nessuna mail, nessuna riga rossa — solo scelte peggiori.

Un commento che spiega una soglia la fa sembrare attiva anche quando non
lo e, e vale meno di niente: chi legge il file pensa che il caso sia
coperto. ORE_MINIME ora si usa davvero, e qui si verifica che resti usata.

    python prove/maturita.py
"""
import inspect
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import prestazioni as P

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


# La scheda vera sta in state/prestazioni.md e la legge il prompt di
# selezione: una prova che la sovrascrive con dati finti sporcherebbe la
# produzione, quindi si scrive altrove.
TEMP = Path(tempfile.mkdtemp(prefix="prove-maturita-"))
P.SCHEDA = TEMP / "prestazioni.md"

# Numeri finti ma plausibili: il Reel chiede, la prova risponde senza rete.
NUMERI = {}
P._insights = lambda media_id: NUMERI.get(media_id, {"views": 700, "reach": 600,
                                                     "likes": 9, "saved": 2,
                                                     "shares": 1})

ADESSO = datetime(2026, 10, 9, 14, 19, tzinfo=timezone.utc)


def reel(ore_fa, *, hook, media_id=None, views=700):
    quando = ADESSO - timedelta(hours=ore_fa)
    mid = media_id or f"m{int(ore_fa)}"
    NUMERI[mid] = {"views": views, "reach": views - 50, "likes": 9,
                   "saved": 2, "shares": 1}
    return {"clip_id": hook[:6], "ig_media_id": mid, "hook": hook,
            "published_at": quando.strftime("%Y-%m-%dT%H:%M:%SZ")}


print("— leggere la data —")
check("la Z di Instagram si legge",
      P._eta_ore("2026-10-09T11:55:31Z", ADESSO) is not None)
check("due ore e mezza sono due ore e mezza",
      abs(P._eta_ore("2026-10-09T11:55:00Z", ADESSO) - 2.4) < 0.1)
check("una data senza fuso si legge come UTC, non va in errore",
      abs(P._eta_ore("2026-10-08T14:19:00", ADESSO) - 24.0) < 0.01)
check("una data illeggibile dice 'non lo so', non 'zero ore'",
      P._eta_ore("ieri sera", ADESSO) is None)
check("campo vuoto: 'non lo so'", P._eta_ore("", ADESSO) is None)

print("\n— il pomeriggio del 9 ottobre —")
# La situazione vera: due Reel al giorno, e la lavorazione gira nel mezzo.
PUBBLICATI = [
    reel(26 * 24, hook="Si può diventare più belli senza chirurgia?", views=3815),
    reel(10 * 24, hook="Perché paghi le tasse per la pensione?", views=803),
    reel(48, hook="Hai notato che tutto è in abbonamento?", views=185),
    reel(21.7, hook="Zero accesso ai soldi", views=240),
    reel(2.4, hook="Il tuo stipendio decide che auto guidi", views=180),
]
righe = P.raccogli(PUBBLICATI, adesso=ADESSO)
hooks = [r["hook"] for r in righe]

check("il Reel di stamattina non entra nella scheda",
      "Il tuo stipendio decide che auto guidi" not in hooks)
check("nemmeno quello di ieri pomeriggio, che ha 21 ore",
      "Zero accesso ai soldi" not in hooks)
check("quello di 48 ore resta, anche se ha fatto poche views",
      "Hai notato che tutto è in abbonamento?" in hooks)
check("i Reel maturi ci sono tutti", len(righe) == 3)
check("restano ordinati dal piu recente",
      hooks[0] == "Hai notato che tutto è in abbonamento?")

print("\n— senza il filtro, cosa imparava Claude —")
# Con ore_minime=0 si riproduce il comportamento di prima.
prima = P.raccogli(PUBBLICATI, adesso=ADESSO, ore_minime=0)
peggiore_prima = min(prima, key=lambda r: r["views"])["hook"]
peggiore_adesso = min(righe, key=lambda r: r["views"])["hook"]
check("prima il peggiore della tabella era il Reel di due ore fa",
      peggiore_prima == "Il tuo stipendio decide che auto guidi")
check("adesso il peggiore e un Reel che ha davvero avuto il suo tempo",
      peggiore_adesso == "Hai notato che tutto è in abbonamento?")

print("\n— la scheda non si assottiglia —")
# Lo scarto dei giovani deve avvenire prima del taglio a `limite`: se si
# tagliasse prima, ogni giorno due Reel giovani si porterebbero via due
# posti e la scheda avrebbe sempre meno righe mature di quelle chieste.
MOLTI = [reel(ore_fa=(30 - i) * 24, hook=f"maturo {i}", views=500 + i)
         for i in range(28)]
MOLTI += [reel(3, hook="appena uscito A", media_id="gA"),
          reel(1, hook="appena uscito B", media_id="gB")]
dieci = P.raccogli(MOLTI, limite=10, adesso=ADESSO)
check("chiesti 10 Reel, arrivano 10 Reel maturi (non 8)", len(dieci) == 10)
check("nessun Reel giovane tra quei 10",
      all(r["hook"].startswith("maturo") for r in dieci))

print("\n— un Reel senza data non si butta —")
SENZA = [{"ig_media_id": "x1", "hook": "data persa", "published_at": ""},
         reel(72, hook="normale")]
check("resta in tabella: 'non so quanti anni ha' non vuol dire 'e giovane'",
      "data persa" in [r["hook"] for r in P.raccogli(SENZA, adesso=ADESSO)])
check("e la sua eta si scrive '?', non '0 giorni'",
      "| ? |" in P.scrivi_scheda(P.raccogli(
          SENZA + [reel(100, hook="terzo")], adesso=ADESSO)))

print("\n— quello che legge il prompt —")
testo = P.scrivi_scheda(P.raccogli(MOLTI, limite=10, adesso=ADESSO))
check("la scheda dice da quanti giorni e online ogni Reel", "| gg |" in testo)
check("e avvisa che i Reel di oggi non ci sono",
      "ultime 24 ore" in testo)
check("i giovani non compaiono nemmeno nel testo",
      "appena uscito" not in testo)
check("la scheda vera non e stata toccata dalla prova",
      P.SCHEDA.parent == TEMP)

print("\n— la soglia deve restare collegata —")
# Il difetto di partenza non era una soglia sbagliata: era una soglia che
# nessuno leggeva. Se un domani raccogli() smette di usarla, questa prova
# cade subito invece di lasciare in piedi un commento che mente.
corpo = inspect.getsource(P.raccogli)
check("raccogli() usa la soglia", "ore_minime" in corpo)
check("e il suo valore di partenza e ORE_MINIME",
      inspect.signature(P.raccogli).parameters["ore_minime"].default == P.ORE_MINIME)
check("ORE_MINIME vale 24 ore", P.ORE_MINIME == 24)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

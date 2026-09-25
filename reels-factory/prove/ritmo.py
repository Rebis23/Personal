"""Due Reel al giorno su Instagram, quattro su Shorts. Ma non attaccati.

Lorenzo, 25/09: "da domani voglio due reel al giorno su Instagram" e
"quattro al giorno su YouTube derivanti dai 38 che abbiamo in archivio
finché non sei in pari".

Il rischio non e sbagliare il numero: e il modo in cui GitHub consegna le
esecuzioni programmate. Arrivano in ritardo anche di otto ore, e a volte
due arretrate insieme. Con la vecchia regola — "se ne e gia uscito uno
oggi, basta" — bastava cambiare il numero. Con due al giorno no: due turni
consegnati insieme farebbero uscire i due Reel a un minuto di distanza.

    python prove/ritmo.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
import yaml                                                    # noqa: E402

CFG = yaml.safe_load((RADICE / "config.yaml").read_text(encoding="utf-8"))
verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- Quello che chiede Lorenzo, letto dalla configurazione vera ---------
prova("Instagram: due Reel al giorno",
      CFG["instagram"]["al_giorno"] == 2, str(CFG["instagram"].get("al_giorno")))
prova("Shorts: quattro al giorno mentre si recupera",
      CFG["shorts"]["al_giorno"] == 4, str(CFG.get("shorts")))

print()
# --- La regola vera di cmd_publish, riprodotta qui ----------------------
def si_pubblica(usciti_oggi, ultima_iso, *, tetto, distanza, adesso):
    """True se e il momento di pubblicare. Ricalca cmd_publish."""
    if len(usciti_oggi) >= tetto:
        return False
    if usciti_oggi and distanza > 0:
        quando = datetime.fromisoformat(max(usciti_oggi).replace("Z", "+00:00"))
        if (adesso - quando).total_seconds() / 3600 < distanza:
            return False
    return True


ORA = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc)
TETTO = CFG["instagram"]["al_giorno"]
DIST = CFG["instagram"]["distanza_minima_ore"]


def iso(ore_fa):
    return (ORA - timedelta(hours=ore_fa)).strftime("%Y-%m-%dT%H:%M:%SZ")


prova("a giornata vuota si pubblica",
      si_pubblica([], None, tetto=TETTO, distanza=DIST, adesso=ORA))
prova("dopo il primo, a sei ore di distanza, esce il secondo",
      si_pubblica([iso(6)], None, tetto=TETTO, distanza=DIST, adesso=ORA))
prova("dopo il primo, a un minuto, NON esce il secondo",
      not si_pubblica([iso(0.02)], None, tetto=TETTO, distanza=DIST, adesso=ORA),
      "e il caso dei due turni arretrati consegnati insieme")
prova("dopo il primo, a due ore, non esce ancora",
      not si_pubblica([iso(2)], None, tetto=TETTO, distanza=DIST, adesso=ORA))
prova("dopo due Reel la giornata e chiusa",
      not si_pubblica([iso(8), iso(2)], None, tetto=TETTO, distanza=DIST, adesso=ORA))
prova("il terzo non esce nemmeno se e passato tanto tempo",
      not si_pubblica([iso(12), iso(6)], None, tetto=TETTO, distanza=DIST, adesso=ORA))

print()
# --- I due Reel devono starci dentro la finestra oraria -----------------
inizio, fine = CFG["instagram"]["ore_pubblicazione"]
ore_utili = fine - inizio
prova("nella finestra ci stanno due Reel distanziati",
      ore_utili >= DIST * (TETTO - 1),
      f"finestra {inizio}-{fine} = {ore_utili}h, servono {DIST*(TETTO-1)}h")

print()
# --- La scorta: l'archivio deve reggere il ritmo nuovo ------------------
arc = CFG["archive"]
prova("si ripesca dall'archivio prima di restare a secco",
      arc["queue_below"] >= TETTO,
      f"queue_below {arc['queue_below']} contro {TETTO} Reel al giorno")
prova("una lavorazione al giorno e permessa",
      arc["min_days_between"] <= 1, str(arc["min_days_between"]))
prova("il tetto sui video d'archivio non e piu il collo di bottiglia",
      arc["max_videos"] >= 30, str(arc["max_videos"]))

print()
# --- Shorts: il tetto giornaliero e il conteggio di chi e gia salito ----
def quante_oggi(voci, oggi, tetto):
    def _q(v):
        return "" if isinstance(v, str) else v.get("at", "")
    gia = sum(1 for v in voci if _q(v).startswith(oggi))
    return max(0, tetto - gia)


OGGI = "2026-09-26"
prova("a giornata vuota se ne caricano quattro",
      quante_oggi([], OGGI, 4) == 4)
prova("se ne sono gia saliti tre, ne resta uno",
      quante_oggi([{"clip_id": "a", "at": f"{OGGI}T06:00:00Z"}] * 3, OGGI, 4) == 1)
prova("a tetto raggiunto non ne sale piu nessuno",
      quante_oggi([{"clip_id": "a", "at": f"{OGGI}T06:00:00Z"}] * 4, OGGI, 4) == 0)
prova("quelli di ieri non contano per oggi",
      quante_oggi([{"clip_id": "a", "at": "2026-09-25T06:00:00Z"}] * 4, OGGI, 4) == 4)
prova("lo stato vecchio, con le stringhe nude, non fa saltare niente",
      quante_oggi(["vecchia-1", "vecchia-2"], OGGI, 4) == 4)

print()
# --- Quando si e "in pari" -----------------------------------------------
# Finita l'arretrato la regola non cambia: si carica quello che c'e. Con due
# Reel al giorno su Instagram, su Shorts ne salgono due. Converge da sola.
def da_caricare(pubblicate, fatti, tetto):
    resto = [c for c in pubblicate if c not in fatti]
    return min(len(resto), tetto)


ARRETRATO = [f"clip-{i}" for i in range(38)]
prova("con 38 arretrati se ne caricano 4 al giorno",
      da_caricare(ARRETRATO, set(), 4) == 4)
prova("in pari, se Instagram ne ha fatti 2, su Shorts ne salgono 2",
      da_caricare(ARRETRATO, set(ARRETRATO[:36]), 4) == 2,
      "il tetto e 4 ma le clip disponibili sono 2")
prova("in pari e senza novita non sale niente",
      da_caricare(ARRETRATO, set(ARRETRATO), 4) == 0)

giorni = -(-38 // 4)
print(f"\n  38 arretrati a 4 al giorno = {giorni} giorni per essere in pari")
prova("il recupero finisce in meno di due settimane", giorni <= 14, f"{giorni} giorni")

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

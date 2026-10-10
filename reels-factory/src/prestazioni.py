"""Come sono andati i Reel gia pubblicati.

Finora Claude sceglieva i momenti al buio: nessuno gli diceva mai quali clip
avevano poi fatto views e quali erano morte. Questo modulo interroga Instagram,
mette i numeri veri accanto agli hook e produce una scheda che il prompt di
selezione legge a ogni lavorazione. Cosi la scelta si allena sui risultati di
questo profilo, non su regole generiche prese da un manuale.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import instagram

SCHEDA = Path(__file__).resolve().parent.parent / "state" / "prestazioni.md"

# Sotto questa soglia i numeri non si sono ancora assestati: un Reel di due ore
# fa non e "andato male", e solo giovane.
#
# La soglia e stata scritta il giorno in cui e nato il modulo, con il commento
# qui sopra, e per tre settimane non l'ha letta nessuno: raccogli() prendeva
# tutto. Cosi ogni lavorazione del pomeriggio metteva in fondo alla scheda il
# Reel uscito quella mattina — poche centinaia di views perche aveva due ore —
# e il prompt lo presentava a Claude come un hook da non ripetere. La scheda
# nata per insegnare quali clip funzionano stava insegnando il contrario, e si
# correggeva da sola il giorno dopo senza che nessuno vedesse l'errore.
ORE_MINIME = 24

# Perche due soglie e non una: ORE_MINIME decide chi ENTRA nei numeri (24 ore,
# oltre le quali un Reel ha dei dati), GIORNI_VERDETTO decide su chi si
# PRONUNCIA un giudizio. Alla prima corsa del riscontro, con la sola soglia
# delle 24 ore, sotto "Sono morti" e finito un Reel di un giorno a 385 views:
# nessuno sa ancora se sia morto. Entrare in tabella e essere condannati non
# richiedono la stessa pazienza.
GIORNI_VERDETTO = 7


def _eta_ore(quando: str, adesso: datetime) -> float | None:
    """Ore passate dalla pubblicazione. None se la data non si legge.

    None non significa "giovane": significa "non lo so". Un Reel senza data
    resta nella scheda — escluderlo per un campo illeggibile butterebbe via
    un risultato vero.
    """
    try:
        t = datetime.fromisoformat((quando or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (adesso - t).total_seconds() / 3600.0


def _insights(media_id: str) -> dict:
    r = requests.get(
        f"{instagram.BASE}/{media_id}/insights",
        params={"metric": "views,reach,likes,saved,shares",
                "access_token": instagram._token()},
        timeout=60,
    )
    dati = r.json()
    if "error" in dati:
        return {}
    return {v["name"]: v["values"][0]["value"] for v in dati.get("data", [])}


def maturi(published: list[dict], *, limite: int = 25,
           adesso: datetime | None = None,
           ore_minime: float = ORE_MINIME) -> list[tuple[dict, float | None]]:
    """I Reel che si possono giudicare, dal piu recente, con la loro eta.

    Sta fuori da raccogli() perche serve anche per una domanda diversa:
    quanti Reel AVREBBERO dovuto rispondere. Senza quel numero, un Instagram
    muto e una lista vuota si assomigliano troppo — e il riassunto finirebbe
    per dire «troppo pochi Reel» quando il problema e il token.
    """
    adesso = adesso or datetime.now(timezone.utc)

    pronti = []
    for p in published:
        if not p.get("ig_media_id"):
            continue
        eta = _eta_ore(p.get("published_at", ""), adesso)
        if eta is not None and eta < ore_minime:
            continue
        pronti.append((p, eta))
    return list(reversed(pronti[-limite:]))


def raccogli(published: list[dict], *, limite: int = 25,
             adesso: datetime | None = None,
             ore_minime: float = ORE_MINIME) -> list[dict]:
    """Numeri veri per gli ultimi Reel pubblicati maturi, dal piu recente.

    I Reel delle ultime ORE_MINIME ore restano fuori: non sono dati, sono
    dati non ancora arrivati. Lo scarto avviene PRIMA del taglio a `limite`,
    altrimenti i giovani che vengono buttati si porterebbero dietro il posto
    di altrettanti Reel maturi e la scheda si assottiglierebbe ogni giorno.
    """
    righe = []
    for p, eta in maturi(published, limite=limite, adesso=adesso,
                         ore_minime=ore_minime):
        m = _insights(p["ig_media_id"])
        if not m:
            continue
        righe.append({
            "hook": p.get("hook", ""),
            "data": p.get("published_at", "")[:10],
            "video_id": p.get("video_id", ""),
            "giorni": None if eta is None else int(eta // 24),
            "views": m.get("views", 0),
            "salvataggi": m.get("saved", 0),
            "like": m.get("likes", 0),
            "condivisioni": m.get("shares", 0),
        })
    return righe


def scrivi_scheda(righe: list[dict]) -> str:
    """La scheda che finisce nel prompt. Ordinata per views: Claude deve vedere
    prima cosa ha funzionato e in fondo cosa e morto, con i numeri accanto."""
    if len(righe) < 3:
        testo = ("(non ci sono ancora abbastanza Reel pubblicati per dire "
                 "cosa funziona su questo profilo)")
        SCHEDA.write_text(testo, encoding="utf-8")
        return testo

    ordinate = sorted(righe, key=lambda r: r["views"], reverse=True)
    mediana = statistics.median(r["views"] for r in ordinate)

    parti = [
        "Risultati veri dei Reel gia usciti su questo profilo, dal piu visto al meno visto.",
        f"Mediana delle views: {mediana:.0f}. I salvataggi contano piu dei like: "
        "sono il segnale che il contenuto valeva la pena di essere ritrovato.",
        f"La colonna gg dice da quanti giorni il Reel e online: le views crescono "
        f"nel tempo, quindi un Reel di 2 giorni a 600 views non e andato peggio "
        f"di uno di 30 giorni a 700. I Reel usciti nelle ultime {ORE_MINIME} ore "
        f"non sono in tabella: sarebbero bassi solo perche giovani.",
        "",
        "| views | salv | like | gg | hook |",
        "|------:|-----:|-----:|---:|------|",
    ]
    for r in ordinate:
        gg = "?" if r.get("giorni") is None else r["giorni"]
        parti.append(f"| {r['views']} | {r['salvataggi']} | {r['like']} | {gg} | {r['hook']} |")

    meta = max(1, len(ordinate) // 3)
    migliori = ordinate[:meta]
    peggiori = ordinate[-meta:]
    parti += [
        "",
        f"I {len(migliori)} migliori hanno fatto in media {statistics.mean(r['views'] for r in migliori):.0f} views, "
        f"i {len(peggiori)} peggiori {statistics.mean(r['views'] for r in peggiori):.0f}.",
        "Studia cosa distingue i primi dagli ultimi PRIMA di scegliere: "
        "quella differenza vale piu di qualunque regola generale.",
    ]
    testo = "\n".join(parti)
    SCHEDA.write_text(testo, encoding="utf-8")
    return testo


def leggi_scheda() -> str:
    """Usata dal prompt di selezione. Se la scheda non c'e, si tira avanti."""
    try:
        return SCHEDA.read_text(encoding="utf-8").strip()
    except OSError:
        return "(nessuno storico disponibile: giudica con i criteri generali)"


def _per_mille(r: dict) -> float:
    """Salvataggi per mille views. Le views dicono quanti hanno guardato, i
    salvataggi quanti hanno voluto ritrovarlo: un Reel da 500 views con 10
    salvataggi ha detto qualcosa di piu utile di uno da 3000 con 5."""
    return (r["salvataggi"] * 1000 / r["views"]) if r["views"] else 0.0


def riassunto(righe: list[dict], *, titoli: dict[str, str] | None = None) -> str:
    """Il riscontro per Lorenzo, non per il prompt.

    scrivi_scheda() produce la tabella che Claude legge prima di scegliere.
    Questo invece e il foglio che legge una persona una volta a settimana:
    cosa ha girato, cosa e morto, e soprattutto QUALE VIDEO LUNGO rende i
    Reel migliori — l'unica di queste informazioni su cui lui puo agire
    quando decide cosa girare la settimana dopo.
    """
    if len(righe) < 3:
        return (f"Solo {len(righe)} Reel maturi: troppo pochi per dire "
                f"cosa funziona. Riprovo la settimana prossima.")

    titoli = titoli or {}
    ordinate = sorted(righe, key=lambda r: r["views"], reverse=True)
    mediana = statistics.median(r["views"] for r in righe)

    parti = [f"📊 Riscontro Reel — {len(righe)} usciti e maturi "
             f"(esclusi quelli delle ultime {ORE_MINIME} ore)",
             "",
             f"Mediana: {mediana:.0f} views."]

    # La settimana contro quella prima: una mediana da sola non dice se il
    # profilo sta crescendo o si sta spegnendo.
    datati = [r for r in righe if r["giorni"] is not None]
    ultima = [r["views"] for r in datati if r["giorni"] < 7]
    prima = [r["views"] for r in datati if 7 <= r["giorni"] < 14]
    if len(ultima) >= 2 and len(prima) >= 2:
        a, b = statistics.median(ultima), statistics.median(prima)
        verso = "in salita" if a > b else ("in discesa" if a < b else "fermi")
        parti.append(f"Ultimi 7 giorni: mediana {a:.0f} su {len(ultima)} Reel. "
                     f"I 7 giorni prima: {b:.0f} su {len(prima)}. Siamo {verso}.")

    def riga(r):
        gg = "?" if r["giorni"] is None else f"{r['giorni']}gg"
        return (f"  {r['views']:>5} views · {r['salvataggi']:>2} salv · "
                f"{gg:>4}  {r['hook']}")

    # 24 ore bastano per mettere un Reel in tabella accanto alla sua eta, non
    # per dire "questo e morto". Alla prima corsa vera il verdetto suonava
    # cosi: «Sono morti: 385 views, 1gg» — un Reel di un giorno. Le due
    # classifiche con un giudizio dentro guardano solo i Reel che hanno avuto
    # il loro tempo; la tabella del prompt, che mostra i giorni, no.
    giudicabili = [r for r in righe
                   if r["giorni"] is None or r["giorni"] >= GIORNI_VERDETTO]
    if len(giudicabili) >= 3:
        classifica = sorted(giudicabili, key=lambda r: r["views"], reverse=True)
        nota = f" (almeno {GIORNI_VERDETTO} giorni online)"
    else:
        classifica = ordinate
        nota = " (nessuno ha ancora una settimana: numeri ancora in corsa)"
    # Tre e tre solo se ce n'e abbastanza: con cinque Reel giudicabili, due
    # liste da tre si sovrapporrebbero e lo stesso Reel comparirebbe fra
    # quelli che hanno girato E fra i morti.
    quanti = max(1, min(3, len(classifica) // 2))
    parti += ["", f"Hanno girato{nota}:"] + [riga(r) for r in classifica[:quanti]]
    parti += ["", "Sono morti:"] + [riga(r) for r in classifica[-quanti:]]

    # I salvataggi per mille views crescono insieme alle views, quindi questa
    # classifica regge anche sui Reel giovani: ci stanno tutti.
    salvati = sorted(righe, key=_per_mille, reverse=True)[:3]
    parti += ["", "Piu salvati (per mille views): contano piu delle views:"]
    parti += [f"  {_per_mille(r):>4.1f} ‰  {r['hook']}" for r in salvati]

    # Il raggruppamento che su Instagram non si vede: quale video lungo ha
    # prodotto i Reel migliori. E la domanda che decide cosa girare.
    # Anche qui solo i Reel giudicabili: l'ultimo video girato avrebbe tutte
    # le clip giovani e sembrerebbe il peggiore ogni volta.
    per_video: dict[str, list[int]] = {}
    for r in giudicabili:
        if r.get("video_id"):
            per_video.setdefault(r["video_id"], []).append(r["views"])
    grossi = {v: n for v, n in per_video.items() if len(n) >= 2}
    if len(grossi) >= 2:
        parti += ["", "Per video di partenza (quale girare di piu):"]
        for v, views in sorted(grossi.items(),
                               key=lambda kv: statistics.median(kv[1]),
                               reverse=True):
            nome = titoli.get(v) or v
            parti.append(f"  mediana {statistics.median(views):>5.0f} · "
                         f"{len(views)} Reel · {nome[:60]}")

    return "\n".join(parti)

"""Come sono andati i Reel gia pubblicati.

Finora Claude sceglieva i momenti al buio: nessuno gli diceva mai quali clip
avevano poi fatto views e quali erano morte. Questo modulo interroga Instagram,
mette i numeri veri accanto agli hook e produce una scheda che il prompt di
selezione legge a ogni lavorazione. Cosi la scelta si allena sui risultati di
questo profilo, non su regole generiche prese da un manuale.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import requests

from . import instagram

SCHEDA = Path(__file__).resolve().parent.parent / "state" / "prestazioni.md"

# Sotto questa soglia i numeri non si sono ancora assestati: un Reel di due ore
# fa non e "andato male", e solo giovane.
ORE_MINIME = 24


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


def raccogli(published: list[dict], *, limite: int = 25) -> list[dict]:
    """Numeri veri per gli ultimi Reel pubblicati, dal piu recente."""
    righe = []
    for p in reversed(published[-limite:]):
        if not p.get("ig_media_id"):
            continue
        m = _insights(p["ig_media_id"])
        if not m:
            continue
        righe.append({
            "hook": p.get("hook", ""),
            "data": p.get("published_at", "")[:10],
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
        "",
        "| views | salv | like | hook |",
        "|------:|-----:|-----:|------|",
    ]
    for r in ordinate:
        parti.append(f"| {r['views']} | {r['salvataggi']} | {r['like']} | {r['hook']} |")

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

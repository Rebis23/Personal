"""Cosa sfonda su Instagram in questa nicchia, e con quali suoni.

Non guarda i Reel di Lorenzo: pesca dagli hashtag della nicchia i Reel che
hanno fatto numeri veri, ne estrae gli SCHEMI ricorrenti con Claude e scrive
due schede che il prompt di selezione legge a ogni lavorazione:

  nicchia.md  — aperture, struttura, chiusure, ritmo, anti-schemi
  suoni.md    — le tracce audio che ricorrono sotto i Reel che vanno forte

Gira su GitHub, dove il token Apify vive gia come segreto: non serve passarlo
a mano da nessuna parte. Costa una manciata di centesimi a esecuzione, quindi
si lancia una volta a settimana, non a ogni video.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

from . import apify

RADICE = Path(__file__).resolve().parent.parent
SCHEDA_NICCHIA = RADICE / "nicchia.md"
SCHEDA_SUONI = RADICE / "suoni.md"

ACTOR = "apify~instagram-hashtag-scraper"

# I nomi dei campi cambiano da actor a actor e da una versione all'altra.
# Invece di fidarsi di una chiave fissa si prova una lista di alias: se
# domani l'actor rinomina "videoViewCount" in "playCount", continua a funzionare.
ALIAS = {
    "views": ("videoViewCount", "videoPlayCount", "playCount", "viewCount", "views"),
    "like": ("likesCount", "likeCount", "likes"),
    "commenti": ("commentsCount", "commentCount", "comments"),
    "caption": ("caption", "text", "description"),
    "url": ("url", "permalink", "postUrl"),
    "tipo": ("productType", "type", "mediaType"),
    "durata": ("videoDuration", "duration"),
    "autore": ("ownerUsername", "username", "owner"),
    "suono": ("musicInfo", "audio", "musicName", "songName"),
}


def _campo(item: dict, nome: str):
    for chiave in ALIAS[nome]:
        if item.get(chiave) not in (None, "", 0):
            return item[chiave]
    return None


def _e_reel(item: dict) -> bool:
    tipo = str(_campo(item, "tipo") or "").lower()
    return "clip" in tipo or "reel" in tipo or "video" in tipo


def raccogli(hashtag: list[str], *, per_hashtag: int = 40, minimo_views: int = 20000) -> list[dict]:
    """I Reel della nicchia che hanno superato la soglia, dal piu visto."""
    grezzi = apify._run_actor(ACTOR, {
        "hashtags": hashtag,
        "resultsLimit": per_hashtag,
    }, timeout_minutes=15)["items"]

    if grezzi:
        # La prima esecuzione dice che forma hanno davvero i dati: se domani
        # qualcosa non torna, il registro ha gia le chiavi sotto gli occhi.
        print(f"   🔍 {len(grezzi)} post grezzi. Chiavi del primo: "
              f"{sorted(grezzi[0].keys())[:18]}")

    reel = []
    for item in grezzi:
        if not _e_reel(item):
            continue
        views = _campo(item, "views") or 0
        if views < minimo_views:
            continue
        reel.append({
            "views": views,
            "like": _campo(item, "like") or 0,
            "commenti": _campo(item, "commenti") or 0,
            "durata": _campo(item, "durata"),
            "autore": _campo(item, "autore"),
            "url": _campo(item, "url"),
            "suono": _campo(item, "suono"),
            "caption": (str(_campo(item, "caption") or ""))[:600],
        })
    reel.sort(key=lambda r: r["views"], reverse=True)
    return reel


ISTRUZIONI = """Sei un analista di contenuti brevi. Qui sotto trovi Reel italiani \
di crescita personale, psicologia applicata e mentalita che hanno fatto numeri \
molto sopra la media, con views, durata e caption.

Il tuo compito NON e riassumerli. E estrarre gli SCHEMI che si ripetono, cioe le \
regole di costruzione che uno potrebbe applicare a un contenuto diverso. \
"Apre negando una cosa che il pubblico da per certa" e uno schema. \
"Il reel di Tizio sul sonno" non lo e.

Scrivi in italiano un documento markdown con esattamente queste sezioni:

## 1. Schemi di apertura (primi 3 secondi)
## 2. Struttura del corpo
## 3. Chiusure
## 4. Ritmo e durata
## 5. Cosa NON fanno mai

Regole:
- Ogni schema deve essere ACCIONABILE: chi lo legge deve poter dire "questo \
momento del video lo rispetta / non lo rispetta".
- Dove puoi, quantifica (durata mediana, quante idee per reel, a che secondo \
cade il colpo).
- Metti solo schemi che vedi ripetuti in ALMENO TRE reel diversi. Se una cosa \
la fa uno solo, non e uno schema: e un caso.
- Niente preamboli, niente conclusioni: solo il documento."""


def distilla(reel: list[dict], *, model: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    dati = json.dumps([
        {k: r[k] for k in ("views", "like", "durata", "caption")} for r in reel[:40]
    ], ensure_ascii=False, indent=1)
    r = client.messages.create(
        model=model, max_tokens=8000,
        system=ISTRUZIONI,
        messages=[{"role": "user", "content": f"Ecco i Reel:\n\n{dati}"}],
    )
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()


def scrivi_suoni(reel: list[dict]) -> str:
    """Le tracce che ricorrono sotto i Reel forti. Non si possono agganciare
    via API, ma dicono il genere e il ritmo da cercare tra le musiche libere."""
    conta: dict[str, list[int]] = {}
    for r in reel:
        s = r.get("suono")
        nome = (s.get("song_name") or s.get("artist_name") or "") if isinstance(s, dict) else str(s or "")
        nome = nome.strip()
        if nome:
            conta.setdefault(nome, []).append(r["views"])
    righe = ["# Suoni ricorrenti sotto i Reel forti della nicchia", "",
             "Non si possono agganciare via API (solo l'app del telefono lo permette).",
             "Servono a capire GENERE e RITMO da cercare tra le musiche libere.", "",
             "| usi | views medie | traccia |", "|----:|------------:|---------|"]
    for nome, v in sorted(conta.items(), key=lambda kv: (-len(kv[1]), -max(kv[1])))[:25]:
        righe.append(f"| {len(v)} | {sum(v)//len(v)} | {nome[:70]} |")
    if len(righe) == 6:
        righe.append("| — | — | (l'actor non ha restituito le tracce audio) |")
    testo = "\n".join(righe)
    SCHEDA_SUONI.write_text(testo, encoding="utf-8")
    return testo

"""La scuola: cosa rende forte un video breve, imparato dai video brevi forti.

Non guarda i Reel di Lorenzo e non chiede niente a nessuno. Interroga la
YouTube Data API — chiave gia nei segreti — cerca gli Shorts italiani della
nicchia, calcola per ognuno quanto ha SUPERATO la media del suo canale, e
manda i vincitori a Claude perche ne estragga gli schemi ricorrenti.

Perche gli Shorts e non i Reel: sono lo stesso formato, verticale e sotto il
minuto, con lo stesso pubblico e le stesse regole di aggancio. Gli schemi si
trasferiscono. E soprattutto: gli Shorts sono raggiungibili con una API
ufficiale, gratuita e senza scraping, mentre i Reel no.

Il punteggio di outlier e il cuore: un video con 300.000 views su un canale
che ne fa 5.000 di media insegna qualcosa (ha funzionato la COSTRUZIONE), un
video con 300.000 views su un canale da un milione no (ha funzionato il
canale). Senza questo rapporto si finisce a studiare i grossi e a imparare
niente.
"""

from __future__ import annotations

import os
import statistics
from pathlib import Path

import requests

BASE = "https://www.googleapis.com/youtube/v3"
SCHEDA = Path(__file__).resolve().parent.parent / "nicchia.md"


class ScuolaError(RuntimeError):
    pass


def _chiave() -> str:
    k = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not k:
        raise ScuolaError(
            "Secret YOUTUBE_API_KEY mancante. E l'unica cosa che il sistema "
            "non puo procurarsi da solo, perche va creata dentro un account "
            "Google. Si fa in tre minuti ed e gratis:\n"
            "  1. console.cloud.google.com -> nuovo progetto (nome qualsiasi)\n"
            "  2. API e servizi -> Libreria -> 'YouTube Data API v3' -> Abilita\n"
            "  3. API e servizi -> Credenziali -> Crea credenziali -> Chiave API\n"
            "  4. github.com/Rebis23/Personal -> Settings -> Secrets and "
            "variables -> Actions -> New repository secret\n"
            "     nome: YOUTUBE_API_KEY   valore: la chiave\n"
            "Nessuna carta di credito: la quota gratuita e 10.000 unita al "
            "giorno e questa ricerca ne usa 500 a settimana.")
    return k


def _get(risorsa: str, **params) -> dict:
    params["key"] = _chiave()
    r = requests.get(f"{BASE}/{risorsa}", params=params, timeout=60)
    if r.status_code == 403:
        raise ScuolaError(
            "YouTube Data API ha risposto 403: quasi sempre e la quota "
            "esaurita. Le ricerche hanno un tetto a parte di 100 al giorno; "
            "tutto il resto pesca da 10.000 unita giornaliere. "
            f"Dettaglio: {r.text[:200]}")
    r.raise_for_status()
    return r.json()


def cerca_shorts(query: str, *, quanti: int = 25, giorni: int = 90) -> list[str]:
    """Gli id degli Shorts italiani piu pertinenti per una domanda."""
    from datetime import datetime, timedelta, timezone
    dopo = (datetime.now(timezone.utc) - timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = _get("search", part="id", q=query, type="video",
             videoDuration="short",          # sotto i 4 minuti: include gli Shorts
             relevanceLanguage="it", regionCode="IT",
             order="viewCount",              # i piu visti, non i piu recenti
             publishedAfter=dopo, maxResults=min(quanti, 50))
    return [i["id"]["videoId"] for i in d.get("items", []) if i["id"].get("videoId")]


def _durata_secondi(iso: str) -> int:
    """PT1M23S -> 83. Serve a tenere solo il formato corto vero."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def dettagli(video_ids: list[str]) -> list[dict]:
    """Titolo, descrizione, views, durata e canale. Una sola unita di quota
    ogni 50 video: e la chiamata piu economica dell'API."""
    fuori = []
    for i in range(0, len(video_ids), 50):
        blocco = video_ids[i:i + 50]
        d = _get("videos", part="snippet,statistics,contentDetails",
                 id=",".join(blocco), maxResults=50)
        for v in d.get("items", []):
            durata = _durata_secondi(v["contentDetails"].get("duration"))
            if not (5 <= durata <= 180):     # fuori da qui non e formato breve
                continue
            fuori.append({
                "id": v["id"],
                "titolo": v["snippet"]["title"],
                "descrizione": (v["snippet"].get("description") or "")[:400],
                "canale_id": v["snippet"]["channelId"],
                "canale": v["snippet"]["channelTitle"],
                "durata": durata,
                "views": int(v["statistics"].get("viewCount", 0)),
                "like": int(v["statistics"].get("likeCount", 0)),
                "commenti": int(v["statistics"].get("commentCount", 0)),
            })
    return fuori


def _mediana_canale(canale_ids: list[str], *, ultimi: int = 40) -> dict[str, float]:
    """Il metro su cui misurare lo scarto: la MEDIANA delle views degli ultimi
    video di ogni canale.

    Non la media di sempre: quella e falsata da due cose. Il video che e
    esploso una volta la gonfia, e i video di dieci anni fa non dicono niente
    su come va oggi il canale. La mediana degli ultimi quaranta e il "normale"
    vero di quel creator adesso.

    Costa poco: una unita per prendere la playlist dei caricamenti, una ogni
    cinquanta video per sfogliarla, una ogni cinquanta per le statistiche."""
    mediane = {}
    for cid in dict.fromkeys(canale_ids):
        try:
            c = _get("channels", part="contentDetails", id=cid)
            items = c.get("items", [])
            if not items:
                continue
            playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
            pl = _get("playlistItems", part="contentDetails",
                      playlistId=playlist, maxResults=min(ultimi, 50))
            ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
            if len(ids) < 5:
                continue
            v = _get("videos", part="statistics", id=",".join(ids[:50]), maxResults=50)
            views = [int(x["statistics"].get("viewCount", 0)) for x in v.get("items", [])]
            views = [x for x in views if x > 0]
            if len(views) >= 5:
                mediane[cid] = statistics.median(views)
        except Exception:                       # noqa: BLE001
            continue                            # un canale che non risponde non ferma il resto
    return mediane


def outlier(query_list: list[str], *, per_query: int = 25,
            scarto_minimo: float = 3.0) -> list[dict]:
    """I video brevi che hanno battuto la media del proprio canale di almeno
    N volte. Sono quelli da cui si impara qualcosa."""
    ids: list[str] = []
    for q in query_list:
        trovati = cerca_shorts(q, quanti=per_query)
        print(f"   🔎 «{q}»: {len(trovati)} video")
        ids += trovati
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []

    video = dettagli(ids)
    print(f"   🎬 {len(video)} sono davvero formato breve (5-180s)")
    medie = _mediana_canale([v["canale_id"] for v in video])

    for v in video:
        normale = medie.get(v["canale_id"], 0)
        v["scarto"] = round(v["views"] / normale, 1) if normale > 0 else 0.0

    forti = [v for v in video if v["scarto"] >= scarto_minimo]
    forti.sort(key=lambda v: v["scarto"], reverse=True)
    print(f"   ⭐ {len(forti)} hanno superato di {scarto_minimo}x la media del loro canale")
    return forti


ISTRUZIONI = """Sei un analista di contenuti brevi verticali. Qui sotto trovi \
video brevi italiani di crescita personale, psicologia e mentalita che hanno \
fatto molte piu views della MEDIA DEL LORO STESSO CANALE. Il campo "scarto" \
dice quante volte hanno superato quella media: uno scarto di 20 significa che \
quel video ha fatto venti volte il normale per chi l'ha pubblicato.

E il dato che conta: isola la COSTRUZIONE dalla dimensione del canale. Un \
video con 500.000 views su un canale enorme non insegna niente; uno con \
80.000 su un canale che ne fa 3.000 insegna tutto.

Il tuo compito NON e riassumere. E estrarre gli SCHEMI che si ripetono: le \
regole di costruzione applicabili a un contenuto diverso. \
"Apre nominando una cosa che il pubblico da per certa e la nega" e uno schema. \
"Il video di Tizio sul sonno" non lo e.

Hai titoli, descrizioni, durate e numeri — non hai il video. Quindi lavora su \
cio che vedi davvero: il TITOLO e la prima riga della descrizione sono, nel \
formato breve, quasi sempre l'aggancio stesso. Non inventare cose sul \
montaggio che non puoi sapere.

Scrivi in italiano un documento markdown con esattamente queste sezioni:

## 1. Schemi di aggancio
Gli schemi ricorrenti nei titoli e nelle aperture. Per ognuno: come si \
riconosce, perche funziona, e DUE esempi veri presi da questi dati con il \
loro scarto.

## 2. Cosa hanno in comune i primi dieci
Le costanti dei dieci con lo scarto piu alto, in confronto agli altri.

## 3. Durata e formato
Cosa dicono i numeri sulla durata: c'e una lunghezza che vince? Quantifica.

## 4. Parole e costruzioni che ricorrono
Le formulazioni linguistiche che tornano piu spesso nei titoli forti.

## 5. Cosa NON fanno mai
Gli anti-schemi: cosa e assente dai titoli forti ed e invece presente in \
quelli deboli.

Regole:
- Ogni schema deve comparire in ALMENO TRE video diversi. Sotto quella \
soglia non e uno schema, e un caso: scartalo.
- Quantifica ogni volta che puoi.
- Niente preamboli, niente conclusioni: solo il documento."""


def distilla(video: list[dict], *, model: str) -> str:
    import json
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    dati = json.dumps([
        {k: v[k] for k in ("titolo", "descrizione", "durata", "views", "scarto", "like")}
        for v in video[:60]
    ], ensure_ascii=False, indent=1)
    r = client.messages.create(
        model=model, max_tokens=8000, system=ISTRUZIONI,
        messages=[{"role": "user", "content": f"Ecco i video:\n\n{dati}"}],
    )
    return "".join(b.text for b in r.content
                   if getattr(b, "type", "") == "text").strip()


def scrivi_scheda(video: list[dict], schemi: str, query: list[str]) -> None:
    mediana = statistics.median(v["scarto"] for v in video) if video else 0
    testa = (
        "# La scuola: come sono costruiti i video brevi che sfondano\n\n"
        f"> Estratto automaticamente da **{len(video)} video brevi italiani** che hanno\n"
        f"> superato di almeno 3 volte la media del proprio canale (scarto mediano:\n"
        f"> {mediana:.1f}x). Ricerche usate: {', '.join(query)}.\n"
        ">\n"
        "> Sono SCHEMI, non esempi da copiare. Il prompt di selezione legge questo\n"
        "> file a ogni lavorazione. Si rigenera da solo, nessuno lo compila a mano.\n\n"
        "---\n\n"
    )
    coda = ["\n\n---\n\n## I venti video da cui viene tutto questo\n",
            "| scarto | views | durata | titolo |", "|-------:|------:|-------:|--------|"]
    for v in video[:20]:
        coda.append(f"| {v['scarto']}x | {v['views']:,} | {v['durata']}s | {v['titolo'][:70]} |")
    SCHEDA.write_text(testa + schemi + "\n".join(coda) + "\n", encoding="utf-8")

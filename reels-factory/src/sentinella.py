"""Prova tutte le chiavi e dice quale sta per morire, prima che muoia.

PERCHE ESISTE. Sei giorni, tre blocchi, tutti e tre scoperti dal fatto che
non uscivano Reel:

    25/09  credito Anthropic a zero  -> sei corse morte dopo aver scaricato
                                        e trascritto, a pagamento, per niente
    27/09  minuti GitHub esauriti    -> ogni corsa rifiutata in due secondi,
                                        e la fabbrica ferma due giorni
    30/09  Apify 403 su tutti        -> nessun video nuovo per cinque giorni,
                                        e la coda a zero il 3 ottobre

Nessuno dei tre fornitori avvisa prima. E ogni volta la diagnosi e arrivata
leggendo i log DOPO che Lorenzo si era accorto che mancava qualcosa — cioe
nel momento peggiore, quando il danno e gia fatto e si lavora di fretta.

Quello che mancava non era un controllo in piu dentro la lavorazione: era
un posto dove la domanda «le chiavi sono vive?» venisse fatta a vuoto, a
freddo, quando non serve. Costa pochi secondi e qualche chiamata gratis.

COME. Ogni servizio ha la sua domanda piu economica — quella che non
produce niente e non consuma quota:

    Anthropic    un token, per sapere se l'API apre          (brain)
    Apify        GET /v2/users/me: chi sono e quanta quota ho
    ElevenLabs   GET /v1/user/subscription: crediti residui
    YouTube      il refresh del token OAuth                   (shorts)
    Instagram    GET /me sul Graph                            (instagram)
    R2           l'elenco del bucket                          (storage)

Nessuna di queste scarica, monta o pubblica niente.

E la cosa importante: un servizio NON configurato non e un guasto. Scribe e
diventato la rete di sicurezza il 28/09, Drive non e mai stato configurato:
chiamarli "rotti" vorrebbe dire due righe rosse ogni settimana, e una
sentinella che grida sempre e una sentinella che non si guarda piu.
"""

from __future__ import annotations

import os

import requests


class Esito:
    """Com'e andata una verifica. `vivo` None vuol dire «non configurato»."""

    def __init__(self, servizio: str, vivo: bool | None, dettaglio: str = "",
                 serve: bool = True) -> None:
        self.servizio = servizio
        self.vivo = vivo
        self.dettaglio = dettaglio
        self.serve = serve          # False = la fabbrica gira anche senza

    @property
    def grave(self) -> bool:
        """Da fermare tutto? Solo cio che e rotto E serve davvero."""
        return self.vivo is False and self.serve

    def riga(self) -> str:
        segno = {True: "✅", False: "❌", None: "➖"}[self.vivo]
        if self.vivo is None:
            # Il dettaglio di un servizio non configurato dice GIA perche:
            # ripetere "non configurato" prima sarebbe rumore.
            return f"  {segno} {self.servizio:12} {self.dettaglio or 'non configurato'}"
        stato = {True: "vivo", False: "ROTTO"}[self.vivo]
        coda = f" — {self.dettaglio}" if self.dettaglio else ""
        return f"  {segno} {self.servizio:12} {stato}{coda}"


def _chiave(nome: str) -> str:
    return os.environ.get(nome, "").strip()


def anthropic(model: str) -> Esito:
    if not _chiave("ANTHROPIC_API_KEY"):
        return Esito("Anthropic", None, "manca ANTHROPIC_API_KEY")
    from . import brain
    vivo, guasto = brain.cervello_pronto(model)
    return Esito("Anthropic", vivo, "" if vivo else guasto)


def apify() -> Esito:
    """GET /v2/users/me — la chiamata che avrebbe svelato il 403 del 30/09.

    Risponde anche con la quota del mese: la parte che serve per avvisare
    PRIMA, non dopo.
    """
    token = _chiave("APIFY_TOKEN")
    if not token:
        return Esito("Apify", None, "manca APIFY_TOKEN")
    try:
        r = requests.get("https://api.apify.com/v2/users/me",
                         params={"token": token}, timeout=20)
    except Exception as e:                              # noqa: BLE001
        return Esito("Apify", False, f"non raggiungibile: {e}")
    if r.status_code == 401:
        return Esito("Apify", False, "token non valido: va rigenerato")
    if r.status_code == 403:
        return Esito("Apify", False,
                     "403: token rifiutato o account sospeso — "
                     "guarda console.apify.com, Billing")
    if r.status_code != 200:
        return Esito("Apify", False, f"HTTP {r.status_code}: {r.text[:120]}")
    dati = (r.json() or {}).get("data") or {}
    piano = (dati.get("plan") or {}).get("id") or "?"
    return Esito("Apify", True, f"piano {piano}")


def elevenlabs() -> Esito:
    chiave = _chiave("ELEVENLABS_API_KEY")
    if not chiave:
        # Dal 28/09 Scribe e la rete, non la strada: senza chiave la
        # fabbrica trascrive in casa con Whisper e non manca niente.
        return Esito("ElevenLabs", None, "non configurato (si usa Whisper)",
                     serve=False)
    try:
        r = requests.get("https://api.elevenlabs.io/v1/user/subscription",
                         headers={"xi-api-key": chiave}, timeout=20)
    except Exception as e:                              # noqa: BLE001
        return Esito("ElevenLabs", False, f"non raggiungibile: {e}",
                     serve=False)
    if r.status_code != 200:
        return Esito("ElevenLabs", False,
                     f"HTTP {r.status_code}: {r.text[:120]}", serve=False)
    d = r.json() or {}
    usati = d.get("character_count") or 0
    tetto = d.get("character_limit") or 0
    resto = max(0, tetto - usati)
    # ~330 crediti al minuto di audio, ~17,5 minuti il video medio di Lorenzo
    video = resto / (330 * 17.5) if resto else 0
    return Esito("ElevenLabs", True,
                 f"{resto:,} crediti (~{video:.0f} video)", serve=False)


def youtube() -> Esito:
    """Il token di YouTube scade ogni 7 giorni se l'app resta in Testing."""
    from . import shorts
    if not shorts.configurato():
        return Esito("YouTube", None, "non configurato (niente Shorts)",
                     serve=False)
    try:
        token = shorts._accesso()
    except Exception as e:                              # noqa: BLE001
        return Esito("YouTube", False, f"{e}", serve=False)
    if not token:
        return Esito("YouTube", False,
                     "refresh rifiutato: se l'app e rimasta in Testing il "
                     "token scade ogni 7 giorni e va rifatto", serve=False)
    return Esito("YouTube", True, "", serve=False)


def instagram() -> Esito:
    if not (_chiave("IG_ACCESS_TOKEN") and _chiave("IG_USER_ID")):
        return Esito("Instagram", None, "manca IG_ACCESS_TOKEN o IG_USER_ID")
    from . import instagram as ig
    try:
        return Esito("Instagram", True, ig.check_connection())
    except Exception as e:                              # noqa: BLE001
        return Esito("Instagram", False, f"{e}")


def r2() -> Esito:
    if not _chiave("R2_ACCOUNT_ID"):
        return Esito("R2", None, "manca R2_ACCOUNT_ID")
    from . import storage
    try:
        storage._client().head_bucket(Bucket=os.environ["R2_BUCKET"].strip())
        return Esito("R2", True, "")
    except Exception as e:                              # noqa: BLE001
        return Esito("R2", False, f"{e}")


def riassunto(esiti: list[Esito]) -> tuple[str, int]:
    """Il testo da stampare e il codice d'uscita.

    Esce 1 solo se qualcosa di NECESSARIO e rotto: cosi la mail di
    fallimento arriva quando serve agire, e non ogni settimana per dire che
    Drive non e configurato. Le cose rotte ma non necessarie restano scritte
    nel riassunto, dove si leggono senza fretta.
    """
    righe = ["🔑 Stato delle chiavi"]
    righe += [e.riga() for e in esiti]
    gravi = [e for e in esiti if e.grave]
    minori = [e for e in esiti if e.vivo is False and not e.serve]
    if gravi:
        nomi = ", ".join(e.servizio for e in gravi)
        righe.append(f"❌ La fabbrica non puo lavorare: {nomi}")
        for e in gravi:
            righe.append(f"::error::{e.servizio}: {e.dettaglio}")
    elif minori:
        nomi = ", ".join(e.servizio for e in minori)
        righe.append(f"⚠️ Rotto ma non blocca: {nomi}")
        for e in minori:
            righe.append(f"::warning::{e.servizio}: {e.dettaglio}")
    else:
        righe.append("✅ Tutto a posto")
    return "\n".join(righe), (1 if gravi else 0)


def controlla(model: str) -> tuple[str, int]:
    return riassunto([anthropic(model), apify(), r2(), instagram(),
                      elevenlabs(), youtube()])

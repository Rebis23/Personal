"""Quanti segnali di inizio frase ci sono in una trascrizione.

Serve a rispondere con un numero a una domanda di Lorenzo del 13/10: i
tagli cadono a meta frase, si puo migliorare, e ElevenLabs vale la spesa?

La clip parte dove c'e una PROVA che cominci una proposizione, e le prove
possibili sono cinque (src/aggancio.py): un muro di punteggiatura, una
pausa lunga, una svolta del discorso, una virgola, una pausa breve. Tre di
queste cinque non vengono dal testo ma dai TEMPI — e i tempi li da il
motore di trascrizione.

Misurato il 17/10 su 34 secondi di voce vera di Lorenzo, con Whisper
large-v3, prima con vad_filter=True (come in produzione) e poi senza:

    stacchi fra parole a zero    111 su 115       in tutte e due
    pause >= 0.45s (PAUSA)       0                in tutte e due
    pause >= 1.0s (PAUSA_FORTE)  0                in tutte e due
    stacco piu lungo             0.20s            in tutte e due
    punteggiatura                1 segno, 1.8/min in tutte e due

Il sospetto era il VAD — buttare i silenzi prima di trascrivere. Smentito:
identico. I tempi parola-per-parola di faster-whisper arrivano incollati
uno all'altro, quindi l'informazione sui silenzi non c'e e basta. Due
delle cinque prove (PAUSA, PAUSA_FORTE) sono rami che su questo materiale
non possono scattare mai, e una terza (virgola) dipende da una
punteggiatura che su questa clip fa 1,8 segni al minuto.

Non e un difetto da riparare nel nostro codice: e un segnale che il
fornitore non ci da. Per questo il conto va fatto sullo stesso audio con
l'altro motore, invece di discuterlo.
"""
from __future__ import annotations

MURI = ".:;?!—–"
# La virgola e una delle cinque prove in aggancio.py, non un dettaglio: su
# un parlato senza punti e senza pause puo essere l'unica cosa che resta.
# La prima versione di questo metro la ignorava, e misurava quattro prove su
# cinque chiamandole "gli attacchi offerti".
VIRGOLE = ","
PAUSA = 0.45
PAUSA_FORTE = 1.0
# «ma», «però», «invece»: l'unica prova che vive nel testo e non nei tempi.
SVOLTE = {"ma", "pero", "però", "invece", "anzi", "eppure", "tuttavia"}


def misura(parole: list[dict]) -> dict:
    """I numeri che dicono quanti attacchi un motore ci mette a disposizione.

    `parole` sono dizionari {word, start, end}, la forma che usano sia
    transcribe.py che il resto della fabbrica.
    """
    pulite = [p for p in parole if (p.get("word") or "").strip()]
    n = len(pulite)
    if n < 2:
        return {"parole": n, "durata": 0.0, "stacchi": 0, "zeri": 0,
                "pause": 0, "pause_forti": 0, "stacco_medio": 0.0,
                "stacco_max": 0.0, "segni": 0, "segni_min": 0.0,
                "virgole": 0, "svolte": 0, "attacchi": 0}

    stacchi = [pulite[i]["start"] - pulite[i - 1]["end"] for i in range(1, n)]
    durata = pulite[-1]["end"] - pulite[0]["start"]
    segni = sum(1 for p in pulite if set(p["word"]) & set(MURI))
    virgole = sum(1 for p in pulite if set(p["word"]) & set(VIRGOLE))
    svolte = sum(1 for p in pulite
                 if p["word"].strip(" ,.;:!?").lower() in SVOLTE)
    pause = sum(1 for s in stacchi if s >= PAUSA)
    forti = sum(1 for s in stacchi if s >= PAUSA_FORTE)
    return {
        "parole": n,
        "durata": durata,
        "stacchi": len(stacchi),
        "zeri": sum(1 for s in stacchi if s <= 0.001),
        "pause": pause,
        "pause_forti": forti,
        "stacco_medio": sum(stacchi) / len(stacchi),
        "stacco_max": max(stacchi),
        "segni": segni,
        "segni_min": (segni / (durata / 60)) if durata > 0 else 0.0,
        "virgole": virgole,
        "svolte": svolte,
        # Quante prove di inizio frase questo motore mette sul tavolo —
        # tutte e cinque quelle di aggancio.py. Non e il numero di clip
        # buone: e il numero di punti fra cui scegliere. A zero, la clip
        # parte dove l'ha tagliata il modello.
        "attacchi": segni + virgole + pause + svolte,
    }


def scheda(nome: str, m: dict) -> str:
    """La misura in forma leggibile, per il log di un run."""
    return "\n".join([
        f"{nome}",
        f"  parole            {m['parole']} in {m['durata']:.0f}s",
        f"  stacchi a zero    {m['zeri']} su {m['stacchi']}",
        f"  pause >= {PAUSA}s   {m['pause']}",
        f"  pause >= {PAUSA_FORTE}s    {m['pause_forti']}",
        f"  stacco medio      {m['stacco_medio']:.3f}s   max {m['stacco_max']:.2f}s",
        f"  punteggiatura     {m['segni']} segni, {m['segni_min']:.1f}/min",
        f"  virgole           {m['virgole']}",
        f"  svolte            {m['svolte']}",
        f"  ATTACCHI OFFERTI  {m['attacchi']}",
    ])


def confronto(a: tuple[str, dict], b: tuple[str, dict]) -> str:
    """Le due schede in fila e la riga che conta."""
    (nome_a, ma), (nome_b, mb) = a, b
    righe = [scheda(nome_a, ma), "", scheda(nome_b, mb), "", "— la differenza —"]
    righe.append(f"  attacchi: {ma['attacchi']} con {nome_a}, "
                 f"{mb['attacchi']} con {nome_b}")
    if ma["attacchi"] == mb["attacchi"] == 0:
        righe.append("  nessuno dei due da un punto da cui partire: su questo "
                     "audio la clip parte dove la taglia il modello")
    elif mb["attacchi"] > ma["attacchi"]:
        quante = mb["attacchi"] - ma["attacchi"]
        righe.append(f"  {nome_b} ne offre {quante} in piu: sono {quante} punti "
                     f"fra cui scegliere che prima non c'erano")
    return "\n".join(righe)

"""Parsing dei sottotitoli automatici YouTube (formato json3) in parole temporizzate."""

import json
from pathlib import Path


def parse_json3(path: Path) -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, ordinato nel tempo."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    words: list[dict] = []
    for event in data.get("events", []):
        t_start = event.get("tStartMs")
        if t_start is None or "segs" not in event:
            continue
        duration = event.get("dDurationMs", 0)
        for seg in event["segs"]:
            text = (seg.get("utf8") or "").strip()
            if not text or text == "\n":
                continue
            start_ms = t_start + seg.get("tOffsetMs", 0)
            words.append({"word": text, "start": start_ms / 1000.0, "end": None,
                          "_event_end": (t_start + duration) / 1000.0})

    words.sort(key=lambda w: w["start"])
    # La fine di ogni parola è l'inizio della successiva (limitata alla fine
    # dell'evento), così l'evidenziazione karaoke resta fluida.
    for i, w in enumerate(words):
        next_start = words[i + 1]["start"] if i + 1 < len(words) else w["_event_end"]
        w["end"] = min(max(next_start, w["start"] + 0.08), w["start"] + 3.0)
        del w["_event_end"]
    return words


def to_timed_text(words: list[dict], marker_every: float = 10.0) -> str:
    """Trascrizione testuale con marcatori [mm:ss] ogni ~10s, per Claude."""
    if not words:
        return ""
    parts: list[str] = []
    next_marker = 0.0
    for w in words:
        if w["start"] >= next_marker:
            m, s = divmod(int(w["start"]), 60)
            parts.append(f"\n[{m:02d}:{s:02d}]")
            next_marker = w["start"] + marker_every
        parts.append(w["word"])
    return " ".join(parts).strip()


def snap_to_words(words: list[dict], start: float, end: float) -> tuple[float, float]:
    """Aggancia i confini della clip ai confini reali delle parole, con un
    piccolo margine, così non si taglia una parola a metà."""
    in_range = [w for w in words if w["start"] >= start - 1.5 and w["end"] <= end + 1.5]
    if not in_range:
        return start, end
    first = min(in_range, key=lambda w: abs(w["start"] - start))
    last = max((w for w in in_range if w["end"] <= end + 1.5), key=lambda w: w["end"])
    snapped_start = max(0.0, first["start"] - 0.25)
    snapped_end = last["end"] + 0.45
    return snapped_start, snapped_end


def words_in_clip(words: list[dict], start: float, end: float) -> list[dict]:
    """Parole della clip, con tempi RELATIVI all'inizio della clip."""
    # Contenimento STRETTO. I confini arrivano gia con un margine (-0.20s in
    # testa, +0.40s in coda) che serve al video per non tranciare l'audio: se
    # qui si allentasse ancora, dentro quel margine entrerebbero le prime
    # parole della frase successiva e i sottotitoli mostrerebbero un pezzo di
    # frase che non c'entra.
    out = []
    for w in words:
        if w["start"] >= start and w["end"] <= end:
            out.append({
                "word": w["word"],
                "start": max(0.0, w["start"] - start),
                "end": max(0.0, w["end"] - start),
            })
    return out


# --------------------------------------------------------------- frasi ---
# Il taglio alla PAROLA più vicina lasciava clip che iniziavano e finivano a
# metà frase (segnalato da Lorenzo il 25/08). Qui la trascrizione viene divisa
# in frasi vere e i confini della clip ci si agganciano sopra.

_TERMINAL = (".", "!", "?", "…")
_PAUSE_SPLIT = 0.75      # silenzio che vale quanto un punto
_MAX_SENTENCE = 20.0     # oltre, Whisper ha semplicemente omesso la punteggiatura


def _closes_sentence(word: str) -> bool:
    """True se la parola chiude una frase. Esclude sigle e numeri ('n.', '3.')
    dove il punto non e un punto fermo."""
    text = word.strip()
    if not text.endswith(_TERMINAL):
        return False
    stem = text.rstrip("".join(_TERMINAL) + "\"'»)")
    return len(stem) > 1 and not stem.isdigit()


def _split_long(group: list[dict]) -> list[list[dict]]:
    """Spezza un blocco troppo lungo nella sua pausa interna piu ampia."""
    span = group[-1]["end"] - group[0]["start"]
    if span <= _MAX_SENTENCE or len(group) < 6:
        return [group]
    best_i, best_gap = None, 0.0
    for i in range(2, len(group) - 2):
        gap = group[i]["start"] - group[i - 1]["end"]
        if gap > best_gap:
            best_i, best_gap = i, gap
    if best_i is None:
        return [group]
    return _split_long(group[:best_i]) + _split_long(group[best_i:])


def sentences(words: list[dict]) -> list[dict]:
    """Raggruppa le parole in frasi: [{start, end, text}].

    Si chiude su punteggiatura forte oppure su una pausa lunga — nel parlato
    Whisper la punteggiatura salta spesso, il silenzio no.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    for i, w in enumerate(words):
        current.append(w)
        gap_next = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 99.0
        if _closes_sentence(w["word"]) or gap_next >= _PAUSE_SPLIT:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    out = []
    for g in groups:
        for piece in _split_long(g):
            out.append({
                "start": piece[0]["start"],
                "end": piece[-1]["end"],
                "text": " ".join(p["word"] for p in piece).strip(),
            })
    return out


def _sentence_at(sents: list[dict], t: float) -> int:
    """Indice della frase che contiene t, o della prima che inizia dopo."""
    for i, s in enumerate(sents):
        if s["end"] >= t:
            return i
    return len(sents) - 1



def _pads(sents: list[dict], i0: int, i1: int,
          head: float = 0.20, tail: float = 0.40) -> tuple[float, float]:
    """Margini da lasciare attorno alla clip, senza invadere le frasi vicine.

    Un margine fisso va bene quando tra una frase e l'altra c'e mezzo secondo
    di respiro, ma nel parlato serrato le frasi si toccano: li un margine di
    0.40s si porta dentro le prime parole della frase successiva. Si prende
    quindi meta della pausa reale, mai piu del massimo voluto.
    """
    gap_before = sents[i0]["start"] - sents[i0 - 1]["end"] if i0 > 0 else 1.0
    gap_after = (sents[i1 + 1]["start"] - sents[i1]["end"]
                 if i1 + 1 < len(sents) else 1.0)
    return (min(head, max(0.0, gap_before * 0.5)),
            min(tail, max(0.05, gap_after * 0.5)))


def snap_to_sentences(words: list[dict], start: float, end: float, *,
                      min_seconds: float, max_seconds: float) -> tuple[float, float]:
    """Porta i confini della clip su frasi intere, rispettando la durata.

    Claude stima i secondi leggendo i marcatori [mm:ss]: sono approssimativi e
    cadono in mezzo alle frasi. Qui si corregge sul timing reale delle parole.
    """
    sents = sentences(words)
    if not sents:
        return snap_to_words(words, start, end)

    i0 = _sentence_at(sents, start)
    s0 = sents[i0]
    # Se il taglio richiesto cade oltre il primo terzo della frase, quella frase
    # e gia iniziata da un pezzo: meglio partire dalla successiva che riproporne
    # una monca
    span = max(0.001, s0["end"] - s0["start"])
    if (start - s0["start"]) / span > 0.35 and i0 + 1 < len(sents):
        i0 += 1

    i1 = i0
    for i in range(i0, len(sents)):
        if sents[i]["end"] <= end + 2.0:
            i1 = i
        else:
            break

    def dur(a: int, b: int) -> float:
        return sents[b]["end"] - sents[a]["start"]

    # Troppo lunga: si tolgono frasi dal fondo. Troppo corta: se ne aggiungono,
    # ma solo finche si resta sotto il massimo
    while i1 > i0 and dur(i0, i1) > max_seconds:
        i1 -= 1
    while i1 + 1 < len(sents) and dur(i0, i1) < min_seconds:
        if dur(i0, i1 + 1) > max_seconds:
            break
        i1 += 1

    head, tail = _pads(sents, i0, i1)
    return max(0.0, sents[i0]["start"] - head), sents[i1]["end"] + tail


def sentence_around(words: list[dict], t: float, *,
                    min_seconds: float = 1.5,
                    max_seconds: float = 6.0) -> tuple[float, float] | None:
    """La frase intera che contiene l'istante t — serve per il cold open.

    Se e troppo corta si allunga con la frase successiva; se e troppo lunga
    non va bene come apertura e si rinuncia.
    """
    sents = sentences(words)
    if not sents:
        return None
    # Claude stima il secondo leggendo i marcatori [mm:ss]: puo sbagliare di
    # un paio di secondi e finire nel silenzio tra due frasi. Si prende quella
    # piu vicina, non la prima che comincia dopo.
    def distance(s: dict) -> float:
        if s["start"] <= t <= s["end"]:
            return 0.0
        return min(abs(t - s["start"]), abs(t - s["end"]))
    i = min(range(len(sents)), key=lambda k: distance(sents[k]))
    a, b = i, i
    while b + 1 < len(sents) and (sents[b]["end"] - sents[a]["start"]) < min_seconds:
        b += 1
    span = sents[b]["end"] - sents[a]["start"]
    if span < min_seconds or span > max_seconds:
        return None
    head, tail = _pads(sents, a, b, head=0.15, tail=0.25)
    return max(0.0, sents[a]["start"] - head), sents[b]["end"] + tail


def words_for_clip(words: list[dict], start: float, end: float,
                   punch: tuple[float, float] | None = None) -> list[dict]:
    """Parole del montato finale, con tempi relativi al primo fotogramma.

    Con il cold open il montato e [frase forte] + [clip]: le parole della
    frase forte vengono prima, quelle della clip slittano in avanti della sua
    durata. Senza cold open si comporta come words_in_clip.
    """
    if punch is None:
        return words_in_clip(words, start, end)
    p_start, p_end = punch
    offset = p_end - p_start
    out = words_in_clip(words, p_start, p_end)
    for w in words_in_clip(words, start, end):
        out.append({"word": w["word"],
                    "start": w["start"] + offset,
                    "end": w["end"] + offset})
    return out

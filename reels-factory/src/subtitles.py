"""Generazione sottotitoli ASS stile Reels.

Due stili:
  - "word"    → una parola alla volta, grande, bianca, centrata sul video
                (stile Modern Wisdom / Chris Williamson)
  - "karaoke" → gruppi di poche parole con evidenziazione della parola
                pronunciata (stile classico Reels)
"""

from pathlib import Path

ASS_HEADER_KARAOKE = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Reel,{font},{size},{highlight},{base},&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Gruppi di 2-3 parole: bianco pieno con una leggera ombra morbida attorno
# (bordo nero semi-trasparente sfumato con \blur). Allineamento centrale,
# la posizione esatta arriva con \pos.
ASS_HEADER_WORD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{font},{size},{base},{base},&H82000000,&H96000000,-1,0,0,0,100,100,0,0,1,3,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_time(seconds: float) -> str:
    cs = round(max(0.0, seconds) * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_color(short_bgr: str) -> str:
    """Da "&H00FFFF&" (BGR) al formato completo ASS &HAABBGGRR."""
    hexpart = short_bgr.strip("&H").strip("&").zfill(6)[-6:]
    return f"&H00{hexpart.upper()}"


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(
    words: list[dict],
    out_path: Path,
    *,
    font: str = "Nunito",
    font_size: int = 112,
    highlight_color: str = "&H00FFFF&",
    base_color: str = "&HFFFFFF&",
    words_per_line: int = 3,
    vertical_position: float = 0.5,
    style: str = "word",
    uppercase: bool = False,
) -> Path:
    """Scrive il file .ass. `words` ha tempi relativi all'inizio della clip."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if style == "word":
        content = _build_word(words, font, font_size, base_color,
                              vertical_position, uppercase,
                              words_per_screen=words_per_line)
    else:
        content = _build_karaoke(words, font, font_size, highlight_color,
                                 base_color, words_per_line, vertical_position,
                                 uppercase)
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ------------------------------------------------------------------- WORD ---

def _build_word(
    words: list[dict],
    font: str,
    font_size: int,
    base_color: str,
    vertical_position: float,
    uppercase: bool,
    words_per_screen: int = 3,
) -> str:
    header = ASS_HEADER_WORD.format(
        font=font, size=font_size, base=_ass_color(base_color),
    )
    x, y = 540, int(vertical_position * 1920)

    # Gruppi di massimo `words_per_screen` parole, spezzati anche sulle
    # pause naturali del parlato
    groups: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur and (len(cur) >= words_per_screen
                    or w["start"] - cur[-1]["end"] > 0.7):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    lines: list[str] = []
    for i, g in enumerate(groups):
        start = g[0]["start"]
        # Il gruppo resta a schermo fino al successivo (niente sfarfallio),
        # ma nei silenzi lunghi sparisce dopo un attimo
        if i + 1 < len(groups):
            end = min(groups[i + 1][0]["start"], g[-1]["end"] + 0.8)
        else:
            end = g[-1]["end"] + 0.4
        if end - start < 0.15:
            end = start + 0.15
        text = _escape(" ".join(w["word"].strip() for w in g))
        if uppercase:
            text = text.upper()
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Word,,0,0,0,,"
            f"{{\\pos({x},{y})\\blur2}}{text}"
        )
    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------------- KARAOKE ---

def _build_karaoke(
    words: list[dict],
    font: str,
    font_size: int,
    highlight_color: str,
    base_color: str,
    words_per_line: int,
    vertical_position: float,
    uppercase: bool,
) -> str:
    """Il karaoke ASS parte dal colore Secondary (base) e "riempie" con il
    Primary (evidenziazione) parola per parola tramite i tag \\k."""
    margin_v = int((1.0 - vertical_position) * 1920)
    header = ASS_HEADER_KARAOKE.format(
        font=font,
        size=font_size,
        highlight=_ass_color(highlight_color),
        base=_ass_color(base_color),
        margin_v=margin_v,
    )

    lines: list[str] = []
    for i in range(0, len(words), words_per_line):
        group = words[i:i + words_per_line]
        start = group[0]["start"]
        end = group[-1]["end"]
        if end - start < 0.15:
            end = start + 0.15
        parts = []
        cursor = start
        for w in group:
            # Eventuale silenzio prima della parola: karaoke "vuoto"
            gap_cs = round((w["start"] - cursor) * 100)
            if gap_cs > 2:
                parts.append(f"{{\\k{gap_cs}}}")
            dur_cs = max(1, round((w["end"] - w["start"]) * 100))
            word = w["word"].upper() if uppercase else w["word"]
            parts.append(f"{{\\k{dur_cs}}}{_escape(word)} ")
            cursor = w["end"]
        text = "".join(parts).rstrip()
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Reel,,0,0,0,,{text}"
        )
    return header + "\n".join(lines) + "\n"

"""Un banner bocciato non esce. Nemmeno se a bocciarlo e stato l'altro giudice.

I banner passano davanti a due giudici, e fanno due lavori diversi:

    prova_a_freddo()      la frase si regge per chi non ha visto il video?
    nomina_argomento()    la frase dice di cosa si parla?

Il secondo e nato il 6/09, dopo il Reel sulla religione uscito col titolo
«Zanzara che depone le uova negli occhi»: la prova a freddo non poteva
accorgersene, perche quella riga letta da sola incuriosisce davvero.

Ma il filtro in fondo a select_clips() ne ascoltava uno solo:

    usable = [c for i, c in enumerate(usable)
              if i in salvati or i not in esiti or esiti[i][0]]

`esiti` e il verdetto della prova a freddo. Una clip bocciata SOLTANTO sul
tema non compare li dentro, quindi «i not in esiti» era vero e la clip
restava — con l'hook di prima, o con la riscrittura appena giudicata
insufficiente. Il 15/10 e successo per davvero: «Essere competitivi è
davvero una cosa brutta?» ha fatto cadere la riscrittura, il log ha scritto
«❄️ anche la riscrittura cade», e il Reel e andato in coda con quel banner.

Un controllo che parla e nessuno che gli dia retta e peggio di un controllo
che non c'e: chi legge il codice vede il controllo e crede che il caso sia
coperto.

    python prove/respinti.py
"""
import sys
import types
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import brain as B

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


class FintaClip:
    """Quanto basta di ClipPick perche select_clips la tratti da clip."""

    def __init__(self, start, hook, argomento, forza=9):
        self.start_seconds = float(start)
        self.end_seconds = float(start) + 40.0
        self.hook = hook
        self.hook_pattern = "prova"
        self.hook_strength = forza
        self.argomento = argomento


def gira(clips, *, freddo, tema_ok, riscritture, ricontrollo):
    """Fa girare select_clips() con i giudici finti e torna (clip, stampato).

    Finto e solo chi parla col modello. Il filtro in fondo — quello sotto
    esame — e il codice vero: se lo cambio male, qui si vede.
    """
    import io
    import os
    from contextlib import redirect_stdout

    class Risposta:
        stop_reason = "end_turn"
        usage = types.SimpleNamespace(input_tokens=0, output_tokens=0)
        parsed_output = types.SimpleNamespace(clips=clips)

    class Messaggi:
        def parse(self, **_):
            return Risposta()

    class Cliente:
        def __init__(self, **_):
            self.messages = Messaggi()

    originali = {}

    def sostituisci(nome, valore, dove=B):
        originali[(dove, nome)] = getattr(dove, nome)
        setattr(dove, nome, valore)

    os.environ.setdefault("ANTHROPIC_API_KEY", "prova")
    sostituisci("Anthropic", Cliente, B.anthropic)
    sostituisci("segna", lambda *a, **k: None, B.conto)
    sostituisci("leggi_scheda", lambda *a, **k: "", B.prestazioni)
    sostituisci("load_hooks_library", lambda: "")
    sostituisci("load_nicchia", lambda: "")
    sostituisci("nomina_argomento",
                lambda hook, arg: tema_ok.get(hook, True), B.aggancio)
    sostituisci("accorcia", lambda hooks, **k: {}, B.aggancio)
    # prova_a_freddo viene chiamata due volte: prima su tutti, poi solo sulle
    # riscritture. Le due risposte arrivano in fila.
    risposte = [freddo, ricontrollo]
    sostituisci("prova_a_freddo", lambda hooks, **k: risposte.pop(0))
    sostituisci("riscrivi_hooks", lambda falliti, t, **k: dict(riscritture))

    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            fuori = B.select_clips("[00:00] niente", "video", model="m",
                                   brand_context="", clips_per_video=4,
                                   min_seconds=20, max_seconds=90)
    finally:
        for (dove, nome), valore in originali.items():
            setattr(dove, nome, valore)
    return fuori, buffer.getvalue()


BUONA = "Nessuno te lo dice ma funziona"
FUORI_TEMA = "Essere competitivi è davvero una cosa brutta?"

print("— il caso del 15/10, con la riscrittura che cade —")
clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, FUORI_TEMA, "la competizione")]
fuori, log = gira(
    clips,
    freddo={0: (True, "ok"), 1: (True, "si regge")},   # a freddo PASSA
    tema_ok={FUORI_TEMA: False},                       # ma non nomina il tema
    riscritture={1: "Una riscrittura che non regge"},
    ricontrollo={0: (False, "non dice niente")},       # e la riscrittura cade
)
check("la clip col banner bocciato due volte non esce", len(fuori) == 1)
check("quella buona resta", fuori and fuori[0].hook == BUONA)
check("e il log lo dice invece di farlo in silenzio", "🚫 1 clip tolte" in log)
check("il motivo del taglio resta scritto", "anche la riscrittura cade" in log)

print("\n— se la riscrittura regge, la clip esce con quella —")
clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, FUORI_TEMA, "la competizione")]
fuori, log = gira(
    clips,
    freddo={0: (True, "ok"), 1: (True, "si regge")},
    tema_ok={FUORI_TEMA: False},
    riscritture={1: "La competizione ti sta rovinando"},
    ricontrollo={0: (True, "ok, si capisce")},
)
check("escono tutte e due", len(fuori) == 2)
check("con il banner nuovo, non quello vecchio",
      [c.hook for c in fuori] == [BUONA, "La competizione ti sta rovinando"])
check("e nessun taglio da annunciare", "🚫" not in log)

print("\n— e se la riscrittura non arriva proprio —")
# riscrivi_hooks() puo tornare vuoto: modello giu, risposta illeggibile.
# Prima restava l'hook di partenza, gia bocciato. Adesso la clip esce di
# scena: meglio un Reel in meno che un Reel col titolo sbagliato.
clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, FUORI_TEMA, "la competizione")]
fuori, log = gira(
    clips,
    freddo={0: (True, "ok"), 1: (True, "si regge")},
    tema_ok={FUORI_TEMA: False},
    riscritture={},
    ricontrollo={},
)
check("la clip fuori tema non esce", [c.hook for c in fuori] == [BUONA])

print("\n— la prova a freddo continua a funzionare come prima —")
DEBOLE = "Il vantaggio iniziale è sempre dello stupido"
clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, DEBOLE, "la stupidità")]
fuori, log = gira(
    clips,
    freddo={0: (True, "ok"), 1: (False, "aforisma senza contesto")},
    tema_ok={},                                   # il tema lo nomina
    riscritture={1: "Partire stupidi conviene davvero"},
    ricontrollo={0: (True, "ok")},
)
check("bocciata a freddo e riscritta bene: esce", len(fuori) == 2)

clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, DEBOLE, "la stupidità")]
fuori, log = gira(
    clips,
    freddo={0: (True, "ok"), 1: (False, "aforisma senza contesto")},
    tema_ok={},
    riscritture={1: "Un'altra che non regge"},
    ricontrollo={0: (False, "no")},
)
check("bocciata a freddo e riscritta male: non esce",
      [c.hook for c in fuori] == [BUONA])

print("\n— una clip che nessuno boccia passa liscia —")
clips = [FintaClip(0, BUONA, "il lavoro"), FintaClip(100, "Altra buona", "x")]
fuori, _ = gira(clips, freddo={0: (True, "ok"), 1: (True, "ok")},
                tema_ok={}, riscritture={}, ricontrollo={})
check("non si tocca niente quando non c'e niente da togliere", len(fuori) == 2)

print("\n— l'hook caduto non resta appeso alla clip —")
# La clip esce di scena, ma l'oggetto vive ancora: se un domani qualcuno lo
# rimette in gioco deve trovarci la frase di partenza, non quella bocciata
# due volte. E' una pulizia, non una riparazione: la clip se ne va comunque.
clips = [FintaClip(0, BUONA, "il lavoro"),
         FintaClip(100, FUORI_TEMA, "la competizione")]
gira(clips, freddo={0: (True, "ok"), 1: (True, "ok")},
     tema_ok={FUORI_TEMA: False},
     riscritture={1: "Riscrittura caduta"},
     ricontrollo={0: (False, "no")})
check("la clip bocciata si ritrova l'hook di partenza",
      clips[1].hook == FUORI_TEMA)

print("\n— il filtro deve restare uno solo —")
import inspect
corpo = inspect.getsource(B.select_clips)
# Solo le righe di codice: il filtro vecchio e citato apposta nel commento
# qui sopra, e cercarlo nel sorgente intero lo ritroverebbe li.
codice = "\n".join(r for r in corpo.splitlines()
                   if not r.lstrip().startswith("#"))
check("il filtro guarda l'insieme dei respinti",
      "if i not in respinti or i in salvati" in codice)
check("e non piu solo la prova a freddo",
      "i not in esiti or esiti[i][0]" not in codice)
check("i respinti nascono dalla stessa lista dei bocciati",
      "respinti = {i for i, *_ in bocciati}" in corpo)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

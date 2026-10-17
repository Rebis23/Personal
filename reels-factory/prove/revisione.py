"""Il file che Lorenzo legge prima che i Reel escano.

Lorenzo, 15/10: «facciamo che le prossime volte che prepari un reel mi mandi
prima la trascrizione e ti do io un feedback di quanto funziona e poi ti do
delle alternative e vediamo come iterare».

Dietro la richiesta ci sono due lamentele precise, e il file deve rispondere
a tutte e due: i tagli non cadono nel punto giusto («spesso finisci per fare
dei tagli che non sono esatti sul momento»), e gli agganci non danno contesto
(«come se partisse da 0 e terminasse da solo»). Per questo ogni clip mostra
il banner, la prima frase che si sente e il testo intero.

La trascrizione c'era sempre stata: la fabbrica la calcola per i
sottotitoli, per le enfasi e per la riga d'apertura, e poi la buttava. Il
17/10, per avere il testo di dieci clip gia montate, ho dovuto riscaricarle
da R2 e rifare Whisper sul montato — con la musica dentro. Adesso finisce
in coda insieme alla clip.

    python prove/revisione.py
"""
import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
if "anthropic" not in sys.modules:
    finto = types.ModuleType("anthropic")
    finto.Anthropic = object
    sys.modules["anthropic"] = finto
from src import main as M

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


def scrivi(coda, nome="out.md"):
    """Fa girare `revisione` su una coda finta e torna (testo, stampato)."""
    import tempfile
    lavoro = Path(tempfile.mkdtemp(prefix="prove-revisione-"))
    dove = lavoro / nome
    vecchio_carica, vecchio_argv = M.state_mod.load_state, sys.argv
    M.state_mod.load_state = lambda: {"queue": coda}
    sys.argv = ["main", "revisione", str(dove)]
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            esito = M.cmd_revisione()
    finally:
        M.state_mod.load_state, sys.argv = vecchio_carica, vecchio_argv
    testo = dove.read_text(encoding="utf-8") if dove.exists() else ""
    return testo, buffer.getvalue(), esito


PIENA = {
    "clip_id": "abc-1", "video_id": "abc", "video_title": "Il video lungo",
    "hook": "I soldi non fanno la felicità: falso",
    "media_url": "https://r2/abc-1.mp4", "created_at": "2026-10-17T08:00:00Z",
    "testo": "Te lo dicono da sempre. I soldi non fanno la felicità, falso: "
             "sopra una certa soglia smettono di contare, sotto contano "
             "tantissimo.",
    "inizio": 312.0, "fine": 368.0,
}

print("— una clip con la trascrizione —")
testo, log, esito = scrivi([PIENA])
check("il file viene scritto", esito == 0 and testo)
check("c'e il banner nel titolo", "I soldi non fanno la felicità: falso" in testo)
check("c'e la trascrizione intera", "sopra una certa soglia" in testo)
check("c'e la prima frase, isolata", "**Parte da:** «Te lo dicono da sempre»" in testo)
check("ci sono i secondi nel video di partenza", "312s → 368s" in testo)
check("e il link al montato, per guardarlo", "https://r2/abc-1.mp4" in testo)
check("il titolo del video lungo da il contesto", "Il video lungo" in testo)

print("\n— una clip senza trascrizione lo DICE —")
# Il caso delle dieci clip del 15/10: montate prima che la fabbrica tenesse
# il testo. Una riga vuota qui sarebbe la cosa peggiore: chi legge crede di
# aver letto la trascrizione e di averla trovata corta.
VECCHIA = {k: v for k, v in PIENA.items() if k not in ("testo", "inizio", "fine")}
VECCHIA["clip_id"] = "vecchia-1"
testo, log, esito = scrivi([VECCHIA])
check("lo scrive invece di lasciare il buco",
      "Trascrizione non salvata" in testo)
check("e lo conta anche a voce", "1 senza trascrizione" in log)
check("ma la clip compare comunque", "vecchia-1" in testo)
check("senza inventarsi i secondi", "→" not in testo.split("- video:")[0])

print("\n— un testo ripescato lo deve dichiarare —")
# Lorenzo legge questo file anche per giudicare la qualita della
# trascrizione. Il testo delle dieci clip del 15/10 l'ho ripreso con
# Whisper sul montato, con la musica sotto: se non c'e scritto, lui
# giudica una cosa credendo di giudicarne un'altra.
RIPESCATA = dict(PIENA, clip_id="ripescata-1",
                 testo_da="whisper sul montato, 17/10 (recupero)")
testo, _, _ = scrivi([RIPESCATA])
check("c'e scritto da dove viene", "whisper sul montato" in testo)
check("e la trascrizione c'e comunque", "sopra una certa soglia" in testo)
testo, _, _ = scrivi([PIENA])
check("mentre il testo della lavorazione non porta avvisi",
      "Testo ripreso" not in testo)

print("\n— un banner troppo lungo si vede subito —")
LUNGA = dict(PIENA, clip_id="lunga-1",
             hook="Perché per un ricco 2.000 euro sono pochi")
testo, _, _ = scrivi([LUNGA])
check("8 parole, segnalate nel titolo", "⚠️ 8 parole" in testo)
check("e il conto e quello giusto: «2.000» e una parola",
      "⚠️ 9 parole" not in testo)
testo, _, _ = scrivi([PIENA])
check("mentre un banner nei limiti non porta avvisi", "⚠️" not in testo)

print("\n— la coda vuota non produce un file vuoto —")
testo, log, esito = scrivi([])
check("esce a posto", esito == 0)
check("senza scrivere niente", testo == "")
check("dicendolo", "Coda vuota" in log)

print("\n— tutte e dieci in fila —")
coda = [dict(PIENA, clip_id=f"c-{i}", hook=f"Banner numero {i}")
        for i in range(1, 11)]
testo, log, _ = scrivi(coda)
check("il conto in testa e giusto", testo.startswith("# Clip in attesa — 10"))
check("ci sono tutti e dieci i titoli",
      all(f"## {i}. Banner numero {i}" in testo for i in range(1, 11)))

print("\n— e l'ingest la deve SALVARE, se no questo file resta vuoto —")
# La parte che si rompe per prima: un comando che legge un campo che
# nessuno scrive. Qui si guarda chi scrive.
import inspect
# La voce in coda la costruisce _process_video(), non cmd_ingest(): la prima
# versione di questa prova guardava cmd_ingest e dava tre ROTTO su un
# codice giusto. Una prova che cerca nel posto sbagliato dice "manca" di una
# cosa che c'e — e la prossima volta uno la aggiunge due volte.
sorgente = inspect.getsource(M._process_video)
check('la clip in coda porta "testo"', '"testo": aggancio.ricuci(' in sorgente)
check("preso dalle parole del montato, non dalla trascrizione intera",
      'w["word"].strip() for w in clip_words' in sorgente)
check("e porta anche i secondi nel video", '"inizio": round(start, 1)' in sorgente)
check("il comando e nella tabella", '"revisione": cmd_revisione' in
      (RADICE / "src" / "main.py").read_text(encoding="utf-8"))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

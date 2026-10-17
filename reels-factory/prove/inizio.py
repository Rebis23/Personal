"""Le dieci correzioni di Lorenzo del 17/10, messe a fare da giudice.

Lui ha riguardato una per una le dieci clip ferme in coda e ha detto, per
ognuna, da dove doveva partire o perche non andava. Quelle righe sono la
specifica: stanno in inizio.md per esteso, e qui diventano una prova che
gira a ogni commit.

Cosa NON prova questo file: che il modello scelga bene. Quello lo dice
solo un Reel vero. Prova le due cose che si possono provare senza
chiamarlo — che il veto meccanico prenda i casi che sa prendere senza
toccare quelli buoni, e che le regole arrivino davvero al modello invece
di restare in un file che nessuno legge.

    python prove/inizio.py
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
from src import aggancio as A

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


# Gli inizi veri delle dieci clip, e il verdetto di Lorenzo.
# (inizio, lo prende il veto meccanico?, nota)
BOCCIATI = [
    ("perché un high performer è una persona che è in grado", True,
     "n.1 — «via il perché prima di un high performer»"),
    ("è complessa e magari si stressa e accumula ansia", False,
     "n.2 — «è complessa» chi? Serve il soggetto, non una lista di parole"),
    ("Normalmente ha una caratteristica che è la spinta", False,
     "n.3 — comincia con un avverbio innocuo: la prende solo il giudizio"),
    ("nutrire e quella personalità che invece mi è utile", False,
     "n.4 — la clip va buttata, non spostata"),
    ("e tutte cose assolutamente false, ma che le persone", True,
     "n.9 — «tutte cose quali?»"),
    ("Perché non farlo? Loro ti diranno di no", True,
     "n.10 — «fare cosa?»"),
]

APPROVATI = [
    ("un high performer è una persona che è in grado", "n.1, come l'ha corretta"),
    ("chi di solito ha forte agency decide rapidamente", "n.2, come l'ha corretta"),
    ("Beh, in questo momento stai pensando nel modo sbagliato",
     "n.5, accettata: un «Beh» in testa non e un difetto da bocciare"),
    ("Noi siamo nella nostra mente conscia il 5% del tempo", "n.6, «OTTIMO»"),
    ("Per me 2.000 euro al mese sono pochi", "n.7, «OTTIMO»"),
    ("Ha comprato solo libri in giapponese, 24 ore al giorno",
     "n.8 — verbo senza soggetto, ma il contesto lo da il banner"),
]

print("— i sei inizi bocciati —")
presi = 0
for frase, atteso, nota in BOCCIATI:
    motivo = A.apertura_vietata(frase)
    if motivo:
        presi += 1
    check(f"{'preso' if motivo else 'lo prende solo il giudizio'} · {nota}",
          bool(motivo) == atteso)

print("\n— e i sei approvati non devono essere toccati —")
for frase, nota in APPROVATI:
    motivo = A.apertura_vietata(frase)
    check(f"passa · {nota}", motivo == "")

print("\n— quanto copre il veto, detto in chiaro —")
# Questo numero va tenuto onesto, non alzato: tre su sei e quello che una
# lista di parole sa fare. Gonfiarlo vorrebbe dire bocciare anche i buoni,
# ed e lo stesso errore della soglia di radicato() provata ieri.
check(f"prende {presi} dei 6 bocciati, e lo dichiara", presi == 3)
# Le citazioni di Lorenzo nel file vanno a capo dove capita, quindi si
# cerca sul testo con gli spazi appiattiti: inseguire i ritorni a capo
# farebbe fallire la prova su un file giusto.
import re as _re
_GREZZO = (RADICE / "inizio.md").read_text(encoding="utf-8")
# Via anche il «>» delle citazioni: una frase di Lorenzo che va a capo
# dentro un blockquote diventa «Manca > il soggetto», e la prova direbbe
# che la citazione non c'e mentre c'e.
TESTO = _re.sub(r"\s+", " ", _re.sub(r"^>\s?", "", _GREZZO, flags=_re.M))
check("gli altri tre restano al giudizio, ed e scritto in inizio.md",
      "nessuna lista di parole proibite se ne accorge" in TESTO)

print("\n— la riparazione della n.1: si toglie la parola, non la clip —")
# «devi partire da "un high performer è una persona..." senza [...] il
# "perchè" prima». Togliendo la prima parola la frase si salva da sola.
frase = "perché un high performer è una persona"
check("«perché» in testa e vietato", A.apertura_vietata(frase) != "")
senza = " ".join(frase.split()[1:])
check(f"ma senza regge: «{senza}»", A.apertura_vietata(senza) == "")
check("e il codice fa proprio questo",
      'pulita = " ".join(frase.split()[1:])'
      in (RADICE / "src" / "aggancio.py").read_text(encoding="utf-8"))

print("\n— le ammesse sono ammesse davvero —")
for p in ("chi", "noi", "per", "un", "una", "beh"):
    check(f"«{p}» puo aprire un Reel", p not in A.MAI_IN_TESTA)
for p in ("e", "ma", "perché", "quindi", "questo", "ehm"):
    check(f"«{p}» no", p in A.MAI_IN_TESTA)

print("\n— le regole devono ARRIVARE al modello —")
# Un file di regole che nessuno legge e peggio di nessun file: chi lo
# apre crede che il caso sia coperto.
regole = A._regole_inizio()
check("inizio.md viene letto", len(regole) > 2000)
check("e ci sono tutte e dieci le correzioni, numerate",
      all(f"### {i} —" in regole for i in range(1, 11)))
check("con le parole di Lorenzo, non un mio riassunto",
      all(s in TESTO for s in (
          "OTTIMO HOOK è molto bello",
          "Come ha imparato il giapponese in 30 giorni",
          "tutte cose quali? Di cosa parliamo?",
          "Manca il soggetto che probabilmente era prima del reel")))
check("il prompt le porta dentro", "{regole}" in A.SCEGLI_INIZIO)
check("e chiede la frase copiata, non riscritta",
      "copiata parola per parola" in A.SCEGLI_INIZIO)
check("e offre lo SCARTA, che e la correzione n.4",
     "SCARTA" in A.SCEGLI_INIZIO)

print("\n— e main.py deve dare retta allo SCARTA —")
principale = (RADICE / "src" / "main.py").read_text(encoding="utf-8")
check("scegli_inizio() ha preso il posto di dal_parlato()",
      "aggancio.scegli_inizio(" in principale
      and "aggancio.dal_parlato(" not in principale)
check("e quando dice SCARTA la clip non si monta",
      'detta.get("scarta")' in principale and "continue" in principale)
check("gli inizi gia usati arrivano ancora alla scelta: niente due clip "
      "che aprono uguale",
      "gia_usati=frozenset(banner_usati)" in principale)

print("\n— il fallback senza il file —")
import builtins
vero = builtins.open
check("se inizio.md sparisce resta una regola, non il vuoto",
      len(A._regole_inizio()) > 50)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

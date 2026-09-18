"""Il banner deve nominare l'argomento — ma senza bocciare chi lo nomina.

La regola e nata il 6/09, dallo screenshot di Lorenzo: un Reel sulla
religione uscito col titolo «Zanzara che depone le uova negli occhi». La
zanzara nel video c'e davvero, ma chi scorre legge il titolo e non capisce
di cosa si parla.

Il 17/09 la stessa regola ha bocciato SEI banner su sei, e almeno due
ingiustamente:

    «Niente ti farebbe cambiare idea? E ego»  — la clip parlava di «l'ego
    nei dibattiti». La stessa identica parola, respinta da un apostrofo.

    «Vannacci o corteo LGBT? Sei un tifoso»   — la clip parlava di «pensare
    per tifoserie». Stessa radice, respinta perche «tifoso» ha sei lettere e
    restava intera mentre «tifoserie» ne ha nove e veniva tagliata a
    «tifose».

Una guardia che boccia chi e in regola costringe a riscrivere banner che
andavano bene, e ogni riscrittura e un'altra occasione di perdere la clip.
Quel giorno il video ne ha rese tre invece di sei.

Questa prova tiene insieme le due cose: i banner fuori tema restano fuori,
quelli in tema passano.

    python prove/argomento.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.aggancio import nomina_argomento, _radice          # noqa: E402

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- Devono PASSARE: il banner nomina davvero l'argomento --------------
IN_TEMA = [
    # I due casi veri del 17/09, bocciati per un apostrofo e per un taglio.
    ("Niente ti farebbe cambiare idea? È ego", "l'ego nei dibattiti"),
    ("Vannacci o corteo LGBT? Sei un tifoso", "pensare per tifoserie"),
    # Parenti vere, che devono combaciare.
    ("Il porno ti rimpicciolisce il cervello", "la pornografia"),
    ("Cervello si sviluppa fino a 25 anni", "lo sviluppo del cervello"),
    ("Giudichi le persone da quello che dicono?", "giudicare le persone"),
    ("La Bibbia prova che Dio esiste?", "la Bibbia"),
    ("La preghiera funziona anche senza Dio", "la preghiera"),
    # L'articolo elidato non deve contare, da nessuna delle due parti.
    ("Quanto conta l'allenamento?", "allenamento"),
    ("Parliamo di ego", "dell'ego"),
]
for hook, arg in IN_TEMA:
    prova(f"passa «{hook[:44]}»", nomina_argomento(hook, arg),
          f"argomento «{arg}»")

print()
# --- Devono essere BOCCIATI: il banner parla d'altro --------------------
FUORI_TEMA = [
    # Quello da cui e nata la regola.
    ("Zanzara che depone le uova negli occhi", "Dio e il male sugli animali"),
    ("Il 99% delle persone ha torto", "seguire la massa"),
    ("Se ti amasse, ti tratterebbe meglio", "giudicare le persone"),
    ("La fatica non cambia mai. Cambi tu", "fare cose difficili"),
    # INPS e l'ente della pensione, ma il codice non puo saperlo: e un
    # limite dichiarato, non un guasto. Se un giorno passasse, vorrebbe
    # dire che le radici sono diventate troppo corte.
    ("L'INPS è uno schema Ponzi", "tasse e pensione"),
]
for hook, arg in FUORI_TEMA:
    prova(f"boccia «{hook[:44]}»", not nomina_argomento(hook, arg),
          f"argomento «{arg}»")

print()
# --- Il taglio dev'essere simmetrico -----------------------------------
prova("due parenti danno la stessa radice, comunque siano lunghe",
      _radice("tifoso") == _radice("tifoserie") == _radice("tifoseria"),
      f"{_radice('tifoso')} / {_radice('tifoserie')} / {_radice('tifoseria')}")
prova("l'articolo elidato sparisce", _radice("l'ego") == _radice("ego") == "ego",
      f"{_radice(chr(108)+chr(39)+'ego')!r}")
prova("ma un apostrofo che non e un articolo non taglia la parola",
      _radice("po'") == "po", repr(_radice("po'")))
prova("parole diverse restano diverse",
      _radice("pensione") != _radice("pensare"),
      f"{_radice('pensione')} / {_radice('pensare')}")
prova("un argomento vuoto non boccia niente",
      nomina_argomento("Qualunque cosa", ""))

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

"""Il banner deve riprendere parole che in QUELLA clip si sentono davvero.

Lorenzo, 13/10: «devi migliorare la scelta degli hook perché spesso non
danno contesto alla persona, come se partisse da 0 e terminasse da solo».

Il 17/10, col testo delle dieci clip ferme in coda finalmente in mano, ho
contato quante parole piene di ogni banner si sentono nella sua clip:

    5/6  «Vuoi un fisico bestiale? Stai pensando male»
    4/4  «La tua mente inconscia comanda il 95%»
    4/5  «Perché per un ricco 2.000 euro sono pochi»
    3/4  «Perché i più competenti restano invisibili?»
    3/3  «Giapponese in 30 giorni»
    2/4  «Essere competitivi è davvero una cosa brutta?»
    ---- la riga cade qui da sola ----
    1/4  «Ci metti settimane a prendere una decisione?»
    1/4  «I soldi non fanno la felicità: falso»
    0/3  «Prova a urlare in strada»
    0/5  «Perdere 4 ore sui reel»

Le quattro sotto la riga sono le quattro che non funzionano, e per due
motivi diversi: «Perdere 4 ore sui reel» e «Prova a urlare in strada»
nominano cose che nella clip non si dicono — si dicono prima, nel video
lungo; le due a 1 riprendono la frase tagliata via un attimo prima
dell'inizio della clip, quindi il Reel comincia da una risposta a una
domanda che nessuno ha sentito.

PERCHE' IL CONTROLLO CHE C'ERA NON LE HA FERMATE: nomina_argomento()
confronta il banner con `argomento`, ma l'argomento lo scrive lo stesso
modello che ha scritto il banner, nello stesso respiro. Se si convince che
la clip parli dei reel, scrive «i reel» di qua e «Perdere 4 ore sui reel»
di la, e i due si danno ragione a vicenda. Due cose scritte dalla stessa
penna non si verificano l'una con l'altra.

    python prove/radicato.py
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


# I dieci casi veri, col parlato INTERO della loro clip — prove/clip-15ott.json,
# trascritto il 17/10. La prima versione di questa prova usava riassunti che
# avevo scritto io, e su «Ci metti settimane a prendere una decisione?» dava
# 0/4 dove il testo vero da 1/4: avevo accorciato via proprio la parola che
# decideva. Un banco di prova riscritto a mano misura la mia idea del caso,
# non il caso.
import json
VERI = json.loads((RADICE / "prove" / "clip-15ott.json").read_text())

# Quanti, su quattro, ne prende il controllo. Non e una resa: e il confine
# di cio che un conteggio di parole sa decidere.
ATTESI = {
    "Perdere 4 ore sui reel": (0, 5, False),            # parla di archetipi
    "Prova a urlare in strada": (0, 3, False),          # si dice prima, non qui
    "Perché i più competenti restano invisibili?": (3, 4, True),
    "Ci metti settimane a prendere una decisione?": (1, 4, True),
    "Essere competitivi è davvero una cosa brutta?": (2, 4, True),
    "Vuoi un fisico bestiale? Stai pensando male": (5, 6, True),
    "La tua mente inconscia comanda il 95%": (4, 4, True),
    "Perché per un ricco 2.000 euro sono pochi": (4, 5, True),
    "Giapponese in 30 giorni": (3, 3, True),
    "I soldi non fanno la felicità: falso": (1, 4, True),
}

print("— i dieci casi veri del 15/10, sul parlato intero —")
for clip in VERI:
    hook = clip["hook"]
    va, dentro, piene = A.radicato(hook, clip["testo"])
    atteso = ATTESI[hook]
    verso = "va riscritto" if not va else "passa"
    check(f"{dentro}/{piene} · {verso:<12} · «{hook[:44]}»",
          (dentro, piene, va) == atteso)

print("\n— e prende le due che un conteggio PUO prendere —")
# Le due a zero sono le due in cui il banner nomina una cosa che nella clip
# non si dice mai. Le due a 1 — «Ci metti settimane», «I soldi non fanno la
# felicità» — riprendono la frase tagliata via un attimo prima dell'inizio:
# a queste il conteggio non arriva, e restano a Lorenzo. Dirlo qui serve a
# non raccontarsi che il controllo copra tutto.
bocciate = [c["hook"] for c in VERI if not A.radicato(c["hook"], c["testo"])[0]]
check(f"due su quattro, e sono le due a zero: {bocciate}",
      bocciate == ["Perdere 4 ore sui reel", "Prova a urlare in strada"])

print("\n— il caso che ha dato il nome al controllo —")
# La zanzara del 6/09, ma stavolta misurata sul parlato invece che
# sull'etichetta: la zanzara nella clip si SENTE, quindi questo controllo
# la lascia passare. E' nomina_argomento() che deve bocciarla, perche
# l'argomento e Dio. I due controlli servono a due cose diverse e nessuno
# dei due basta da solo.
ZANZARA = ("Zanzara che depone le uova negli occhi",
           "pensate a quella zanzara che depone le uova negli occhi dei "
           "bambini, che senso ha in un mondo creato da un dio buono")
va, dentro, piene = A.radicato(*ZANZARA)
check(f"radicato la lascia passare: la zanzara si sente ({dentro}/{piene})", va)
check("ed e nomina_argomento che la boccia, sull'argomento vero",
      not A.nomina_argomento(ZANZARA[0], "la fede in Dio"))
# QUESTO E' IL CONTROESEMPIO CHE HA ABBASSATO LA SOGLIA. L'aggancio che
# Lorenzo ha indicato come quello giusto ha UNA parola piena in comune col
# parlato della clip: «dio». Le altre tre generalizzano bene — zanzara
# diventa «animali», «che senso ha» diventa «il male». Con la soglia a 2
# questo controllo bocciava l'aggancio perfetto.
buono = "Perché Dio permette il male sugli animali?"
va, dentro, piene = A.radicato(buono, ZANZARA[1])
check(f"e l'aggancio che Lorenzo voleva passa ({dentro}/{piene}): "
      f"generalizza, non sbaglia clip", va)
check("passa anche da nomina_argomento",
      A.nomina_argomento(buono, "la fede in Dio"))
check("con la soglia a 2 sarebbe stato bocciato — ecco perche e a 1",
      A.RADICI_MINIME == 1 and dentro < 2)

print("\n— i bordi —")
check("parlato vuoto: non lo so, e non lo so non e colpevole",
      A.radicato("Un banner qualunque", "")[0])
vuote_in_fila = " ".join(sorted(A.VUOTE)[:6])
check(f"banner di sole parole vuote: niente da verificare ({vuote_in_fila})",
      A.radicato(vuote_in_fila, "qualunque parlato")[0])
check("ma se una parola piena c'e, va cercata",
      not A.radicato("e che cosa non si fa col giapponese",
                     "qualunque parlato")[0])
check("banner con UNA parola piena: quella deve esserci",
      A.radicato("Il giapponese", "studiare giapponese tutto il giorno")[0]
      and not A.radicato("Il giapponese", "studiare francese")[0])
check("l'apostrofo non spezza il confronto",
      A.radicato("L'ego nei dibattiti",
                 "quando entra in gioco l'ego nei dibattiti si perde")[0])
check("le parenti si riconoscono: «competenti» e «competenza»",
      A.radicato("Le competenze non bastano",
                 "avere competenza non basta se nessuno ti vede")[0])
check("il numero scritto all'italiana resta una parola",
      A.radicato("2.000 euro sono pochi", "per me 2.000 euro sono pochi")[0])

print("\n— e deve essere collegato dove si decide —")
import inspect
from src import brain as B
corpo = inspect.getsource(B.select_clips)
check("select_clips chiama radicato()", "aggancio.radicato(" in corpo)
check("sulla finestra di parlato della clip, non sull'argomento",
      "transcript.finestra(timed_transcript, c.start_seconds" in corpo)
check("senza contorno: le parole di PRIMA non devono fare da alibi",
      "contorno=0.0" in corpo)
check("e senza finestra non si boccia nessuno",
      "if not finestra:" in corpo)
check("il verdetto finisce in fuori_tema, che fa riscrivere e non buttare",
      "fuori_tema[i] = (f\"delle {piene} parole piene" in corpo)
check("e nel log ci va il numero, non un si o un no",
      'parole piene si sentono nella clip' in corpo)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

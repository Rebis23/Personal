"""La clip deve partire dove comincia qualcosa, non dove capita.

Lorenzo, 13/10: «non tracci bene il momento in cui parte, la conversazione
spesso parte a metà, quindi il Reel non impressiona per niente perché non
parte in un momento interessante». Nel log della lavorazione dell'11/10, due
clip su tre partivano cosi:

    ▶️ «i buoni propositi non funzionano»            manca "il motivo per cui"
    ▶️ «prossimi 90 giorni sono fuori da Instagram»  manca "i"

La causa non era la scelta, era come nascevano le opzioni. Il codice offriva
OGNI parola come possibile partenza, scartando solo una lista corta di
legature in cui mancavano perfino gli articoli. Misurato sul parlato vero
dell'11/09: 255 candidate in 26 secondi, tutte frammenti a meta frase. Il
modello scegliera bene fra opzioni sbagliate, e la clip non puo che partire
a meta.

E i due segnali che servivano a riconoscere un inizio erano lì, scritti, e
non venivano usati: PAUSA = 0.45 dichiarata e mai letta, la variabile delle
virgole calcolata e mai guardata.

Adesso una candidata deve avere una PROVA di essere un inizio — muro di
punteggiatura, virgola, o pausa misurata — e dove non ce n'e nessuna non si
offre niente: la clip resta dove l'ha tagliata la selezione, che segue le
frasi. Meglio nessuna riga che la "a" sospesa dell'11/09.

    python prove/attacco.py
"""
import json
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


def parla(*coppie, da=0.0, passo=0.4, stacco=0.0):
    """Parole finte: (testo, pausa_prima). Tempi contigui come li da Whisper."""
    parole, t = [], da
    for testo, pausa in coppie:
        t += pausa
        parole.append({"word": testo, "start": round(t, 3),
                       "end": round(t + passo, 3)})
        t += passo + stacco
    return parole


print("— le tre prove di un inizio —")
MURO = parla(("Basta.", 0), ("Gli", 0), ("obiettivi", 0), ("annuali", 0),
             ("non", 0), ("funzionano", 0))
check("dopo un punto comincia una proposizione",
      A._attacco(MURO, 1, pausa=A.PAUSA) == "muro")
VIRGOLA = parla(("Senti,", 0), ("domani", 0), ("cambia", 0), ("tutto", 0))
check("dopo una virgola e un inizio probabile",
      A._attacco(VIRGOLA, 1, pausa=A.PAUSA) == "virgola")
PAUSA = parla(("parlo", 0), ("poi", 0.9), ("basta", 0), ("davvero", 0))
check("mezzo secondo di silenzio vale come inizio",
      A._attacco(PAUSA, 1, pausa=0.45) == "pausa")
LISCIO = parla(("credere", 0), ("fermamente", 0), ("nel", 0), ("dio", 0))
check("in mezzo a un sintagma non c'e nessuna prova",
      A._attacco(LISCIO, 2, pausa=A.PAUSA) == "")

print("\n— la prima parola della finestra non e un inizio —")
# Era la rete di sicurezza che l'11/09 ha fatto uscire «a credere fermamente
# nel dio cristiano»: la finestra comincia dove l'ha tagliata la selezione,
# non dove comincia una frase.
check("indice 0 non vale, qualunque parola sia",
      A._attacco(MURO, 0, pausa=A.PAUSA) == "")

print("\n— il parlato vero dell'11/09 —")
VERO = json.loads((RADICE / "prove" / "parole-reel-11set.json").read_text())
# 94 parole, 26 secondi, zero punteggiatura e tutti gli stacchi a 0.00s:
# in questo materiale ne' i muri ne' le pause esistono. Restano le svolte.
cand = A.tratti_parlati(VERO, 0.0, 26.0)
check(f"prima erano 255 candidate, adesso sono {len(cand)}", len(cand) == 12)
check("e la «a» sospesa dell'11/09 non c'e piu",
      not any("credere fermamente" in c["testo"] for c in cand))
check("nascono tutte da una svolta del discorso",
      {c["attacco"] for c in cand} == {"svolta"})
# Le tre svolte di quei 26 secondi, lette nel parlato vero:
#   4.7s  «ma fa mi spiegare»        (Whisper per "ma fammi spiegare")
#  17.7s  «però non è per forza un dio»
#  22.1s  «però dà lì a cegliele il cristianesimo»
# Tutte e tre sono punti da cui un Reel puo partire davvero.
check("e partono dai tre punti giusti",
      sorted({round(c["start"], 1) for c in cand}) == [4.7, 17.7, 22.1])

print("\n— dove le prove ci sono, le candidate escono —")
BUONO = parla(("Il", 0), ("punto", 0), ("e", 0), ("questo.", 0),
              ("Gli", 0), ("obiettivi", 0), ("annuali", 0), ("non", 0),
              ("funzionano", 0), ("mai,", 0), ("servono", 0),
              ("priorita", 0), ("molto", 0), ("chiare", 0))
cand = A.tratti_parlati(BUONO, 0.0, 20.0)
check(f"{len(cand)} candidate, non zero", len(cand) > 0)
check("ognuna porta la prova da cui nasce",
      all(c["attacco"] in A.PROVE_APERTURA for c in cand))
# Una legatura in testa si ammette SOLO dopo un punto, dove e l'inizio di
# una frase e non un troncone: «Gli obiettivi annuali non funzionano mai».
def lecita(c):
    primo = A.parole(c["testo"])[0].lower()
    if primo not in A.LEGATURE:
        return True
    return c["attacco"] == "muro" and primo in A.AMMESSE_DOPO_MURO
check("nessuna comincia con una legatura, se non dopo un punto",
      all(lecita(c) for c in cand))
check("«Gli obiettivi annuali non funzionano» dopo il punto c'e",
      any(c["testo"].startswith("Gli obiettivi") for c in cand))
inizi = {c["testo"].split()[0] for c in cand}
check(f"partono da «Gli» (dopo il punto) o «servono» (dopo la virgola): {sorted(inizi)}",
      inizi <= {"Gli", "servono"})
check("una riga non attraversa il punto",
      not any("questo" in c["testo"] and "obiettivi" in c["testo"] for c in cand))

print("\n— i due casi che Lorenzo ha visto —")
# «prossimi 90 giorni sono fuori da Instagram»: "prossimi" e un aggettivo in
# mezzo alla frase. Nessuna lista di parole lo fermerebbe — serve la prova.
INSTAGRAM = parla(("io", 0), ("nei", 0), ("prossimi", 0), ("90", 0),
                  ("giorni", 0), ("sono", 0), ("fuori", 0), ("da", 0),
                  ("Instagram", 0))
cand = A.tratti_parlati(INSTAGRAM, 0.0, 20.0)
check("«prossimi 90 giorni...» non viene piu offerto",
      not any(c["testo"].startswith("prossimi") for c in cand))
# «i buoni propositi non funzionano»: ora "i" e fra le legature.
check("«i» e una legatura", "i" in A.LEGATURE)
check("come «il», «un», «una»",
      {"il", "un", "una", "uno"} <= A.LEGATURE)
PROPOSITI = parla(("perche", 0), ("i", 0), ("buoni", 0), ("propositi", 0),
                  ("non", 0), ("funzionano", 0), ("mai", 0))
cand = A.tratti_parlati(PROPOSITI, 0.0, 20.0)
check("«i buoni propositi non funzionano» non viene piu offerto",
      not any(c["testo"].startswith("i buoni") for c in cand))

print("\n— la pausa si puo misurare, non si indovina —")
# La soglia di 0.45s non e scelta su dati veri: nella trascrizione in
# archivio tutti gli stacchi sono 0.00s. Quindi deve restare regolabile, e
# il log deve dire quante candidate nascono da ogni prova.
SOSPIRO = parla(("dice", 0), ("una", 0), ("cosa", 0), ("Domani", 0.3),
                ("cambia", 0), ("tutto", 0), ("davvero", 0))
check("con soglia 0.45 quello stacco da 0.3s non conta",
      A._attacco(SOSPIRO, 3, pausa=0.45) == "")
check("con soglia 0.25 conta", A._attacco(SOSPIRO, 3, pausa=0.25) == "pausa")
check("e tratti_parlati accetta la soglia da fuori",
      len(A.tratti_parlati(SOSPIRO, 0.0, 20.0, pausa=0.25)) > 0)
check("mentre con quella di oggi quel tratto non offre niente",
      A.tratti_parlati(SOSPIRO, 0.0, 20.0) == [])

print("\n— le prove devono restare collegate —")
import inspect
corpo = inspect.getsource(A.tratti_parlati)
check("tratti_parlati() chiede la prova a _attacco()", "_attacco(" in corpo)
check("e scarta chi non ce l'ha", "if not prova:" in corpo)
check("e la deroga dopo il punto passa da AMMESSE_DOPO_MURO",
      "AMMESSE_DOPO_MURO" in corpo)
check("PAUSA e usata davvero, non solo dichiarata",
      "pausa" in inspect.signature(A.tratti_parlati).parameters
      and inspect.signature(A.tratti_parlati).parameters["pausa"].default == A.PAUSA)
check("le prove sono quelle dichiarate",
      set(A.PROVE_APERTURA) == {"muro", "pausa_forte", "svolta", "virgola", "pausa"})
check("e le forti — quelle che ammettono un articolo in testa — sono due",
      set(A.PROVE_FORTI) == {"muro", "pausa_forte"})

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

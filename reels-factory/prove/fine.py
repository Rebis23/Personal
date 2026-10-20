"""Anche la fine si legge, invece di cercarla nei silenzi.

L'inizio e passato a giudizio il 17/10, su richiesta di Lorenzo: «parlo
direttamente tu, senza utilizzare software esterni». La fine era rimasta a
misura, e si e visto nella prima corsa buona del metodo nuovo. La clip 2 e
uscita di 75 secondi — il tetto esatto — e finiva cosi:

    «...L'internal locus of control, cioe la convinzione proprio cieca del
     fatto che le tue azioni abbiano un impatto reale sugli eventi [...]
     Il locus di controllo È»

Taglio netto su «È». E' lo stesso difetto dell'11/09, per lo stesso
motivo: punti_finali() offre un punto solo dove la voce si ferma almeno
0,28s o dove Whisper mette un segno forte. Su quel video gli stacchi fra
le parole sono quasi tutti zero esatto — il massimo misurato e 0,20s — e i
segni sono 0,6 al minuto. Nessun punto, e la clip va a sbattere contro il
tetto.

    python prove/fine.py
"""
import inspect
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
from src import chiusura as C

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


def parla(frase, da=0.0, passo=0.5, stacco=0.0):
    """Parlato con i tempi attaccati, come lo da Whisper su questo materiale."""
    parole, t = [], da
    for w in frase.split():
        parole.append({"word": w, "start": round(t, 3),
                       "end": round(t + passo, 3)})
        t += passo + stacco
    return parole


print("— il caso vero: senza pause e senza segni —")
# Lo stesso materiale su cui punti_finali() non trova niente.
VERO = parla("Tutti noi conosciamo persone estremamente competenti che sono "
             "invisibili perche sono prive di assertivita e questo le "
             "rende straordinarie ma incapaci di cogliere le opportunita "
             "essere bravi e farsi riconoscere non sono la stessa cosa e "
             "necessitano di due tratti differenti attenzione pero perche "
             "dentro lo studio c'e un altro tratto molto importante che si "
             "chiama agency di cui avevo gia parlato nel video sulla "
             "consapevolezza l'agency non e nient'altro che la sensazione "
             "profonda di essere un agente causale nella tua vita")
punti = C.punti_finali(VERO, 0.0, min_seconds=20.0, max_seconds=75.0)
# UN punto lo trova sempre, ed e il trucco che mi ha ingannato scrivendo
# questa prova: l'ultima parola della finestra non ha una parola dopo,
# quindi le si attribuisce una pausa infinita e passa il controllo. Non e
# un punto di chiusura: e il bordo della finestra, cioe il tetto dei 75
# secondi. In produzione questo diventa «Un solo finale possibile» e la
# clip esce lunga quanto il massimo consentito.
check(f"il metodo a misura trova un punto solo ({len(punti)})", len(punti) == 1)
check("e quel punto e l'ultima parola della finestra, cioe il tetto",
      punti and abs(punti[0]["fine"] - VERO[-1]["end"]) < 0.01)
check("nessun punto nasce da una pausa vera",
      all(p["pausa"] > 9 or p["forte"] for p in punti))

print("\n— il ritrovamento delle ultime parole —")
fine = A.trova_fine_nel_parlato(VERO, "non sono la stessa cosa", 0.0, 1e9)
check(f"si ritrova quando finisce la frase scelta ({fine}s)", fine is not None)
inizio = A.trova_nel_parlato(VERO, "non sono la stessa cosa", 0.0, 1e9)
check("ed e dopo il punto in cui comincia", fine and inizio and fine > inizio)
check("una frase che non c'e torna None",
      A.trova_fine_nel_parlato(VERO, "una frase mai detta qui", 0.0, 1e9) is None)
check("le due funzioni usano la stessa ricerca, non due copie",
      "_cerca(" in inspect.getsource(A.trova_nel_parlato)
      and "_cerca(" in inspect.getsource(A.trova_fine_nel_parlato))

print("\n— i paletti attorno alla scelta —")
corpo = inspect.getsource(C.fine_dal_testo)
check("il minimo resta un minimo", "quando - start < min_seconds" in corpo)
check("e si tiene la fine di prima invece di accorciare troppo",
      "tengo la fine di prima" in corpo)
check("il massimo limita la finestra che il modello legge",
      "ultimo = start + max_seconds" in corpo)
check("con poco parlato non si inventa una fine",
      "len(dentro) < 12" in corpo)
check("NESSUNO vuol dire «non si chiude qui», e torna None",
      'testo.upper().startswith("NESSUN")' in corpo)
check("e il prompt chiede di copiare, non di riscrivere",
      "Copiale parola per parola" in C.DOVE_CHIUDE)
check("dice anche che meglio presto che tardi",
      "Meglio tagliare PRESTO" in C.DOVE_CHIUDE)

print("\n— il collegamento, e la rete sotto —")
principale = (RADICE / "src" / "main.py").read_text(encoding="utf-8")
check("main.py prova prima a leggere", "chiusura.fine_dal_testo(" in principale)
check("e se non esce niente ricade sul metodo a misura",
      "if fine is None:" in principale
      and "chiusura.scegli_finale(" in principale)
check("scegli_finale non e stata buttata: su un video punteggiato bene "
      "costa meno", hasattr(C, "scegli_finale"))
check("l'argomento si calcola una volta sola per tutti e due",
      "argomento = (getattr(pick," in principale)

print("\n— e dove le pause CI SONO, il metodo vecchio funziona ancora —")
CON_PAUSE = parla("Tutti noi conosciamo persone competenti che sono "
                  "invisibili perche sono prive di assertivita.", stacco=0.4)
CON_PAUSE += parla("Essere bravi e farsi riconoscere non sono la stessa cosa.",
                   da=CON_PAUSE[-1]["end"] + 0.6, stacco=0.4)
punti = C.punti_finali(CON_PAUSE, 0.0, min_seconds=5.0, max_seconds=75.0)
check(f"li i punti si trovano ({len(punti)})", len(punti) > 0)


print("\n— e la lunghezza giusta sta scritta, coi numeri veri —")
# I verdetti di Lorenzo sui Reel veri: promossi 28, 32, 46 secondi;
# bocciati per prolissita 62, 71, 73. La finestra non e un'opinione.
check("il prompt dice la finestra", "FRA 25 E 45 SECONDI" in C.DOVE_CHIUDE)
check("e dice perche, coi numeri", "28, 32 e 46" in C.DOVE_CHIUDE
      and "62, 71 e 73" in C.DOVE_CHIUDE)
check("e dice di preferirla anche a una chiusura piu completa",
      "perde chi" in C.DOVE_CHIUDE)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

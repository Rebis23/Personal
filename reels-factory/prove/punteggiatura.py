"""Il codice conta la punteggiatura invece di fidarsi del modello.

Il Reel dell'11/09 si chiudeva a meta frase e Lorenzo l'ha notato: «lascia
in sospeso, poi si ferma improvvisamente». Nel tratto di quel Reel non c'era
UN segno di punteggiatura — 94 parole, zero punti, zero virgole, contate nel
fixture il 28/09. E sentences() spezza sui segni forti «oppure» su una pausa
di 0,75 secondi: senza segni restava solo la pausa, cioe il respiro.

Il 28/09, passando a Whisper grande, avevo scritto che il modello piccolo
«non punteggia». Poi l'ho misurato su 68 secondi dell'audio vero e mi sono
sbagliato: `small` fa 10,6 punti fermi al minuto, `large-v3` ne fa 11,5.
Punteggiano tutti e due.

Il difetto vero era gia scritto nel config di agosto: Whisper «smette di
mettere la punteggiatura per minuti interi». Non assenza — INTERMITTENZA. E
qui sta la parte che conta per questa prova, perche la mia prima versione
guardava solo la media, e la media nasconde esattamente il guasto che ci
interessa: un video da 10 punti al minuto puo avere dentro un buco di due
minuti, e la clip che casca nel buco viene tagliata sul respiro comunque. La
guardia avrebbe detto «va bene» e il Reel sarebbe uscito sbagliato — che e
letteralmente il caso da cui tutto e partito.

Quindi si misurano due cose, e la prova le protegge separatamente: quanti
segni ci sono (il modello sta punteggiando?) e quanto e lungo il tratto
peggiore senza segni (c'e un punto dove chiudere la clip che finira li?).

Le due direzioni dell'errore costano cose diverse: bocciare una trascrizione
buona costa una chiamata a pagamento per niente; promuoverne una con un buco
dentro costa un Reel tagliato sul respiro.

    python prove/punteggiatura.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import punteggiatura as P

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


def parole(testo: str, minuti: float) -> list[dict]:
    """Finge una trascrizione: le parole di `testo` spalmate su `minuti`."""
    pezzi = testo.split()
    passo = (minuti * 60) / max(len(pezzi), 1)
    return [{"word": p, "start": round(i * passo, 3),
             "end": round((i + 1) * passo, 3)}
            for i, p in enumerate(pezzi)]


print("\n— il tratto muto dell'11 settembre, quello del Reel sbagliato —")
VERO = json.load(open(Path(__file__).parent / "parole-reel-11set.json"))
check("in quel tratto la densita e zero", P.densita(VERO) == 0.0)
check("94 parole, nessun segno forte",
      sum(1 for p in VERO for c in p["word"] if c in ".?!") == 0)
check("ed e tutto un vuoto: nessun punto in cui chiudere",
      P.vuoto_massimo(VERO) > 20)

print("\n— l'audio vero di Lorenzo, misurato il 28/09 —")
# I due modelli su 68s della clip 6GSTLqWek5k-1. Numeri veri, non inventati:
# servono da ancora, perche se un domani la soglia venisse alzata sopra questi
# valori la fabbrica pagherebbe Scribe su trascrizioni che vanno bene.
check("large-v3 misurato a 11,5 punti/min passa la soglia", 11.5 >= P.SOGLIA)
check("small misurato a 10,6 punti/min la passa anche lui", 10.6 >= P.SOGLIA)
check("e i loro vuoti (13,0s e 14,5s) stanno sotto il limite",
      max(13.0, 14.5) <= P.VUOTO_MAX)
check("la soglia resta ben sotto il misurato: non boccia il buono",
      P.SOGLIA < 10.6 / 2)

print("\n— parlato normale: passa —")
# Cinque frasi in un minuto: il ritmo di chi spiega qualcosa.
normale = parole(
    "Questa e la prima frase. Poi ne arriva una seconda. La terza pone una "
    "domanda? La quarta risponde. E la quinta chiude il discorso.", 1.0)
check(f"5 punti in un minuto passa ({P.densita(normale):.1f}/min)",
      P.abbastanza(normale) is True)

print("\n— parlato senza punteggiatura: bocciato —")
muto = parole(" ".join(["parola"] * 150), 1.0)
check("zero segni su un minuto viene bocciato", P.abbastanza(muto) is False)
check("e la densita lo dice", P.densita(muto) == 0.0)

print("\n— il caso che costa: un punto solo in cinque minuti —")
# Il modo realistico in cui un modello scarso sbaglia: non zero assoluto,
# ma un segno ogni tanto. Sotto soglia deve cadere comunque.
scarso = parole(" ".join(["parola"] * 700) + " fine.", 5.0)
check(f"0,2 punti/min viene bocciato ({P.densita(scarso):.2f}/min)",
      P.abbastanza(scarso) is False)

print("\n— non bocciare per poco audio —")
# Su dieci secondi un punto in piu o in meno ribalta la densita: bocciare
# qui vuol dire pagare Scribe per una trascrizione che andava bene.
breve = parole("Frase corta senza punto", 0.2)
check("sotto il mezzo minuto si passa e basta", P.abbastanza(breve) is True)
mezzo = parole(" ".join(["parola"] * 80), 0.49)
check("anche se non ha nemmeno un segno", P.abbastanza(mezzo) is True)
# Appena si supera il mezzo minuto il giudizio torna severo.
oltre = parole(" ".join(["parola"] * 100), 0.6)
check("passato il mezzo minuto invece si giudica",
      P.abbastanza(oltre) is False)

print("\n— niente esplode sui casi vuoti —")
check("lista vuota: densita zero", P.densita([]) == 0.0)
check("lista vuota: non abbastanza", P.abbastanza([]) is False)
check("una parola sola non divide per zero", P.densita(
    [{"word": "ciao.", "start": 1.0, "end": 1.0}]) == 0.0)
check("parole senza i campi attesi non esplodono",
      P.densita([{"word": "x"}, {"word": "y"}]) == 0.0)

print("\n— si contano i segni forti, non le virgole —")
virgole = parole("una, due, tre, quattro, cinque, sei, sette, otto,", 1.0)
check("otto virgole non fanno una frase",
      P.abbastanza(virgole) is False)
domande = parole("Davvero? Sicuro? Come? Quando? Perche?", 1.0)
check("i punti di domanda contano", P.abbastanza(domande) is True)
urla = parole("Basta! Adesso! Subito! Ora! Via!", 1.0)
check("i punti esclamativi contano", P.abbastanza(urla) is True)

print("\n— IL CASO CHE LA MEDIA NASCONDE —")
# Un video che punteggia bene per tre minuti e poi smette per due: e il
# guasto vero di Whisper, ed e quello che la prima versione di questa
# guardia lasciava passare.
buono = parole("Prima frase. Seconda frase. Terza frase. Quarta frase. "
               "Quinta frase. Sesta frase. Settima frase. Ottava frase. "
               "Nona frase. Decima frase.", 1.0)
muto_lungo = parole(" ".join(["parola"] * 300), 2.0)
for p in muto_lungo:          # attacca il tratto muto dopo quello buono
    p["start"] += 60; p["end"] += 60
misto = buono + muto_lungo
check(f"la media sembra buona ({P.densita(misto):.1f} punti/min)",
      P.densita(misto) >= P.SOGLIA)
check(f"ma il vuoto e enorme ({P.vuoto_massimo(misto):.0f}s)",
      P.vuoto_massimo(misto) > P.VUOTO_MAX)
check("quindi viene BOCCIATA — la prima versione la promuoveva",
      P.abbastanza(misto) is False)

print("\n— il vuoto si misura anche in coda —")
# Se il parlato finisce senza segno, quel pezzo muto e reale.
coda = parole("Inizio pulito. " + " ".join(["parola"] * 200), 1.5)
check("una coda muta lunga viene contata",
      P.vuoto_massimo(coda) > 60)

print("\n— le soglie si possono spostare da chi chiama —")
check("con soglia 10 il parlato normale non basta piu",
      P.abbastanza(normale, soglia=10.0) is False)
check("e con vuoto_max strettissimo cade anche lui",
      P.abbastanza(normale, vuoto_max=1.0) is False)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

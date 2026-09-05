"""Prova del meccanismo dell'aggancio, sull'esempio vero di Lorenzo."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src import aggancio as A

ok = fallite = 0


def check(nome, cond):
    global ok, fallite
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        fallite += 1
        print("  ROTTO ", nome)


# --- 1. contiguita: si puo solo TAGLIARE -------------------------------------
intero = ("selezionando quale comportamento mi è utile e a quel punto basta "
          "eseguirlo ed è lì che pensare diventa roba da stupidi")
check("il frammento vero e riconosciuto",
      A.e_contiguo("pensare diventa roba da stupidi", intero))
check("un frammento riscritto viene respinto",
      not A.e_contiguo("pensare è roba da stupidi", intero))
check("parole rimescolate: respinte",
      not A.e_contiguo("roba da stupidi pensare", intero))
check("parole aggiunte: respinte",
      not A.e_contiguo("pensare diventa davvero roba da stupidi", intero))
check("frammento piu lungo dell'originale: respinto",
      not A.e_contiguo(intero + " e basta", "pensare"))
check("accenti e maiuscole non contano",
      A.e_contiguo("Pensare Diventa Roba", "pensare diventa roba da stupidi"))

# --- 2. conteggio parole ------------------------------------------------------
check("conta 5 parole", A.quante("pensare diventa roba da stupidi") == 5)
check("la punteggiatura non conta come parola",
      A.quante("meno materia grigia, letteralmente più piccolo") == 6)
check("i numeri contano", A.quante("Nei primi 30 giorni stai peggio") == 6)

# --- 3. trovare l'aggancio nel parlato ----------------------------------------
# Whisper restituisce parole con i tempi, punteggiatura attaccata.
frasi = ("selezionando quale comportamento mi è utile e a quel punto basta "
         "eseguirlo, ed è lì che pensare diventa roba da stupidi. Perché a "
         "quel punto non serve più.").split()
words = [{"word": w, "start": 100.0 + i * 0.4, "end": 100.0 + i * 0.4 + 0.35}
         for i, w in enumerate(frasi)]

t = A.trova_nel_parlato(words, "pensare diventa roba da stupidi", 95.0, 130.0)
atteso = words[[w["word"] for w in words].index("pensare")]["start"]
check(f"trova l'aggancio a {t}s (atteso {atteso}s)", t == atteso)
check("l'apertura si sposta in avanti di 6 secondi", t is not None and t - 100.0 > 5)

check("una frase che non c'e non viene inventata",
      A.trova_nel_parlato(words, "il cervello si rimpicciolisce", 95.0, 130.0) is None)
check("fuori dalla finestra non si cerca",
      A.trova_nel_parlato(words, "pensare diventa roba da stupidi", 0.0, 50.0) is None)

# tolleranza: Whisper si mangia una parola in coda
check("tollera una parola mancante in coda",
      A.trova_nel_parlato(words, "pensare diventa roba da stupidi davvero",
                          95.0, 130.0) == atteso)
# ma non deve agganciarsi su due parole a caso
check("non aggancia su un frammento troppo corto e generico",
      A.trova_nel_parlato(words, "a quel", 95.0, 130.0) is None
      or A.trova_nel_parlato(words, "a quel", 95.0, 130.0) > 0)

# --- 4. gli agganci veri in coda, misurati ------------------------------------
print("\n  Gli agganci delle 5 clip in coda, misurati:")
veri = [
    "Uno studio del 2014 ha misurato il cervello di chi guarda porno con regolarità: meno materia grigia, letteralmente più piccolo",
    "Più contenuti per adulti guardi, meno riesci a dire di no: si rimpicciolisce la corteccia prefrontale, quella che governa autocontrollo e conseguenze a lungo termine",
    "Dopo ogni video per adulti il tuo cervello rilascia prolattina, e la prolattina blocca il testosterone: i tuoi muscoli crescono meno e la voglia di competere sparisce",
    "Nei primi 30 giorni senza porno stai peggio di prima: nebbia mentale, ansia, libido a zero — ecco perché succede",
    "Il cervello smette di svilupparsi a 25 anni: quello studio è falso",
]
for i, h in enumerate(veri, 1):
    n = A.quante(h)
    print(f"    {i}. {n:>2} parole  {'DA ACCORCIARE' if n > A.MAX_PAROLE else 'ok'}")
check("tutti e cinque superano il limite tranne forse l'ultimo",
      sum(1 for h in veri if A.quante(h) > A.MAX_PAROLE) >= 4)

print(f"\n{ok} verdi, {fallite} rotti")
sys.exit(1 if fallite else 0)

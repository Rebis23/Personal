"""Le righe del banner devono uscire dalle parole pronunciate.

Il 5/09 il log diceva, su cinque clip su cinque, "L'aggancio non si ritrova
nel parlato". Era garantito: il banner nasceva come frase scritta dal modello
e la si cercava nel sonoro. Adesso nasce dal sonoro.

Questa prova non chiama nessun modello: verifica la parte meccanica, cioe
che i tratti proposti siano davvero pezzi di parlato, comincino dove
comincia una proposizione, non scavalchino un punto, e portino con se il
secondo giusto.

    python prove/parlato.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import aggancio as a                                  # noqa: E402

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


def parla(frase: str, t0: float = 0.0, passo: float = 0.35) -> list[dict]:
    """Finge Whisper: una parola ogni `passo` secondi."""
    out, t = [], t0
    for w in frase.split():
        out.append({"word": w, "start": round(t, 2), "end": round(t + passo - 0.05, 2)})
        t += passo
    return out


# La frase di Lorenzo, quella su cui ha fatto l'esempio.
LORENZO = ("selezionando quale comportamento mi e utile e a quel punto basta "
           "eseguirlo ed e li che pensare diventa roba da stupidi.")
w = parla(LORENZO)
t = a.tratti_parlati(w, 0, 99)
testi = [x["testo"] for x in t]

prova("da una frase sola escono dei tratti", len(t) > 0, f"{len(t)}")

# LA PROVA CHE CONTA. Lorenzo ha indicato lui quale doveva essere la riga:
# «pensare diventa roba da stupidi». Sta in mezzo a un periodo, senza virgole
# e senza pause. Il primo tentativo tagliava solo sulla punteggiatura e
# offriva quattro opzioni, tutte dentro la premessa — cioe proprio il difetto
# che lui aveva segnalato. Se questa prova torna rossa, il meccanismo non sa
# fare la cosa per cui e stato scritto.
prova("la riga indicata da Lorenzo e fra le opzioni",
      any("pensare diventa roba da stupidi" in x.lower() for x in testi),
      str(testi[:5]))
prova("ogni tratto sta nel limite delle 7 parole",
      all(a.quante(x) <= 7 for x in testi))
prova("ogni tratto e un pezzo consecutivo del parlato",
      all(a.e_contiguo(x, LORENZO) for x in testi))
prova("ogni tratto porta il secondo in cui parte",
      all(isinstance(x["start"], (int, float)) for x in t))
prova("il secondo e quello della sua prima parola",
      all(abs(x["start"] - next(ww["start"] for ww in w
                                if a.parole(ww["word"])[:1] == a.parole(x["testo"])[:1]
                                and abs(ww["start"] - x["start"]) < 0.01)) < 0.01
          for x in t[:5]))

# Il punto fermo e un muro: nessun tratto lo scavalca.
DUE = "Il cervello si rimpicciolisce. Il testosterone crolla e i muscoli non crescono."
t2 = a.tratti_parlati(parla(DUE), 0, 99)
prova("nessun tratto scavalca il punto fermo",
      not any("rimpicciolisce" in x["testo"] and "testosterone" in x["testo"]
              for x in t2))
prova("dopo il punto fermo comincia un tratto",
      any(x["testo"].lower().startswith("il testosterone") for x in t2),
      str([x['testo'] for x in t2][:6]))

# Una pausa lunga vale come punteggiatura.
w3 = parla("questo non funziona") + parla("il problema e un altro", t0=6.0)
t3 = a.tratti_parlati(w3, 0, 99)
prova("dopo una pausa lunga comincia un tratto",
      any(x["testo"].lower().startswith("il problema") for x in t3),
      str([x['testo'] for x in t3]))

# "ma" apre la frase che fa male.
w4 = parla("tutti dicono di pubblicare ogni giorno ma i clienti non arrivano lo stesso")
t4 = a.tratti_parlati(w4, 0, 99)
prova("il «ma» apre un tratto",
      any(x["testo"].lower().startswith("ma i clienti") for x in t4),
      str([x['testo'] for x in t4][:8]))

# La misura vera: quante righe si offrono per una clip di ~50 secondi.
lungo = " ".join([LORENZO, DUE,
                  "tutti dicono di pubblicare ogni giorno, ma i clienti non arrivano.",
                  "il punto e che stai usando lo strumento sbagliato da tre anni.",
                  "instagram e intrattenimento, youtube e ricerca: non si somigliano.",
                  "chi ti cerca su youtube ha gia deciso di spendere dei soldi."])
t5 = a.tratti_parlati(parla(lungo), 0, 999)
prova("per una clip lunga l'elenco resta leggibile", len(t5) <= 220, f"{len(t5)} tratti")
print(f"         ({len(lungo.split())} parole di parlato → {len(t5)} righe fra cui scegliere)")

# La finestra si rispetta: niente che venga da fuori.
t6 = a.tratti_parlati(parla(lungo), 10.0, 20.0)
prova("fuori dalla finestra non si pesca",
      all(9.4 <= x["start"] <= 20.0 for x in t6), str([x["start"] for x in t6][:4]))

print(f"\n{verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

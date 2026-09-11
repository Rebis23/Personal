"""Il Reel deve finire, non spegnersi.

L'11/09 e uscito un Reel che finiva cosi:

    "...mi rendo conto che pero da li a scegliere il cristianesimo, un dio
     specifico con un nome, una storia, delle regole"

e basta. Lorenzo: "lascia in sospeso, poi si ferma improvvisamente. Dev'essere
un discorso completo, finito in se stesso."

Le parole di quel Reel, coi tempi veri, stanno in parole-reel-11set.json:
sono la base di questa prova.

    python prove/finale.py
"""
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from src.chiusura import punti_finali, _pulita, _testo_segnato, SOSPESE  # noqa: E402
from src.transcript import ultima_parola_entro                          # noqa: E402

PAROLE = json.loads((Path(__file__).parent / "parole-reel-11set.json").read_text())
verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- Il Reel vero dell'11/09 -------------------------------------------
punti = punti_finali(PAROLE, 0.0, min_seconds=8.0, max_seconds=30.0)
print(f"\n  punti di chiusura trovati nel Reel dell'11/09: {len(punti)}")
for p in punti:
    print(f"    {p['fine']:5.1f}s  …{p['coda'][-52:]}")
print()

# LA SCOPERTA. Dentro i 26 secondi che sono usciti c'e UN SOLO punto in cui
# si potrebbe chiudere — l'ultimo, cioe proprio quello sbagliato: negli ultimi
# diciotto secondi Lorenzo non prende fiato una volta. Quindi il finale buono
# non era scegliebile dentro i confini che il codice si era dato: stava piu
# avanti, nei 48 secondi ancora disponibili sotto il tetto dei 75. E per
# questo che scegli_finale() guarda tutte le parole del video e non solo
# quelle della clip.
prova("dentro il Reel uscito non c'era nessun finale buono da scegliere",
      len(punti) == 1, f"trovati {len(punti)}")
prova("e l'unico punto disponibile era proprio quello sbagliato",
      punti[0]["coda"].endswith("delle regole"), punti[0]["coda"][-40:])
prova("tutti i finali stanno dentro la durata ammessa",
      all(8.0 <= p["fine"] <= 30.0 for p in punti))
prova("nessun finale cade su una parola che lascia la frase appesa",
      all(_pulita(p["coda"].split()[-1]) not in SOSPESE for p in punti),
      str([p["coda"].split()[-1] for p in punti]))
prova("i finali sono in ordine di tempo",
      [p["fine"] for p in punti] == sorted(p["fine"] for p in punti))
prova("due finali non cadono quasi nello stesso istante",
      all(b["fine"] - a["fine"] >= 0.9 for a, b in zip(punti, punti[1:])))

# Il modello sceglie leggendo il parlato coi numeri dentro: devono esserci
# tutti, in ordine, e il testo dev'essere leggibile.
segnato = _testo_segnato(PAROLE, 0.0, punti)
prova("il parlato mostrato al modello ha tutti i punti numerati",
      all(f"⟦{i + 1}⟧" in segnato for i in range(len(punti))),
      segnato[-90:])
prova("i numeri compaiono in ordine crescente",
      [int(t) for t in __import__("re").findall(r"⟦(\d+)⟧", segnato)]
      == list(range(1, len(punti) + 1)))

# --- Le parole appese ---------------------------------------------------
for parola in ("però", "che", "da", "quindi", "un", "e", "mentre"):
    prova(f"«{parola}» non puo chiudere un Reel", _pulita(parola) in SOSPESE)
prova("«cervello» invece puo chiudere un Reel", _pulita("cervello") not in SOSPESE)

# --- Un parlato con dei respiri dentro (costruito) ----------------------
# Le parole vere del Reel non bastano a provare la scelta fra piu finali:
# non hanno pause. Qui se ne costruisce uno che ne ha, per verificare che
# i punti vengano trovati, diradati e messi in fila.
def parlato(coppie):
    """coppie = [(parola, inizio, fine)] -> lista di parole."""
    return [{"word": w, "start": a, "end": b} for w, a, b in coppie]


COSTRUITO = parlato([
    ("Il", 0.0, 0.3), ("cervello", 0.3, 1.0), ("cambia", 1.0, 1.6),
    ("sempre", 1.6, 2.2),
    ("ma", 10.0, 10.3), ("serve", 10.3, 10.9), ("tempo", 10.9, 11.6),
    ("e", 12.4, 12.6), ("costanza", 12.6, 13.4),
    ("quindi", 14.2, 14.8),
    ("non", 16.0, 16.3), ("mollare", 16.3, 17.0),
])
p2 = punti_finali(COSTRUITO, 0.0, min_seconds=10.0, max_seconds=30.0)
print("\n  finali nel parlato costruito:")
for x in p2:
    print(f"    {x['fine']:5.1f}s  …{x['coda'][-40:]}")
print()
prova("in un parlato con dei respiri si trovano piu finali", len(p2) >= 2,
      f"trovati {len(p2)}")
prova("il finale su «quindi» viene scartato",
      all(not x["coda"].endswith("quindi") for x in p2),
      str([x["coda"][-12:] for x in p2]))
prova("il finale su «mollare» c'e", any(x["coda"].endswith("mollare") for x in p2),
      str([x["coda"][-12:] for x in p2]))
prova("il finale su «tempo» c'e", any(x["coda"].endswith("tempo") for x in p2))

# --- Il taglio al tetto non tranch'a meta una parola --------------------
fine = ultima_parola_entro(PAROLE, 0.0, 20.0)
dentro = [w for w in PAROLE if w["end"] <= 20.0]
prova("il tetto arretra al confine di parola",
      abs(fine - (max(w["end"] for w in dentro) + 0.25)) < 0.01,
      f"{fine:.2f}")
prova("il tetto non allunga mai la clip", fine <= 20.0 + 0.25)
tagliate = [w for w in PAROLE if w["start"] < fine - 0.25 < w["end"]]
prova("nessuna parola resta tagliata in due", not tagliate, str(tagliate))

# --- Una clip che non ha nessun punto buono -----------------------------
prova("senza parole non si inventa un finale",
      punti_finali([], 0.0, min_seconds=20.0, max_seconds=75.0) == [])
prova("se la finestra e tutta fuori durata non si torna niente",
      punti_finali(PAROLE, 0.0, min_seconds=200.0, max_seconds=300.0) == [])

# --- E la clip deve anche COMINCIARE pulita ----------------------------
# Il Reel dell'11/09 apriva su «a credere fermamente nel dio cristiano»: la
# prima cosa che si sente e una "a" appesa. Due cause, tutte e due riparate.
from src.transcript import inizio_pulito                                # noqa: E402
from src.aggancio import tratti_parlati                                 # noqa: E402

attaccate = parlato([("portato", 0.0, 0.90), ("a", 0.90, 1.05),
                     ("credere", 1.05, 1.60), ("fermamente", 1.60, 2.30)])
prova("il margine d'attacco non si porta dentro la parola di prima",
      abs(inizio_pulito(attaccate, 1.05) - 1.05) < 0.01,
      f"{inizio_pulito(attaccate, 1.05):.2f}")

staccate = parlato([("portato", 0.0, 0.30), ("credere", 1.05, 1.60),
                    ("fermamente", 1.60, 2.30)])
prova("ma se c'e silenzio il margine resta",
      abs(inizio_pulito(staccate, 1.05) - 0.90) < 0.01)

# La finestra comincia su una legatura: nessun attacco proposto puo partire
# da li. Prima c'era una rete che la rimetteva dentro d'ufficio.
su_legatura = parlato([("a", 0.0, 0.2), ("credere", 0.2, 0.8),
                       ("fermamente", 0.8, 1.5), ("nel", 1.5, 1.7),
                       ("dio", 1.7, 2.0), ("cristiano", 2.0, 2.7),
                       ("di", 2.7, 2.9), ("proposito", 2.9, 3.6)])
offerti = tratti_parlati(su_legatura, 0.0, 4.0)
prova("nessun attacco comincia con una legatura",
      all(not t["testo"].lower().startswith(("a ", "e ", "di ", "che "))
          for t in offerti),
      str([t["testo"] for t in offerti][:3]))

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

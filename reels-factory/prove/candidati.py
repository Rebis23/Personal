"""candidati(): il codice ritaglia, e nessuna opzione puo essere inventata."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src import aggancio as A

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


VERI = {
    "senza punteggiatura (dove spezza alzava le mani)":
        "Ogni video per adulti che guardi allena il tuo cervello a fare lo spettatore invece del protagonista",
    "coi due punti":
        "I programmi di recupero dalle dipendenze durano 90 giorni: è il tempo che serve alla tua corteccia prefrontale per tornare online",
    "coi due punti e la coda":
        "Ti hanno detto che il cervello smette di svilupparsi a 25 anni: quello studio è falso, i partecipanti avevano al massimo 20 anni",
    "la religiosa":
        "I dati dicono che uno dei modi più efficaci per uscire da una dipendenza è convertirsi, ma non puoi decidere di credere in Dio per smettere di fumare",
}

for nome, h in VERI.items():
    c = A.candidati(h)
    print(f"\n  {nome}: {len(c)} tratti possibili")
    for x in c[:3]:
        print(f"     es. «{x}»")
    check(f"ce ne sono ({nome})", len(c) > 0)
    check("tutti dentro il limite", all(4 <= A.quante(x) <= 7 for x in c))
    check("TUTTI contigui: nessuno puo essere una riscrittura",
          all(A.e_contiguo(x, h) for x in c))
    check("nessun doppione", len({" ".join(A.parole(x)) for x in c}) == len(c))

print()
# il caso che spezza() non risolveva
h = VERI["senza punteggiatura (dove spezza alzava le mani)"]
check("spezza() da sola non ce la faceva", A.spezza(h) is None)
buoni = [x for x in A.candidati(h) if "cervello" in x.lower()]
check(f"fra i tratti ce n'e uno buono: {buoni[:1]}", len(buoni) > 0)

# una frase gia corta non genera niente di piu corto di se stessa
corta = "Nella tomba c'è Maometto, Gesù no"
check("una frase corta produce solo tratti piu corti o niente",
      all(A.quante(x) <= 7 for x in A.candidati(corta)))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

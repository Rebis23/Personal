"""spezza() sui quattro agganci veri usciti dal ritaglio del 4/09 sera."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src import aggancio as A

VERI = [
    "Il tuo cervello diventa letteralmente più piccolo",
    "Ogni video per adulti che guardi allena il tuo cervello a fare lo spettatore invece del protagonista",
    "I programmi di recupero dalle dipendenze durano 90 giorni: è il tempo che serve alla tua corteccia prefrontale per tornare online",
    "Ti hanno detto che il cervello smette di svilupparsi a 25 anni: quello studio è falso, i partecipanti avevano al massimo 20 anni",
]

print("GLI AGGANCI VERI DI STASERA\n")
risolti = 0
for h in VERI:
    n = A.quante(h)
    if n <= A.MAX_PAROLE:
        print(f"  {n:>2}p  già a posto   «{h}»")
        risolti += 1
        continue
    t = A.spezza(h)
    if t is None:
        print(f"  {n:>2}p  NON RISOLTO   «{h[:62]}…»")
    else:
        ok = A.e_contiguo(t, h)
        print(f"  {n:>2}p → {A.quante(t)}p  «{t}»" + ("" if ok else "   ⚠️ NON CONTIGUO"))
        if ok and A.quante(t) <= A.MAX_PAROLE:
            risolti += 1

print(f"\nrisolti {risolti} su {len(VERI)}\n")

print("CASI DI CONTROLLO\n")
ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


# quello che Lorenzo aveva indicato a mano
lor = ("selezionando quale comportamento mi è utile e a quel punto basta "
       "eseguirlo ed è lì che pensare diventa roba da stupidi")
check("una frase senza punteggiatura non viene mutilata", A.spezza(lor) is None)

check("frase già corta: niente da spezzare",
      A.spezza("Nella tomba c'è Maometto, Gesù no") is None
      or A.quante(A.spezza("Nella tomba c'è Maometto, Gesù no")) <= 7)

lungo = ("I dati dicono che uno dei modi più efficaci per uscire da una "
         "dipendenza è convertirsi, ma non puoi decidere di credere in Dio "
         "per smettere di fumare")
t = A.spezza(lungo)
check(f"la religiosa non ha un tratto corto: giusto lasciarla stare (t={t})", t is None)
check("e resta un pezzo dell'originale", t is None or A.e_contiguo(t, lungo))

# nessun risultato deve mai superare il limite o scendere sotto le 3 parole
for h in VERI + [lungo]:
    t = A.spezza(h)
    if t is not None:
        check(f"limite rispettato su «{t[:34]}…»", 3 <= A.quante(t) <= 7)
        check("contiguo", A.e_contiguo(t, h))

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

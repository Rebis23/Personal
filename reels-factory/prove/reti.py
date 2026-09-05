"""Le reti devono scattare PROPRIO quando il modello non risponde bene.

Il 5/09 il modello ha risposto senza graffe. `accorcia` ha fatto "return {}"
lì per lì, e i tre agganci lunghi del video sul porno sono usciti a 17, 16 e
20 parole — il difetto che Lorenzo aveva chiesto di togliere il 4/09. Le due
reti (scegli fra i tratti pronti, taglia sui due punti) erano scritte, erano
provate, ed erano irraggiungibili: stavano dopo il return.

Questa prova prende i tre agganci veri di quel giorno e mette il modello nel
peggiore stato possibile — non risponde affatto — per verificare che escano
comunque corti. Nessuna rete, nessuna chiamata: solo `spezza`.

    python prove/reti.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import aggancio                                      # noqa: E402

# I tre agganci usciti lunghi il 5/09, copiati dal log della run 33962041923.
VERI = {
    3: "Ogni video per adulti che guardi allena il tuo cervello a fare lo "
       "spettatore, non il protagonista",
    4: "Quando smetti col porno i primi 30 giorni stai peggio: nebbia "
       "mentale, ansia, libido a zero",
    5: "Ti hanno detto che il cervello smette di svilupparsi a 25 anni: "
       "quello studio era fatto su ragazzi di vent'anni",
}


class ModelloMuto:
    """Il caso peggiore: ogni chiamata al modello fallisce."""
    class messages:
        @staticmethod
        def create(**_):
            raise RuntimeError("modello non raggiungibile (finto, di proposito)")


aggancio._cliente = lambda: ModelloMuto()

fuori = aggancio.accorcia(dict(VERI), model="finto")

print()
errori = 0
for i, intero in sorted(VERI.items()):
    tagliato = fuori.get(i)
    n_prima = aggancio.quante(intero)
    if tagliato is None:
        print(f"  ✗ {i}: resta a {n_prima} parole — «{intero[:60]}…»")
        errori += 1
        continue
    n = aggancio.quante(tagliato)
    ok = n <= aggancio.MAX_PAROLE and aggancio.e_contiguo(tagliato, intero)
    print(f"  {'✓' if ok else '✗'} {i}: {n_prima}p → {n}p  «{tagliato}»")
    if not ok:
        errori += 1

print(f"\n{len(fuori)}/{len(VERI)} agganci accorciati senza il modello")
if errori:
    print("Con il modello muto le reti devono comunque prendere quello che "
          "ha un punto di rottura.")
sys.exit(1 if len(fuori) == 0 else 0)

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

# QUALI DEVONO FARCELA, dichiarato prima invece che constatato dopo. Le
# reti tagliano dove la frase si spezza da sola; il 5 non ha un punto di
# rottura utile e resta lungo — e un esito previsto dal 4/09, non un
# difetto. Scriverlo qui serve a due cose: il conto non chiama "rotto"
# qualcosa che va come deve, e se un domani il 5 cominciasse a passare
# (o il 3 a fallire) la prova se ne accorge.
ATTESI = {3: True, 4: True, 5: False}


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
    atteso = ATTESI.get(i, True)
    if tagliato is None:
        come_deve = not atteso
        print(f"  {'✓' if come_deve else '✗'} {i}: resta a {n_prima} parole"
              f"{' (previsto: non ha un punto di rottura)' if come_deve else ''}"
              f" — «{intero[:56]}…»")
        if not come_deve:
            errori += 1
        continue
    n = aggancio.quante(tagliato)
    buono = n <= aggancio.MAX_PAROLE and aggancio.e_contiguo(tagliato, intero)
    come_deve = buono == atteso
    print(f"  {'✓' if come_deve else '✗'} {i}: {n_prima}p → {n}p  «{tagliato}»"
          + ("" if atteso else "  (non doveva farcela: guardare)"))
    if not come_deve:
        errori += 1

print(f"\n{len(fuori)}/{len(VERI)} agganci accorciati senza il modello")
if errori:
    print("Con il modello muto le reti devono comunque prendere quello che "
          "ha un punto di rottura.")
# Vedi prove/tutte.py: senza questa riga i controlli non si contano, e
# questo file girava da settimane senza che il suo numero entrasse nel
# totale che riferisco a Lorenzo.
print(f"\n{len(VERI) - errori} verdi, {errori} rotti")
sys.exit(1 if errori else 0)

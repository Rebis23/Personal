"""Una parola per pagina: davvero, non solo nella configurazione.

build_pages ha una fase che RIUNISCE le parole rimaste sole ("felice," dopo
una virgola). Con words_per_screen=1 non deve piu unire niente, ma il codice
non e stato scritto pensando a 1: va provato invece che dato per buono.
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src.remotion_render import build_pages

# Una frase con tutte le trappole: virgole, punto, pause lunghe, parola sola.
testo = ("pensare diventa roba da stupidi, quando sai gia cosa fare. "
         "Allora esegui e basta")
words = []
t = 0.0
for i, w in enumerate(testo.split()):
    pausa = 0.9 if w.endswith(".") else 0.08
    words.append({"word": w, "start": round(t, 3), "end": round(t + 0.30, 3)})
    t += 0.30 + pausa

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


for n in (1, 3):
    pagine = build_pages(words, set(), words_per_screen=n)
    conteggi = [len(p["words"]) for p in pagine]
    print(f"\n  words_per_screen={n} → {len(pagine)} pagine, parole per pagina: {conteggi}")
    if n == 1:
        check("nessuna pagina ha piu di una parola", max(conteggi) == 1)
        check("nessuna parola persa per strada", sum(conteggi) == len(words))
        check("le pagine non si sovrappongono",
              all(pagine[i]["end"] <= pagine[i + 1]["start"] + 1e-6
                  for i in range(len(pagine) - 1)))
        check("ogni pagina dura qualcosa", all(p["end"] > p["start"] for p in pagine))
        mostra = " ".join(p["words"][0]["text"] for p in pagine[:6])
        print(f"    prime sei: {mostra}")
    else:
        check("con 3 il raggruppamento funziona ancora", max(conteggi) <= 3)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

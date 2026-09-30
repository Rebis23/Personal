"""La fila degli actor e il piano dei tentativi devono dire la stessa cosa.

Il 28/09 la fabbrica ha bruciato due tentativi e novanta secondi di pausa
prima di scaricare:

    ⚠️ Apify fallito (actor 1/4, streamers, 1080p): 402 Payment Required
    ⚠️ Apify fallito (actor 2/4, streamers, 720p): 402 Payment Required
    ☁️ Apify run 1OS8gaL5CeQiB0iYX avviato (memo23)...  -> scaricato

Non era il credito: memo23 ha scaricato con lo stesso token trenta secondi
dopo. Era streamers, che ora vuole un abbonamento suo — e stava primo.

La riparazione e banale (cambiare l'ordine), ma c'era una trappola: il piano
dei tentativi nominava STREAMERS a mano, quindi riordinare la fila NON
avrebbe cambiato chi si prova per primo. Due posti che dicono la stessa cosa
sono due posti che prima o poi si contraddicono, e chi legge la fila crede di
aver capito l'ordine. Ora il piano legge PROVIDERS[0].

    python prove/fila_apify.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import apify

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


def nomi(plan):
    return [(a[0].split("~")[0], q) for (a, q) in plan]


print("\n— chi si prova per primo —")
piano = apify._attempts("1080p")
check(f"il primo tentativo e il primo della fila: {nomi(piano)[0]}",
      piano[0][0] is apify.PROVIDERS[0])
check("e non streamers, che dal 28/09 chiede un abbonamento",
      "streamers" not in nomi(piano)[0][0])

print("\n— il piano segue la fila, non un nome scritto a mano —")
# La prova vera: se si cambia l'ordine, il piano deve cambiare con lui.
originale = list(apify.PROVIDERS)
try:
    apify.PROVIDERS[:] = [apify.EPCTEX, apify.MEMO23, apify.STREAMERS]
    check("riordinando la fila cambia anche il primo tentativo",
          apify._attempts("1080p")[0][0] is apify.EPCTEX)
    apify.PROVIDERS[:] = [apify.STREAMERS, apify.MEMO23, apify.EPCTEX]
    check("e cambia di nuovo se si rimette streamers primo",
          apify._attempts("1080p")[0][0] is apify.STREAMERS)
finally:
    apify.PROVIDERS[:] = originale
check("la fila e stata rimessa a posto",
      apify.PROVIDERS[0] is apify.MEMO23)

print("\n— la doppia chance del primo resta —")
piano = apify._attempts("1080p")
check("il primo actor ha due tentativi (1080p poi 720p)",
      piano[0][0] is piano[1][0] and piano[1][1] == "720p")
check("chiedendo 720p non si ripete la stessa qualita",
      [q for (_, q) in apify._attempts("720p")].count("720p")
      == len(apify.PROVIDERS))

print("\n— tutti gli actor restano raggiungibili —")
presenti = {n for (n, _) in nomi(apify._attempts("1080p"))}
check(f"nessuno e stato buttato via: {sorted(presenti)}",
      len(presenti) == len(apify.PROVIDERS))
check("streamers e ancora in fila, piu in basso",
      "streamers" in presenti)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

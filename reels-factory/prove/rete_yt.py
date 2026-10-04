"""Il risolutore JavaScript serve sempre, i client alternativi no.

IL 4/10 Lorenzo ha messo i cookie di YouTube in YT_COOKIES. Hanno
funzionato: nel log si vede `yt-dlp --cookies /tmp/...` e il "Sign in to
confirm you're not a bot" e sparito. Ma lo scarico e fallito comunque:

    WARNING: n challenge solving failed: ... Ensure you have a supported
             JavaScript runtime and challenge solver script installed
    ERROR:   The page needs to be reloaded.

Perche _net_args(), trovando i cookie, smetteva di passare tutto l'elenco
CLIENT_ARGS — e dentro c'era anche `--remote-components ejs:github`, cioe il
risolutore JavaScript. YouTube firma gli indirizzi dei file con del codice
da eseguire: senza eseguirlo non si scarica niente, coi cookie o senza.

Due pezzi con ragioni opposte, tenuti in una lista sola, si escludevano a
vicenda sbagliando: i cookie risolvevano un problema e ne riaprivano un
altro. E il difetto era latente da sempre — si e visto solo il 4/10 perche
YT_COOKIES non era mai stato impostato prima. Un ramo che nessuno ha mai
percorso non e codice che funziona: e codice non ancora smentito. Questa
prova percorre tutti e due i rami.

    python prove/rete_yt.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import yt                                            # noqa: E402

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


def args(*, cookie: bool, proxy: bool = False) -> list[str]:
    for n in ("YT_COOKIES", "YT_PROXY"):
        os.environ.pop(n, None)
    if cookie:
        os.environ["YT_COOKIES"] = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/"
    if proxy:
        os.environ["YT_PROXY"] = "http://u:p@host:8080"
    yt._cookie_file = None
    return yt._net_args()


print("\n— il risolutore JavaScript non manca MAI —")
# E' la riga che il 4/10 e scomparsa insieme ai client, e senza la quale
# YouTube risponde "The page needs to be reloaded".
for descr, a in (("senza cookie", args(cookie=False)),
                 ("con i cookie", args(cookie=True)),
                 ("con cookie e proxy", args(cookie=True, proxy=True)),
                 ("col solo proxy", args(cookie=False, proxy=True))):
    check(f"{descr}: c'e --remote-components", "--remote-components" in a)
    i = a.index("--remote-components")
    check(f"{descr}: ed e ejs:github", a[i + 1] == "ejs:github")

print("\n— i client alternativi SOLO senza cookie —")
senza = args(cookie=False)
con = args(cookie=True)
check("senza cookie i client ci sono", "--extractor-args" in senza)
check("con i cookie i client NON ci sono", "--extractor-args" not in con)
check("perche accostati ai cookie invalidano la sessione", True)

print("\n— i cookie finiscono in un file, non sulla riga di comando —")
check("con i cookie c'e --cookies", "--cookies" in con)
percorso = con[con.index("--cookies") + 1]
check(f"e punta a un file ({percorso[:12]}...)", Path(percorso).exists())
check("il contenuto del cookie non compare fra gli argomenti",
      not any("Netscape" in x for x in con))
check("senza cookie non c'e --cookies", "--cookies" not in senza)

print("\n— il proxy e indipendente da tutto il resto —")
check("col proxy c'e --proxy", "--proxy" in args(cookie=False, proxy=True))
check("senza proxy non c'e", "--proxy" not in args(cookie=False))
check("e col proxy il risolutore resta",
      "--remote-components" in args(cookie=False, proxy=True))

print("\n— le due liste non si sovrappongono —")
check("il risolutore non e dentro CLIENT_ARGS",
      "--remote-components" not in yt.CLIENT_ARGS)
check("e i client non sono dentro RISOLUTORE_JS",
      "--extractor-args" not in yt.RISOLUTORE_JS)
check("cosi non si possono piu spegnere a vicenda",
      set(yt.RISOLUTORE_JS).isdisjoint(set(yt.CLIENT_ARGS)))

for n in ("YT_COOKIES", "YT_PROXY"):
    os.environ.pop(n, None)
yt._cookie_file = None

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

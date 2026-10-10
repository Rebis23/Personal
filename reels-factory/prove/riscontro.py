"""Il riscontro settimanale deve dire qualcosa su cui si possa agire.

I numeri veri dei Reel la fabbrica li legge da settembre, ma li vedeva solo
Claude: finivano nella scheda che il prompt di selezione si rilegge prima di
scegliere le clip. A Lorenzo arrivavano la coda, i banner e i guasti — mai
un risultato. Per tre settimane la domanda «questo Reel ha girato?» aveva
una risposta dentro la fabbrica che nessuna persona leggeva.

Un riscontro che elenca views e si ferma li non serve: quelle le vede anche
su Instagram. Serve la cosa che Instagram non mostra — da quale video LUNGO
sono nati i Reel migliori — perche e la sola di queste informazioni che
cambia una decisione: cosa girare la settimana dopo.

    python prove/riscontro.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import prestazioni as P

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        print(f"  ok   {nome}")
        ok += 1
    else:
        print(f"  ROTTO {nome}")
        rotti += 1


def r(views, salv, giorni, hook, video="AAA"):
    return {"hook": hook, "views": views, "salvataggi": salv, "like": 9,
            "condivisioni": 1, "giorni": giorni, "video_id": video,
            "data": "2026-10-01"}


print("— quando non c'e niente da dire —")
testo = P.riassunto([r(700, 2, 5, "uno"), r(500, 1, 6, "due")])
check("due Reel non fanno una tendenza, e lo dice", "troppo pochi" in testo)
check("non inventa una mediana su due numeri", "Mediana" not in testo)

print("— il riscontro vero —")
RIGHE = [
    r(3815, 26, 26, "Si può diventare più belli senza chirurgia?", "look1"),
    r(2431, 12, 25, "Se sei simmetrico al 100% sei spaventoso", "look1"),
    r(508, 0, 24, "I report di lookmaxxing valgono 200 euro?", "look1"),
    r(2409, 11, 20, "La Chiesa è tra le peggiori istituzioni", "fede1"),
    r(1929, 8, 19, "In Cina nessuno vede Gesù", "fede1"),
    r(1553, 7, 18, "Credi alla resurrezione solo perché è Gesù?", "fede1"),
    r(803, 1, 5, "Perché paghi le tasse per la pensione?", "soldi1"),
    r(652, 0, 4, "Se deleghi, il 70% fatto bene basta", "soldi1"),
    r(336, 0, 11, "Estetica o personalità: chi vince davvero?", "look1"),
    r(185, 1, 10, "Hai notato che tutto è in abbonamento?", "soldi1"),
]
testo = P.riassunto(RIGHE, titoli={"look1": "Lookmaxxing: quanto conta l'aspetto",
                                   "fede1": "Dio esiste? Il dibattito",
                                   "soldi1": "Soldi e libertà"})
print("\n" + testo + "\n")

check("dice quanti Reel ha letto", "10 usciti e maturi" in testo)
check("dice che i Reel di oggi non ci sono", "ultime 24 ore" in testo)
check("il piu visto e in cima ai tre che hanno girato",
      testo.index("senza chirurgia") < testo.index("Sono morti:"))
check("il meno visto e tra i morti",
      testo.index("in abbonamento") > testo.index("Sono morti:"))

print("— i salvataggi, non i like —")
# 26 salvataggi su 3815 views fanno 6.8‰; 12 su 2431 ne fanno 4.9. Un Reel
# molto visto non e automaticamente il piu utile.
check("la classifica dei salvataggi e pesata sulle views",
      "6.8 ‰" in testo)
check("un Reel con zero salvataggi non ci finisce",
      "lookmaxxing valgono 200 euro" not in testo.split("Per video")[0]
      .split("Piu salvati")[1])

print("— due settimane entrambe finite —")
# La prima versione confrontava gli ultimi 7 giorni con i 7 prima, e alla
# prima corsa vera ha detto «604 contro 750, siamo in discesa». Falso per
# costruzione: le views di un Reel di due giorni non sono ancora arrivate,
# quelle di uno di dieci si. Misurava l'eta delle settimane, e la settimana
# in corso perde sempre. Ora il confronto e fra la settimana scorsa (7-13gg)
# e quella prima (14-20gg), entrambe ferme.
SETTIMANE = [r(900, 3, 8, "scorsa alta"), r(700, 2, 9, "scorsa bassa"),
             r(500, 1, 15, "prima alta"), r(300, 1, 16, "prima bassa"),
             r(2000, 9, 1, "uscito ieri, ancora in corsa"),
             r(1800, 8, 2, "uscito due giorni fa")]
sett = P.riassunto(SETTIMANE)
check("confronta la settimana scorsa con quella prima",
      "Settimana scorsa" in sett and "Quella prima" in sett)
check("800 contro 400: in salita", "Siamo in salita" in sett)
check("i Reel di questi giorni restano fuori dal confronto",
      "su 2 Reel" in sett)
check("e la pagina dice perche", "stanno ancora salendo" in sett)
# Il caso che sbagliava: due Reel giovani e deboli non devono bastare a
# dichiarare una discesa.
GIOVANI_DEBOLI = [r(200, 1, 1, "ieri"), r(260, 1, 2, "due giorni"),
                  r(900, 3, 8, "a"), r(950, 3, 10, "b"),
                  r(800, 3, 15, "c"), r(820, 3, 17, "d")]
check("due Reel giovani e bassi non ribaltano una settimana in salita",
      "Siamo in salita" in P.riassunto(GIOVANI_DEBOLI))
magri = P.riassunto([r(900, 2, 8, "uno solo della settimana scorsa"),
                     r(500, 1, 15, "a"), r(400, 1, 16, "b"), r(300, 1, 30, "c")])
check("con un solo Reel nella settimana non azzarda il confronto",
      "Settimana scorsa" not in magri)

print("— la domanda che cambia una decisione —")
check("raggruppa per video di partenza", "Per video di partenza" in testo)
check("il video della fede ha la mediana migliore e sta in cima",
      testo.index("Dio esiste?") < testo.index("Lookmaxxing"))
check("usa il titolo del video, non l'id",
      "fede1" not in testo and "Dio esiste?" in testo)
check("se il titolo manca resta l'id, non una riga vuota",
      "look1" in P.riassunto(RIGHE, titoli={}))
uno = [r(900, 2, 3, "a", "solo"), r(800, 2, 4, "b", "altro"),
       r(700, 2, 5, "c", "terzo")]
check("un Reel per video non e un raggruppamento: la sezione non appare",
      "Per video di partenza" not in P.riassunto(uno))

print("— un Reel di un giorno non e un Reel morto —")
# Alla prima corsa vera, 10/10 ore 00:25, il riscontro diceva questo:
#
#     Sono morti:
#         468 views ·  1 salv ·  4gg  Perché vietarti un'abitudine...
#         385 views ·  1 salv ·  1gg  Hai notato che tutto è in abbonamento?
#         366 views ·  0 salv ·  2gg  Estetica o personalità: chi vince?
#
# Due dei tre "morti" avevano uno e due giorni, e in cima alla stessa pagina
# c'era un Reel di 3 giorni a 3885 views: la classifica per views crude,
# applicata a Reel di eta diversa, finisce per misurare l'eta. 24 ore bastano
# per entrare in tabella accanto al proprio numero di giorni; per una
# condanna no.
GIOVANI = [
    r(3885, 27, 3, "Si può diventare più belli senza chirurgia?", "look1"),
    r(2544, 11, 14, "Destra o sinistra? Stai ragionando da tifoso", "fede1"),
    r(1553, 7, 18, "Credi alla resurrezione solo perché è Gesù?", "fede1"),
    r(965, 9, 20, "Cos'è un archetipo? Guarda Gandalf e Yoda", "arche1"),
    r(803, 1, 12, "Perché paghi le tasse per la pensione?", "soldi1"),
    r(694, 3, 22, "Esistono 12 archetipi, tu ne hai due", "arche1"),
    r(468, 1, 4, "Perché vietarti un'abitudine non funziona mai", "soldi1"),
    r(385, 1, 1, "Hai notato che tutto è in abbonamento?", "soldi1"),
    r(366, 0, 2, "Estetica o personalità: chi vince davvero?", "look1"),
]
testo_g = P.riassunto(GIOVANI)
morti = testo_g.split("Sono morti:")[1].split("Piu salvati")[0]
check("il Reel di ieri non viene dichiarato morto",
      "in abbonamento" not in morti)
check("nemmeno quello di due giorni", "Estetica o personalità" not in morti)
check("nemmeno quello di quattro", "vietarti un'abitudine" not in morti)
check("il peggiore dichiarato ha almeno una settimana",
      "Esistono 12 archetipi" in morti)
check("e la pagina dice su cosa si sta pronunciando",
      "almeno 7 giorni online" in testo_g)
girati = testo_g.split("Hanno girato")[1].split("Sono morti")[0]
check("sul Reel di 3 giorni non si pronuncia ne in un senso ne nell'altro: "
      "3885 views sono molte, ma e presto per chiamarlo un successo",
      "senza chirurgia" not in girati and "senza chirurgia" not in morti)
check("ma i suoi numeri contano nella mediana e fra i piu salvati",
      "senza chirurgia" in testo_g)
check("con cinque Reel giudicabili le due liste non si sovrappongono: "
      "nessun Reel e insieme fra quelli che hanno girato e fra i morti",
      not set(girati.split("\n")) & set(morti.split("\n")) - {""})

print("— un profilo appena partito —")
NUOVI = [r(900, 3, 2, "a"), r(700, 2, 3, "b"), r(500, 1, 1, "c"),
         r(300, 1, 2, "d"), r(200, 0, 3, "e"), r(100, 0, 1, "f")]
nuovo = P.riassunto(NUOVI)
check("senza Reel maturi non tace: dice che i numeri sono in corsa",
      "ancora una settimana" in nuovo)
check("e la classifica la fa comunque, perche e tutto cio che c'e",
      "a" in nuovo and "Mediana" in nuovo)

print("— l'ultimo video girato non deve sembrare il peggiore —")
# soldi1 ha tre Reel: 803 (12gg), 468 (4gg), 385 (1gg). Contando i giovani
# la sua mediana e 468 e finisce in fondo; sui soli Reel giudicabili ha un
# Reel solo e non entra in classifica — che e la risposta onesta.
gruppi = testo_g.split("Per video di partenza")[1]
check("un video con un solo Reel maturo non viene classificato",
      "soldi1" not in gruppi)
check("i video con abbastanza Reel maturi ci sono",
      "fede1" in gruppi and "arche1" in gruppi)

print("— niente divisioni per zero —")
check("un Reel a zero views non fa saltare il riscontro",
      "Mediana" in P.riassunto(RIGHE + [r(0, 0, 3, "mai partito")]))

print("— Instagram muto non e 'pochi Reel' —")
# Il token Instagram e scaduto due volte da quando la fabbrica esiste. Se
# scade di nuovo, raccogli() torna una lista vuota e il riassunto, da solo,
# direbbe «troppo pochi Reel per dire cosa funziona»: una frase tranquilla
# al posto di un guasto. E il modo piu sicuro di non accorgersi di niente.
import io
import contextlib
from datetime import datetime, timedelta, timezone

from src import main as M
from src import state as S

VECCHIO = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
FINTO_STATO = {
    "published": [{"clip_id": f"a-{i}", "video_id": "vid", "hook": f"hook {i}",
                   "ig_media_id": f"m{i}", "published_at": VECCHIO}
                  for i in range(5)],
    "processed_videos": [{"video_id": "vid", "title": "Un video"}],
}
S_load = S.load_state
S.load_state = lambda: FINTO_STATO
M.state_mod.load_state = lambda: FINTO_STATO

P._insights = lambda media_id: {}          # Instagram risponde con errore
fuori = io.StringIO()
with contextlib.redirect_stdout(fuori):
    codice = M.cmd_riscontro()
muto = fuori.getvalue()
check("il job esce rosso quando nessun Reel da numeri", codice == 1)
check("e dice la causa vera: token o permesso", "token scaduto" in muto)
check("non dice 'troppo pochi Reel'", "troppo pochi" not in muto)
check("nomina quanti Reel avrebbero dovuto rispondere", "5 Reel maturi" in muto)

# Meta risponde a tratti: tre Reel su cinque e un riscontro parziale, non un
# guasto. Deve uscire il riscontro, con l'avviso di cosa manca.
P._insights = lambda media_id: ({} if media_id in ("m0", "m1")
                                else {"views": 700, "saved": 3, "likes": 9,
                                      "shares": 1, "reach": 600})
fuori = io.StringIO()
with contextlib.redirect_stdout(fuori):
    codice = M.cmd_riscontro()
parziale = fuori.getvalue()
check("una risposta parziale non fa cadere il report", codice == 0)
check("ma avvisa quanti Reel sono rimasti fuori", "2 Reel su 5" in parziale)
check("e il riscontro c'e comunque", "Mediana" in parziale)
S.load_state = S_load

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

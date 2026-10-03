"""La sentinella deve svegliare solo quando serve davvero.

SEI GIORNI, TRE BLOCCHI, tutti e tre scoperti dal fatto che non uscivano
Reel:

    25/09  credito Anthropic a zero  -> sei corse morte dopo aver scaricato
                                        e trascritto, a pagamento, per niente
    27/09  minuti GitHub esauriti    -> ogni corsa rifiutata in due secondi,
                                        fabbrica ferma due giorni
    30/09  Apify 403 su tutti        -> nessun video nuovo per cinque giorni,
                                        coda a zero il 3 ottobre

Nessun fornitore avvisa prima. Quello che mancava non era un controllo in
piu dentro la lavorazione: era un posto dove la domanda «le chiavi sono
vive?» venisse fatta a freddo, quando non serve.

E una sentinella ha due modi di essere inutile, non uno. Se tace quando una
chiave e morta, non serve a niente. Ma se grida ogni settimana perche Drive
non e configurato e ElevenLabs non serve piu, dopo tre volte non la si
guarda piu — e allora tace anche lei, solo in un modo piu rumoroso. Questa
prova protegge i due lati: cio che serve e rotto FERMA tutto, cio che non
serve resta scritto e non ferma niente.

    python prove/sentinella.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.sentinella import Esito, riassunto                    # noqa: E402

ok = rotti = 0


def check(nome, cond):
    global ok, rotti
    if cond:
        ok += 1
        print("  OK    ", nome)
    else:
        rotti += 1
        print("  ROTTO ", nome)


VIVO = [Esito("Anthropic", True), Esito("Apify", True, "piano FREE"),
        Esito("R2", True), Esito("Instagram", True)]

print("\n— tutto a posto: non sveglia nessuno —")
testo, codice = riassunto(VIVO)
check("esce 0", codice == 0)
check("e lo dice", "Tutto a posto" in testo)
check("nessun ::error:: nel log", "::error::" not in testo)

print("\n— il caso del 30/09: Apify morta —")
testo, codice = riassunto(VIVO[:1] + [
    Esito("Apify", False, "403: token rifiutato o account sospeso"),
    Esito("R2", True), Esito("Instagram", True)])
check("esce 1: la mail di fallimento deve arrivare", codice == 1)
check("nomina il servizio rotto", "Apify" in testo)
check("dice che la fabbrica non puo lavorare",
      "non puo lavorare" in testo)
check("e mette l'annotazione per GitHub", "::error::Apify" in testo)
check("col motivo dentro", "403" in testo)

print("\n— il caso del 25/09: credito Anthropic a zero —")
testo, codice = riassunto([
    Esito("Anthropic", False, "credito esaurito — serve una ricarica"),
    Esito("Apify", True), Esito("R2", True), Esito("Instagram", True)])
check("esce 1", codice == 1)
check("e dice cosa fare, non solo cosa e rotto", "ricarica" in testo)

print("\n— cio che NON serve non ferma la fabbrica —")
# Scribe e la rete dal 28/09, gli Shorts sono un extra: se cadono loro, i
# Reel escono comunque. Fermare tutto per questo sarebbe un falso allarme.
testo, codice = riassunto(VIVO + [
    Esito("ElevenLabs", False, "HTTP 401", serve=False),
    Esito("YouTube", False, "refresh rifiutato", serve=False)])
check("esce 0: i Reel escono comunque", codice == 0)
check("ma resta scritto nel riassunto", "ElevenLabs" in testo)
check("come avviso, non come errore",
      "::warning::" in testo and "::error::" not in testo)
check("e lo dice a parole", "non blocca" in testo)

print("\n— non configurato non e rotto —")
# Se un servizio non configurato contasse come guasto, ci sarebbe una riga
# rossa ogni settimana e la sentinella diventerebbe rumore di fondo.
testo, codice = riassunto(VIVO + [
    Esito("ElevenLabs", None, "non configurato (si usa Whisper)", serve=False),
    Esito("Drive", None, "non configurato", serve=False)])
check("esce 0", codice == 0)
check("dice che tutto e a posto", "Tutto a posto" in testo)
check("e il simbolo non e un errore", "➖" in testo and "❌" not in testo)

print("\n— la riga non si ripete addosso —")
riga = Esito("ElevenLabs", None, "non configurato (si usa Whisper)").riga()
check(f"una sola volta «non configurato»: {riga.strip()}",
      riga.count("non configurato") == 1)

print("\n— un guasto su cio che serve vince su tutto il resto —")
testo, codice = riassunto([
    Esito("Anthropic", True),
    Esito("Apify", False, "403"),
    Esito("YouTube", False, "scaduto", serve=False)])
check("esce 1 per il grave", codice == 1)
check("e il minore non maschera il grave",
      "::error::Apify" in testo and "non puo lavorare" in testo)

print("\n— grave vuol dire rotto E necessario —")
check("rotto e necessario: grave", Esito("x", False, serve=True).grave is True)
check("rotto ma non necessario: non grave",
      Esito("x", False, serve=False).grave is False)
check("non configurato: mai grave",
      Esito("x", None, serve=True).grave is False)
check("vivo: mai grave", Esito("x", True, serve=True).grave is False)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

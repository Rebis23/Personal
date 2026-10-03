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

print("\n— i due errori trovati dalla sentinella alla sua prima corsa —")
# Non sono casi inventati: sono le due righe sbagliate del 3/10 alle 08:20.
import src.sentinella as S                                    # noqa: E402


class FintaRisposta:
    def __init__(self, codice, testo):
        self.status_code = codice
        self.text = testo

    def json(self):
        import json as _j
        try:
            return _j.loads(self.text)
        except Exception:                                      # noqa: BLE001
            return {}


# (a) ElevenLabs: chiave ristretta al solo Speech to Text. Gliel'ho fatta
# creare cosi io: leggere l'abbonamento NON le e permesso, ed e giusto.
VERO_401 = ('{"detail":{"type":"authentication_error","code":"unauthorized",'
            '"message":"The API key you used is missing the permission '
            'user_read to execute this operation."}}')
import os                                                      # noqa: E402
os.environ["ELEVENLABS_API_KEY"] = "finta"
S.requests.get = lambda *a, **k: FintaRisposta(401, VERO_401)
e = S.elevenlabs()
check(f"una chiave ristretta NON e rotta: {e.dettaglio[:40]}", e.vivo is True)
check("e non fa gridare la sentinella", e.grave is False)

# Una chiave davvero invalida invece deve risultare rotta.
S.requests.get = lambda *a, **k: FintaRisposta(401, '{"detail":"invalid api key"}')
check("ma una chiave invalida resta rotta", S.elevenlabs().vivo is False)

# (b) Apify: il 2/10 ho detto "token rifiutato". Era valido, piano FREE — il
# 403 veniva dalla quota per avviare gli actor. Il token vivo non basta.
os.environ["APIFY_TOKEN"] = "finta"
S.requests.get = lambda *a, **k: FintaRisposta(
    200, '{"data":{"plan":{"id":"FREE"}}}')
S._quota_apify = lambda t: 0.0
e = S.apify()
check("token valido + quota a zero = ROTTO", e.vivo is False)
check("e dice che gli actor danno 403 anche col token buono",
      "403" in e.dettaglio and "token valido" in e.dettaglio)
check("ed e grave: senza scarico non si lavora", e.grave is True)

S._quota_apify = lambda t: 4.2
e = S.apify()
check("con quota residua e vivo", e.vivo is True)
check("e la quota si legge nel dettaglio", "4.2" in e.dettaglio)

S._quota_apify = lambda t: None
e = S.apify()
check("quota non leggibile non e un guasto", e.vivo is True)
check("ma viene detto", "non leggibile" in e.dettaglio)

print(f"\n{ok} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

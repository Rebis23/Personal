"""Trascrizione del video: Whisper grande in casa, Scribe se non punteggia.

L'ordine e cambiato tre volte, e ogni volta per un motivo misurato.

Fino al 23/09 era Whisper `small` sul runner. Gratis, e con un difetto: la
punteggiatura andava e veniva. Nel tratto del Reel dell'11 settembre non
c'era UN segno (94 parole, zero punti, zero virgole), e senza segni
sentences() spezzava sulle pause di 0,75 secondi — cioe sui respiri. Da li i
Reel chiusi a meta frase.

Attenzione a non raccontarselo male, come ho fatto io il 28/09 per mezz'ora:
`small` NON e un modello che non punteggia. Misurato su 68 secondi di audio
vero fa 10,6 punti fermi al minuto. Il difetto e l'intermittenza — "smette di
mettere la punteggiatura per minuti interi", era gia scritto nel config di
agosto — e un tratto muto in mezzo a un video puntato bene basta a rovinare
la clip che ci casca dentro.

Dal 23/09 la strada principale e diventata Scribe di ElevenLabs, che
punteggia. Ha risolto i tagli, e costa: 330 crediti al minuto di audio,
~5.800 crediti per un video da 17 minuti, ~$22 al mese di abbonamento.

Dal 28/09 il repo e pubblico e i minuti del runner sono gratis e illimitati.
Quello che rendeva attraente Scribe — la velocita, perche i minuti si
pagavano — non e piu una valuta. Quindi si riprova Whisper, ma col modello
GRANDE: la punteggiatura mancava al modello piccolo, non a Whisper.

E qui la parte che conta: nessuno garantisce che il modello grande punteggi
in modo continuo. Ne la documentazione di faster-whisper ne quella di Groq
promettono niente sulla punteggiatura. Quindi non si spera — si conta.
Whisper large gira gratis, poi punteggiatura.py guarda due cose: quanti segni
ci sono in tutto, e quanto e lungo il tratto peggiore senza nessun segno. La
seconda e quella che serve davvero: una media buona puo nascondere un buco di
due minuti, e la clip che ci finisce dentro viene tagliata sul respiro come
l'11 settembre. Solo se una delle due misure e fuori si paga Scribe.

Misurato il 28/09 su 68s di audio vero: large-v3 fa 11,5 punti/min con un
vuoto massimo di 13,0s; small 10,6 e 14,5s. Il limite del vuoto e 40s, cioe
tre volte piu largo. Su quel pezzo il gratis basta.

Se cadono tutte e due resta comunque la trascrizione di Whisper: un Reel
tagliato male esce, un Reel che non esiste no.

Sostituisce i sottotitoli automatici di YouTube: timing parola-per-parola
(essenziale per il karaoke) e nessuna attesa che YouTube li generi.
"""

from pathlib import Path

from . import punteggiatura, scribe

# Whisper e Scribe chiamano le lingue in modo diverso: "it" contro "ita".
# Tradurre qui evita di dover cambiare tutti i punti che chiamano.
ISO3 = {"it": "ita", "en": "eng", "es": "spa", "fr": "fra", "de": "deu"}


# SCRIBE E' SPENTO. Lorenzo, 17/10: «Ora non utilizzare più le whisper, le
# venlabs, perché vedo che non stai facendo un buon lavoro, parlo
# direttamente tu, senza utilizzare software esterni».
#
# Misurato quello stesso giorno sullo stesso audio — 34 secondi di voce
# vera — Scribe offriva 20 punti di attacco contro i 7 di Whisper, 9,0
# segni al minuto contro 1,8. Quindi era davvero meglio. E non serve lo
# stesso, perche da oggi la clip non parte piu dove lo dice un segnale
# misurato: parte dove lo decide una lettura del testo
# (aggancio.scegli_inizio, regole e correzioni in inizio.md). Pagare per
# avere piu segnali meccanici, quando i segnali meccanici non decidono
# piu niente, sarebbe spendere per un contorno.
#
# Il codice resta e si riaccende mettendo True qui. Le parole di Whisper
# servono ancora a due cose — i sottotitoli e ritrovare nell'audio la
# frase scelta — e per quelle bastano: il TESTO era giusto, erano i tempi
# a non dire niente.
SCRIBE_ACCESO = False


def transcribe_words(video_path: Path, model_size: str = "large-v3",
                     language: str = "it", *,
                     scribe_model: str = scribe.MODELLO,
                     usa_scribe: bool = SCRIBE_ACCESO) -> list[dict]:
    """Ritorna [{word, start, end}] in secondi, stessa forma di parse_json3."""
    parole = _con_whisper(video_path, model_size, language)

    if parole and punteggiatura.abbastanza(parole):
        print(f"  ✅ Punteggiatura sufficiente "
              f"({punteggiatura.densita(parole):.1f} punti/min): "
              f"non servono servizi a pagamento")
        return parole

    if parole:
        # QUALE DELLE DUE MISURE E' FUORI, non una sola a caso. Il 17/10
        # il log ha scritto «Punteggiatura troppo scarsa (13,1 punti/min,
        # serve 2.0)»: 13,1 contro 2,0 e sei volte la soglia, e la riga
        # diceva il contrario di quello che mostrava. A essere fuori era
        # l'altra misura — un tratto lungo senza nemmeno un segno — che
        # nel messaggio non compariva.
        #
        # Una riga di log che si contraddice da sola e peggio di nessuna
        # riga: chi la legge smette di fidarsi di tutte le altre.
        d = punteggiatura.densita(parole)
        vuoto = punteggiatura.vuoto_massimo(parole)
        motivi = []
        if d < punteggiatura.SOGLIA:
            motivi.append(f"{d:.1f} segni/min invece di {punteggiatura.SOGLIA}")
        if vuoto > punteggiatura.VUOTO_MAX:
            motivi.append(f"{vuoto:.0f}s di fila senza un segno "
                          f"(il massimo e {punteggiatura.VUOTO_MAX:.0f})")
        print(f"  ⚠️ Punteggiatura non affidabile: {' e '.join(motivi)}. "
              f"Senza segni si taglierebbe sui respiri")

    if usa_scribe and scribe.disponibile():
        print("  💳 Passo a Scribe, che punteggia")
        da_scribe = scribe.trascrivi(video_path,
                                     language=ISO3.get(language, language),
                                     model=scribe_model)
        if da_scribe:
            return da_scribe
        print("  ↩️ Scribe non ha funzionato")

    if parole:
        print("  ⚠️ Tengo la trascrizione di Whisper cosi com'e: i tagli "
              "saranno meno precisi, ma il Reel esce")
    return parole


def _risorse() -> str:
    """Memoria e disco liberi, in una riga. Serve a sapere, non a decidere.

    Dal 18 al 20/10 tre corse sono morte nello stesso identico punto: la
    riga di onnxruntime che faster-whisper stampa mentre carica il modello.
    GitHub le ha chiuse con «the runner has received a shutdown signal»,
    che dice solo che il runner e sparito, non perche.

    Non e il video: lo stesso identico video e passato al tentativo dopo.
    Non e il tempo: 22:21, 12:39, 11:12. Resta una risorsa che a volte
    manca proprio mentre il modello grande entra in memoria — e questa
    riga, stampata prima e dopo, lo dira invece di farmelo indovinare.
    Un guasto che si ripete senza lasciare un numero e un guasto che si
    ripara a caso.
    """
    pezzi = []
    try:
        import shutil as _sh
        tot, _usato, libero = _sh.disk_usage("/")
        pezzi.append(f"disco {libero / 2**30:.1f} GB liberi su {tot / 2**30:.0f}")
    except OSError:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            info = {r.split(":")[0]: r.split()[1] for r in f if ":" in r}
        disponibile = int(info.get("MemAvailable", 0)) / 2**20
        totale = int(info.get("MemTotal", 0)) / 2**20
        pezzi.append(f"memoria {disponibile:.1f} GB liberi su {totale:.0f}")
    except (OSError, ValueError, IndexError):
        pass
    return " · ".join(pezzi) or "(risorse non leggibili)"


def _con_whisper(video_path: Path, model_size: str, language: str) -> list[dict]:
    from faster_whisper import WhisperModel  # import pigro: pacchetto pesante

    print(f"  🎙️ Trascrizione con Whisper ({model_size}, {language})...")
    print(f"     prima di caricare il modello: {_risorse()}", flush=True)
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"     modello in memoria:          {_risorse()}", flush=True)
        segments, info = model.transcribe(
            str(video_path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )

        words: list[dict] = []
        for segment in segments:
            for w in segment.words or []:
                text = w.word.strip()
                if text:
                    words.append({"word": text,
                                  "start": round(w.start, 3),
                                  "end": round(w.end, 3)})
    except Exception as e:                       # noqa: BLE001
        # Il modello grande pesa ~3 GB: se il disco del runner non ce la fa,
        # o il download cade, non si porta giu tutta la lavorazione — c'e
        # ancora Scribe dopo.
        print(f"  ⚠️ Whisper non ha funzionato: {e}")
        return []

    print(f"  🎙️ Trascrizione completata: {len(words)} parole")
    return words

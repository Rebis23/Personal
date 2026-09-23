"""Scribe: la lettura della risposta, e la rete che regge quando cade.

Lorenzo ha chiesto ElevenLabs per le trascrizioni. Il punto delicato non e
la chiamata — quella o funziona o no — ma due cose che il codice deve fare
bene senza che nessuno se ne accorga:

  1. L'elenco che torna da ElevenLabs NON contiene solo parole: ci sono
     anche gli spazi («spacing») e i rumori riconosciuti («audio_event»),
     ognuno col suo tempo. Se entrassero nella lista diventerebbero parole
     finte: finirebbero nei sottotitoli, nel conteggio, e nella scelta di
     dove far partire e finire le clip.

  2. Quando Scribe non si puo usare — chiave assente, risposta storta, rete
     giu — la lavorazione deve proseguire con Whisper, non fermarsi.

    python prove/scribe.py
"""
import os
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from src.scribe import _parole, disponibile, MODELLO, URL      # noqa: E402
from src.transcribe import ISO3                                # noqa: E402

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


# --- La risposta, nella forma vera documentata da ElevenLabs ------------
RISPOSTA = {
    "language_code": "ita",
    "language_probability": 0.98,
    "text": "Il cervello cambia sempre.",
    "words": [
        {"text": "Il", "type": "word", "start": 0.0, "end": 0.24},
        {"text": " ", "type": "spacing", "start": 0.24, "end": 0.26},
        {"text": "cervello", "type": "word", "start": 0.26, "end": 0.81},
        {"text": " ", "type": "spacing", "start": 0.81, "end": 0.83},
        {"text": "(risata)", "type": "audio_event", "start": 0.83, "end": 1.40},
        {"text": "cambia", "type": "word", "start": 1.40, "end": 1.92},
        {"text": "sempre", "type": "word", "start": 1.92, "end": 2.45},
    ],
}

parole = _parole(RISPOSTA)
print(f"\n  7 voci nella risposta -> {len(parole)} parole tenute:")
for p in parole:
    print(f"    {p['start']:5.2f}-{p['end']:5.2f}  {p['word']}")
print()

prova("gli spazi non diventano parole",
      all(p["word"].strip() for p in parole))
prova("i rumori riconosciuti non diventano parole",
      all("risata" not in p["word"] for p in parole),
      str([p["word"] for p in parole]))
prova("restano solo le quattro parole vere", len(parole) == 4, str(parole))
prova("le parole sono quelle giuste",
      [p["word"] for p in parole] == ["Il", "cervello", "cambia", "sempre"])
prova("i tempi sono numeri, non stringhe",
      all(isinstance(p["start"], float) and isinstance(p["end"], float)
          for p in parole))
prova("ogni parola finisce dopo che e cominciata",
      all(p["end"] > p["start"] for p in parole))
prova("le parole sono in ordine di tempo",
      all(b["start"] >= a["start"] for a, b in zip(parole, parole[1:])))

print()
# La forma dev'essere la stessa di Whisper, altrimenti tutto il resto della
# fabbrica — banner, apertura, chiusura, sottotitoli — non la riconosce.
prova("la forma e quella che si aspetta il resto della fabbrica",
      all(set(p) == {"word", "start", "end"} for p in parole),
      str(set(parole[0])))

print()
# --- I casi storti ------------------------------------------------------
prova("una risposta senza parole non rompe niente", _parole({}) == [])
prova("una risposta con solo spazi da zero parole",
      _parole({"words": [{"text": " ", "type": "spacing",
                          "start": 0, "end": 1}]}) == [])
prova("una parola vuota viene scartata",
      _parole({"words": [{"text": "   ", "type": "word",
                          "start": 0, "end": 1}]}) == [])

print()
# --- La rete: senza chiave non si prova nemmeno -------------------------
prima = os.environ.pop("ELEVENLABS_API_KEY", None)
prova("senza chiave Scribe si dichiara non disponibile", not disponibile())
os.environ["ELEVENLABS_API_KEY"] = "   "
prova("una chiave fatta di spazi non conta", not disponibile())
os.environ["ELEVENLABS_API_KEY"] = "finta"
prova("con una chiave Scribe si dichiara disponibile", disponibile())
if prima is None:
    os.environ.pop("ELEVENLABS_API_KEY", None)
else:
    os.environ["ELEVENLABS_API_KEY"] = prima

print()
# --- Le lingue: Whisper dice "it", ElevenLabs vuole "ita" ---------------
prova("l'italiano viene tradotto per ElevenLabs", ISO3["it"] == "ita")
prova("l'inglese viene tradotto per ElevenLabs", ISO3["en"] == "eng")
prova("una lingua sconosciuta passa com'e", ISO3.get("zz", "zz") == "zz")

print()
prova("l'indirizzo e quello ufficiale",
      URL == "https://api.elevenlabs.io/v1/speech-to-text", URL)
prova("il modello di partenza e scritto una volta sola",
      MODELLO == "scribe_v2", MODELLO)

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

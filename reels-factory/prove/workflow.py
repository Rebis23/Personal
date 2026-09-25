"""I workflow devono essere validi PER GITHUB, non solo come YAML.

Il 25/09 un commento a cui mancava il cancelletto ha rotto il workflow
degli Shorts. La riga era:

    Quante caricarne al giorno sta in config.yaml (shorts.al_giorno): quattro

e il controllo che facevo — yaml.safe_load — diceva verde. Giustamente:
quella riga E' YAML valido, diventa una chiave «Quante caricarne al giorno
sta in config.yaml (shorts.al_giorno)» che vale «quattro». E' GitHub a
rifiutarla, perche in cima a un workflow ci vanno solo certe chiavi.

Il guasto si e visto solo provando a far partire il workflow. Questa prova
lo trova prima, e senza rete: controlla che in cima a ogni workflow ci
siano solo le chiavi che GitHub conosce.

    python prove/workflow.py
"""
import sys
from pathlib import Path

import yaml

RADICE = Path(__file__).resolve().parent.parent.parent
FLUSSI = sorted((RADICE / ".github" / "workflows").glob("*.yml"))

# Le chiavi ammesse in cima a un workflow. `True` e la sorpresa: YAML legge
# «on:» come il booleano vero, non come la stringa "on".
AMMESSE = {"name", "run-name", True, "on", "permissions", "env", "defaults",
           "concurrency", "jobs"}
OBBLIGATORIE = {"jobs"}

verdi = rotti = 0


def prova(nome, condizione, dettaglio=""):
    global verdi, rotti
    if condizione:
        verdi += 1
        print(f"  OK     {nome}")
    else:
        rotti += 1
        print(f"  ROTTO  {nome}  {dettaglio}")


prova("i workflow ci sono", len(FLUSSI) > 0, str(RADICE))
print()

for f in FLUSSI:
    testo = f.read_text(encoding="utf-8")
    try:
        d = yaml.safe_load(testo)
    except yaml.YAMLError as e:
        prova(f"{f.name}: si legge come YAML", False, str(e)[:120])
        continue

    if not isinstance(d, dict):
        prova(f"{f.name}: e una mappa", False, type(d).__name__)
        continue

    intruse = set(d) - AMMESSE
    prova(f"{f.name}: nessuna chiave che GitHub non conosce",
          not intruse,
          "probabile commento senza cancelletto -> " +
          "; ".join(repr(k)[:70] for k in intruse))

    prova(f"{f.name}: ha i jobs", OBBLIGATORIE <= set(d),
          f"chiavi trovate: {sorted(str(k) for k in d)}")

    for nome_job, job in (d.get("jobs") or {}).items():
        if not isinstance(job, dict):
            prova(f"{f.name}: il job {nome_job} e una mappa", False)
            continue
        prova(f"{f.name}: il job {nome_job} sa dove girare",
              "runs-on" in job or "uses" in job,
              f"chiavi: {sorted(job)}")

print()
# La riga vera che ha rotto tutto, tenuta come campione.
ROTTA = ("# in testa va bene\n"
         "Quante caricarne sta in config.yaml (shorts.al_giorno): quattro\n"
         "name: prova\n"
         "jobs:\n  x:\n    runs-on: ubuntu-latest\n")
letta = yaml.safe_load(ROTTA)
prova("la riga del 25/09 e YAML valido (per questo era sfuggita)",
      isinstance(letta, dict))
prova("ma questa prova la riconosce come intrusa",
      bool(set(letta) - AMMESSE),
      str(sorted(str(k) for k in letta)))

print()
# --- Chi lancia la fabbrica deve installare TUTTE le dipendenze ---------
# Il 25/09 il workflow degli Shorts installava tre pacchetti scelti a mano —
# quelli che servono a caricare un video — ed e morto su "No module named
# anthropic". src/main.py importa tutti i moduli in cima, anche quelli che
# quel comando non usa: un elenco curato a mano si rompe ogni volta che
# qualcuno aggiunge un import da un'altra parte.
for f in FLUSSI:
    testo = f.read_text(encoding="utf-8")
    if "src.main" not in testo:
        continue
    prova(f"{f.name}: installa da requirements.txt, non a mano",
          "requirements.txt" in testo,
          "lancia src.main ma si sceglie i pacchetti da solo")

print()
# --- Chi tocca le clip deve ricevere i segreti di R2 --------------------
# Terzo inciampo della stessa famiglia in un'ora: il passo gira, ma
# nell'ambiente gli manca qualcosa che il codice usa. Il 25/09 il workflow
# degli Shorts ha saltato tutte e 37 le clip con «non ricavo l'indirizzo
# ('R2_ACCOUNT_ID')»: i file stanno su R2 e i segreti non arrivavano.
for f in FLUSSI:
    testo = f.read_text(encoding="utf-8")
    tocca_clip = any(c in testo for c in ("src.main shorts",
                                          "src.main publish",
                                          "src.main ingest"))
    if not tocca_clip:
        continue
    prova(f"{f.name}: riceve i segreti di R2",
          "R2_ACCOUNT_ID" in testo and "R2_PUBLIC_BASE_URL" in testo,
          "scarica o carica clip ma non ha le credenziali di R2")

print(f"\n  {verdi} verdi, {rotti} rotti")
sys.exit(1 if rotti else 0)

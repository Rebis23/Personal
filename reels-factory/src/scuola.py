"""La scuola: cosa rende forte un video breve, imparato dai video brevi forti.

Non guarda i Reel di Lorenzo, non chiede una chiave a nessuno e non passa da
servizi a pagamento. Usa yt-dlp sugli elenchi pubblici di YouTube — la
ricerca e la scheda "Shorts" di un canale — che rispondono anche da qui,
dove invece l'estrazione del singolo video viene bloccata. E una distinzione
che vale tutto: per imparare come sono costruiti gli agganci servono i
TITOLI e le VIEWS, e gli elenchi danno esattamente quelli.

Perche gli Shorts e non i Reel: sono lo stesso formato, verticale e sotto il
minuto, con lo stesso pubblico e le stesse regole di aggancio. Gli schemi si
trasferiscono. E gli Shorts sono leggibili senza chiedere niente a nessuno,
mentre per i Reel ogni strada passa da uno scraper a pagamento.

Il punteggio di outlier e il cuore. Un video con 300.000 views su un canale
che ne fa 5.000 di mediana insegna qualcosa: ha funzionato la COSTRUZIONE.
Lo stesso numero su un canale da un milione non insegna niente: ha
funzionato il canale. Senza questo rapporto si finisce a studiare i grossi e
a imparare zero. Il metro e la MEDIANA degli ultimi Shorts di quel canale,
non la media: la media la sposta un solo video esploso, la mediana no.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import time
from pathlib import Path

SCHEDA = Path(__file__).resolve().parent.parent / "nicchia.md"
STORICO = Path(__file__).resolve().parent.parent / "state" / "scuola.json"

# Quanto resta valido un outlier trovato. Sei mesi: gli agganci non cambiano
# ogni settimana, ma nemmeno restano veri per sempre.
GIORNI_VALIDI = 180

# Fra una chiamata e l'altra si respira. YouTube non ama le raffiche, e qui
# non abbiamo nessuna fretta: gira una volta a settimana.
PAUSA = 2.0


class ScuolaError(RuntimeError):
    pass


def _lista(bersaglio: str, *, quanti: int) -> list[dict]:
    """Sfoglia un elenco di YouTube senza scaricare niente.

    `--flat-playlist` si ferma alla scheda dell'elenco: niente chiamate al
    player del singolo video, che e proprio quello che da qui viene rifiutato
    con "Sign in to confirm you're not a bot". Da qui escono titolo, views e
    (nella ricerca) durata e canale: abbastanza per tutta l'analisi."""
    cmd = ["yt-dlp", bersaglio, "--flat-playlist", "--playlist-end", str(quanti),
           "--no-warnings", "--ignore-errors", "-J"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return []
    if p.returncode != 0 and not p.stdout.strip():
        return []
    try:
        return json.loads(p.stdout).get("entries") or []
    except (json.JSONDecodeError, AttributeError):
        return []


# Parole che in italiano sono frequentissime e nelle lingue che gli somigliano
# non esistono: "che" in portoghese e "que", "non" e "nao", "piu" e "mais".
# Bastano loro a separare un canale italiano da uno brasiliano o spagnolo,
# che altrimenti la ricerca di YouTube mescola senza pieta.
ITALIANE = {"che", "non", "piu", "perche", "questo", "questa", "quello", "quella",
            "sono", "gli", "della", "delle", "nella", "nel", "essere", "fare",
            "hai", "puoi", "devi", "tuo", "tua", "cosa", "anche", "ogni",
            "senza", "molto", "sei", "ho", "il", "lo", "una", "dei", "degli",
            "mai", "solo", "tutti", "tutto", "quando", "adesso", "ecco",
            "sulla", "dalla", "dal", "sul", "queste", "quelli", "niente",
            "nessuno", "sempre", "meglio", "davvero", "troppo", "gia", "cosi",
            "pero", "quindi", "invece", "oppure", "allora", "vuoi", "fai",
            "sai", "deve", "puo", "vorrei", "smetti", "smettere",
            # parole piene che nelle lingue vicine si scrivono diverse:
            # "vita" e vida, "soldi" e dinheiro, "lavoro" e trabalho.
            "vita", "soldi", "lavoro", "persone", "mondo", "anni", "giorno",
            "bisogno", "successo", "testa", "figli", "paura", "abitudini",
            "mente", "sbagli", "sbagliato", "vero", "verita"}
# Simmetricamente: parole frequentissime in inglese, spagnolo e portoghese
# che in italiano non esistono. Ce ne vogliono tante perche un titolo e corto
# e una sola parola spia non basta a condannarlo.
ALTRUI = {
    # inglese
    "the", "you", "your", "and", "this", "these", "those", "what", "how",
    "why", "who", "when", "of", "is", "are", "was", "were", "be", "been",
    "have", "has", "will", "would", "can", "could", "should", "about",
    "just", "only", "because", "people", "life", "things", "make", "know",
    "think", "never", "always", "say", "said", "their", "there", "here",
    "she", "we", "us", "my", "but", "if", "then", "than", "out", "down",
    "one", "two", "for", "with", "that", "they", "them", "from", "it",
    "don", "doesn", "didn", "won", "let", "get", "want", "need", "love",
    # spagnolo e portoghese
    "que", "nao", "voce", "mais", "com", "para", "seu", "sua", "isso",
    "muito", "porque", "los", "las", "pero", "mas", "esto", "esta", "este",
    "de", "do", "em", "um", "uma", "por", "quem", "tudo", "nada", "dinheiro",
    "trabalho", "pessoas", "ser", "hacer", "tener", "dice", "hace", "hay",
    "cuando", "donde", "siempre", "nunca", "tambien", "bien", "vida",
}


def _parole(testo: str) -> list[str]:
    import re
    import unicodedata
    piano = unicodedata.normalize("NFD", testo.lower())
    piano = "".join(c for c in piano if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z']+", piano)


def e_italiano(testi: list[str], *, minimo: int = 3) -> bool:
    """Vero se questi testi sono scritti in italiano.

    Si guarda il rapporto, non il conteggio: un canale italiano che mette una
    parola inglese nel titolo resta italiano, uno brasiliano che ne azzecca
    una italiana per caso no.

    `minimo` cambia col materiale. Su una manciata di titoli di un canale si
    puo chiedere tre indizi; su un titolo solo, che di parole ne ha otto, ne
    basta uno — altrimenti si buttano via titoli italianissimi come "La
    lezione da 20.000 dollari che cambiera la tua vita"."""
    it = altro = 0
    for t in testi:
        for w in _parole(t):
            if w in ITALIANE:
                it += 1
            elif w in ALTRUI:
                altro += 1
    return it >= minimo and it > altro


def e_straniero(testo: str) -> bool:
    """Vero solo se il testo e chiaramente di un'altra lingua.

    Serve una domanda diversa da `e_italiano`. Su un canale gia riconosciuto
    italiano, pretendere indizi italiani in OGNI titolo butta via titoli
    italianissimi ma corti — "Il paradosso della scelta" non ha nessuna delle
    parole spia. Qui quindi non si chiede la prova che sia italiano: si
    scarta solo cio che si dichiara straniero."""
    it = altro = 0
    for w in _parole(testo):
        if w in ITALIANE:
            it += 1
        elif w in ALTRUI:
            altro += 1
    return altro >= 2 and altro > it


def canali_della_nicchia(query: list[str], *, per_ricerca: int = 25,
                         massimo: int = 20, escludi: set[str] | None = None) -> list[dict]:
    """Chi pubblica, in italiano, sui temi che ci interessano.

    Si parte dalla ricerca perche e il modo per scoprire canali che non
    conosciamo: una lista scritta a mano invecchierebbe e rifletterebbe solo
    i nostri gusti. Qui la nicchia si ridefinisce da sola ogni settimana.

    La ricerca di YouTube pero non sa stare dentro una lingua: alle domande
    italiane risponde volentieri con canali brasiliani e spagnoli, che sui
    numeri sembrano ottimi e come scuola non valgono niente. Quindi ogni
    canale si porta dietro i titoli con cui e stato trovato, e su quelli si
    decide se tenerlo — prima di spendere una chiamata per spogliarlo."""
    visti: dict[str, dict] = {}
    for q in query:
        entries = _lista(f"ytsearch{per_ricerca}:{q}", quanti=per_ricerca)
        nuovi = 0
        for e in entries:
            cid = e.get("channel_id")
            url = e.get("uploader_url") or e.get("channel_url")
            if not cid or not url or cid in (escludi or ()):
                continue        # dal proprio canale non si impara niente di nuovo
            titolo = (e.get("title") or "").strip()
            if cid in visti:
                visti[cid]["titoli"].append(titolo)
                continue
            visti[cid] = {"id": cid, "url": url, "titoli": [titolo],
                          "nome": e.get("channel") or e.get("uploader") or "?"}
            nuovi += 1
        print(f"   🔎 «{q}»: {len(entries)} risultati, {nuovi} canali nuovi")
        time.sleep(PAUSA)
    if not visti:
        raise ScuolaError(
            "La ricerca su YouTube non ha restituito niente. Di solito e un "
            "blocco temporaneo dell'indirizzo IP del runner: non si insiste, "
            "si riprova al giro dopo.")

    italiani = [c for c in visti.values() if e_italiano(c["titoli"])]
    print(f"   🇮🇹 {len(italiani)} canali su {len(visti)} sono italiani")
    return italiani[:massimo]


VAGLIO = """Ti do dei canali YouTube italiani, ognuno con alcuni titoli suoi. Devo imparare come si costruiscono i video brevi in UNA nicchia precisa: crescita personale, psicologia applicata, mentalita, disciplina, business e imprenditoria, rivolti a un pubblico adulto italiano che vuole migliorare risultati e testa.

Tieni solo i canali che stanno davvero dentro questa nicchia.

Scarta senza pieta: misteri e complotti, storia e archeologia, curiosita, cronaca, intrattenimento generico, gaming, musica, clip di podcast senza tema, notizie, religione, sport, canali di sole citazioni motivazionali doppiate. Un canale che sui numeri va benissimo ma parla di piramidi non mi insegna niente su come si aggancia il mio pubblico.

Rispondi SOLO con gli identificativi tenuti, uno per riga, senza altro testo. Se non ne merita nessuno, rispondi con una riga vuota."""


def vaglia_nicchia(canali: list[dict], *, model: str) -> list[dict]:
    """Toglie i canali che sono italiani ma fuori tema.

    La lingua la riconosce una lista di parole; l'argomento no. Qui serve
    qualcuno che legga: una sola chiamata a Claude, su trenta righe di
    titoli, prima di spendere una chiamata di rete per canale.

    Il tetto di token e largo per un motivo: il modello ragiona prima di
    rispondere, e quel ragionamento consuma il budget. Con un tetto stretto
    tornava una risposta vuota — nessun canale scartato e nessun errore, cioe
    il modo peggiore di fallire. Ora se la risposta arriva monca lo si dice."""
    if not canali:
        return []
    righe = []
    for c in canali:
        campione = " | ".join(dict.fromkeys(c["titoli"]))[:300]
        righe.append(f"{c['id']} :: {c['nome']} :: {campione}")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
        r = client.messages.create(
            model=model, max_tokens=8000, system=VAGLIO,
            messages=[{"role": "user", "content": "\n".join(righe)}],
        )
        testo = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    except Exception as e:                      # noqa: BLE001
        print(f"   ⚠️ vaglio non riuscito ({e}): tengo tutti i canali italiani")
        return canali
    # Si cerca l'identificativo dentro tutta la risposta invece di pretendere
    # una riga pulita: con trenta canali capita che arrivino con un trattino
    # davanti o il nome accanto, e una riga che non combacia esatta buttava
    # via l'intero vaglio.
    scelti = [c for c in canali if c["id"] in testo]
    if not scelti:
        motivo = ("il modello ha finito i token prima di rispondere"
                  if r.stop_reason == "max_tokens" else "non ha tenuto nessuno")
        print(f"   ⚠️ vaglio a vuoto ({motivo}): tengo tutti i canali italiani")
        return canali
    print(f"   🎯 {len(scelti)} canali su {len(canali)} sono davvero della nicchia")
    return scelti


def shorts_del_canale(canale: dict, *, quanti: int = 30) -> list[dict]:
    """Gli Shorts recenti di un canale, dal piu nuovo.

    La scheda Shorts da titolo e views e basta — niente durata, niente
    descrizione. Non e un limite: in questo formato il titolo E l'aggancio,
    ed e su quello che si impara."""
    entries = _lista(canale["url"].rstrip("/") + "/shorts", quanti=quanti)
    fuori = []
    for e in entries:
        views = e.get("view_count")
        titolo = (e.get("title") or "").strip()
        if not titolo or not isinstance(views, int) or views <= 0:
            continue
        fuori.append({
            "id": e.get("id"),
            "titolo": titolo,
            "views": views,
            "canale": canale["nome"],
            "canale_id": canale["id"],
            "url": e.get("url") or f"https://www.youtube.com/shorts/{e.get('id')}",
        })
    return fuori


def outlier(query: list[str], *, model: str, per_ricerca: int = 25,
            scarto_minimo: float = 3.0, canali_max: int = 20,
            shorts_per_canale: int = 30, shorts_minimi: int = 8,
            mediana_minima: int = 500, views_minime: int = 5000,
            per_canale_max: int = 4,
            escludi: set[str] | None = None) -> list[dict]:
    """I video brevi che hanno battuto la mediana del proprio canale.

    Tre filtri, e servono tutti e tre.

    `shorts_minimi`: un canale con cinque Shorts non ha un "normale", ha un
    caso, e ogni scarto calcolato su di lui e rumore.

    `mediana_minima`: su un canale che fa venticinque views a video, il video
    da trecento e dodici volte la mediana — e non ha insegnato niente a
    nessuno, perche trecento persone non sono un pubblico. Sotto una certa
    dimensione il rapporto misura il caso, non la costruzione.

    `views_minime`: e la controprova assoluta. Un moltiplicatore alto su
    numeri piccoli resta un numero piccolo; qui vogliamo video che hanno
    davvero raggiunto qualcuno.

    `per_canale_max` e il quarto, ed e nato da un errore vero. Al primo giro
    completo dieci dei primi tredici outlier erano dello stesso creator, che
    intitola tutto "10 frasi sulla forza", "8 verita sulla solitudine". La
    distillazione ne ha ricavato la legge "il pubblico italiano vuole le
    liste numerate" — che non e una legge della nicchia, e l'abitudine di un
    signore. Con un tetto per canale nessuno puo dettare da solo la scuola."""
    canali = canali_della_nicchia(query, per_ricerca=per_ricerca,
                                  massimo=canali_max * 2, escludi=escludi)
    canali = vaglia_nicchia(canali, model=model)[:canali_max]
    print(f"   📺 {len(canali)} canali da spogliare")

    tutti: list[dict] = []
    for c in canali:
        try:
            s = shorts_del_canale(c, quanti=shorts_per_canale)
        except Exception:                       # noqa: BLE001
            s = []                              # un canale muto non ferma gli altri
        time.sleep(PAUSA)
        if len(s) < shorts_minimi:
            continue
        # La prova del nove sulla lingua si fa qui, sui titoli veri del
        # canale. Alla ricerca in italiano rispondono anche creator italiani
        # che pero pubblicano gli Shorts in inglese per prendere il mondo: il
        # loro aggancio e ottimo e non c'entra niente col pubblico di Lorenzo.
        stranieri = sum(1 for v in s if e_straniero(v["titolo"]))
        if stranieri > len(s) * 0.4:
            print(f"      {c['nome'][:34]:<34} saltato · {stranieri}/{len(s)} "
                  "titoli non italiani")
            continue
        normale = statistics.median(v["views"] for v in s)
        if normale < mediana_minima:
            print(f"      {c['nome'][:34]:<34} saltato · mediana {int(normale):,}"
                  f" sotto le {mediana_minima:,}")
            continue
        for v in s:
            v["scarto"] = round(v["views"] / normale, 1)
            v["mediana_canale"] = int(normale)
        tutti += s
        print(f"      {c['nome'][:34]:<34} {len(s):>3} shorts · mediana {int(normale):>8,}")

    forti = [v for v in tutti
             if v["scarto"] >= scarto_minimo and v["views"] >= views_minime]
    # Anche su un canale italiano capita il titolo in inglese, e da quello si
    # imparerebbe un aggancio che non parla al pubblico di Lorenzo.
    forti = [v for v in forti if not e_straniero(v["titolo"])]
    # Un titolo di due parole non ha una struttura da cui imparare: "Seguimi
    # @tizio" e un invito a seguire, non un aggancio.
    forti = [v for v in forti if len(_parole(v["titolo"])) >= 3]
    forti.sort(key=lambda v: v["scarto"], reverse=True)

    quanti: dict[str, int] = {}
    tenuti = []
    for v in forti:
        n = quanti.get(v["canale_id"], 0)
        if n >= per_canale_max:
            continue
        quanti[v["canale_id"]] = n + 1
        tenuti.append(v)
    if len(tenuti) < len(forti):
        print(f"   ⚖️ {len(forti) - len(tenuti)} scartati per non far dettare "
              f"la scuola a un canale solo (tetto: {per_canale_max} a testa)")
    forti = tenuti
    print(f"   ⭐ {len(forti)} su {len(tutti)} hanno superato di {scarto_minimo}x la "
          f"mediana del loro canale con almeno {views_minime:,} views")
    return forti


def _oggi() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _eta(giorno: str) -> int:
    from datetime import datetime, timezone
    try:
        d = datetime.strptime(giorno, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 10_000
    return (datetime.now(timezone.utc) - d).days


def accumula(nuovi: list[dict], *, per_canale_max: int = 4) -> list[dict]:
    """Somma la vendemmia di oggi a quelle passate e riscrive lo storico.

    La nicchia italiana e piccola: in un giro solo si trovano quindici o venti
    outlier, che bastano appena a distinguere uno schema da una coincidenza.
    Ma i giri sono settimanali, e ogni settimana la ricerca pesca canali un po'
    diversi. Accumulando, dopo un mese la scuola ragiona su ottanta video
    invece che su sedici — e sono video trovati in momenti diversi, quindi
    meno legati a cosa girava quella settimana.

    Il tetto per canale si riapplica sul totale: se non lo facessi, il canale
    che ogni settimana piazza i suoi quattro finirebbe per possedere lo
    storico esattamente come possedeva il primo giro."""
    vecchi = []
    if STORICO.exists():
        try:
            vecchi = json.loads(STORICO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            vecchi = []
    vecchi = [v for v in vecchi if _eta(v.get("visto_il", "")) <= GIORNI_VALIDI]

    per_id = {v["id"]: v for v in vecchi if v.get("id")}
    aggiunti = 0
    for v in nuovi:
        if not v.get("id"):
            continue
        if v["id"] not in per_id:
            aggiunti += 1
        v = dict(v, visto_il=v.get("visto_il") or _oggi())
        per_id[v["id"]] = v                     # il dato fresco vince sul vecchio

    corpus = sorted(per_id.values(), key=lambda v: v["scarto"], reverse=True)
    quanti: dict[str, int] = {}
    tenuti = []
    for v in corpus:
        n = quanti.get(v.get("canale_id", ""), 0)
        if n >= per_canale_max:
            continue
        quanti[v.get("canale_id", "")] = n + 1
        tenuti.append(v)

    STORICO.parent.mkdir(parents=True, exist_ok=True)
    STORICO.write_text(json.dumps(tenuti, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"   📚 storico: {aggiunti} nuovi, {len(tenuti)} video in tutto da "
          f"{len({v.get('canale_id') for v in tenuti})} canali")
    return tenuti


ISTRUZIONI = """Sei un analista di contenuti brevi verticali. Qui sotto trovi \
video brevi italiani di crescita personale, psicologia e mentalita che hanno \
fatto molte piu views della MEDIANA DEL LORO STESSO CANALE. Il campo "scarto" \
dice quante volte hanno superato quella mediana: uno scarto di 20 significa \
che quel video ha fatto venti volte il normale per chi l'ha pubblicato.

E il dato che conta: isola la COSTRUZIONE dalla dimensione del canale. Un \
video con 500.000 views su un canale enorme non insegna niente; uno con \
80.000 su un canale che ne fa 3.000 insegna tutto.

Il tuo compito NON e riassumere. E estrarre gli SCHEMI che si ripetono: le \
regole di costruzione applicabili a un contenuto diverso. \
"Apre nominando una cosa che il pubblico da per certa e la nega" e uno schema. \
"Il video di Tizio sul sonno" non lo e.

Hai i titoli e i numeri — non hai il video. Nel formato breve il titolo e \
quasi sempre l'aggancio stesso, quindi lavora su quello e non inventare \
niente sul montaggio, che non puoi sapere.

Scrivi in italiano un documento markdown con esattamente queste sezioni:

## 1. Schemi di aggancio
Gli schemi ricorrenti nei titoli. Per ognuno: come si riconosce, perche \
funziona, e DUE esempi veri presi da questi dati con il loro scarto.

## 2. Cosa hanno in comune i primi dieci
Le costanti dei dieci con lo scarto piu alto, in confronto agli altri.

## 3. Lunghezza e forma del titolo
Cosa dicono i dati sulla forma: quante parole, domanda o affermazione, \
numeri, nomi propri, seconda persona. Quantifica.

## 4. Parole e costruzioni che ricorrono
Le formulazioni linguistiche che tornano piu spesso nei titoli forti.

## 5. Cosa NON fanno mai
Gli anti-schemi: cosa e assente dai titoli forti ed e invece presente in \
quelli deboli.

Regole:
- Ogni schema deve comparire in ALMENO TRE video diversi DI ALMENO DUE \
CANALI DIVERSI. Un modo di intitolare che usa un creator solo non e uno \
schema della nicchia: e l'abitudine di quel creator, e copiarla significa \
copiare lui. Guarda sempre il campo "canale" prima di dichiarare uno schema.
- Se uno schema ti sembra fortissimo ma vive su un canale solo, mettilo \
comunque, ma dichiaralo per quello che e: "presente solo su X, da trattare \
come ipotesi da provare, non come regola".
- Quantifica ogni volta che puoi.
- Niente preamboli, niente conclusioni: solo il documento."""


def distilla(video: list[dict], *, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    dati = json.dumps([
        {k: v[k] for k in ("titolo", "views", "scarto", "mediana_canale", "canale")}
        for v in video[:120]
    ], ensure_ascii=False, indent=1)
    r = client.messages.create(
        model=model, max_tokens=8000, system=ISTRUZIONI,
        messages=[{"role": "user", "content": f"Ecco i video:\n\n{dati}"}],
    )
    return "".join(b.text for b in r.content
                   if getattr(b, "type", "") == "text").strip()


def scrivi_scheda(video: list[dict], schemi: str, query: list[str]) -> None:
    mediana = statistics.median(v["scarto"] for v in video) if video else 0
    canali = len({v["canale_id"] for v in video})
    eta = [_eta(v.get("visto_il", "")) for v in video if v.get("visto_il")]
    arco = (f" Raccolti nell'arco di {max(eta)} giorni."
            if eta and max(eta) > 7 else "")
    testa = (
        "# La scuola: come sono costruiti i video brevi che sfondano\n\n"
        f"> Estratto automaticamente da **{len(video)} video brevi italiani** di\n"
        f"> {canali} canali diversi, che hanno superato di almeno 3 volte la mediana\n"
        f"> del proprio canale (scarto mediano: {mediana:.1f}x).{arco}\n"
        f"> Filoni cercati: {', '.join(query)}.\n"
        ">\n"
        "> Sono SCHEMI, non esempi da copiare. Il prompt di selezione legge questo\n"
        "> file a ogni lavorazione. Si rigenera da solo, nessuno lo compila a mano.\n\n"
        "---\n\n"
    )
    coda = ["\n\n---\n\n## I venti video da cui viene tutto questo\n",
            "| scarto | views | canale | titolo |",
            "|-------:|------:|--------|--------|"]
    for v in video[:20]:
        coda.append(f"| {v['scarto']}x | {v['views']:,} | {v['canale'][:22]} | {v['titolo'][:64]} |")
    SCHEDA.write_text(testa + schemi + "\n".join(coda) + "\n", encoding="utf-8")

"""Quanta punteggiatura c'e in una trascrizione — e se basta a tagliare bene.

PERCHE ESISTE. Il Reel dell'11/09 si chiudeva a meta frase: «...da li a
scegliere il cristianesimo, un dio specifico con un nome, una storia, delle
regole» e basta. La regola di chiusura funzionava; mancava la materia prima.
sentences() spezza sui segni forti «oppure» su una pausa di 0,75 secondi, e
nel tratto di quel Reel non c'era UN segno: 94 parole, zero punti, zero
virgole (contate il 28/09 nel fixture prove/parole-reel-11set.json). Senza
segni l'unico criterio che restava era la pausa — cioe il respiro.

QUELLO CHE HO CREDUTO E CHE NON E VERO. Il 28/09, passando a Whisper grande,
avevo scritto qui che il modello piccolo «non punteggia». Poi l'ho misurato
sul serio, su 68 secondi dell'audio vero di Lorenzo, e non e cosi: `small`
ha reso 10,6 punti fermi al minuto, `large-v3` 11,5. Tutti e due punteggiano.

Il difetto vero e un altro, ed era gia scritto nel config di agosto: Whisper
«smette di mettere la punteggiatura per minuti interi». Non e assenza, e
INTERMITTENZA. E questo cambia la misura da fare, perche una media per video
nasconde esattamente il guasto che ci interessa: un video che fa 10 punti al
minuto di media puo avere dentro un buco di due minuti senza un segno, e la
clip che casca nel buco viene tagliata sul respiro comunque. La media
passerebbe la guardia e il Reel uscirebbe sbagliato — che e precisamente
quello che e successo l'11 settembre.

Quindi qui si guardano DUE cose: quanti segni ci sono in tutto, e quanto e
lungo il tratto peggiore senza nessun segno. La prima dice se il modello sta
punteggiando; la seconda dice se c'e un punto dove tagliare la clip che
finira proprio li.

MISURATO il 28/09 su 68s di audio vero (clip 6GSTLqWek5k-1):

    modello     punti/min   vuoto piu lungo
    large-v3       11,5          13,0 s
    small          10,6          14,5 s

Su quel pezzo vanno bene tutti e due. `large-v3` vince altrove — ha scritto
«La Chiesa Cattolica» e «cristiano» dove `small` ha perso l'articolo e ha
scritto «cristiana» — e dal 28/09 i minuti del runner sono gratis (repo
pubblico), quindi il modello grande non costa piu niente in cambio.
"""

# Punti fermi al minuto sotto i quali il modello non sta punteggiando affatto.
#
# Misurato: 10-11 al minuto sul parlato vero di Lorenzo, con tutti e due i
# modelli. Il parlato italiano normale viaggia fra le 4 e le 8 frasi al
# minuto. Due e sotto tutto questo e sopra lo zero: non serve precisione,
# serve distinguere «punteggia» da «non punteggia», e quei due casi in
# pratica sono 10 e 0.
SOGLIA = 2.0

# Secondi di parlato senza un punto fermo oltre i quali il tratto e inservibile.
#
# Legato alla durata di una clip, non a un gusto: i Reel stanno fra i 60 e i
# 75 secondi, e servono almeno due punti di taglio possibili per scegliere.
# Con un buco di 40 secondi dentro una clip da 70 non c'e scelta: si taglia
# dove capita. Il 25/09 e capitato per davvero — dentro i 26 secondi
# pubblicati c'era UN solo punto di taglio possibile in tutto.
#
# Misurato: 13-14 secondi sul parlato vero, cioe tre volte sotto il limite.
VUOTO_MAX = 40.0

FORTI = ".?!"


def _minuti(parole: list[dict]) -> float:
    if not parole:
        return 0.0
    return (parole[-1].get("end", 0) - parole[0].get("start", 0)) / 60


def _e_fine(parola: dict) -> bool:
    return any(c in FORTI for c in str(parola.get("word", "")))


def densita(parole: list[dict]) -> float:
    """Punti fermi per minuto di parlato. Zero parole = zero."""
    minuti = _minuti(parole)
    if minuti <= 0:
        return 0.0
    forti = sum(1 for p in parole
                for c in str(p.get("word", ""))
                if c in FORTI)
    return forti / minuti


def vuoto_massimo(parole: list[dict]) -> float:
    """Il tratto piu lungo, in secondi, senza nemmeno un punto fermo.

    Conta anche la coda: se il testo finisce senza segno, quel pezzo senza
    punteggiatura e reale e va misurato come gli altri.
    """
    if not parole:
        return 0.0
    ultimo = parole[0].get("start", 0)
    peggio = 0.0
    for p in parole:
        if _e_fine(p):
            peggio = max(peggio, p.get("end", 0) - ultimo)
            ultimo = p.get("end", 0)
    return max(peggio, parole[-1].get("end", 0) - ultimo)


def abbastanza(parole: list[dict], *, soglia: float = SOGLIA,
               vuoto_max: float = VUOTO_MAX) -> bool:
    """La trascrizione si puo usare per decidere dove tagliare?

    Vanno bene tutte e due le cose: che ci sia punteggiatura, e che non ci
    sia un tratto abbastanza lungo da contenere una clip intera senza un
    punto dove chiuderla.

    Serve un minimo di parlato prima di giudicare: su dieci secondi un punto
    in piu o in meno ribalta la densita, e bocciare una trascrizione buona
    costa una chiamata a pagamento per niente. Sotto il mezzo minuto si passa.
    """
    if not parole:
        return False
    if _minuti(parole) < 0.5:
        return True
    return densita(parole) >= soglia and vuoto_massimo(parole) <= vuoto_max

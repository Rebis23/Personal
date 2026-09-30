"""Quanto aspettare fra un Reel e il successivo, dato il tempo che resta.

IL GUASTO DEL 29/09. Doveva uscire 2 Reel; ne e uscito 1. Nessun errore nel
log, nessuna corsa fallita: il codice ha fatto esattamente quello che c'era
scritto.

I turni di publish sono sette, dalle 07:30 alle 19:30 UTC. Quel giorno
GitHub li ha consegnati cosi:

    18:49  -> pubblica 6GSTLqWek5k-3        (20:49 ora italiana)
    20:08  -> niente
    21:30  -> niente
    23:04  -> niente

Il primo turno della giornata e arrivato con **undici ore** di ritardo. Gli
altri tre sono caduti dopo le 22:00 italiane, fuori dalla finestra di
pubblicazione. Quindi di sette turni, uno solo e atterrato dentro la
finestra — e con la distanza minima fissa a 5 ore, un turno solo puo fare un
Reel solo. Il secondo Reel era diventato impossibile nel momento in cui il
primo e uscito alle 20:49: cinque ore dopo sono l'1:49 di notte.

La distanza di 5 ore era giusta quando il ritmo era 1 Reel al giorno e
serviva solo a impedire che due turni arretrati consegnati insieme
sparassero due Reel nello stesso minuto. A 2 al giorno, con i turni che
arrivano a grappolo la sera, quella stessa regola diventa il tappo.

LA RIPARAZIONE. La distanza non e piu un numero: si calcola da quanto
tempo resta. Se ci sono due Reel da piazzare e tredici ore di finestra, si
sta larghi. Se ne resta uno e c'e un'ora, si pubblica subito — perche
l'alternativa non e "pubblicarlo meglio piu tardi", e non pubblicarlo.

Il limite fisso resta come tetto: non si sta MAI piu larghi di quello, e la
protezione contro i due Reel nello stesso minuto non si perde, perche quando
il tempo che resta e molto la distanza richiesta torna a essere quella
larga.
"""

MINIMO_ASSOLUTO = 0.5   # mezz'ora: due Reel nello stesso minuto non si fanno mai


def distanza_richiesta(*, distanza_piena: float, ora_adesso: int,
                       fine_finestra: int, gia_usciti: int,
                       tetto: int) -> float:
    """Ore da aspettare dall'ultimo Reel, viste le ore che restano.

    `ora_adesso` e `fine_finestra` sono ore italiane intere, come le usa
    ore_pubblicazione nel config.

    Torna sempre almeno MINIMO_ASSOLUTO: la regola serve a distribuire i
    Reel, non a farne uscire due attaccati quando il tempo e finito.
    """
    restano = max(0, tetto - gia_usciti)
    if restano <= 0:
        return distanza_piena

    ore_utili = max(0.0, float(fine_finestra - ora_adesso))
    if ore_utili <= 0:
        # Fuori finestra la distanza non serve: decide il controllo dell'orario.
        return distanza_piena

    # Quanto spazio si puo lasciare fra i Reel che restano, stando dentro la
    # finestra. Con due Reel da piazzare in tre ore: un'ora e mezza a testa.
    spazio = ore_utili / restano
    return max(MINIMO_ASSOLUTO, min(distanza_piena, spazio))

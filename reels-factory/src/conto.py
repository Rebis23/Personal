"""Quanto costa in token una lavorazione — misurato, non stimato.

PERCHE. Dal 25/09 Lorenzo chiede quanto costa un video, e ogni volta gli ho
dato una divisione: «venti dollari hanno coperto tre lavorazioni, quindi
sei-sette dollari l'una». E' aritmetica su un dato solo, e non dice la cosa
che serve per decidere — QUALE chiamata costa. Senza quello, scegliere su
quali chiamate mettere un modello piu economico e tirare a indovinare: si
rischia di spostare le tre che costano un centesimo e lasciare su Opus
l'unica che costa un dollaro.

COME. Ogni risposta dell'API porta con se `usage`. Qui si sommano i token
per nome di chiamata e si traduce in dollari coi prezzi del modello. Niente
stime: se un numero non e stato misurato, non compare.

I prezzi stanno qui perche cambiano con i modelli, non con il codice: quando
Lorenzo cambiera modello, questa tabella e il posto da aggiornare — e se un
modello non c'e, si contano i token e si lasciano stare i dollari, invece di
inventare un prezzo.
"""

from __future__ import annotations

# Dollari per milione di token (ingresso, uscita). Il ragionamento e
# fatturato come uscita: su questi modelli e la voce che pesa.
PREZZI = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


class Conto:
    """Il registratore di cassa di una lavorazione."""

    def __init__(self) -> None:
        # nome chiamata -> [chiamate, token ingresso, token uscita]
        self.voci: dict[str, list[int]] = {}

    def segna(self, nome: str, usage) -> None:
        """Registra l'uso di una risposta. `usage` e response.usage."""
        riga = self.voci.setdefault(nome, [0, 0, 0])
        riga[0] += 1
        riga[1] += int(getattr(usage, "input_tokens", 0) or 0)
        riga[2] += int(getattr(usage, "output_tokens", 0) or 0)

    def dollari(self, nome: str, model: str) -> float | None:
        """Costo di una voce, o None se il prezzo del modello non lo sappiamo."""
        prezzo = PREZZI.get(model)
        if prezzo is None or nome not in self.voci:
            return None
        _, dentro, fuori = self.voci[nome]
        return dentro / 1e6 * prezzo[0] + fuori / 1e6 * prezzo[1]

    def totale(self, model: str) -> float | None:
        if model not in PREZZI:
            return None
        return sum(self.dollari(n, model) or 0.0 for n in self.voci)

    def scheda(self, model: str) -> str:
        """Il riassunto da stampare a fine lavorazione.

        Ordinato dal piu caro: la prima riga e quella su cui vale la pena
        ragionare, e le ultime sono quelle che non vale la pena toccare.
        """
        if not self.voci:
            return "   💰 Nessuna chiamata registrata"
        noto = model in PREZZI
        righe = [f"   💰 Costo della lavorazione ({model})"]
        ordine = sorted(self.voci,
                        key=lambda n: self.dollari(n, model) or 0.0,
                        reverse=True)
        for nome in ordine:
            q, dentro, fuori = self.voci[nome]
            soldi = self.dollari(nome, model)
            coda = f"  ${soldi:.4f}" if soldi is not None else ""
            righe.append(f"      {nome:22} {q:2}x  "
                         f"{dentro:7} in / {fuori:7} out{coda}")
        tot = self.totale(model)
        if tot is not None:
            righe.append(f"      {'TOTALE':22}       ${tot:.3f}")
        elif not noto:
            righe.append(f"      (prezzo di {model} non in tabella: "
                         f"solo token, nessun dollaro inventato)")
        return "\n".join(righe)


# Il conto della lavorazione in corso. Globale di modulo per un motivo
# pratico: le chiamate al modello stanno in sei file diversi e passare un
# parametro attraverso tutte le firme avrebbe voluto dire toccare codice che
# funziona per una cosa che serve solo a misurare. Una riga per chiamata,
# nessun cambio di firma, e se domani si vuole togliere si cancellano quelle
# righe senza ricucire niente.
CORRENTE = Conto()


def segna(nome: str, usage) -> None:
    """Registra l'uso sul conto della lavorazione in corso. Non esplode mai.

    Il conteggio e una comodita, non un pezzo della pipeline: se per qualche
    ragione l'oggetto usage e diverso da come ce lo aspettiamo, si perde la
    misura di quella chiamata e si va avanti. Un Reel non si perde per un
    contatore.
    """
    try:
        CORRENTE.segna(nome, usage)
    except Exception:                                   # noqa: BLE001
        pass


def azzera() -> None:
    """Inizio di una lavorazione nuova: il conto riparte da zero."""
    CORRENTE.voci.clear()


def scheda_corrente(model: str) -> str:
    """La scheda del conto in corso, pronta da stampare."""
    return CORRENTE.scheda(model)

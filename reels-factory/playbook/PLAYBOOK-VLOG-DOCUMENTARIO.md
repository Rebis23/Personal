# Playbook — Vlog documentario («What comes after you've made it?»)

> Ricavato il 26/09/2026 dall'analisi fotogramma per fotogramma di *I found love in Italy as an 8-figure entrepreneur* (Mr. FourToEight, 8:55, 24 fps).
> Materiale di analisi in `~/Downloads/vlog-riferimento-analisi/`: `cuts.json` (137 tagli), `shots.json`, `transcript.json` (parole con timestamp), `sheet_00..04.jpg` (un fotogramma per inquadratura), `spettro.png` (audio + tagli + parlato), `z_*.jpg` (sequenze dense).
> È il fratello del playbook RIFLETTENDO EDIT: quello serve per i long-form parlati, questo per i **vlog di viaggio/vita**, dove comandano musica e voce fuori campo.

---

## 1. L'idea in una riga

Non è un diario di viaggio: è un **saggio personale con le immagini di un viaggio sotto**. La domanda del titolo («cosa viene dopo che ce l'hai fatta?») regge tutto; ogni città è un capitolo che risponde con uno stato d'animo diverso. Le immagini illustrano la voce, la musica decide il ritmo, i momenti ripresi dal vivo spezzano la riflessione e la rendono vera.

## 2. I numeri (misurati, non stimati)

| Misura | Valore |
|---|---|
| Durata | 8:55 |
| Tagli | 137 (138 inquadrature) |
| Inquadratura media / mediana | 3,9 s / 2,3 s |
| Più corta / più lunga | 0,17 s / 43,5 s |
| Transizioni | **solo tagli netti**. Zero dissolvenze, zero effetti. Anche il nero dei cartelli entra ed esce con taglio netto |
| Formato | 16:9 pieno, niente bande nere |

Il ritmo **cambia per sezione**, ed è questa la vera tecnica:

| Sezione | Tempo | Inquadratura media | Cosa succede |
|---|---|---|---|
| Intro pianoforte + titolo | 0:00–0:11 | 2,7 s | domanda del titolo, firma |
| Cold open (trailer) | 0:11–0:44 | **1,2 s** | montaggio a tempo di musica |
| Toscana | 0:44–3:13 | 6–7 s | inquadrature lunghe, voce fuori campo |
| Lago di Garda | 3:13–5:15 | **2,4 s** | voce densa + tante immagini che la illustrano |
| Milano | 5:15–6:18 | 4 s | capitolo cupo, poche immagini lunghe |
| Sardegna | 6:18–8:48 | 8 s | lungo pezzo dal vivo, poi finale |
| Chiusura | 8:48–8:55 | — | 7 s di nero e silenzio |

**Regola**: veloce quando mostri, lento quando rifletti. Il cold open e il Garda sono veloci; Toscana e Sardegna respirano.

## 3. Struttura (la scaletta da copiare)

1. **Gancio sonoro in scena (0:00–0:11).** Lui al pianoforte, inquadratura larga e fissa. I primi 5 secondi hanno **solo l'ambiente**, niente musica. La domanda del titolo esce **una parola alla volta**: «What comes» su nero → «after» sopra il pianoforte → «you've made it?» che si aggiunge in un altro punto dello schermo. Poi il cartello «a documentary by Mr. FourToEight» su nero.
2. **Cold open (0:11–0:44).** Parte la canzone vera e 28 tagli in 33 secondi mostrano **il meglio di tutto il viaggio** (Garda, Sardegna, Toscana, lei, il mare, i piatti, l'acquerello): è il trailer. Si chiude su un'immagine che respira (il tramonto dalla finestra) e sul primo cartello di luogo.
3. **Capitoli per luogo.** Ognuno si apre con un **cartello su nero** di circa 2 secondi (`Tuscany, Italy`, `Lake Garda`, `Milan, Italy`, `Sardinia, Italy`) e ha un suo stato d'animo:
   - Toscana = lentezza, riposo senza sensi di colpa;
   - Garda = colore, sensi, lei che scopre l'Europa;
   - Milano = fine di un capitolo, peso;
   - Sardegna = polarità, ritorno nel corpo, ambizione.
4. **Dentro ogni capitolo si alternano tre registri**, sempre questi:
   - **A. Voce fuori campo + musica** (riflessivo, ~51% del video);
   - **B. Momento dal vivo senza musica** (selfie, room service, tuono, la barca: ~31%);
   - **C. Musica sola** (respiro, paesaggi, cartelli: ~18%).
   Mai due blocchi A lunghi di fila: dopo una riflessione arriva sempre un momento vero (il tuono, il «Room service!», la bestemmia in barca) che la rende credibile.
5. **Finale.** Riprende l'immagine del cold open (la barca), torna la musica, arriva la riflessione più profonda («ricordare chi eri prima che il mondo ti dicesse chi essere»), tagli ogni 3,5 s su gesti quotidiani (le carte, la bandana, lei che lo spinge), poi **7 secondi di nero muto**.

## 4. Musica e sincronizzazioni

### 4.1 Il trucco del pianoforte (la musica nasce dalla scena)
- 0:00–0:05: sul pianoforte si sente solo la stanza.
- **0:05,33: si torna al pianoforte e nello stesso fotogramma entra la prima nota della colonna sonora.** Sembra che la stia suonando lui: la musica di sottofondo nasce dalla scena.
- 0:07: entra il basso. **0:11,00: il taglio sulla barca coincide con l'ingresso pieno della canzone**, il «drop». 0:19,7: entra la voce cantata.
- Da replicare con qualunque strumento suonato in scena (per noi la chitarra): **prima l'ambiente vero, poi la nota della traccia che parte esattamente sul ritorno allo strumento, poi il drop sul primo taglio del trailer.**

### 4.2 Tagli a tempo, ma solo dove conta
Ho misurato ogni taglio contro i colpi percussivi della traccia (separazione armonica/percussiva, finestra ±45 ms):

| Sezione | Tagli sul colpo | Caso puro |
|---|---|---|
| Intro + cold open | **68%** | 35% |
| Toscana | 38% | 35% |
| Garda | 31% | 35% |
| Sardegna / finale | 27% | 35% |

Quindi: **nel trailer si taglia sul colpo** (0:21,29 → 0:22,12 → 0:22,96 → 0:23,79: un taglio ogni 0,83 s, cioè ogni battuta a ~72 bpm, perfettamente regolare). A 0:17,3–0:18,6 ci sono 5 tagli da 0,2–0,3 s: una raffica su un rullante.
**Nelle parti narrate la musica NON detta il taglio**: 57 tagli su 137 cadono addirittura **a metà di una parola**. La voce è uno strato continuo e indipendente; le immagini le scorrono sotto.

### 4.3 La voce fuori campo guida le immagini (sincronia parola → immagine)
Nel Garda il taglio arriva **sulla parola** che l'immagine illustra, con 0–300 ms di anticipo:
- «…got to Lake **Garda**» → strada del Garda (3:38,7)
- «smelled like **lemons**» → cassette di limoni, targa di limoni, limonaia (3:42,7 → 3:46,9)
- «just **boats on the water**» → le barche (4:20,0)
- «kids licking lemon ice. And **Jade**.» → selfie con lei, taglio esattamente su «Jade» (4:23,2)
- «the **world-class food**» → i piatti (4:46,6 e 4:47,8)
- «The elder tells her…» → lei che dipinge (5:54,7)
- «Our final stop» → Sardegna

Regola: **ogni sostantivo concreto della voce ha la sua immagine**, e l'immagine arriva un soffio prima della parola.

### 4.4 Il passaggio voce fuori campo → audio in presa diretta
- La coda della frase fuori campo («…to see what's underneath») **scavalca il taglio** ed entra sul selfie (1:20,7); la musica sparisce, restano vento e tuono, e lui parla in camera («You hear that lightning and thunder?»). È un **L-cut**: l'audio del pensiero finisce sopra l'immagine del momento reale.
- «Room service!» (2:27,6) arriva nello stesso fotogramma del taglio sulla camera: la musica si interrompe di colpo e si passa al parlato.
- In barca (6:50–8:00) il parlato in presa diretta attraversa i tagli e le schiaffate di camera: l'audio non si interrompe mai, anche quando l'immagine salta.
- Dentro la voce fuori campo del Garda spunta una battuta dal vivo («It's so good. I want this so bad», 4:06,8): **il suono vero di una clip sopra il racconto**, per un secondo.

### 4.5 La musica si spegne per il vero, si riaccende per il pensiero
Dallo spettrogramma (`spettro.png`):
- musica ON sotto la voce: 0:44–1:21, 1:58–2:27, 3:38–5:03, 5:15–6:05, 8:00–8:48;
- musica OFF, solo presa diretta: 1:21–1:58 (tuono), 2:27–3:10 (room service), 6:50–8:00 (barca);
- musica SOLA (respiro): 5:03–5:15, 6:05–6:18, 6:41–6:50 (canzone con voce cantata), cartelli.
- Sotto la voce, fra una frase e l'altra, restano **1–2 secondi di sola musica**: la voce non è mai continua, respira.
- Tracce: una canzone con voce cantata per l'apertura, tappeti strumentali calmi (pianoforte/archi) sotto la voce, un tappeto con basso più scuro per Milano, un altro più luminoso per il finale (~112 bpm). **Ogni capitolo ha la sua traccia.**

## 5. Parole a schermo

- **Font**: serif classico tipo Times New Roman, regolare (non corsivo, non grassetto), bianco, senza riquadro, ombra appena percettibile.
- **Dimensione**: piccola. A 360p l'altezza del testo è ~8 px → a 1080p **circa 26–30 px**. Deve sembrare un libro, non un reel.
- **Sottotitoli su TUTTO il parlato** (voce fuori campo e presa diretta), centrati a ~90% dell'altezza, **2–6 parole per volta**, a pezzi di frase («lemon ice, and Jade.»). Minuscole, punteggiatura normale; le parolacce sono scritte a metà («Jade's f— I don't»).
- **Titolo d'apertura**: una parola o due per volta, in punti diversi dello schermo, che **si aggiungono** senza cancellare le precedenti (sul nero e poi sopra la scena).
- **Cartelli di luogo**: stesso font, centrati su nero pieno, `Città, Paese`, ~2 s, taglio netto in entrata e in uscita.
- Niente grafiche, niente frecce, niente emoji, niente effetti sul testo.

## 6. Immagini

- **Tre tipi di ripresa, sempre alternati**:
  1. **Cavalletto largo fisso, lui che agisce dentro l'inquadratura** (cammina verso la camera, si sdraia sull'erba, legge, si siede sul muretto). Sono i pezzi lunghi (13–22 s) sotto la voce: il soggetto è piccolo, il luogo è grande.
  2. **Selfie grandangolare a mano** (GoPro/0,5x) per i momenti dal vivo: mosso, vicino, imperfetto.
  3. **Dettagli e soggettive**: mani che dipingono, la tazzina, i limoni, il volante, la scia della barca, il piatto dall'alto.
- **Controluce e interni scuri**: le silhouette alla finestra (tramonti, lei sul balcone) sono usate come pause.
- **Richiami**: le stesse inquadrature tornano (acquerello a 0:19 e 6:02, balcone a 0:25 e 5:00, barca a 0:11 e 8:03). Il cold open semina, il film raccoglie.
- **Colore**: caldo, neri appena sollevati, pelle calda, acqua turchese piena; resa da pellicola, non da vlog saturo.

## 7. Ricetta operativa per i nostri vlog

1. **Scegli la domanda del titolo** (una frase sola, spezzabile in 3 pezzi). Per Lorenzo ad esempio: «Cosa resta / quando smetti / di correre?».
2. **Scrivi prima la voce fuori campo**: 1 paragrafo per capitolo, frasi brevi, sostantivi concreti (serviranno come immagini), una citazione o una storia a metà (la poesia *Lost* di David Whyte fa da perno al capitolo di Milano). Registrala a parte, microfono vicino, voce bassa e lenta.
3. **Inventario del girato in 3 cesti**: A) inquadrature da cavalletto larghe, B) selfie/presa diretta con battute vere, C) dettagli. Segna i momenti «veri» con audio buono (risate, battute, imprevisti).
4. **Apertura**: la clip dello strumento (chitarra) con l'ambiente vero → titolo a pezzi → la prima nota della traccia sul ritorno allo strumento → drop sul primo taglio del trailer.
5. **Cold open di 30–35 s**: le 25–30 immagini più belle di tutto il girato, tagliate sui colpi della canzone (1 battuta o 2 per taglio, una raffica da 0,2 s sul rullante a metà).
6. **Capitoli**: cartello su nero → voce + cavalletto lungo → almeno un momento dal vivo senza musica → pezzo veloce illustrato parola per parola → 10 s di sola musica per respirare.
7. **Finale**: richiama l'immagine d'apertura, la frase più profonda, gesti quotidiani, nero muto 5–7 s.
8. **Sottotitoli** su tutto, serif piccolo, 2–6 parole.
9. **QA**: (a) nessun taglio del cold open a più di 45 ms da un colpo; (b) ogni sostantivo concreto della voce ha la sua immagine; (c) le giunture dell'audio in presa diretta non mozzano parole (vedi QA giunture del playbook principale); (d) volume voce −14/−16 LUFS integrati, musica sotto la voce a −22/−24 dB, musica sola a −16.

## 8. Cosa NON copiare

- Le parolacce in inglese e il tono «100 billion dollar business»: per Lorenzo la corrispondente è l'ambizione detta sottovoce, non l'esibizione.
- Il sottotitolo inglese: noi in italiano; inglese solo se il vlog è pensato per un pubblico estero.

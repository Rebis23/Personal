# Da dove parte la clip

Questo file viene letto a ogni lavorazione e passato a Claude quando decide
il primo fotogramma di un Reel. È separato da `hooks.md` apposta: quello
riguarda il **banner scritto**, questo riguarda **la prima frase che si
sente**. Sono due cose diverse e il 90% dei Reel sbagliati del 15/10
sbagliava la seconda.

Il 17/10 Lorenzo ha corretto a mano tutte e dieci le clip ferme in coda.
Quelle correzioni sono la regola: stanno qui sotto parola per parola, e
sono gli esempi su cui il modello si allinea prima di scegliere.

---

## La regola, in una riga

**Chi apre il Reel non ha visto niente. La prima frase deve bastargli.**

Non «deve incuriosire», non «deve essere forte»: deve essere **capibile da
sola**. Se per capirla serve la frase di prima, il taglio è sbagliato —
anche se quello che viene dopo è bellissimo.

Tre domande, in quest'ordine. Se una sola fa "no", il taglio va spostato:

1. **Di chi o di cosa si sta parlando?** Deve essere detto nella prima
   frase, oppure nel banner. Mai darlo per sottinteso.
2. **La prima frase regge da sola?** Letta fuori dal video, vuol dire
   qualcosa?
3. **Il Reel si chiude?** Se finisse qui, uno avrebbe ricevuto una cosa
   intera, o si sente tagliato fuori?

E una quarta, che non riguarda il taglio ma la scelta: **il punto è
davvero interessante?** Un taglio pulito su un contenuto tiepido resta un
Reel tiepido.

## La clip si può anche BUTTARE

Non tutte le clip si aggiustano spostando l'inizio. Un pezzo di raccordo,
un rimando a un altro video, un esempio che vive solo dentro il discorso
grande: quelli non diventano Reel, si scartano. **Meglio due Reel buoni
che sei pieni.**

---

## Le dieci correzioni di Lorenzo (17/10/2026)

Sono il banco di prova: `prove/inizio.py` le verifica tutte.

### 1 — «Perché i più competenti restano invisibili?»
Partiva da: *«perché un high performer è una persona…»*
> «devi partire da "un high performer è una persona..." Senza tenere la
> parola tagliata iniziale e il "perchè" prima di "un high performer"»

**Regola: via il «perché» in testa.** Un «perché» apre una subordinata:
risponde a una domanda che chi guarda non ha sentito. E via la parola
troncata iniziale.

### 2 — «Ci metti settimane a prendere una decisione?»
Partiva da: *«è complessa e magari si stressa e accumula ansia»*
> «non ha senso come hook, nè tanto meno è contestualizzato o funziona
> come inizio di un video breve autoconclusivo. inizia da "chi di solito
> ha forte agency..."»

**Regola: «è complessa» chi?** Un aggettivo che si riferisce a una cosa
nominata prima non è un inizio. La frase giusta ha un soggetto, anche
generico: *«chi di solito ha forte agency decide rapidamente»*.

### 3 — «Essere competitivi è davvero una cosa brutta?»
Partiva da: *«Normalmente ha una caratteristica…»*
> «fuori contesto e non ha senso come reel. Di chi stiamo parlando? Manca
> il soggetto che probabilmente era prima del reel.»

**Regola: il soggetto non si eredita dal pezzo precedente.** E attenzione:
qui la prima parola è un avverbio innocuo («Normalmente»), quindi nessuna
lista di parole proibite se ne accorge. Questa la prende solo la domanda
«di chi stiamo parlando?».

### 4 — «Perdere 4 ore sui reel»
Partiva da: *«ehmmm, nutrire, quella personalità»*
> «Tutto questo reel è inutile, non è autoconclusivo nè sensato da solo.»

**Regola: si butta.** Era il pezzo in cui Lorenzo rimanda a un altro video
sugli archetipi. Nessun inizio lo salva, e infatti il banner parlava di
tutt'altro. Clip come questa non vanno montate.

### 5 — «Vuoi un fisico bestiale? Stai pensando male»
> «Scelta media del contenuto (hook poco interessante, video tagliato non
> bene in termini di attenzione ed engagement, non è un punto COSÌ
> interessante), ma va bene»

**Regola: passa, ma è il minimo sindacale.** L'inizio («Beh, in questo
momento stai pensando nel modo sbagliato») è accettato — quindi un «Beh»
in testa non è un difetto da bocciare. Il problema è a monte: il punto
scelto non era abbastanza forte.

### 6 — «La tua mente inconscia comanda il 95%»
> «OTTIMO HOOK è molto bello»

Parte da *«Noi siamo nella nostra mente conscia il 5% del tempo, il
restante 95% è guidato dalla nostra mente inconscia»*. Soggetto («noi»),
numero concreto, affermazione che contraddice il senso comune, e il banner
dice la stessa cosa della prima frase.

### 7 — «Perché per un ricco 2.000 euro sono pochi»
> «OTTIMO HOOK bravo»

Parte da *«Per me 2.000 euro al mese sono pochi»*. **Nota: questo banner è
di 8 parole, una sopra il limite** — e Lorenzo lo chiama ottimo. Quindi il
limite delle 7 parole è una guida, non un veto: **il contesto batte la
brevità**. Un banner di 8 parole che si capisce vale più di uno di 6 che
non si capisce.

### 8 — «Giapponese in 30 giorni»
> «L'hook testuale dovrebbe dare più contesto dato che l'hook è semi-
> interessante ma non molto contestuale e sensato per chi guarda da 0 il
> video: per questo meglio "Come ha imparato il giapponese in 30 giorni".
> Magari c'è un hook ancora più efficace. Inoltre, la parte di idiomi può
> essere tagliata per rendere il video più engaging e meno prolisso.»

**Due regole.** Primo: il banner può **aggiungere** il contesto che il
parlato dà per scontato — «Come ha imparato» dice che è la storia di
qualcuno, «Giapponese in 30 giorni» da solo non lo dice. Secondo: dentro
la clip si può **tagliare la parte prolissa**; la durata non è sacra.

Nota: questa clip parte da *«Ha comprato solo libri in giapponese»*, cioè
un verbo senza soggetto esplicito — e Lorenzo non l'ha segnalato come
difetto. Perché il soggetto glielo dà il banner. **Banner e prima frase
rispondono insieme alla domanda «di chi parliamo?»**: basta che uno dei
due lo faccia.

### 9 — «I soldi non fanno la felicità: falso»
Partiva da: *«e tutte cose assolutamente false»*
> «non ha senso, tutte cose quali? Di cosa parliamo? Fuori contesto.»

**Regola: niente «e» in testa, niente «tutte cose» senza le cose.** Il
banner qui ripete la frase che è stata tagliata via un attimo prima: il
Reel si apre sulla risposta a una domanda che nessuno ha sentito.

### 10 — «Prova a urlare in strada»
Partiva da: *«Perché non farlo?»*
> «non si capisce di cosa parliamo. Qual è l'argomento? Non c'è un inizio
> sensato. Se lo scrivessi da zero, non avrebbe senso il reel. Non è
> autoconclusivo»

**Regola: «Perché non farlo?» — fare cosa?** Una domanda retorica che
rimanda a qualcosa di non detto è il contrario di un inizio. E il banner
nominava l'urlo in strada, che in questa clip non si sente mai.

---

## E mai un rimando al video lungo

Il 18/10 una clip e uscita con questo inizio:

> *«in questo video ti voglio spiegare come capire esattamente che cosa la
> tua parte inconscia vuole»*

Frase intera, soggetto, verbo: passa tutte e tre le domande qui sopra. E
non va bene lo stesso, perche **«questo video» per chi guarda un Reel non
esiste**. Sta scorrendo, e arrivato qui per caso, e si sente annunciare un
video che non vedra mai. Lo stesso vale per «come vi dicevo», «nel video
di prima», «oggi vi parlo di», «prima di cominciare»: sono cerniere del
video lungo, e nel Reel restano appese nel vuoto.

E' la stessa famiglia della correzione n.4 — la clip che rimandava al
video sugli archetipi — vista dall'altro capo: li era la fine a rimandare
altrove, qui e l'inizio.

## In testa non ci vanno mai

Una lista corta e certa, da tenere come pavimento — **non come il
controllo principale**, perché la n. 3 dimostra che una frase può essere
fuori contesto pur cominciando con una parola innocua:

- congiunzioni e connettivi: *e, ed, ma, però, perché, quindi, allora,
  cioè, anzi, invece, dunque, comunque, tuttavia, eppure*
- dimostrativi senza referente: *questo, questa, questi, queste, quello,
  quella, quelli, quelle, ciò*, e formule come *«tutte cose…»*
- esitazioni e parole troncate: *ehm, mmh,* o un pezzo di parola

Sono ammessi, e li trovi negli esempi approvati: *chi* (soggetto
generico), *noi*, *per*, *un/una*, *beh*.

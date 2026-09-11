# Libreria degli hook — Reels Factory

Questo file viene letto a ogni esecuzione e passato a Claude quando sceglie le
clip. Serve a una cosa sola: **far sì che ogni clip parta su una frase che
ferma lo scroll**, non su un'introduzione tiepida.

Modificalo liberamente: aggiungi gli schemi che vedi funzionare, cancella
quelli che non ti somigliano. Il sistema si adatta al volo, senza toccare il
codice.

---

## Le cinque regole non negoziabili

1. **La clip deve APRIRE sull'hook.** Non due frasi prima. Il primo secondo di
   parlato è già il gancio: se il momento forte arriva dopo, si taglia lì —
   oppure lo si estrae e lo si mette in apertura a freddo (vedi *Cold open*).
2. **Deve far capire di cosa si parla, non per forza finire.** Su Instagram
   la voce parte insieme al testo: il banner non deve reggersi da solo come
   un titolo, deve far restare mezzo secondo di piu. Un frammento sospeso e
   uno degli schemi che funzionano meglio — *«NOI NON DICEVAMO CHE LA MAFIA
   ERA...»* (×93), *«C'è una frase che ho imparato alla scuola di
   psicoterapia:»* (×20). Quello che non va bene e il frammento che non fa
   capire il tema: *e*, *ma*, *quindi*, *che*, *allora* in apertura sono
   quasi sempre quel caso.
3. **Massimo 7 parole, concrete.** "Il 95% delle tue scelte non le fai tu"
   funziona. "Parliamo di come funziona la mente inconscia" no. Sette e il
   limite oltre il quale il banner va a capo e smette di fermare lo scroll:
   sopra quella soglia il codice taglia d'ufficio, quindi tanto vale
   scriverlo gia corto e scegliere tu quale pezzo tenere.
4. **Deve creare SCONTRO.** Non basta essere interessante: serve un attrito.
   Contraddire una convinzione diffusa, mettere due cose in opposizione, dire
   la cosa scomoda che nessuno dice ad alta voce. Se nessuno può dissentire,
   non è un hook — è una didascalia.
5. **DEVE NOMINARE L'ARGOMENTO.** Chi scorre non ha visto niente: se il
   banner nomina un dettaglio invece del tema, il Reel non si capisce e non
   si ferma nessuno. Lorenzo, 6/09, davanti a un Reel sulla religione che in
   cima diceva *«Zanzara che depone le uova negli occhi»*:

   > "L'hook non fa capire l'argomento, perché in questo video si parla di
   > religione. Un hook perfetto sarebbe stato **«Perché Dio permette il male
   > sugli animali?»**: parlava del concetto del video — Dio, la religione —
   > ed era coerente con la mia argomentazione."

   La zanzara nel video c'è davvero: è l'esempio che porta il discorso. Ma
   l'argomento è Dio. **Il banner nomina l'argomento, non l'esempio.**

   Attenzione: questa regola ha sostituito quella vecchia, che diceva il
   contrario — "il banner riprende le parole davvero pronunciate". Era un mio
   errore: avevo unito in un meccanismo solo due cose diverse, "la clip parte
   sulla frase forte" e "il banner ferma lo scroll". La clip parte ancora su
   una frase pronunciata; il banner invece si scrive, e puo essere una
   domanda che nel video non si sente mai.

---

## Il Reel deve anche FINIRE

L'hook fa fermare lo scroll. Ma un Reel che aggancia e poi si spegne a metà
frase è un Reel sprecato: chi guarda resta ad aspettare un seguito che non
arriva, e non arriva neanche il pensiero "questo tizio sa di cosa parla".

Lorenzo, 11/09/2026, su un Reel uscito quella mattina:

> "Ha una conclusione sbagliata, nel senso che lascia in sospeso: dice 'da lì
> a credere a un dio che ha delle regole della Bibbia eccetera eccetera' e poi
> si ferma improvvisamente. Dev'essere un discorso completo, comprensibile e
> finito in sé stesso."

Quel Reel finiva letteralmente così — «...un dio specifico con un nome, una
storia, delle regole» — e si spegneva.

**Perché succedeva.** La fine della clip la decideva `snap_to_sentences`, e lì
"frase" non vuol dire quello che sembra: si chiude sulla punteggiatura di
Whisper — che nel parlato salta quasi sempre — oppure su una pausa di 0,75
secondi. Una pausa è un respiro. La clip finiva dove Lorenzo prendeva fiato.

**La regola.** Il punto in cui il Reel finisce si sceglie, non si subisce:

- l'ultima frase è **finita** — niente "però", niente "da lì a", niente elenchi
  lasciati aperti;
- il **ragionamento** è arrivato al punto, non solo alla premessa o all'esempio;
- se subito dopo il taglio arrivasse il silenzio, avrebbe senso.

Meglio una clip più corta che chiude di una più lunga che si spegne. E meglio
allungarla fino alla conclusione che fermarla prima: il tetto è 75 secondi, di
solito c'è spazio.

Come per l'apertura, la regola è **meccanica**: `chiusura.py` elenca tutti i
punti in cui la clip può finire, scarta quelli che cadono su una parola appesa,
e il modello sceglie fra quelli rimasti. Un vincolo che il codice non verifica
non è un vincolo — e infatti "chiudersi su una frase completa" era già scritto
nel prompt da settimane, e non è bastato.

---

## Cold open — il momento forte per primo

Se dentro la clip c'è una frase più tagliente di quella con cui la clip
comincia, si estrae e si monta **prima** dell'inizio: si sente la frase forte,
stacco secco, e riparte il discorso dal principio.

Funziona quando la frase regge da sola fuori contesto. Non funziona quando ha
bisogno di ciò che viene prima per capirsi — in quel caso niente cold open,
meglio una clip pulita che un'apertura confusa.

- ✅ "Lo sforzo non paga le bollette." → stacco → si riparte dal ragionamento
- ❌ "E quindi capisci che è proprio quello il punto." → non significa nulla da sola

---

## Cosa dicono i dati — i REEL, non i titoli YouTube (6/09/2026)

Prima avevo guardato i titoli YouTube. Lorenzo mi ha fermato: «non ti ho
chiesto l'hook su YouTube, questo sarà un Reel su Instagram». Ha ragione, e
i due formati chiedono cose diverse:

> Un titolo YouTube si legge **accanto a una miniatura, mentre scegli** cosa
> guardare: deve reggersi da solo. Un banner su un Reel si legge **in mezzo
> secondo, mentre stai gia scorrendo e l'audio sta gia partendo**: non deve
> reggersi da solo, deve far restare mezzo secondo di piu.

Quello che segue viene da 24 fra Reel e TikTok italiani che hanno sfondato
rispetto alla media del loro creatore, con il testo VERO dei primi 3 secondi.
Il numero fra parentesi e quante volte hanno superato quella media.

**1. Corti. Molto piu corti di un titolo.**
- *Ci vogliono 5 secondi* (×86)
- *Ho postato una foto seminuda* (×27)
- *Genio o setta? La vera storia.* (×156)

**2. LA DOMANDA e la forma che vince piu spesso** — spesso e la domanda che
farebbe l'intervistatore:
- *PERCHÉ ABBIAMO INVENTATO DIO* (×27)
- *SAI COSA BISOGNA FARE QUANDO UN PARENTE PARLA MALE DI TE?* (×212)
- *PERCHÉ HAI CHIUSO IL NEGOZIO DI ORO 91?* (×26)
- *Ma davvero la gente non sa la DIFFERENZA tra intelligenza e cultura?* (×38)

Nota bene: *«PERCHÉ ABBIAMO INVENTATO DIO»* e quasi parola per parola
l'esempio che ha fatto Lorenzo — *«Perché Dio permette il male sugli
animali?»*. Aveva ragione, e i dati lo confermano.

**3. Il frammento sospeso funziona — e su YouTube no.** Su Instagram la voce
parte insieme al testo, quindi la frase puo restare a meta:
- *NOI NON DICEVAMO CHE LA MAFIA ERA...* (×93)
- *perché condanniamo solo* (×34)
- *C'è una frase che ho imparato alla scuola di psicoterapia:* (×20)

Questo **contraddice la regola 2** di questo file, che dice "frase intera,
mai un frammento". La regola resta giusta per il senso — il frammento deve
comunque far capire di cosa si parla — ma un banner che finisce sospeso non
e un errore: e uno degli schemi che funzionano meglio.

**4. La provocazione binaria.** *O SEI SINNER O SEI UN FALLITO* (×113),
*Genio o setta?* (×156).

**5. Il nome riconoscibile fa il lavoro dell'argomento.** *CARD. PIZZABALLA:
DICO COSE CHE FANNO ARRABBIARE* (×38), *Charlie Kirk* (×31), *Denzel
Washington* (×150). Se nella clip si nomina qualcuno che il pubblico
riconosce, quel nome va nel banner.

**6. La confessione in prima persona.** *Sai che sono stato denunciato per
istigazione all'odio razziale?* (×68), *Ho postato una foto seminuda* (×27).

**Cosa NON copiare:** le liste numerate ("7 abitudini…") dominano YouTube ma
una clip non e una lista: promettere sette cose e mostrarne una fa chiudere
il Reel.

---

## Schemi che funzionano (adattali, non copiarli)

### 1. Affermazione contraria
Ribalta una convinzione data per scontata. È lo schema più forte in assoluto.
- "Studia e prenditi una laurea: è il consiglio peggiore degli ultimi 20 anni."
- "Postare ogni giorno ti sta bruciando l'account."
- "Non ti serve più disciplina. Ti serve meno roba da decidere."

### 2. Numero + conseguenza
Un dato secco che riguarda chi ascolta.
- "Il 95% delle tue giornate lo decide qualcun altro."
- "Ho perso 4.000 euro prima di capire questa cosa."
- "3 mesi a postare tutti i giorni. Zero clienti."

### 3. Errore che stai facendo
Fa leva sulla paura di perdere, non sul desiderio di guadagnare.
- "Se stai ancora facendo così, stai buttando via metà del tuo lavoro."
- "Questo errore ti costa clienti ogni singola settimana."
- "Vorrei che qualcuno me l'avesse detto prima di iniziare."

### 4. Chiamata diretta al pubblico
Il pubblico deve sentirsi nominato: chi non si riconosce scrolla, ed è giusto.
- "Se lavori da solo e non riesci a staccare, questo è per te."
- "Se hai più di 30 anni e ti senti in ritardo, fermati un secondo."

### 5. Ciclo aperto
Prometti qualcosa che si scopre solo restando.
- "Non volevo dirlo, ma tanto vale."
- "C'è una cosa che nessuno ti dice sul lavorare per sé."
- "Aspetta, prima di prendere quella decisione."

### 6. Prima e dopo
Il risultato prima del metodo.
- "Da 300 visualizzazioni a un milione in due mesi. Ti spiego come."
- "Ci mettevo 45 minuti. Ora tre. Stessa cosa."

### 7. Confessione
La vulnerabilità funziona quando è specifica, non generica.
- "Per tre anni ho fatto la cosa sbagliata convinto fosse giusta."
- "Ho iniziato per pigrizia, non per visione."

### 8. Verità scomoda
Il tono di casa: si dice la cosa che gli altri non dicono.
- "Le visualizzazioni non pagano le bollette."
- "Nessuno te lo dice perché non conviene a nessuno."

---

## Cosa NON è un hook (esempi da evitare)

- "Oggi parliamo di come funzionano i paradigmi" → è un indice, non un gancio
- "Allora, dunque, riprendendo il discorso di prima" → riferimento a contesto
- "È molto importante capire questa cosa" → nessuna informazione, nessuna tensione
- "Ciao a tutti, bentornati sul canale" → saluto
- Hook che promette qualcosa che poi la clip non mantiene

---

## Tono di Lorenzo

Iperrealismo: verità diretta, niente fuffa, niente promesse miracolose, mai da
guru. L'hook può essere duro, mai gridato. Meglio una frase secca e vera che
una a effetto e vuota.

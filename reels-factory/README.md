# 🎬 Reels Factory — da YouTube a Reels Instagram, in automatico

Workflow agentico completo: **ogni volta che esce un nuovo video sul canale
YouTube**, il sistema lo scarica, **Claude sceglie i momenti migliori**, li
taglia in verticale 9:16, imprime i **sottotitoli stile Reels** (parola
evidenziata mentre viene pronunciata) e li **pubblica su Instagram come Reels**,
uno al giorno.

Costo di esercizio: **~1-2 € al mese** (solo le chiamate a Claude — tutto il
resto è gratuito: GitHub Actions, Cloudflare R2 free tier, Instagram Graph API).
Un servizio equivalente tipo OpusClip + Zapier costerebbe 50-80 €/mese.

## Come funziona

```
YouTube (feed RSS, ogni giorno alle 18:00)
   │  nuovo video?
   ▼
[Ingest — GitHub Actions]
   ├─ Apify scarica il video (YouTube blocca i runner GitHub; ~3 cent/video)
   ├─ Whisper trascrive in locale (timing parola per parola, gratis)
   ├─ Claude (claude-opus-5) legge la trascrizione → sceglie 3 clip
   │     + scrive caption e hashtag per ognuna, nel tono Media Profit
   ├─ ffmpeg taglia, converte 9:16, imprime sottotitoli karaoke
   └─ upload su Cloudflare R2 → clip in coda (state/queue.json, committato)
   ▼
[Publish — GitHub Actions, 1 volta al giorno]
   └─ Instagram Graph API pubblica la prossima clip come Reel
```

Le 3 clip di un video escono quindi **distribuite su 3 giorni** — copertura
continua del feed senza spam.

---

## Configurazione iniziale (una volta sola, ~30 minuti)

### 1. Canale YouTube

In [`config.yaml`](./config.yaml) imposta `youtube.channel_id` con l'ID del
canale (inizia con `UC...`): lo trovi in YouTube Studio → Impostazioni →
Canale → Impostazioni avanzate.

### 2. Cloudflare R2 (hosting temporaneo dei video)

Instagram scarica i video da un URL pubblico: usiamo R2 (già in casa, il CRM
è su Cloudflare — free tier: 10 GB, traffico in uscita gratuito).

1. Dashboard Cloudflare → **R2** → *Create bucket* → nome es. `mediaprofit-reels`
2. Nel bucket → *Settings* → **Public access** → abilita il dominio `r2.dev`
   (o collega un dominio custom) → copia l'URL pubblico (`https://pub-xxx.r2.dev`)
3. R2 → *Manage R2 API Tokens* → crea un token **Object Read & Write** limitato
   al bucket → copia Access Key ID e Secret Access Key
4. L'Account ID è nella colonna destra della dashboard Cloudflare

### 3. Instagram Graph API (account business — già ce l'hai ✅)

Requisiti: account Instagram **business/creator** collegato a una **Pagina
Facebook**.

1. [developers.facebook.com](https://developers.facebook.com) → *My Apps* →
   **Create App** → tipo *Business*
2. Aggiungi il prodotto **Instagram Graph API**
3. In **Graph API Explorer** genera un token utente con i permessi:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `business_management`
4. Rendi il token **long-lived** (60 giorni) con lo scambio token, oppure —
   meglio, non scade mai — crea un **System User** in Business Manager e
   genera il token da lì
5. Recupera l'**IG User ID**: nel Graph Explorer chiama
   `GET /me/accounts` → prendi l'`id` della Pagina → poi
   `GET /{page-id}?fields=instagram_business_account` → l'`id` restituito è
   l'`IG_USER_ID`

> ⚠️ Il token da Graph Explorer scade dopo 60 giorni. Il token da **System
> User** no: usa quello per non doverci più pensare.

### 4. Chiave API Anthropic

[console.anthropic.com](https://console.anthropic.com) → API Keys → crea una
chiave. Con 1 video a settimana la spesa è di pochi centesimi al mese.

### 5. GitHub Secrets

Nel repo: **Settings → Secrets and variables → Actions → New repository
secret**. Servono questi 9 segreti:

| Secret | Valore |
|---|---|
| `ANTHROPIC_API_KEY` | chiave API Anthropic |
| `IG_ACCESS_TOKEN` | token Instagram long-lived / system user |
| `IG_USER_ID` | ID dell'account Instagram business |
| `R2_ACCOUNT_ID` | Account ID Cloudflare |
| `R2_ACCESS_KEY_ID` | Access Key del token R2 |
| `R2_SECRET_ACCESS_KEY` | Secret Key del token R2 |
| `R2_BUCKET` | nome del bucket (es. `mediaprofit-reels`) |
| `R2_PUBLIC_BASE_URL` | URL pubblico del bucket (es. `https://pub-xxx.r2.dev`) |
| `APIFY_TOKEN` | token API di [console.apify.com](https://console.apify.com) (piano free) |

### 6. Primo test

1. In `config.yaml` metti `instagram.auto_publish: false` (modalità prova)
2. GitHub → **Actions → Reels Factory · Ingest → Run workflow**: processa
   l'ultimo video e mette le clip in coda (le vedi in `state/queue.json`,
   i file mp4 su R2 — guardali per controllare qualità di taglio e sottotitoli)
3. **Actions → Reels Factory · Publish → Run workflow** con *dry run* spuntato:
   mostra la caption che pubblicherebbe, senza pubblicare
4. Quando sei soddisfatto: rimetti `auto_publish: true`, committa, e da lì
   va tutto da solo

---

## Uso quotidiano

**Niente.** È questo il punto. 🙂

- Esce un video → al controllo delle 18:00 le clip vengono preparate e messe in coda
- Ogni giorno alle 11:30 esce un Reel (finché la coda non è vuota)
- Lo stato è sempre visibile in [`state/queue.json`](./state/queue.json)
- Log completi in GitHub → Actions

### Regolazioni utili (in `config.yaml`)

| Cosa | Dove |
|---|---|
| Numero di clip per video | `clips.per_video` |
| Durata min/max delle clip | `clips.min_seconds` / `max_seconds` |
| Ritaglio pieno vs sfondo sfocato | `clips.vertical_mode`: `crop` / `blur` |
| Stile sottotitoli (font, colori, posizione) | sezione `subtitles` |
| Hashtag fissi e firma | sezione `instagram` |
| Tono e criteri di selezione delle clip | `claude.brand_context` |
| Orario di pubblicazione | cron in `.github/workflows/reels-publish.yml` |

## Risoluzione problemi

| Sintomo | Causa probabile / soluzione |
|---|---|
| "Sottotitoli automatici non ancora pronti" | Normale nelle prime ore dopo la pubblicazione: riprova da solo al giro successivo |
| Errore Graph API `190` | Token Instagram scaduto → rigenera (o passa al token System User) |
| Errore Graph API su `video_url` | Il bucket R2 non è pubblico → controlla `R2_PUBLIC_BASE_URL` |
| Download fallisce con «Sign in to confirm you're not a bot» | Normale: il download diretto è bloccato, la pipeline passa da sola ad Apify. Se fallisce anche Apify, controlla il secret `APIFY_TOKEN` e i crediti su console.apify.com |
| Clip tagliata male / hook debole | Affina `claude.brand_context` con esempi di cosa vuoi (Claude segue le istruzioni alla lettera) |

## Limiti noti

- **Instagram**: massimo 25 post via API ogni 24h (noi ne facciamo 1)
- **Reels**: durata 3-90s consigliata (rispettata dalla config di default)
- I sottotitoli usano la trascrizione automatica di YouTube: qualche parola
  può essere imprecisa. In pratica per l'italiano parlato chiaro è ottima.

## Cookie YouTube (`YT_COOKIES`) — opzionale

Il download dei video passa da Apify (secret `APIFY_TOKEN`). In aggiunta,
se vuoi tentare prima il download diretto gratuito, puoi dare a yt-dlp
i cookie di un account YouTube loggato — ma non è necessario.

1. **Usa un account Google di riserva**, non quello del canale (nel raro caso
   in cui YouTube segnali l'attività, non rischia l'account principale)
2. Apri una **finestra in incognito** → login su youtube.com con quell'account
   → apri un video qualsiasi
3. Con l'estensione **«Get cookies.txt LOCALLY»** (Chrome) esporta i cookie
   della scheda youtube.com → si scarica `cookies.txt`
4. **Chiudi la finestra in incognito senza fare logout** (così i cookie
   esportati restano validi a lungo)
5. Copia tutto il contenuto di `cookies.txt` nel secret **`YT_COOKIES`**
   (Settings → Secrets and variables → Actions)

Se dopo mesi i download tornano a fallire, ripeti l'esportazione.

# RIFLETTENDO EDIT — Playbook operativo per l'agente

> **Tu (l'agente Claude) sei l'esecutore di questo playbook.** Lorenzo fornisce: il video grezzo,
> i suoi gusti, le correzioni sulle bozze. Tu fai tutto il resto, fino a un file consegnabile.
> Vale per long-form YouTube E Shorts del canale personale di Lorenzo.
> Progetto di riferimento con gli script già pronti: `~/Downloads/C0228-edit/` (sul Mac di Lorenzo).
> Se sei in remoto e non hai quella cartella: in questo documento c'è TUTTO per ricostruire la pipeline.

## Il contratto

1. All'inizio chiedi SOLO tre cose: **formato** (long-form o short), **musica** (quale file Uppbeat), **aggressività del taglio**. Poi corri fino a una bozza rivedibile. Gli umani dirigono bene le bozze e male le specifiche.
2. **Anteprime PRIMA dei render lunghi**: cut-list documentata, frame delle grafiche compositati su frame veri. Uno stile si valida su 3-4 anteprime, non su un render da 20 minuti.
3. Ogni render >2 min va in **background con watcher**. Mai bloccare la conversazione.
4. **Mai sovrascrivere una versione approvata**: file nuovi (`montato-v2`, `finale-v3`…).
5. Ogni taglio documentato in `CUT-LIST.md` (cosa, dove, perché). Le parole di Lorenzo in camera («questo lo stacchiamo», «rifaccio») sono istruzioni di montaggio vincolanti.
6. QA obbligatorio prima di ogni consegna (sezione QA). Consegna = file + spiegazione di cosa è cambiato.
7. Ogni scoperta nuova (bug, trucco, preferenza di Lorenzo) va AGGIUNTA a questo playbook.

## Stile: cosa è approvato e cosa è vietato

- **APPROVATO** (25/08/2026): stile "George Alexander" — artigianale, caldo, da quaderno. Scritte a mano, carta stropicciata, nero caldo, giallo senape. Reference: youtube 8UCIdcIRB1s.
- **BOCCIATO**: stile elegante "DAVIL" (Cinzel + oro + pannelli blu notte). Non riproporlo mai nei video.
- **Vietato**: loghi nelle creative (regola di Lorenzo del 15/08/2026). Mai la foto `lorenzo-ricchieri.png`.
- Tono grafico: mai YouTube-urlato, mai da guru. Iperrealismo.

### Token visivi (esatti)

```
carta        #F5F2EA   (sfondo takeover chiari; base RGB 245,242,234)
inchiostro   #2F4E40   (testo su carta; RGB 47,78,64)
giallo       #E8C34A   (scritte sul footage; RGB 232,195,74)
senape       #C9A227   (giallo su carta, dove il chiaro non legge; RGB 201,162,39)
nero caldo   #0D100E   (takeover scuri; RGB 13,16,14)
bianco caldo #F5F1E8   (testo su nero; RGB 245,241,232)
rosso timbro #A84A3C   (barrature, errori; RGB 168,74,60)
grigio caldo #6E6A60   (etichette secondarie)
```

Font (Google Fonts, scaricare i TTF per PIL):
- **Caveat** (400/600/700) — tutte le scritte a mano. ATTENZIONE: i file di Google hanno nomi mescolati, verificare con `ImageFont.truetype(f,40).getname()`.
- **Patrick Hand** — etichette piccole ("lezione 1:", firme).

## Ambiente (il Mac di Lorenzo)

```
FFMPEG (UNICO che legge i Sony XAVC):
  ~/Library/Python/3.14/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1
  → l'ffmpeg 7.0 in ~/.local/bin FALLISCE sui file Sony con "infe: version < 2" (metadati C2PA).
  In remoto: serve ffmpeg ≥ 7.1.

TRASCRIZIONE: pip3 install --user mlx-whisper (Apple Silicon; in remoto: faster-whisper o whisper)
SORGENTI: scheda SD /Volumes/Untitled/PRIVATE/M4ROOT/CLIP/ — copiare SEMPRE in locale prima.
MUSICA/SFX/STOCK VIDEO: Uppbeat (Lorenzo paga l'abbonamento). I download via estensione Chrome
  NON partono: li scarica Lorenzo a mano. File già scaricati: ~/Downloads/Contenuti OBS/.
GIRATO FUTURO: chiedere sempre il 4K. Il 1080p limita punch-in e Shorts full-bleed.
```

## FASE 1 — Probe & preparazione

```bash
"$FF" -i sorgente.MP4 2>&1 | grep -E "Duration|Stream"    # durata, risoluzione, fps
cp sorgente.MP4 <progetto>/source.mp4                      # mai lavorare dalla SD
# estrai 3-4 frame a tempi diversi e GUARDALI: inquadratura, luce, dove mettere le grafiche
"$FF" -ss 30 -i source.mp4 -frames:v 1 frame30.jpg
# misura la voce: mean_volume sano ≈ -15/-20 dB
"$FF" -ss 60 -t 60 -i source.mp4 -vn -af volumedetect -f null - 2>&1 | grep mean
```

## FASE 2 — Trascrizione word-level (la spina dorsale)

```python
import json, mlx_whisper
r = mlx_whisper.transcribe("audio.wav",                    # prima: -vn -ac 1 -ar 16000
      path_or_hf_repo="mlx-community/whisper-large-v3-turbo",   # MAI small.en: è solo inglese
      language="it", word_timestamps=True)
json.dump(r, open("transcript.json","w"), ensure_ascii=False, indent=1)
```

OGNI decisione (tagli, grafiche, caption, sync) si prende sul transcript, mai a occhio.
Genera anche una versione leggibile con timestamp e marcatori `<<< PAUSA x.xs` per l'analisi.

## FASE 3 — Cut-list

Regole editoriali (nell'ordine):
1. **Tenere sempre la SECONDA ripresa.** Quando Lorenzo ripete una frase/blocco, la prima è la scartata. Vale anche per l'intro: hook doppio → via il primo.
2. Via: false partenze, frasi abbandonate («E questo ci fa capire…» troncato), silenzi > ~1,5 s, telefonate, interruzioni. Le pause brevi di riflessione (0,8–1,3 s) restano: sono il ritmo del canale.
3. «**Lo stacchiamo**» / «troppo complesso» / «no, aspetta» detti in camera = ordini di taglio.
4. **Word-snap** (obbligatorio, mai stimare dagli inizi riga — il primo collaudo mozzò 5 parole):

```python
# words = lista piatta dei word-timestamps del transcript
def snap(seg):
    i = next(k for k, w in enumerate(words) if w["end"] > seg["start"])
    j = max(k for k, w in enumerate(words) if w["start"] <= seg["end"])
    start = max(words[i]["start"] - 0.12, words[i-1]["end"] + 0.03 if i else 0)
    end   = words[j]["end"] + 0.2
    if j + 1 < len(words): end = min(end, words[j+1]["start"] - 0.05)
    return start, end
# stampa SEMPRE prime/ultime parole di ogni segmento: è il modo per beccare code di
# parole abbandonate («aspetta. E questo…») incluse per errore
```

5. Formato cut-list (`cutlist.json`): `{"segments":[{"id":2,"start":51.2,"end":128.0,"zoom":false,"note":"perché"}]}`.

## FASE 4 — Montaggio

```bash
# per ogni segmento (start/end già snappati):
"$FF" -ss <start> -i source.mp4 -t <durata> \
  [-vf "crop=1698:956:111:43,scale=1920:1080:flags=lanczos"]  # solo se zoom=true (1.13x)
  -af "afade=t=in:st=0:d=0.015,afade=t=out:st=<durata-0.015>:d=0.015" \
  -c:v libx264 -preset medium -crf 14 -pix_fmt yuv420p -c:a aac -b:a 192k seg<NN>.mp4
# poi: concat demuxer con -c copy → montato-senza-musica.mp4
# poi musica (video copy, tocca solo l'audio):
"$FF" -i montato.mp4 -stream_loop -1 -i musica.mp3 -filter_complex \
  "[1:a]volume=0.09,afade=t=in:d=1.5,afade=t=out:st=<tot-3>:d=3[m];\
   [0:a][m]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k finale.mp4
```

- **Punch-in alternato**: segmenti pari larghi, dispari zoom 1.13x. Si parte SEMPRE larghi. Serve a nascondere i jump-cut.
- **crf 14 preset medium sugli intermedi**: MAI due generazioni a preset veloce (produce ~4 Mbps → sgranato su YouTube).
- Musica ≈ −21 dB sotto la voce (volume 0.09; in una pausa deve alzare il fondo di ~0,5–1 dB, non di più).

## FASE 5 — Grafiche & animazioni

**Tre formati** (posizioni: mai coprire il viso con i flottanti; ogni overlay DEVE vivere dentro un solo segmento della cut-list, mai attraversare un taglio):
1. **Flottante giallo**: parole chiave in Caveat sul footage, ombra scura sfocata (offset +4,+6, blur 4-5), rotazione ±1,5-2°. Lui resta visibile. 4-6 s.
2. **Takeover carta**: schermo pieno, citazioni e lezioni, inchiostro su carta. 4–8 s.
3. **Takeover nero**: schermo pieno, battute secche, giallo/bianco su nero caldo. 3–5 s.
4. **Polaroid laterale**: cartoncino ~300×450 che entra con la molla da destra/sinistra, doodle che si disegna dentro (spiega senza coprire).

**Texture** (PIL): carta = base #F5F2EA + `Image.effect_noise(sigma 14)` composito con #DEDACE + 7 pieghe (linee alpha 26 sfocate) + vignetta ellittica; nero = base #0D100E + noise 10 + luma centrale #242A25 vignettata.

**Motion (il feel "Remotion" — motore = PNG 50fps da PIL, poi ffmpeg):**
```python
ease(t)   = 1-(1-t)**3                                        # easeOutCubic, per i tratti
back(t)   = 1 + 2.70158*(t-1)**3 + 1.70158*(t-1)**2           # overshoot ~1.1: OGNI pop di parola
spring(t) = 1 - exp(-5.2*t)*cos(11*t)                         # molla: entrate card, rotazioni altalena
```
- pop parola: scala 0.75→back(t), alpha ease(t*1.6), atterraggio con discesa di 14 px
- tratti disegnati progressivamente su curve con wobble sinusoidale + **punta di matita** (punto più scuro sulla testa del tratto finché prog < 1)
- sfondi che respirano: zoom 1.00→1.03 sulla durata + drift sin/cos di ±6 px
- **ogni beat sincronizzato sulla PAROLA del transcript** (il count parte quando la dice, la spunta atterra sul sostantivo)

**Render clip animate**: frame PNG → per takeover `libx264 crf 17`; per flottanti trasparenti **ProRes 4444** (`-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le`, container .mov) — senza alpha diventano riquadri neri.

**Composite finale** (statiche + clip in un solo passaggio):
```
input 0 = video montato; per ogni PNG: -loop 1 -t <dur> -i file.png; per ogni clip: -i clip
[k:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st=<dur-0.35>:d=0.35:alpha=1,
     setpts=PTS-STARTPTS+<start>/TB[ok];  [prev][ok]overlay=0:0:enable='between(t,<start>,<end>)'[vk]
(per i takeover senza alpha: fade normali, non alpha)
```

**Densità long-form**: intro fitta per la retention (≈6 animazioni nei primi 45 s: polaroid, ≠ barrato, checklist con spunte, doodle giocosi, un takeover sulla tesi), poi ~1 grafica ogni 60–90 s sui punti chiave (citazioni con autore, lezioni numerate, concetti animabili: contrasti, pile, inseguimenti, loop).

## FASE 6 — QA (mai fidarsi del render)

```bash
# 1. GIUNTURE: ritagliare 4-5 s d'audio a cavallo di OGNI taglio e ri-trascriverli:
#    se una parola è mozzata si vede nel testo. Nessuna consegna senza questo.
# 2. GRAFICHE: estrarre un frame a metà di ogni overlay DAL FILE RENDERIZZATO,
#    montarli in griglia e guardarli (alpha, posizioni, sync).
# 3. MUSICA: volumedetect in una finestra di pausa, con/senza musica: delta ~0,5-1 dB.
# 4. FILE: "$FF" -i finale.mp4 → durata/risoluzione/audio. Mai fidarsi del log di render.
```

## FASE 7 — Export

```bash
# master YouTube: 4K upscalato ANCHE se il girato è 1080p (corsia di bitrate più alta)
... -filter_complex "...;[vN]scale=3840:2160:flags=lanczos[v4k]" -map "[v4k]" \
    -c:v libx264 -preset fast -crf 16 -pix_fmt yuv420p -c:a copy -movflags +faststart
```

## SHORTS — l'adattamento verticale

- **1080×1920.** Girato 4K → crop verticale full-bleed stretto sul viso (estrai un frame e GUARDALO, mai solo la matematica). Girato 1080p → **layout split**: banda video 1080×608 al centro (`scale=1080:608`), campi carta o nero sopra e sotto (generati con le texture di Fase 5) per caption e grafiche.
- **24–45 s, UN concetto per clip. Hook nei primi 2 secondi** — la frase più forte del blocco, eventualmente con la parola chiave gialla che poppa subito.
- **Caption karaoke SEMPRE** (algoritmo, dal transcript word-level):
  - chunk di 2–3 parole; chunk nuovo a pausa ≥ 0,45 s o punteggiatura
  - visibile da `chunk.start − 0.04` fino a `chunk_successivo.start − 0.04` (mai due caption insieme)
  - Caveat gialla grande (≈90–110 px), bianco per le parole neutre, giallo per le parole-chiave, rosso timbro per i costi/negazioni; ombra come i flottanti
  - una PNG per chunk + overlay con enable (stesso pattern di Fase 5)
- **Ritmo**: pause quasi a zero, punch-in 1.2x, takeover max 2 s, musica a volume 0.15.
- **Da dove nascono**: i blocchi autoconclusivi del long-form, individuati sul transcript (es. dal C0228: paralisi da analisi, il ragno dal buco, la storia del contadino, l'altalena della tesi, il loop scegli→agisci→impara→correggi). Ritagliare con le stesse regole word-snap, poi riquadrare.
- Grafiche: stessi token e stessa motion, font +30%, polaroid centrali invece che laterali.

## GOTCHAS (ognuna è costata tempo vero — leggile prima di iniziare)

| Sintomo | Fix |
|---|---|
| `infe: version < 2` sui file Sony | ffmpeg ≤ 7.0 non legge i metadati C2PA → usare il 7.1 di imageio (path in Ambiente) |
| Parole mozzate ai tagli | Confini stimati dagli inizi riga → word-snap (Fase 3.4), e stampare prime/ultime parole |
| Sgranato su YouTube | Doppia compressione veloce → intermedi crf 14 medium + master 4K upscalato |
| Flottante = riquadro nero | Overlay senza canale alpha → ProRes 4444 yuva444p10le |
| La grafica "salta" a metà | Attraversa un taglio → ogni overlay dentro UN solo segmento |
| Trascrizione in inglese | Modello small.en → large-v3-turbo multilingue |
| Render ripreso ma concat fallisce (`moov atom not found`) | Un task ucciso lascia mp4 troncati che gli script con cache riusano → dopo ogni stop verificare gli intermedi: `ffmpeg -v error -i file -f null -` |
| Download che non partono dal browser automatizzato | L'estensione Chrome blocca i download → Uppbeat lo scarica Lorenzo a mano |
| YouTube blocca yt-dlp (403) e il player nel Chrome remoto | Per studiare una reference: storyboard `yt-dlp -f sb0` con `--extractor-args "youtube:player_client=mweb"` (mosaici in .mhtml, estrarli con email.message_from_bytes) + thumbnail maxres `i.ytimg.com/vi/<id>/maxresdefault.jpg` |
| zsh non splitta le variabili non quotate | Niente `for c in "a b c"; set -- $c` → comandi espliciti |
| Voce che parte a metà parola all'inizio del video | Il primo segmento inizia su una ripresa scartata → controllare che l'apertura sia la ripresa buona |

## File del progetto di riferimento (sul Mac)

```
~/Downloads/C0228-edit/
├── PLAYBOOK.md      ← questo documento
│      · versione web:  https://claude.ai/code/artifact/47d0baa2-4922-406a-8cbe-09fe348990f1
│      · repo GitHub:   https://github.com/Rebis23/riflettendo-edit (privato — playbook, script, cutlist, font, grafiche; niente media)
├── cutlist.json     ← cut-list word-snappata con note
├── monta.py         ← snap + tagli + concat + musica (Fasi 3-4 implementate)
├── grafiche2.py     ← le 9 grafiche statiche stile George (Fase 5)
├── animazioni.py    ← motore animazioni v2 completo: easing, texture, polaroid, cornici b-roll, render finale
├── CUT-LIST.md · transcript.json · fonts/ · grafiche/ · clip-anim/ · broll/
```

Se lavori su questo Mac: USA questi script, non riscriverli. Se sei altrove: ricostruiscili dalle ricette qui sopra — contengono tutto il necessario.

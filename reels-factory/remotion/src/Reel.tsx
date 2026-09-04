import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {z} from 'zod';
import {useFonts} from './fonts';

// Curve del playbook "Riflettendo Edit": e questa la parte che Lorenzo
// voleva — il movimento, non un cambio di identita grafica.
const ease = (t: number) => 1 - Math.pow(1 - t, 3);
const back = (t: number) =>
  1 + 2.70158 * Math.pow(t - 1, 3) + 1.70158 * Math.pow(t - 1, 2);
const clamp01 = (t: number) => Math.max(0, Math.min(1, t));

const wordSchema = z.object({
  text: z.string(),
  em: z.boolean().default(false),
});

const pageSchema = z.object({
  start: z.number(), // secondi dall'inizio della clip
  end: z.number(),
  words: z.array(wordSchema),
});

export const reelSchema = z.object({
  video: z.string(),
  durationSeconds: z.number(),
  pages: z.array(pageSchema),
  fontSize: z.number().default(128),
  verticalPosition: z.number().default(0.68),
  uppercase: z.boolean().default(false),
  hookText: z.string().default(''),
  hookSeconds: z.number().default(0),
  images: z.array(z.string()).default([]),
});

export type ReelProps = z.infer<typeof reelSchema>;

export const defaultReelProps: ReelProps = {
  video: 'input.mp4',
  durationSeconds: 5,
  pages: [
    {start: 0.4, end: 1.6, words: [{text: 'anteprima', em: false}, {text: 'caption', em: true}]},
    {start: 1.8, end: 4.5, words: [{text: 'stile', em: false}, {text: 'premium', em: true}]},
  ],
  fontSize: 128,
  verticalPosition: 0.68,
  uppercase: false,
  hookText: '',
  hookSeconds: 0,
  images: [],
};

// ------------------------------------------------------------- FASCIA ---
// Le foto in cima, come nel riferimento mandato da Lorenzo il 4/09: due o
// tre immagini in fila sopra il banner, dentro la fascia nera che il
// formato quadrato lascia libera (il video occupa 420-1500 su 1920).
//
// Entrano sfalsate di un decimo l'una dall'altra, scendendo di poco: se
// comparissero tutte insieme sembrerebbero un collage incollato, cosi
// invece si posano.

const Fascia: React.FC<{images: string[]}> = ({images}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (images.length === 0) {
    return null;
  }

  const GAP = 22;
  // Tre foto stanno in 1008 px con i margini; con due si allarga ciascuna
  // invece di lasciare un buco al centro.
  const larghezza = Math.min(340, (1008 - GAP * (images.length - 1)) / images.length);
  const altezza = 216;

  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: 42,
          display: 'flex',
          gap: GAP,
        }}
      >
        {images.map((src, i) => {
          const t = clamp01((frame / fps - i * 0.1) / 0.42);
          return (
            <div
              key={src}
              style={{
                width: larghezza,
                height: altezza,
                borderRadius: 26,
                overflow: 'hidden',
                backgroundColor: '#111',
                boxShadow: '0 16px 40px rgba(0,0,0,0.55)',
                opacity: ease(t),
                transform: `translateY(${(1 - ease(t)) * -26}px)`,
              }}
            >
              <img
                src={staticFile(src)}
                style={{width: '100%', height: '100%', objectFit: 'cover'}}
              />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- CAPTION ---

const CaptionPage: React.FC<{
  page: z.infer<typeof pageSchema>;
  fontSize: number;
  verticalPosition: number;
  uppercase: boolean;
}> = ({page, fontSize, verticalPosition, uppercase}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const localFrame = frame - Math.round(page.start * fps);

  // Le parole molto lunghe non devono uscire dal riquadro: il corpo si
  // riduce in proporzione alla parola più lunga della pagina
  // Anton e stretto: una lettera occupa circa mezza altezza di corpo, non
  // 0.62 come Instrument Sans. Col rapporto vecchio le parole lunghe
  // venivano rimpicciolite molto piu del necessario.
  const longest = Math.max(...page.words.map((w) => w.text.length), 1);
  const fitted = Math.min(fontSize, Math.floor(980 / (0.52 * longest)));


  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: verticalPosition * 1920,
          transform: 'translateY(-50%)',
          width: '92%',
          textAlign: 'center',
          // Anton: la grottesca stretta e pesantissima del riferimento.
          // Instrument Sans Bold, al confronto, e larga e leggera — e la
          // ragione per cui le caption "non picchiavano".
          fontFamily: 'Anton',
          fontWeight: 400,
          fontSize: fitted,
          lineHeight: 1.02,
          letterSpacing: '0.005em',
          color: 'white',
          // Ombra corta e scura, spostata in basso a destra: nel riferimento
          // le lettere staccano dallo sfondo con un contatto netto, non con
          // l'alone morbido e diffuso di prima.
          textShadow:
            '0 5px 14px rgba(0,0,0,0.85), 0 10px 34px rgba(0,0,0,0.5)',
        }}
      >
        {page.words.map((w, i) => {
          const text = uppercase ? w.text.toUpperCase() : w.text;
          // ENTRATA "SCHIACCIATA". Ricavata fotogramma per fotogramma dal
          // riferimento che Lorenzo ha mandato il 4/09 ("ma quanto sarebbe
          // bello senza sforzo.mov"): al cambio di parola la nuova entra
          // GIA PIU GRANDE del dovuto e si stringe fino alla misura giusta
          // in quattro fotogrammi scarsi. Prima si faceva il contrario —
          // partiva piccola e cresceva — ed e la differenza fra un
          // sottotitolo che picchia e uno che si gonfia.
          const t = clamp01((localFrame / fps - i * 0.04) / 0.13);
          const anim = {
            // inline-block e necessario per scalare la singola parola, ma
            // fa collassare lo spazio fra una e l'altra: lo si rimette
            // come margine
            display: 'inline-block',
            marginRight: i < page.words.length - 1 ? '0.26em' : 0,
            transform: `scale(${1.34 - 0.34 * ease(t)})`,
            opacity: clamp01(t * 4),
          } as const;
          return (
            <span
              key={i}
              style={
                w.em
                  ? {
                      ...anim,
                      // niente corsivo: Anton non ce l'ha e il browser lo
                      // inclinerebbe a forza, con un risultato storto
                      fontSize: '1.09em',
                      textShadow:
                        '0 2px 8px rgba(0,0,0,0.6), 0 10px 44px rgba(0,0,0,0.65), 0 0 60px rgba(255,255,255,0.28)',
                    }
                  : anim
              }
            >
              {text}
              {i < page.words.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------- HOOK BANNER ---
// Banner bianco con testo nero sopra la testa di chi parla (mai a schermo
// pieno, mai su nero): entra con una molla mentre il video già scorre.
// seconds = 0 → resta visibile per tutta la clip.

const HookBanner: React.FC<{text: string; seconds: number; sottoFascia: boolean}> =
  ({text, seconds, sottoFascia}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const total = seconds > 0 ? Math.round(seconds * fps) : Number.MAX_SAFE_INTEGER;
  if (frame > total) {
    return null;
  }
  const fadeOut =
    seconds > 0
      ? interpolate(frame, [total - 9, total], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1;
  const entrance = spring({
    frame,
    fps,
    config: {damping: 15, stiffness: 190, mass: 0.7},
    durationInFrames: 18,
  });
  const scale = interpolate(entrance, [0, 1], [0.88, 1]);
  const opacity = interpolate(frame, [0, 4], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          // Con le foto in cima il banner scende sotto di loro; senza,
          // resta dov'era. In tutti e due i casi sta nella fascia nera o
          // appena sopra la testa, mai sul viso.
          top: sottoFascia ? 288 : 190,
          opacity: opacity * fadeOut,
          transform: `scale(${scale})`,
          maxWidth: '86%',
          backgroundColor: 'white',
          color: 'black',
          textAlign: 'center',
          fontFamily: 'Instrument Sans',
          fontWeight: 700,
          fontSize: 58,
          lineHeight: 1.22,
          padding: '26px 44px',
          borderRadius: 30,
          boxShadow: '0 14px 44px rgba(0,0,0,0.5)',
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- REEL ---

export const Reel: React.FC<ReelProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const fontCss = useFonts();

  const activePage = props.pages.find((p) => t >= p.start && t < p.end);

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <style>{fontCss}</style>
      <OffthreadVideo src={staticFile(props.video)} />
      {activePage ? (
        <CaptionPage
          page={activePage}
          fontSize={props.fontSize}
          verticalPosition={props.verticalPosition}
          uppercase={props.uppercase}
        />
      ) : null}
      <Fascia images={props.images} />
      {props.hookText ? (
        <HookBanner
          text={props.hookText}
          seconds={props.hookSeconds}
          sottoFascia={props.images.length > 0}
        />
      ) : null}
    </AbsoluteFill>
  );
};

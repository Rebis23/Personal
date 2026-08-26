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
  const longest = Math.max(...page.words.map((w) => w.text.length), 1);
  const fitted = Math.min(fontSize, Math.floor(980 / (0.62 * longest)));


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
          fontFamily: 'Instrument Sans',
          fontWeight: 700,
          fontSize: fitted,
          lineHeight: 1.08,
          color: 'white',
          // Ombra diffusa vera: alone morbido + contatto, niente bordo
          textShadow:
            '0 2px 8px rgba(0,0,0,0.55), 0 10px 36px rgba(0,0,0,0.55), 0 24px 80px rgba(0,0,0,0.35)',
        }}
      >
        {page.words.map((w, i) => {
          const text = uppercase ? w.text.toUpperCase() : w.text;
          // Entrata sfalsata di 5 centesimi: scala 0.78 con overshoot,
          // opacita su ease, atterraggio scendendo di 12 px
          const t = clamp01((localFrame / fps - i * 0.05) / 0.24);
          const anim = {
            // inline-block e necessario per scalare la singola parola, ma
            // fa collassare lo spazio fra una e l'altra: lo si rimette
            // come margine
            display: 'inline-block',
            marginRight: i < page.words.length - 1 ? '0.26em' : 0,
            transform: `translateY(${(1 - ease(t)) * -12}px) scale(${
              0.78 + 0.22 * back(t)
            })`,
            opacity: ease(clamp01(t * 1.6)),
          } as const;
          return (
            <span
              key={i}
              style={
                w.em
                  ? {
                      ...anim,
                      fontStyle: 'italic',
                      fontSize: '1.07em',
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

const HookBanner: React.FC<{text: string; seconds: number}> = ({text, seconds}) => {
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
          top: 190,
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
      {props.hookText ? (
        <HookBanner text={props.hookText} seconds={props.hookSeconds} />
      ) : null}
    </AbsoluteFill>
  );
};

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

  // Pop-in a molla: la pagina "entra" con una micro-spinta morbida
  const pop = spring({
    frame: localFrame,
    fps,
    config: {damping: 16, stiffness: 220, mass: 0.6},
    durationInFrames: 14,
  });
  const scale = interpolate(pop, [0, 1], [0.9, 1]);
  const opacity = interpolate(localFrame, [0, 3], [0, 1], {
    extrapolateRight: 'clamp',
  });

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
          transform: `translateY(-50%) scale(${scale})`,
          opacity,
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
          return (
            <span
              key={i}
              style={
                w.em
                  ? {
                      fontStyle: 'italic',
                      fontSize: '1.07em',
                      textShadow:
                        '0 2px 8px rgba(0,0,0,0.6), 0 10px 44px rgba(0,0,0,0.65), 0 0 60px rgba(255,255,255,0.28)',
                    }
                  : undefined
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

// ----------------------------------------------------------- HOOK CARD ---

const HookCard: React.FC<{text: string; seconds: number}> = ({text, seconds}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const total = Math.round(seconds * fps);
  if (frame > total) {
    return null;
  }
  const fadeOut = interpolate(frame, [total - 9, total], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const entrance = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 160, mass: 0.7},
    durationInFrames: 16,
  });
  const scale = interpolate(entrance, [0, 1], [0.96, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: `rgba(0,0,0,${0.94 * fadeOut})`,
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          opacity: fadeOut,
          transform: `scale(${scale})`,
          width: '80%',
          textAlign: 'center',
          fontFamily: 'Instrument Sans',
          fontWeight: 700,
          fontSize: 92,
          lineHeight: 1.14,
          letterSpacing: '0.01em',
          color: 'white',
          textTransform: 'uppercase',
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

  // Niente caption finché la hook card è a schermo
  const captionsFrom = props.hookText ? props.hookSeconds : 0;
  const activePage =
    t >= captionsFrom
      ? props.pages.find((p) => t >= p.start && t < p.end)
      : undefined;

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
      {props.hookText && props.hookSeconds > 0 ? (
        <HookCard text={props.hookText} seconds={props.hookSeconds} />
      ) : null}
    </AbsoluteFill>
  );
};

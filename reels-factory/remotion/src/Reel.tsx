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
import {C, OMBRA, back, clamp01, ease} from './tokens';

// role: come il playbook colora le parole —
//   neutral = bianco caldo · key = giallo · red = rosso timbro (costi, negazioni)
const wordSchema = z.object({
  text: z.string(),
  role: z.enum(['neutral', 'key', 'red']).default('neutral'),
  start: z.number().default(-1), // secondi assoluti: quando viene pronunciata
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
  fontSize: z.number().default(150),
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
    {
      start: 0.4,
      end: 1.8,
      words: [
        {text: 'lo', role: 'neutral', start: 0.4},
        {text: 'sforzo', role: 'key', start: 0.7},
        {text: 'non', role: 'red', start: 1.1},
      ],
    },
    {
      start: 1.8,
      end: 4.5,
      words: [
        {text: 'paga', role: 'neutral', start: 1.8},
        {text: 'le', role: 'neutral', start: 2.1},
        {text: 'bollette', role: 'key', start: 2.3},
      ],
    },
  ],
  fontSize: 150,
  verticalPosition: 0.68,
  uppercase: false,
  hookText: '',
  hookSeconds: 0,
};

const COLORE = {
  neutral: C.biancoCaldo,
  key: C.giallo,
  red: C.rossoTimbro,
} as const;

// ------------------------------------------------------------- CAPTION ---
// Karaoke del playbook: ogni parola compare quando viene pronunciata, con il
// pop a molla (scala 0.75 → back, alpha su ease, atterraggio da 14 px sopra).

const Parola: React.FC<{
  word: z.infer<typeof wordSchema>;
  pageStart: number;
  indice: number;
  uppercase: boolean;
}> = ({word, pageStart, indice, uppercase}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Il blocco e visibile dal SUO inizio (regola del playbook), non parola per
  // parola man mano che viene pronunciata: con quella lettura a schermo
  // restava spesso una parolina sola. Le parole entrano comunque in
  // sequenza, sfalsate di pochi centesimi, cosi il pop resta vivo.
  const nasce = pageStart + indice * 0.05;
  const t = clamp01((frame / fps - nasce) / 0.24); // 0.24s di ingresso
  const scale = 0.75 + (1 - 0.75) * back(t);
  const opacity = ease(clamp01(t * 1.6));
  const dy = (1 - ease(t)) * -14; // atterra scendendo di 14 px

  const text = uppercase ? word.text.toUpperCase() : word.text;
  return (
    <span
      style={{
        display: 'inline-block',
        transform: `translateY(${dy}px) scale(${scale})`,
        opacity,
        color: COLORE[word.role],
        // Le parole-chiave pesano di piu, come le scritte a mano del playbook
        fontWeight: word.role === 'neutral' ? 600 : 700,
        margin: '0 0.14em',
      }}
    >
      {text}
    </span>
  );
};

const CaptionPage: React.FC<{
  page: z.infer<typeof pageSchema>;
  fontSize: number;
  verticalPosition: number;
  uppercase: boolean;
}> = ({page, fontSize, verticalPosition, uppercase}) => {
  // Caveat ha occhio piccolo: le parole lunghe rientrano comunque, ma il
  // corpo si riduce se la riga rischia di sbordare
  const longest = Math.max(...page.words.map((w) => w.text.length), 1);
  const fitted = Math.min(fontSize, Math.floor(1120 / (0.46 * longest)));

  return (
    <AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: verticalPosition * 1920,
          transform: 'translateY(-50%)',
          width: '92%',
          textAlign: 'center',
          fontFamily: 'Caveat',
          fontSize: fitted,
          lineHeight: 1.02,
          textShadow: OMBRA,
        }}
      >
        {page.words.map((w, i) => (
          <Parola
            key={i}
            word={w}
            pageStart={page.start}
            indice={i}
            uppercase={uppercase}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------- HOOK BANNER ---
// Cartoncino di carta con l'inchiostro verde scuro, appena ruotato: il
// "takeover carta" del playbook ridotto a banner sopra la testa, che e la
// posizione approvata da Lorenzo. Entra con la molla mentre il video scorre.

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
    config: {damping: 14, stiffness: 200, mass: 0.7},
    durationInFrames: 20,
  });
  const scale = interpolate(entrance, [0, 1], [0.86, 1]);
  const rot = interpolate(entrance, [0, 1], [-4.2, -1.4]); // si posa storto
  const opacity = interpolate(frame, [0, 4], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: 175,
          opacity: opacity * fadeOut,
          transform: `scale(${scale}) rotate(${rot}deg)`,
          maxWidth: '86%',
          backgroundColor: C.carta,
          color: C.inchiostro,
          textAlign: 'center',
          fontFamily: 'Caveat',
          fontWeight: 700,
          fontSize: 76,
          lineHeight: 1.06,
          padding: '30px 48px 22px',
          borderRadius: 10,
          boxShadow: '0 18px 50px rgba(0,0,0,0.55)',
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
    <AbsoluteFill style={{backgroundColor: C.neroCaldo}}>
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

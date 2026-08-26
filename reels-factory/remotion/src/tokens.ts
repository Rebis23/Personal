/**
 * Token visivi del playbook "Riflettendo Edit" (stile George Alexander).
 * I valori sono quelli esatti del documento: non inventarne di nuovi.
 */
export const C = {
  carta: '#F5F2EA',
  inchiostro: '#2F4E40',
  giallo: '#E8C34A',
  senape: '#C9A227',
  neroCaldo: '#0D100E',
  biancoCaldo: '#F5F1E8',
  rossoTimbro: '#A84A3C',
  grigioCaldo: '#6E6A60',
} as const;

/** Curve del playbook. t è normalizzato 0→1. */
export const ease = (t: number) => 1 - Math.pow(1 - t, 3); // easeOutCubic
export const back = (t: number) =>
  1 + 2.70158 * Math.pow(t - 1, 3) + 1.70158 * Math.pow(t - 1, 2); // overshoot ~1.1
export const springCurve = (t: number) =>
  1 - Math.exp(-5.2 * t) * Math.cos(11 * t);

export const clamp01 = (t: number) => Math.max(0, Math.min(1, t));

/** Ombra dei flottanti: scura, sfocata, offset +4/+6 (playbook Fase 5). */
export const OMBRA =
  '4px 6px 5px rgba(0,0,0,0.55), 0 12px 40px rgba(0,0,0,0.45)';

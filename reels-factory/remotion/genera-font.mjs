// Rigenera src/font-data.ts incorporando i .ttf di public/fonts come
// data-URI. Serve perche Remotion renderizza in un browser headless senza
// rete: un @font-face che punta a un file esterno resterebbe senza font e le
// caption uscirebbero col ripiego di sistema.
//
//   node genera-font.mjs
//
// Anton e sotto SIL Open Font License (public/fonts/Anton-OFL.txt): si puo
// incorporare e usare su contenuti commerciali.

import {readFileSync, writeFileSync} from 'node:fs';

const FACCE = [
  {file: 'Anton-Regular.ttf', family: 'Anton', weight: 400, style: 'normal'},
  {file: 'InstrumentSans-Bold.ttf', family: 'Instrument Sans', weight: 700, style: 'normal'},
  {file: 'InstrumentSans-BoldItalic.ttf', family: 'Instrument Sans', weight: 700, style: 'italic'},
];

const blocchi = FACCE.map(({file, family, weight, style}) => {
  const b64 = readFileSync(new URL(`public/fonts/${file}`, import.meta.url)).toString('base64');
  return `@font-face {
  font-family: '${family}';
  font-weight: ${weight};
  font-style: ${style};
  src: url(data:font/ttf;base64,${b64}) format('truetype');
}`;
});

writeFileSync(
  new URL('src/font-data.ts', import.meta.url),
  `// Generato da genera-font.mjs: NON modificare a mano.
// I font sono incorporati come data-URI, cosi il rendering non dipende da
// nessuna richiesta di rete del browser headless.
export const FONT_CSS = \`
${blocchi.join('\n\n')}
\`;
`,
);

console.log(`font-data.ts rigenerato con ${FACCE.length} facce`);

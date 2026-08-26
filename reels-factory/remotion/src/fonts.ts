import {useEffect, useState} from 'react';
import {continueRender, delayRender} from 'remotion';
import {FONT_CSS} from './font-data';

/**
 * Inietta i font (incorporati come data-URI) e blocca il rendering
 * finché il browser non li ha caricati: nessuna richiesta di rete.
 */
export const useFonts = (): string => {
  const [handle] = useState(() => delayRender('Caricamento font'));

  useEffect(() => {
    Promise.all([
      document.fonts.load("700 100px 'Instrument Sans'"),
      document.fonts.load("italic 700 100px 'Instrument Sans'"),
    ])
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);

  return FONT_CSS;
};

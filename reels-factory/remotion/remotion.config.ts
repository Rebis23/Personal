import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// In locale / CI si può indicare un Chromium già presente sulla macchina
// (evita il download del browser headless di Remotion)
const executable = process.env.REMOTION_BROWSER_EXECUTABLE;
if (executable) {
  Config.setBrowserExecutable(executable);
}

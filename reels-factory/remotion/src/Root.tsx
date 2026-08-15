import {Composition} from 'remotion';
import {Reel, reelSchema, defaultReelProps} from './Reel';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Reel"
      component={Reel}
      width={1080}
      height={1920}
      fps={30}
      schema={reelSchema}
      defaultProps={defaultReelProps}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(30, Math.ceil(props.durationSeconds * 30)),
      })}
    />
  );
};

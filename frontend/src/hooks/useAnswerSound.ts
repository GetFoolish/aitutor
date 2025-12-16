import { useEffect, useRef } from 'react';

export const useAnswerSound = () => {
  const correctSound = useRef<HTMLAudioElement | null>(null);
  const wrongSound = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Preload sounds for instant playback
    correctSound.current = new Audio('/sounds/correct.wav');
    wrongSound.current = new Audio('/sounds/wrong.wav');
    
    // Set volume to 50% for non-intrusive feedback
    if (correctSound.current) correctSound.current.volume = 0.5;
    if (wrongSound.current) wrongSound.current.volume = 0.5;
  }, []);

  const playCorrectSound = () => {
    correctSound.current?.play().catch(err => 
      console.log('Sound play prevented by browser:', err)
    );
  };

  const playWrongSound = () => {
    wrongSound.current?.play().catch(err => 
      console.log('Sound play prevented by browser:', err)
    );
  };

  return { playCorrectSound, playWrongSound };
};

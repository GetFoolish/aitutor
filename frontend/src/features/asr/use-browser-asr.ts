/**
 * useBrowserASR — Web Speech API speech recognition hook.
 *
 * Ported from OpenMAIC's lib/audio/asr-providers.ts (browser-native approach).
 * Used as a lightweight STT alternative when Gemini Live is not connected.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

type SpeechRecognitionAny = typeof window extends { SpeechRecognition: infer T }
  ? T
  : typeof window extends { webkitSpeechRecognition: infer T }
  ? T
  : never;

function getSpeechRecognition(): SpeechRecognitionAny | null {
  const win = window as any;
  const Ctor = win.SpeechRecognition || win.webkitSpeechRecognition || null;
  return Ctor ? new Ctor() : null;
}

interface UseBrowserASROptions {
  language?: string;
  continuous?: boolean;
  onTranscript?: (text: string, isFinal: boolean) => void;
}

export function useBrowserASR(options: UseBrowserASROptions = {}) {
  const { language = 'en-US', continuous = false, onTranscript } = options;
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [supported] = useState(() => !!getSpeechRecognition());
  const recognitionRef = useRef<any>(null);

  // Keep callback ref fresh
  const onTranscriptRef = useRef(onTranscript);
  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);

  const start = useCallback(() => {
    if (!supported) {
      setError('Web Speech API is not supported in this browser.');
      return;
    }

    const recognition = getSpeechRecognition() as any;
    recognition.lang = language;
    recognition.continuous = continuous;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setListening(true);
      setError(null);
      setTranscript('');
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      const text = finalTranscript || interimTranscript;
      const isFinal = !!finalTranscript;
      setTranscript(text);
      onTranscriptRef.current?.(text, isFinal);
    };

    recognition.onerror = (event: any) => {
      setError(`Speech recognition error: ${event.error}`);
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [supported, language, continuous]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  return {
    start,
    stop,
    listening,
    transcript,
    error,
    supported,
  };
}

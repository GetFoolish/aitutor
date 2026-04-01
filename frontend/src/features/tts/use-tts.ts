/**
 * useTTS — React hook for multi-provider text-to-speech.
 *
 * Persists provider/voice/speed preferences to localStorage.
 * Exposes speak(), stop(), and current state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { speakText, stopAllTTS, getBrowserNativeVoices, TTSHandle } from './tts-service';
import type { TTSModelConfig, TTSProviderId } from './types';
import { TTS_SETTINGS_KEY } from './types';
import { DEFAULT_TTS_PROVIDER, TTS_PROVIDERS } from './constants';

interface TTSSettings {
  providerId: TTSProviderId;
  voice: string;
  speed: number;
  apiKey?: string;
}

function loadSettings(): TTSSettings {
  try {
    const raw = localStorage.getItem(TTS_SETTINGS_KEY);
    if (raw) return JSON.parse(raw) as TTSSettings;
  } catch {
    // ignore
  }
  return {
    providerId: DEFAULT_TTS_PROVIDER,
    voice: '',
    speed: 1.0,
  };
}

export function useTTS() {
  const [settings, setSettingsState] = useState<TTSSettings>(loadSettings);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handleRef = useRef<TTSHandle | null>(null);
  const [browserVoices, setBrowserVoices] = useState<SpeechSynthesisVoice[]>([]);

  // Load browser voices (they populate asynchronously)
  useEffect(() => {
    const refresh = () => setBrowserVoices(getBrowserNativeVoices());
    refresh();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.addEventListener('voiceschanged', refresh);
      return () => window.speechSynthesis.removeEventListener('voiceschanged', refresh);
    }
  }, []);

  const saveSettings = useCallback((next: Partial<TTSSettings>) => {
    setSettingsState((prev) => {
      const updated = { ...prev, ...next };
      localStorage.setItem(TTS_SETTINGS_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const speak = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setError(null);
      setSpeaking(true);

      // Default voice for provider if unset
      const providerConfig = TTS_PROVIDERS[settings.providerId];
      const voice =
        settings.voice ||
        (settings.providerId === 'browser-native-tts'
          ? '' // browser picks system default
          : providerConfig.voices[0]?.id ?? '');

      const config: TTSModelConfig = {
        providerId: settings.providerId,
        voice,
        speed: settings.speed,
        apiKey: settings.apiKey,
      };

      try {
        handleRef.current = await speakText(config, text);
        setSpeaking(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
        setSpeaking(false);
      }
    },
    [settings],
  );

  const stop = useCallback(() => {
    handleRef.current?.stop();
    stopAllTTS();
    setSpeaking(false);
  }, []);

  return {
    speak,
    stop,
    speaking,
    error,
    settings,
    saveSettings,
    browserVoices,
    provider: TTS_PROVIDERS[settings.providerId],
  };
}

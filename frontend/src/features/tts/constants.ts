/**
 * TTS Provider Registry
 *
 * Ported from OpenMAIC's lib/audio/constants.ts.
 * Add new providers here and in tts-service.ts.
 */

import type { TTSProviderConfig, TTSProviderId } from './types';

export const TTS_PROVIDERS: Record<TTSProviderId, TTSProviderConfig> = {
  'browser-native-tts': {
    id: 'browser-native-tts',
    name: 'Browser Native',
    requiresApiKey: false,
    voices: [], // populated at runtime from speechSynthesis.getVoices()
    speedRange: { min: 0.5, max: 2.0, default: 1.0 },
  },
  'openai-tts': {
    id: 'openai-tts',
    name: 'OpenAI TTS',
    requiresApiKey: true,
    defaultBaseUrl: 'https://api.openai.com/v1',
    voices: [
      { id: 'alloy', name: 'Alloy', language: 'en', gender: 'neutral' },
      { id: 'echo', name: 'Echo', language: 'en', gender: 'male' },
      { id: 'fable', name: 'Fable', language: 'en', gender: 'neutral' },
      { id: 'onyx', name: 'Onyx', language: 'en', gender: 'male' },
      { id: 'nova', name: 'Nova', language: 'en', gender: 'female' },
      { id: 'shimmer', name: 'Shimmer', language: 'en', gender: 'female' },
    ],
    speedRange: { min: 0.25, max: 4.0, default: 1.0 },
  },
  'elevenlabs-tts': {
    id: 'elevenlabs-tts',
    name: 'ElevenLabs',
    requiresApiKey: true,
    defaultBaseUrl: 'https://api.elevenlabs.io/v1',
    voices: [
      { id: 'JBFqnCBsd6RMkjVDRZzb', name: 'George', language: 'en', gender: 'male' },
      { id: 'cgSgspJ2msm6clMCkdW9', name: 'Jessica', language: 'en', gender: 'female' },
      { id: 'iP95p4xoKVk53GoZ742B', name: 'Chris', language: 'en', gender: 'male' },
      { id: 'onwK4e9ZLuTAKqWW03F9', name: 'Daniel', language: 'en', gender: 'male' },
      { id: 'XB0fDUnXU5powFXDhCwa', name: 'Charlotte', language: 'en', gender: 'female' },
    ],
    speedRange: { min: 0.7, max: 1.2, default: 1.0 },
  },
};

export const DEFAULT_TTS_PROVIDER: TTSProviderId = 'browser-native-tts';

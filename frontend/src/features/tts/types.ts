/**
 * TTS (Text-to-Speech) Type Definitions
 *
 * Ported from OpenMAIC's lib/audio/types.ts architecture.
 * Provider-agnostic types for multi-provider TTS support.
 */

export type TTSProviderId =
  | 'browser-native-tts'
  | 'openai-tts'
  | 'elevenlabs-tts';

export interface TTSVoiceInfo {
  id: string;
  name: string;
  language: string;
  gender?: 'male' | 'female' | 'neutral';
  description?: string;
}

export interface TTSProviderConfig {
  id: TTSProviderId;
  name: string;
  requiresApiKey: boolean;
  defaultBaseUrl?: string;
  icon?: string;
  voices: TTSVoiceInfo[];
  speedRange: { min: number; max: number; default: number };
}

export interface TTSModelConfig {
  providerId: TTSProviderId;
  voice: string;
  speed?: number;
  apiKey?: string;
  baseUrl?: string;
}

export interface TTSGenerationResult {
  audio: ArrayBuffer;
  format: 'mp3' | 'wav' | 'ogg';
}

/** localStorage key for persisting TTS preferences */
export const TTS_SETTINGS_KEY = 'aitutor_tts_settings';

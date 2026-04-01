export { useTTS } from './use-tts';
export { speakText, stopAllTTS, getBrowserNativeVoices } from './tts-service';
export { TTS_PROVIDERS, DEFAULT_TTS_PROVIDER } from './constants';
export type {
  TTSProviderId,
  TTSVoiceInfo,
  TTSProviderConfig,
  TTSModelConfig,
  TTSGenerationResult,
} from './types';

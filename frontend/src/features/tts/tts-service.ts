/**
 * TTS Service
 *
 * Factory pattern for routing TTS requests to the appropriate provider.
 * Ported from OpenMAIC's lib/audio/tts-providers.ts architecture.
 *
 * Browser Native: runs entirely client-side via Web Speech API.
 * OpenAI / ElevenLabs: proxied through aitutor backend (/api/tts) to keep API keys server-side.
 */

import type { TTSModelConfig, TTSGenerationResult } from './types';

// @ts-ignore — Vite replaces import.meta.env at build time
const TEACHING_ASSISTANT_API_URL: string =
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (typeof (import.meta as any).env !== 'undefined'
    ? (import.meta as any).env.VITE_TEACHING_ASSISTANT_API_URL
    : undefined) || 'http://localhost:8002';

// ─── Browser Native ────────────────────────────────────────────────────────────

let currentUtterance: SpeechSynthesisUtterance | null = null;

function speakBrowserNative(config: TTSModelConfig, text: string): void {
  if (!('speechSynthesis' in window)) {
    throw new Error('Web Speech API not supported in this browser.');
  }
  stopBrowserNative();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = config.speed ?? 1.0;

  if (config.voice) {
    const voices = window.speechSynthesis.getVoices();
    const match = voices.find(
      (v) => v.name === config.voice || v.voiceURI === config.voice,
    );
    if (match) utterance.voice = match;
  }

  currentUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

function stopBrowserNative(): void {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  currentUtterance = null;
}

// ─── Proxied providers (OpenAI, ElevenLabs) ────────────────────────────────────

async function generateProxiedTTS(
  config: TTSModelConfig,
  text: string,
): Promise<TTSGenerationResult> {
  const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: config.providerId,
      text,
      voice: config.voice,
      speed: config.speed ?? 1.0,
      api_key: config.apiKey,
      base_url: config.baseUrl,
    }),
  });

  if (!response.ok) {
    const err = await response.text().catch(() => response.statusText);
    throw new Error(`TTS API error (${response.status}): ${err}`);
  }

  const audio = await response.arrayBuffer();
  return { audio, format: 'mp3' };
}

// ─── Public API ────────────────────────────────────────────────────────────────

export type TTSHandle = {
  stop: () => void;
};

/**
 * Speak text using the configured provider.
 *
 * For browser-native: fires and forgets (no audio buffer returned).
 * For proxied: downloads audio and plays it via an HTMLAudioElement.
 *
 * Returns a handle to stop playback early.
 */
export async function speakText(
  config: TTSModelConfig,
  text: string,
): Promise<TTSHandle> {
  if (config.providerId === 'browser-native-tts') {
    speakBrowserNative(config, text);
    return { stop: stopBrowserNative };
  }

  const result = await generateProxiedTTS(config, text);
  const blob = new Blob([result.audio], { type: 'audio/mpeg' });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);

  const handle: TTSHandle = {
    stop: () => {
      audio.pause();
      audio.currentTime = 0;
      URL.revokeObjectURL(url);
    },
  };

  audio.addEventListener('ended', () => URL.revokeObjectURL(url));
  await audio.play();
  return handle;
}

export function stopAllTTS(): void {
  stopBrowserNative();
}

/** Return voices available for the browser-native provider at runtime. */
export function getBrowserNativeVoices(): SpeechSynthesisVoice[] {
  if (!('speechSynthesis' in window)) return [];
  return window.speechSynthesis.getVoices();
}

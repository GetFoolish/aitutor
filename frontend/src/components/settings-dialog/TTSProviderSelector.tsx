/**
 * TTSProviderSelector
 *
 * Settings UI for choosing TTS provider, voice, speed, and API key.
 * Integrated from OpenMAIC's multi-provider TTS architecture.
 */

import { useEffect, useState } from 'react';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { useTTS } from '../../features/tts';
import { TTS_PROVIDERS } from '../../features/tts/constants';
import type { TTSProviderId } from '../../features/tts/types';

const PROVIDER_OPTIONS: { value: TTSProviderId; label: string }[] = [
  { value: 'browser-native-tts', label: 'Browser Native (free)' },
  { value: 'openai-tts', label: 'OpenAI TTS' },
  { value: 'elevenlabs-tts', label: 'ElevenLabs' },
];

export default function TTSProviderSelector() {
  const { settings, saveSettings, browserVoices, speak, stop, speaking } = useTTS();
  const [previewText, setPreviewText] = useState('Hello! I am your AI tutor.');

  const providerConfig = TTS_PROVIDERS[settings.providerId];

  // Build voice list for current provider
  const voices =
    settings.providerId === 'browser-native-tts'
      ? browserVoices.map((v) => ({ id: v.name, name: v.name, language: v.lang }))
      : providerConfig.voices;

  // Reset voice when provider changes
  useEffect(() => {
    saveSettings({ voice: voices[0]?.id ?? '' });
     
  }, [settings.providerId]);

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold">Read-Aloud TTS</h4>

      {/* Provider */}
      <div className="space-y-1">
        <Label htmlFor="tts-provider">Provider</Label>
        <Select
          value={settings.providerId}
          onValueChange={(v) => saveSettings({ providerId: v as TTSProviderId })}
        >
          <SelectTrigger id="tts-provider">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROVIDER_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* API key (when required) */}
      {providerConfig.requiresApiKey && (
        <div className="space-y-1">
          <Label htmlFor="tts-api-key">API Key</Label>
          <Input
            id="tts-api-key"
            type="password"
            placeholder={`${providerConfig.name} API key`}
            value={settings.apiKey ?? ''}
            onChange={(e) => saveSettings({ apiKey: e.target.value })}
          />
        </div>
      )}

      {/* Voice */}
      {voices.length > 0 && (
        <div className="space-y-1">
          <Label htmlFor="tts-voice">Voice</Label>
          <Select
            value={settings.voice || voices[0]?.id}
            onValueChange={(v) => saveSettings({ voice: v })}
          >
            <SelectTrigger id="tts-voice">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {voices.map((v) => (
                <SelectItem key={v.id} value={v.id}>
                  {v.name}
                  {v.language && v.language !== 'en' ? ` (${v.language})` : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Speed */}
      <div className="space-y-1">
        <Label htmlFor="tts-speed">
          Speed: {settings.speed.toFixed(1)}x
        </Label>
        <input
          id="tts-speed"
          type="range"
          min={providerConfig.speedRange.min}
          max={providerConfig.speedRange.max}
          step={0.1}
          value={settings.speed}
          onChange={(e) => saveSettings({ speed: parseFloat(e.target.value) })}
          className="w-full accent-primary"
        />
      </div>

      {/* Preview */}
      <div className="space-y-1">
        <Label htmlFor="tts-preview">Preview</Label>
        <div className="flex gap-2">
          <Input
            id="tts-preview"
            value={previewText}
            onChange={(e) => setPreviewText(e.target.value)}
            placeholder="Type text to preview..."
          />
          <button
            type="button"
            onClick={() => (speaking ? stop() : speak(previewText))}
            className="px-3 py-1 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90"
          >
            {speaking ? 'Stop' : 'Play'}
          </button>
        </div>
      </div>
    </div>
  );
}

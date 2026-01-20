/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TutorClient } from "./tutor-client";
import { AudioStreamer } from "./audio-streamer";
import { audioContext } from "../../lib/utils";
import VolMeterWorket from "../../lib/worklets/vol-meter";
import { LiveConnectConfig } from "@google/genai";
import { useAuth } from "../../contexts/AuthContext";
import { apiUtils } from "../../lib/api-utils";

// Auto-reconnect configuration
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAY_MS = 2000;

export type UseTutorResults = {
  client: TutorClient;
  setConfig: (config: LiveConnectConfig) => void;
  config: LiveConnectConfig;
  connected: boolean;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  interruptAudio: () => void;
  volume: number;
  assessmentMode?: boolean;
};

export function useTutor(assessmentMode?: boolean): UseTutorResults {
  const client = useMemo(() => new TutorClient(), []);
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const { user } = useAuth();

  const [config, setConfig] = useState<LiveConnectConfig>({});
  const [connected, setConnected] = useState(false);
  const [volume, setVolume] = useState(0);

  // Auto-reconnect state
  const reconnectAttemptsRef = useRef(0);
  const isReconnectingRef = useRef(false);
  const configRef = useRef<LiveConnectConfig>({});
  const userLanguageRef = useRef<string>("English");

  // Keep refs in sync with state
  useEffect(() => {
    configRef.current = config;
  }, [config]);

  useEffect(() => {
    userLanguageRef.current = user?.preferred_language || "English";
  }, [user?.preferred_language]);

  // register audio for streaming server -> speakers
  useEffect(() => {
    if (!audioStreamerRef.current) {
      audioContext({ id: "audio-out" }).then((audioCtx: AudioContext) => {
        audioStreamerRef.current = new AudioStreamer(audioCtx);

        // Throttling mechanism for volume updates
        let lastUpdate = 0;
        const THROTTLE_MS = 100; // Update volume at most every 100ms (10 FPS)

        audioStreamerRef.current
          .addWorklet<any>("vumeter-out", VolMeterWorket, (ev: any) => {
            const now = Date.now();
            if (now - lastUpdate >= THROTTLE_MS) {
              setVolume(ev.data.volume);
              lastUpdate = now;
            }
          })
          .then(() => {
            // Successfully added worklet
          });
      });
    }
  }, [audioStreamerRef]);

  useEffect(() => {
    const onOpen = () => {
      setConnected(true);
      // Reset reconnect attempts on successful connection
      reconnectAttemptsRef.current = 0;
      isReconnectingRef.current = false;
    };

    const onClose = (event?: { reason?: string }) => {
      setConnected(false);
      const reason = event?.reason || '';

      // Check if this is a connection error that we should auto-reconnect
      // Include: deadline errors, timeouts, unknown disconnects (not user-initiated)
      const isReconnectableError = reason.toLowerCase().includes('deadline') ||
                                   reason.toLowerCase().includes('timeout') ||
                                   reason.toLowerCase().includes('expired') ||
                                   reason.toLowerCase().includes('unknown');

      if (isReconnectableError && !isReconnectingRef.current) {
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          isReconnectingRef.current = true;

          console.log(`%c[TUTOR] 🔄 Auto-reconnecting after disconnect (reason: ${reason || 'none'}) - attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS}...`,
            'color: #F39C12; font-weight: bold;');

          // Delay before reconnecting
          setTimeout(async () => {
            try {
              client.disconnect();
              await client.connect(configRef.current, userLanguageRef.current);
              console.log('%c[TUTOR] ✅ Auto-reconnect successful!', 'color: #27AE60; font-weight: bold;');
            } catch (error) {
              console.error('[TUTOR] Auto-reconnect failed:', error);
              isReconnectingRef.current = false;
            }
          }, RECONNECT_DELAY_MS);
        } else {
          console.log('%c[TUTOR] ❌ Max reconnect attempts reached. Please refresh the page.',
            'color: #E74C3C; font-weight: bold;');
          reconnectAttemptsRef.current = 0;
          isReconnectingRef.current = false;
        }
      }
    };

    const onError = (error: ErrorEvent) => {
      console.error("error", error);
    };

    const stopAudioStreamer = () => audioStreamerRef.current?.stop();

    const onAudio = (data: ArrayBuffer) =>
      audioStreamerRef.current?.addPCM16(new Uint8Array(data));

    const onTokenUsage = async (usage: { 
      promptTokenCount: number; 
      candidatesTokenCount: number; 
      totalTokenCount: number;
      cachedContentTokenCount?: number;
      thoughtTokenCount?: number;
      promptTokensDetails?: Array<{ modality: string; tokenCount: number }>;
    }) => {
      try {
        const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';
        await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/tutor/token-usage`, usage);
      } catch (err) {
        console.error("Failed to track token usage:", err);
      }
    };

    client
      .on("error", onError)
      .on("open", onOpen)
      .on("close", onClose)
      .on("interrupted", stopAudioStreamer)
      .on("audio", onAudio)
      .on("tokenUsage", onTokenUsage);

    return () => {
      client
        .off("error", onError)
        .off("open", onOpen)
        .off("close", onClose)
        .off("interrupted", stopAudioStreamer)
        .off("audio", onAudio)
        .off("tokenUsage", onTokenUsage)
        .disconnect();
    };
  }, [client]);

  const connect = useCallback(async () => {
    if (!config) {
      throw new Error("config has not been set");
    }
    client.disconnect();
    // Pass preferred language and assessment mode from context
    const preferredLanguage = user?.preferred_language || "English";
    await client.connect(config, preferredLanguage, assessmentMode);
  }, [client, config, user?.preferred_language, assessmentMode]);

  const disconnect = useCallback(async () => {
    client.disconnect();
    setConnected(false);
  }, [setConnected, client]);

  const interruptAudio = useCallback(() => {
    audioStreamerRef.current?.stop();
  }, []);

  return {
    client,
    config,
    setConfig,
    connected,
    connect,
    disconnect,
    interruptAudio,
    volume,
    assessmentMode,
  };
}

// Export alias for backward compatibility during migration
export { useTutor as useLiveAPI };
export type { UseTutorResults as UseLiveAPIResults };

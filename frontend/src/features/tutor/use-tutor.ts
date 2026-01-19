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

export type UseTutorResults = {
  client: TutorClient;
  setConfig: (config: LiveConnectConfig) => void;
  config: LiveConnectConfig;
  connected: boolean;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  interruptAudio: () => void;
  volume: number;
};

export function useTutor(): UseTutorResults {
  const client = useMemo(() => new TutorClient(), []);
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const { user } = useAuth();

  const [config, setConfig] = useState<LiveConnectConfig>({});
  const [connected, setConnected] = useState(false);
  const [volume, setVolume] = useState(0);

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
    };

    const onClose = () => {
      setConnected(false);
    };

    const onError = (error: ErrorEvent) => {
      console.error("error", error);
    };

    const stopAudioStreamer = () => audioStreamerRef.current?.stop();

    const onAudio = (data: ArrayBuffer) =>
      audioStreamerRef.current?.addPCM16(new Uint8Array(data));

    client
      .on("error", onError)
      .on("open", onOpen)
      .on("close", onClose)
      .on("interrupted", stopAudioStreamer)
      .on("audio", onAudio);

    return () => {
      client
        .off("error", onError)
        .off("open", onOpen)
        .off("close", onClose)
        .off("interrupted", stopAudioStreamer)
        .off("audio", onAudio)
        .disconnect();
    };
  }, [client]);

  const connect = useCallback(async () => {
    if (!config) {
      throw new Error("config has not been set");
    }
    client.disconnect();
    // Pass preferred language from user context
    const preferredLanguage = user?.preferred_language || "English";
    await client.connect(config, preferredLanguage);
  }, [client, config, user?.preferred_language]);

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
  };
}

// Export alias for backward compatibility during migration
export { useTutor as useLiveAPI };
export type { UseTutorResults as UseLiveAPIResults };

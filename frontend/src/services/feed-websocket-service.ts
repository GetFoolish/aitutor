/**
 * Feed WebSocket Service (binary audio + jitter/lag fixed)
 *
 * Binary protocol:
 *  - Audio chunks are sent as WS binary frames (ArrayBuffer)
 *  - Optional metadata JSON messages can be sent occasionally
 *
 * Fixes jitter/lag by:
 *  - Jitter-buffering outbound audio and sending at steady cadence
 *  - Dropping oldest on overflow to reduce latency
 *  - Avoiding base64 overhead entirely for audio
 *  - Preventing reconnect storms / duplicate timers
 */

import { jwtUtils } from "../lib/jwt-utils";

const TEACHING_ASSISTANT_WS_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_WS_URL ||
  (import.meta.env.VITE_TEACHING_ASSISTANT_API_URL?.replace("http", "ws") || "ws://localhost:8002");

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";
type StatusCallback = (status: ConnectionStatus) => void;

class BinaryAudioJitterSender {
  private queue: ArrayBuffer[] = [];
  private running = false;
  private timer: number | null = null;

  private readonly targetBufferedMs: number;
  private readonly flushIntervalMs: number;
  private readonly maxQueueChunks: number;

  private readonly emitFn: (chunk: ArrayBuffer) => void;

  constructor(opts: {
    emitFn: (chunk: ArrayBuffer) => void;
    targetBufferedMs?: number;
    flushIntervalMs?: number;
    maxQueueChunks?: number;
  }) {
    this.emitFn = opts.emitFn;
    this.targetBufferedMs = opts.targetBufferedMs ?? 80;
    this.flushIntervalMs = opts.flushIntervalMs ?? 20;
    this.maxQueueChunks = opts.maxQueueChunks ?? 400;
  }

  push(chunk: ArrayBuffer) {
    if (this.queue.length >= this.maxQueueChunks) {
      // drop oldest to reduce latency
      this.queue.shift();
    }
    this.queue.push(chunk);

    if (!this.running) {
      const approxBufferedMs = this.queue.length * this.flushIntervalMs;
      if (approxBufferedMs >= this.targetBufferedMs) this.start();
    }
  }

  private start() {
    if (this.running) return;
    this.running = true;

    const tick = () => {
      if (!this.running) return;

      const next = this.queue.shift();
      if (!next) {
        this.stop();
        return;
      }

      this.emitFn(next);
      this.timer = window.setTimeout(tick, this.flushIntervalMs);
    };

    this.timer = window.setTimeout(tick, this.flushIntervalMs);
  }

  stop() {
    this.running = false;
    if (this.timer != null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  clear() {
    this.stop();
    this.queue = [];
  }

  get size() {
    return this.queue.length;
  }
}

class FeedWebSocketService {
  private socket: WebSocket | null = null;

  private statusCallbacks: Set<StatusCallback> = new Set();
  private _status: ConnectionStatus = "disconnected";

  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private reconnectTimer: number | null = null;

  private pingInterval: number | null = null;
  private intentionalClose = false;
  private connectPromise: Promise<void> | null = null;

  // steady audio cadence
  private audioSender: BinaryAudioJitterSender;

  // optional: send meta every N chunks (helps server if you want format info)
  private audioMetaEveryN = 50;
  private audioMetaCounter = 0;
  private audioMimeType: string | null = null;

  constructor() {
    this.audioSender = new BinaryAudioJitterSender({
      emitFn: (chunk) => this.flushAudioChunk(chunk),
      targetBufferedMs: 80,
      flushIntervalMs: 20,
      maxQueueChunks: 400,
    });
  }

  setAudioMimeType(mimeType: string) {
    this.audioMimeType = mimeType; // e.g. "audio/pcm;rate=16000"
  }

  private set status(value: ConnectionStatus) {
    if (this._status === value) return;
    this._status = value;
    for (const cb of this.statusCallbacks) cb(value);
  }

  get connectionStatus(): ConnectionStatus {
    return this._status;
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.add(callback);
    return () => this.statusCallbacks.delete(callback);
  }

  async connect(): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) return;
    if (this.connectPromise) return this.connectPromise;

    this.intentionalClose = false;
    this.status = "connecting";

    const token = jwtUtils.getToken();
    if (!token) {
      this.status = "error";
      throw new Error("No authentication token available");
    }

    const url = `${TEACHING_ASSISTANT_WS_URL}/ws/feed?token=${encodeURIComponent(token)}`;

    this.connectPromise = new Promise((resolve, reject) => {
      const ws = new WebSocket(url);
      ws.binaryType = "arraybuffer"; // important for receiving bytes if needed
      this.socket = ws;

      ws.onopen = () => {
        this.status = "connected";
        this.reconnectAttempts = 0;
        this.clearReconnectTimer();
        this.startPingInterval();
        this.audioSender.clear();
        this.audioMetaCounter = 0;
        resolve();
      };

      ws.onclose = (event) => {
        this.stopPingInterval();
        this.audioSender.clear();

        if (this.socket !== ws) return;

        this.socket = null;
        this.connectPromise = null;
        this.status = "disconnected";

        if (!this.intentionalClose && event.code !== 1000) {
          this.attemptReconnect();
        }
      };

      ws.onerror = (err) => {
        this.status = "error";
        this.socket = null;
        this.connectPromise = null;
        reject(err);
      };

      ws.onmessage = (event) => {
        // keep handler light
        queueMicrotask(() => {
          try {
            const data = JSON.parse(event.data);
            if (data?.type === "pong") {
              // ok
            }
          } catch {
            // ignore
          }
        });
      };
    });

    return this.connectPromise;
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    this.stopPingInterval();
    this.audioSender.clear();

    const ws = this.socket;
    this.socket = null;
    this.connectPromise = null;

    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try {
        ws.close(1000, "Client disconnect");
      } catch {}
    }

    this.status = "disconnected";
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    this.clearReconnectTimer();
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(() => {});
    }, delay);
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer != null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startPingInterval(): void {
    if (this.pingInterval) return;

    this.pingInterval = window.setInterval(() => {
      this.sendJson({ type: "ping", timestamp: Date.now() });
    }, 25000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private sendJson(message: unknown): void {
    const ws = this.socket;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
  }

  /** Binary send */
  private flushAudioChunk(chunk: ArrayBuffer): void {
    const ws = this.socket;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // optionally send metadata occasionally (very small JSON)
    this.audioMetaCounter++;
    if (this.audioMimeType && this.audioMetaCounter % this.audioMetaEveryN === 0) {
      this.sendJson({
        type: "audio_meta",
        timestamp: Date.now(),
        data: { mimeType: this.audioMimeType, bytes: chunk.byteLength },
      });
    }

    // send binary: BEST PATH
    ws.send(chunk);
  }

  /** Public API: expects raw PCM bytes as ArrayBuffer */
  sendAudioBytes(chunk: ArrayBuffer): void {
    this.audioSender.push(chunk);
  }

  // keep these as JSON
  sendMedia(base64: string): void {
    this.sendJson({
      type: "media",
      timestamp: Date.now(),
      data: { media: base64 },
    });
  }

  sendTranscript(transcript: string, speaker: "user" | "tutor" = "tutor"): void {
    this.sendJson({
      type: "transcript",
      timestamp: Date.now(),
      data: { transcript, speaker },
    });
  }

  cleanup(): void {
    this.disconnect();
    this.statusCallbacks.clear();
  }
}

export const feedWebSocketService = new FeedWebSocketService();

import { EventEmitter } from "eventemitter3";
import {
  LiveConnectConfig,
  LiveClientToolResponse,
  LiveServerContent,
  LiveServerToolCall,
  LiveServerToolCallCancellation,
  Part,
  LiveServerMessage,
} from "@google/genai";
import { StreamingLog } from "../../types";
import { base64ToArrayBuffer } from "../../lib/utils";
import { TutorService } from "./tutor-service";

export interface TranscriptionData {
  text: string;
  isFinal: boolean;
}

export interface TutorClientEventTypes {
  audio: (data: ArrayBuffer) => void;
  close: (event: CloseEvent) => void;
  content: (data: LiveServerContent) => void;
  error: (error: ErrorEvent) => void;
  interrupted: () => void;
  inputTranscript: (data: TranscriptionData) => void;
  log: (log: StreamingLog) => void;
  open: () => void;
  outputTranscript: (data: TranscriptionData) => void;
  setupcomplete: () => void;
  toolcall: (toolCall: LiveServerToolCall) => void;
  toolcallcancellation: (toolcallCancellation: LiveServerToolCallCancellation) => void;
  turncomplete: () => void;
}

type Status = "connected" | "disconnected" | "connecting";
type CloseLike = { reason?: string };
type RealtimeChunk = { mimeType: string; data: string };

function isAudioInlinePart(p: any): boolean {
  const mt = p?.inlineData?.mimeType;
  return typeof mt === "string" && mt.startsWith("audio/pcm");
}

function safeCloseEvent(reason?: string) {
  try {
    return new CloseEvent("close", { reason });
  } catch {
    return { type: "close", reason } as unknown as CloseEvent;
  }
}

function safeErrorEvent(message: string) {
  try {
    return new ErrorEvent("error", { message });
  } catch {
    return { type: "error", message } as unknown as ErrorEvent;
  }
}

/**
 * Incoming audio jitter buffer (your original, unchanged)
 */
class AudioJitterBuffer {
  private queue: ArrayBuffer[] = [];
  private running = false;
  private timer: number | null = null;

  private readonly targetBufferedMs: number;
  private readonly flushIntervalMs: number;
  private readonly maxQueueChunks: number;

  private readonly emitFn: (data: ArrayBuffer) => void;
  private readonly onDebug?: (msg: string) => void;

  constructor(opts: {
    emitFn: (data: ArrayBuffer) => void;
    onDebug?: (msg: string) => void;
    targetBufferedMs?: number;
    flushIntervalMs?: number;
    maxQueueChunks?: number;
  }) {
    this.emitFn = opts.emitFn;
    this.onDebug = opts.onDebug;
    this.targetBufferedMs = opts.targetBufferedMs ?? 80;
    this.flushIntervalMs = opts.flushIntervalMs ?? 20;
    this.maxQueueChunks = opts.maxQueueChunks ?? 200;
  }

  push(chunk: ArrayBuffer) {
    if (this.queue.length >= this.maxQueueChunks) {
      this.queue.shift();
      this.onDebug?.("Audio queue overflow; dropping oldest chunk.");
    }
    this.queue.push(chunk);

    if (!this.running) {
      const approxBufferedMs = this.queue.length * this.flushIntervalMs;
      if (approxBufferedMs >= this.targetBufferedMs) this.start();
    }
  }

  start() {
    if (this.running) return;
    this.running = true;

    const tick = () => {
      if (!this.running) return;
      const next = this.queue.shift();
      if (next) this.emitFn(next);
      else {
        this.stop();
        return;
      }
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
}

/**
 * NEW: Outgoing realtime scheduler
 * - drains at steady cadence to avoid bursty sends
 * - caps queue; drop oldest audio to reduce latency
 * - keeps only latest video frame (optional)
 */
class RealtimeInputScheduler {
  private audioQ: RealtimeChunk[] = [];
  private videoLatest: RealtimeChunk | null = null;

  private running = false;
  private timer: number | null = null;

  private readonly flushIntervalMs: number;
  private readonly maxAudioChunks: number;
  private readonly sendFn: (chunk: RealtimeChunk) => void;
  private readonly onDebug?: (msg: string) => void;

  constructor(opts: {
    sendFn: (chunk: RealtimeChunk) => void;
    onDebug?: (msg: string) => void;
    flushIntervalMs?: number;
    maxAudioChunks?: number;
  }) {
    this.sendFn = opts.sendFn;
    this.onDebug = opts.onDebug;
    this.flushIntervalMs = opts.flushIntervalMs ?? 20;
    this.maxAudioChunks = opts.maxAudioChunks ?? 300;
  }

  push(chunks: RealtimeChunk[]) {
    for (let i = 0; i < chunks.length; i++) {
      const ch = chunks[i];
      const mt = ch.mimeType;

      if (mt.includes("audio")) {
        if (this.audioQ.length >= this.maxAudioChunks) {
          this.audioQ.shift(); // drop oldest
          this.onDebug?.("Outgoing audio backlog; dropping oldest.");
        }
        this.audioQ.push(ch);
      } else if (mt.includes("image")) {
        // keep only latest frame to avoid backlog
        this.videoLatest = ch;
      } else {
        // send unknown immediately (rare)
        this.sendFn(ch);
      }
    }

    if (!this.running) this.start();
  }

  private start() {
    if (this.running) return;
    this.running = true;

    const tick = () => {
      if (!this.running) return;

      // Send 1 audio chunk per tick (steady cadence)
      const a = this.audioQ.shift();
      if (a) this.sendFn(a);

      // Send latest video occasionally; piggyback on cadence (cheap)
      if (this.videoLatest) {
        const v = this.videoLatest;
        this.videoLatest = null;
        this.sendFn(v);
      }

      // If nothing queued, stop
      if (!this.audioQ.length && !this.videoLatest) {
        this.stop();
        return;
      }

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
    this.audioQ = [];
    this.videoLatest = null;
  }
}

export class TutorClient extends EventEmitter<TutorClientEventTypes> {
  private tutorService: TutorService | null = null;
  private _status: Status = "disconnected";
  private config: LiveConnectConfig | null = null;

  // Incoming audio smoothing
  private audioBuffer: AudioJitterBuffer;

  // NEW: Outgoing smoothing
  private realtimeScheduler: RealtimeInputScheduler;

  // Log coalescing
  private logQueue: StreamingLog[] = [];
  private logFlushTimer: number | null = null;
  private readonly LOG_FLUSH_MS = 100;

  // Transcript coalescing
  private pendingInputTranscript: TranscriptionData | null = null;
  private pendingOutputTranscript: TranscriptionData | null = null;
  private transcriptFlushTimer: number | null = null;
  private readonly TRANSCRIPT_FLUSH_MS = 50;

  public get status() {
    return this._status;
  }

  public get session() {
    return this.tutorService?.isConnected() ? {} : null;
  }

  public getConfig() {
    return { ...this.config };
  }

  constructor() {
    super();
    this.send = this.send.bind(this);

    this.audioBuffer = new AudioJitterBuffer({
      emitFn: (data) => this.emit("audio", data),
      onDebug: (msg) => this.enqueueLog("client.audio", msg),
      targetBufferedMs: 80,
      flushIntervalMs: 20,
      maxQueueChunks: 200,
    });

    // NEW: steady drain outbound
    this.realtimeScheduler = new RealtimeInputScheduler({
      flushIntervalMs: 20,
      maxAudioChunks: 300,
      onDebug: (msg) => this.enqueueLog("client.outgoing", msg),
      sendFn: (chunk) => {
        // Keep sendFn minimal
        if (this.tutorService && this._status === "connected") {
          this.tutorService.sendRealtimeInput(chunk);
        }
      },
    });
  }

  private enqueueLog(type: string, message: StreamingLog["message"]) {
    this.logQueue.push({ date: new Date(), type, message });

    if (this.logFlushTimer == null) {
      this.logFlushTimer = window.setTimeout(() => {
        this.logFlushTimer = null;
        const batch = this.logQueue;
        this.logQueue = [];
        for (const l of batch) this.emit("log", l);
      }, this.LOG_FLUSH_MS);
    }
  }

  private enqueueTranscript(kind: "input" | "output", data: TranscriptionData) {
    if (kind === "input") this.pendingInputTranscript = data;
    else this.pendingOutputTranscript = data;

    if (this.transcriptFlushTimer == null) {
      this.transcriptFlushTimer = window.setTimeout(() => {
        this.transcriptFlushTimer = null;

        const inT = this.pendingInputTranscript;
        const outT = this.pendingOutputTranscript;
        this.pendingInputTranscript = null;
        this.pendingOutputTranscript = null;

        if (inT) this.emit("inputTranscript", inT);
        if (outT) this.emit("outputTranscript", outT);
      }, this.TRANSCRIPT_FLUSH_MS);
    }
  }

  async connect(config: LiveConnectConfig, preferredLanguage?: string): Promise<boolean> {
    if (this._status === "connected" || this._status === "connecting") return false;

    this._status = "connecting";
    this.config = config;

    try {
      this.tutorService = new TutorService();
      await this.tutorService.initialize(preferredLanguage || "English");

      await this.tutorService.connect(config, {
        onopen: () => {
          this._status = "connected";
          this.audioBuffer.clear();
          this.realtimeScheduler.clear();
          this.enqueueLog("client.open", "Connected");
          this.emit("open");
        },

        onmessage: (message: LiveServerMessage) => {
          queueMicrotask(() => this.processGeminiMessage(message));
        },

        onerror: (error: Error) => {
          this._status = "disconnected";
          this.audioBuffer.clear();
          this.realtimeScheduler.clear();
          this.enqueueLog("server.error", error.message);
          this.emit("error", safeErrorEvent(error.message));
        },

        onclose: (event: CloseLike) => {
          this._status = "disconnected";
          this.audioBuffer.clear();
          this.realtimeScheduler.clear();
          this.enqueueLog("server.close", `disconnected${event.reason ? `: ${event.reason}` : ""}`);
          this.emit("close", safeCloseEvent(event.reason));
        },
      });

      return true;
    } catch (error) {
      this._status = "disconnected";
      this.audioBuffer.clear();
      this.realtimeScheduler.clear();
      const msg = error instanceof Error ? error.message : "Failed to connect to Gemini";
      this.enqueueLog("client.error", msg);
      this.emit("error", safeErrorEvent(msg));
      return false;
    }
  }

  private processGeminiMessage(message: LiveServerMessage) {
    if (message.setupComplete) {
      this.enqueueLog("server.send", "setupComplete");
      this.emit("setupcomplete");
      return;
    }

    if (message.toolCall) {
      this.enqueueLog("server.toolCall", "[toolCall]");
      this.emit("toolcall", message.toolCall);
      return;
    }

    if (message.toolCallCancellation) {
      this.enqueueLog("server.toolCallCancellation", "[toolCallCancellation]");
      this.emit("toolcallcancellation", message.toolCallCancellation);
      return;
    }

    const serverContent = message.serverContent;
    if (!serverContent) return;

    if ("interrupted" in serverContent) {
      this.audioBuffer.clear();
      this.enqueueLog("server.content", "interrupted");
      this.emit("interrupted");
      return;
    }

    if ("turnComplete" in serverContent) {
      this.enqueueLog("server.content", "turnComplete");
      this.emit("turncomplete");
    }

    if ("inputTranscription" in serverContent) {
      const t: any = (serverContent as any).inputTranscription;
      if (t?.text) {
        const isFinal = t.finished === true;
        this.enqueueTranscript("input", { text: t.text, isFinal });
        if (isFinal) this.enqueueLog("server.inputTranscript", `[FINAL] ${t.text}`);
      }
    }

    if ("outputTranscription" in serverContent) {
      const t: any = (serverContent as any).outputTranscription;
      if (t?.text) {
        const isFinal = t.finished === true;
        this.enqueueTranscript("output", { text: t.text, isFinal });
        if (isFinal) this.enqueueLog("server.outputTranscript", `[FINAL] ${t.text}`);
      }
    }

    if ("modelTurn" in serverContent) {
      const parts = serverContent.modelTurn?.parts ?? [];
      if (!parts.length) return;

      const nonAudioParts: any[] = [];
      for (let i = 0; i < parts.length; i++) {
        const p: any = parts[i];
        if (isAudioInlinePart(p)) {
          const b64: string | undefined = p.inlineData?.data;
          if (b64) {
            const buf = base64ToArrayBuffer(b64);
            this.audioBuffer.push(buf);
          }
        } else {
          nonAudioParts.push(p);
        }
      }

      if (nonAudioParts.length) {
        const content: LiveServerContent = { modelTurn: { parts: nonAudioParts } } as any;
        this.emit("content", content);
        this.enqueueLog("server.content", `modelTurn parts: ${nonAudioParts.length}`);
      }
    }
  }

  public disconnect() {
    if (!this.tutorService) return false;

    this.audioBuffer.clear();
    this.realtimeScheduler.clear();

    if (this.logFlushTimer != null) {
      clearTimeout(this.logFlushTimer);
      this.logFlushTimer = null;
    }
    if (this.transcriptFlushTimer != null) {
      clearTimeout(this.transcriptFlushTimer);
      this.transcriptFlushTimer = null;
    }

    this.tutorService.disconnect();
    this.tutorService = null;
    this._status = "disconnected";
    this.enqueueLog("client.close", "Disconnected");
    return true;
  }

  /**
   * UPDATED: Instead of sending immediately (bursty),
   * queue and let scheduler drain at steady cadence.
   */
  sendRealtimeInput(chunks: RealtimeChunk[]) {
    if (!this.tutorService || this._status !== "connected") return;

    // Keep minimal: just enqueue
    this.realtimeScheduler.push(chunks);
  }

  sendToolResponse(toolResponse: LiveClientToolResponse) {
    if (!this.tutorService || this._status !== "connected") return;

    if (toolResponse.functionResponses?.length) {
      this.tutorService.sendToolResponse(toolResponse);
      this.enqueueLog("client.toolResponse", `functionResponses: ${toolResponse.functionResponses.length}`);
    }
  }

  send(parts: Part | Part[], turnComplete: boolean = true) {
    if (!this.tutorService || this._status !== "connected") return;

    const arr = Array.isArray(parts) ? parts : [parts];
    this.tutorService.sendClientContent(arr, turnComplete);
    this.enqueueLog("client.send", `parts: ${arr.length}, turnComplete: ${turnComplete}`);
  }
}

export { TutorClient as GenAIProxyClient };

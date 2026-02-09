/**
 * Tutor Client - Direct Gemini Live API client wrapper
 * Provides event-driven interface for Gemini Live API communication
 *
 * Improvements over prototype:
 * - Auto-reconnection with exponential backoff
 * - Session activity tracking (idle detection)
 * - Graceful disconnect vs error disconnect handling
 * - Resilient sendToolResponse / sendRealtimeInput
 */

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
import { difference } from "lodash";
import { TutorService } from "./tutor-service";

/**
 * Transcription data from Gemini input/output audio transcription
 */
export interface TranscriptionData {
  text: string;
  isFinal: boolean;
}

/**
 * Event types that can be emitted by the tutor client.
 */
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
  toolcallcancellation: (tc: LiveServerToolCallCancellation) => void;
  turncomplete: () => void;
  // Emitted when token usage data is received from Gemini
  tokenUsage: (usage: { 
    promptTokenCount: number; 
    candidatesTokenCount: number; 
    totalTokenCount: number;
    cachedContentTokenCount?: number;
    thoughtTokenCount?: number;
    promptTokensDetails?: Array<{ modality: string; tokenCount: number }>;
  }) => void;
}

// ──────────────────────────────────────────────────────────
// Reconnection settings
// ──────────────────────────────────────────────────────────
const MAX_RECONNECT_ATTEMPTS = 3;
const BASE_RECONNECT_DELAY_MS = 2_000;

export class TutorClient extends EventEmitter<TutorClientEventTypes> {
  private tutorService: TutorService | null = null;
  private _status: "connected" | "disconnected" | "connecting" | "reconnecting" = "disconnected";
  private config: LiveConnectConfig | null = null;
  private preferredLanguage: string = "English";
  private assessmentMode: boolean = false;

  // Reconnection state
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalDisconnect = false;

  // Activity tracking
  private lastActivityTime = 0;

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
  }

  protected log(type: string, message: StreamingLog["message"]) {
    const log: StreamingLog = {
      date: new Date(),
      type,
      message,
    };
    this.emit("log", log);
  }

  private touchActivity() {
    this.lastActivityTime = Date.now();
  }

  async connect(config: LiveConnectConfig, preferredLanguage?: string, assessmentMode?: boolean): Promise<boolean> {
    if (this._status === "connected" || this._status === "connecting") {
      return false;
    }

    this._status = "connecting";
    this.config = config;
    this.preferredLanguage = preferredLanguage || "English";
    this.assessmentMode = assessmentMode || false;
    this.intentionalDisconnect = false;
    this.reconnectAttempts = 0;

    return this.doConnect();
  }

  private async doConnect(): Promise<boolean> {
    try {
      // Initialize Tutor Service with preferred language and mode
      this.tutorService = new TutorService();
      await this.tutorService.initialize(this.preferredLanguage, this.assessmentMode);

      // Connect directly to Gemini Live API
      await this.tutorService.connect(this.config!, {
        onopen: () => {
          this._status = "connected";
          this.reconnectAttempts = 0;
          this.touchActivity();
          this.log("client.open", "Connected");
          this.emit("open");
        },
        onmessage: (message: LiveServerMessage) => {
          this.touchActivity();
          this.processGeminiMessage(message);
        },
        onerror: (error: Error) => {
          this.log("server.error", error.message);
          this.emit("error", new ErrorEvent("error", { message: error.message }));
          // Don't set _status here - let onclose handle reconnection
        },
        onclose: (event: { reason?: string }) => {
          const wasConnected = this._status === "connected";
          this._status = "disconnected";
          this.log(
            "server.close",
            `disconnected ${event.reason ? `with reason: ${event.reason}` : ""}`
          );

          if (this.intentionalDisconnect) {
            // User initiated disconnect — no reconnection
            this.emit("close", new CloseEvent("close", { reason: event.reason }));
          } else if (wasConnected && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            // Unexpected disconnect — try to reconnect
            this.scheduleReconnect();
          } else {
            // Give up
            this.emit("close", new CloseEvent("close", { reason: event.reason }));
          }
        },
      });

      return true;
    } catch (error) {
      console.error("Error connecting to Gemini:", error);

      if (!this.intentionalDisconnect && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.scheduleReconnect();
        return false;
      }

      this._status = "disconnected";
      this.emit("error", new ErrorEvent("error", {
        message: error instanceof Error ? error.message : "Failed to connect to Gemini",
      }));
      return false;
    }
  }

  private scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = BASE_RECONNECT_DELAY_MS * Math.pow(2, this.reconnectAttempts - 1);
    this._status = "reconnecting";

    console.log(
      `🔄 TutorClient: Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`
    );
    this.log("client.reconnecting", `Attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      if (this.intentionalDisconnect) return;

      try {
        // Cleanup old service
        if (this.tutorService) {
          try { this.tutorService.disconnect(); } catch { /* ignore */ }
          this.tutorService = null;
        }
        await this.doConnect();
      } catch (err) {
        console.error("Reconnect failed:", err);
      }
    }, delay);
  }

  private processGeminiMessage(message: LiveServerMessage) {
    if (message.setupComplete) {
      this.log("server.send", "setupComplete");
      this.emit("setupcomplete");
      return;
    }
    if (message.toolCall) {
      this.log("server.toolCall", message);
      this.emit("toolcall", message.toolCall);
      return;
    }
    if (message.toolCallCancellation) {
      this.log("server.toolCallCancellation", message);
      this.emit("toolcallcancellation", message.toolCallCancellation);
      return;
    }

    if (message.serverContent) {
      const { serverContent } = message;
      if ("interrupted" in serverContent) {
        this.log("server.content", "interrupted");
        this.emit("interrupted");
        return;
      }
      if ("turnComplete" in serverContent) {
        this.log("server.content", "turnComplete");
        this.emit("turncomplete");
      }

      // Handle input audio transcription (user's speech)
      if ("inputTranscription" in serverContent) {
        const transcription = (serverContent as any).inputTranscription;
        if (transcription?.text) {
          const isFinal = transcription.finished === true;
          this.emit("inputTranscript", { text: transcription.text, isFinal });
          this.log("server.inputTranscript", `${isFinal ? "[FINAL]" : "[PARTIAL]"} ${transcription.text}`);
        }
      }

      // Handle output audio transcription (model's speech)
      if ("outputTranscription" in serverContent) {
        const transcription = (serverContent as any).outputTranscription;
        if (transcription?.text) {
          const isFinal = transcription.finished === true;
          this.emit("outputTranscript", { text: transcription.text, isFinal });
          this.log("server.outputTranscript", `${isFinal ? "[FINAL]" : "[PARTIAL]"} ${transcription.text}`);
        }
      }

      if ("modelTurn" in serverContent) {
        let parts = serverContent.modelTurn?.parts || [];

        // Handle audio parts
        const audioParts = parts.filter(
          (p: any) => p.inlineData && p.inlineData.mimeType?.startsWith("audio/pcm")
        );
        const base64s = audioParts.map((p: any) => p.inlineData?.data);

        // Strip audio parts out
        const otherParts = difference(parts, audioParts);

        base64s.forEach((b64: string) => {
          if (b64) {
            const data = base64ToArrayBuffer(b64);
            this.emit("audio", data);
            this.log(`server.audio`, `buffer (${data.byteLength})`);
          }
        });

        if (!otherParts.length) {
          return;
        }

        parts = otherParts;
        const content = { modelTurn: { parts } };
        this.emit("content", content);
        this.log(`server.content`, message);
      }
    }

    // Extract and emit token usage if available
    if (message.usageMetadata) {
      // Use type assertion to access properties that may not be in the type definition
      const usage = message.usageMetadata as any;
      const tokenUsage = {
        promptTokenCount: usage.promptTokenCount || usage.inputTokenCount || 0,
        candidatesTokenCount: usage.candidatesTokenCount || usage.outputTokenCount || usage.candidateTokenCount || 0,
        totalTokenCount: usage.totalTokenCount || 0,
        // Extract cached content tokens (for 90% discount)
        cachedContentTokenCount: usage.cachedContentTokenCount || usage.cached_content_token_count || 0,
        // Extract thinking tokens (billed as output)
        thoughtTokenCount: usage.thoughtTokenCount || usage.thought_token_count || 0,
        // Extract modality breakdown for accurate pricing
        promptTokensDetails: usage.promptTokensDetails || usage.prompt_tokens_details || []
      };
      
      // Only emit if we have actual token counts
      if (tokenUsage.totalTokenCount > 0) {
        this.emit("tokenUsage", tokenUsage);
      }
    }
  }

  public disconnect() {
    this.intentionalDisconnect = true;

    // Cancel any pending reconnection
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (!this.tutorService) {
      return false;
    }

    this.tutorService.disconnect();
    this.tutorService = null;
    this._status = "disconnected";
    this.log("client.close", "Disconnected");
    return true;
  }

  sendRealtimeInput(chunks: Array<{ mimeType: string; data: string }>) {
    if (!this.tutorService || this._status !== "connected") {
      return;
    }

    this.touchActivity();

    let hasAudio = false;
    let hasVideo = false;

    for (const ch of chunks) {
      try {
        this.tutorService.sendRealtimeInput(ch);
      } catch (err) {
        console.warn("TutorClient: Error sending realtime input chunk:", err);
        continue;
      }

      if (ch.mimeType.includes("audio")) hasAudio = true;
      if (ch.mimeType.includes("image")) hasVideo = true;
      if (hasAudio && hasVideo) break;
    }

    const message =
      hasAudio && hasVideo
        ? "audio + video"
        : hasAudio
          ? "audio"
          : hasVideo
            ? "video"
            : "unknown";
    this.log(`client.realtimeInput`, message);
  }

  sendToolResponse(toolResponse: LiveClientToolResponse) {
    if (!this.tutorService || this._status !== "connected") {
      console.warn("TutorClient: Cannot send tool response — not connected");
      return;
    }

    if (toolResponse.functionResponses && toolResponse.functionResponses.length) {
      try {
        this.tutorService.sendToolResponse(toolResponse);
        this.log(`client.toolResponse`, toolResponse);
      } catch (err) {
        console.error("TutorClient: Error sending tool response:", err);
      }
    }
  }

  send(parts: Part | Part[], turnComplete: boolean = true) {
    if (!this.tutorService || this._status !== "connected") {
      return;
    }

    this.touchActivity();

    this.tutorService.sendClientContent(
      Array.isArray(parts) ? parts : [parts],
      turnComplete
    );

    this.log(`client.send`, {
      turns: Array.isArray(parts) ? parts : [parts],
      turnComplete,
    });
  }
}

// Export alias for backward compatibility during migration
export { TutorClient as GenAIProxyClient };

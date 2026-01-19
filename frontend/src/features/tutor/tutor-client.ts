/**
 * Tutor Client - Direct Gemini Live API client wrapper
 * Provides event-driven interface for Gemini Live API communication
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
 * Each event corresponds to a specific message from Gemini or client state change.
 */
export interface TutorClientEventTypes {
  // Emitted when audio data is received
  audio: (data: ArrayBuffer) => void;
  // Emitted when the connection closes
  close: (event: CloseEvent) => void;
  // Emitted when content is received from the server
  content: (data: LiveServerContent) => void;
  // Emitted when an error occurs
  error: (error: ErrorEvent) => void;
  // Emitted when the server interrupts the current generation
  interrupted: () => void;
  // Emitted when user's speech is transcribed (input audio transcription)
  inputTranscript: (data: TranscriptionData) => void;
  // Emitted for logging events
  log: (log: StreamingLog) => void;
  // Emitted when the connection opens
  open: () => void;
  // Emitted when model's speech is transcribed (output audio transcription)
  outputTranscript: (data: TranscriptionData) => void;
  // Emitted when the initial setup is complete
  setupcomplete: () => void;
  // Emitted when a tool call is received
  toolcall: (toolCall: LiveServerToolCall) => void;
  // Emitted when a tool call is cancelled
  toolcallcancellation: (
    toolcallCancellation: LiveServerToolCallCancellation
  ) => void;
  // Emitted when the current turn is complete
  turncomplete: () => void;
}

export class TutorClient extends EventEmitter<TutorClientEventTypes> {
  private tutorService: TutorService | null = null;
  private _status: "connected" | "disconnected" | "connecting" = "disconnected";
  private config: LiveConnectConfig | null = null;

  public get status() {
    return this._status;
  }

  public get session() {
    // Return a proxy session object for compatibility
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

  async connect(config: LiveConnectConfig): Promise<boolean> {
    if (this._status === "connected" || this._status === "connecting") {
      return false;
    }

    this._status = "connecting";
    this.config = config;

    try {
      // Initialize Tutor Service
      this.tutorService = new TutorService();
      await this.tutorService.initialize();

      // Connect directly to Gemini Live API
      await this.tutorService.connect(config, {
        onopen: () => {
          this._status = "connected";
          this.log("client.open", "Connected");
          this.emit("open");
        },
        onmessage: (message: LiveServerMessage) => {
          // Process Gemini message directly
          this.processGeminiMessage(message);
        },
        onerror: (error: Error) => {
          this._status = "disconnected";
          const errorEvent = new ErrorEvent("error", { message: error.message });
          this.log("server.error", error.message);
          this.emit("error", errorEvent);
        },
        onclose: (event: { reason?: string }) => {
          this._status = "disconnected";
          const closeEvent = new CloseEvent("close", { reason: event.reason });
          this.log(
            "server.close",
            `disconnected ${event.reason ? `with reason: ${event.reason}` : ""}`
          );
          this.emit("close", closeEvent);
        },
      });

      return true;
    } catch (error) {
      console.error("Error connecting to Gemini:", error);
      this._status = "disconnected";
      const errorEvent = new ErrorEvent("error", {
        message: error instanceof Error ? error.message : "Failed to connect to Gemini",
      });
      this.emit("error", errorEvent);
      return false;
    }
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
  }

  public disconnect() {
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

    let hasAudio = false;
    let hasVideo = false;

    for (const ch of chunks) {
      // Send directly to Gemini
      this.tutorService.sendRealtimeInput(ch);

      if (ch.mimeType.includes("audio")) {
        hasAudio = true;
      }
      if (ch.mimeType.includes("image")) {
        hasVideo = true;
      }
      if (hasAudio && hasVideo) {
        break;
      }
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
      return;
    }

    if (
      toolResponse.functionResponses &&
      toolResponse.functionResponses.length
    ) {
      // Send directly to Gemini
      this.tutorService.sendToolResponse(toolResponse);
      this.log(`client.toolResponse`, toolResponse);
    }
  }

  send(parts: Part | Part[], turnComplete: boolean = true) {
    if (!this.tutorService || this._status !== "connected") {
      return;
    }

    // Send directly to Gemini
    this.tutorService.sendClientContent(
      Array.isArray(parts) ? parts : [parts],
      turnComplete
    );

    this.log(`client.send`, {
      turns: Array.isArray(parts) ? parts : [parts],
      turnComplete,
    });
  }

  /**
   * Inject homework content so the tutor can help with it
   * Retries up to 5 times with 500ms delay if not connected
   */
  async injectHomeworkContext(homeworkContent: string, filename: string): Promise<boolean> {
    const maxRetries = 5;
    const retryDelay = 500;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      console.log(`[TutorClient] injectHomework attempt ${attempt}/${maxRetries}, status: ${this._status}`);

      if (this.tutorService && this._status === "connected") {
        try {
          this.tutorService.injectHomeworkContext(homeworkContent, filename);
          this.log(`client.injectHomework`, { filename, attempt });
          console.log(`[TutorClient] Successfully injected homework: ${filename}`);
          return true;
        } catch (error) {
          console.error(`[TutorClient] Error injecting homework:`, error);
        }
      }

      if (attempt < maxRetries) {
        console.log(`[TutorClient] Waiting ${retryDelay}ms before retry...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }

    console.warn(`[TutorClient] Failed to inject homework after ${maxRetries} attempts: tutor not connected`);
    return false;
  }
}

// Export alias for backward compatibility during migration
export { TutorClient as GenAIProxyClient };

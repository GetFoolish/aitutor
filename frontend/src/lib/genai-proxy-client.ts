/**
 * Proxy client for Adam Tutor backend service
 * Connects to local backend instead of directly to Gemini
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
import { StreamingLog } from "../types";
import { base64ToArrayBuffer } from "./utils";
import { difference } from "lodash";

/**
 * Event types that can be emitted by the proxy client.
 * Each event corresponds to a specific message from Gemini or client state change.
 */
export interface LiveClientEventTypes {
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
  // Emitted for logging events
  log: (log: StreamingLog) => void;
  // Emitted when the connection opens
  open: () => void;
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

export class GenAIProxyClient extends EventEmitter<LiveClientEventTypes> {
  private ws: WebSocket | null = null;
  private _status: "connected" | "disconnected" | "connecting" = "disconnected";
  private config: LiveConnectConfig | null = null;

  public get status() {
    return this._status;
  }

  public get session() {
    // Return a proxy session object for compatibility
    return this.ws ? {} : null;
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

    // Connect to local backend
    this.ws = new WebSocket("ws://localhost:8767");

    this.ws.onopen = () => {
      console.log("Connected to Tutor backend");
      // Send connection request to backend (model is determined by backend)
      this.ws!.send(
        JSON.stringify({
          type: "connect",
          config,
        })
      );
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === "open") {
          this._status = "connected";
          this.log("client.open", "Connected");
          this.emit("open");
        } else if (message.type === "close") {
          this._status = "disconnected";
          const closeEvent = new CloseEvent("close", { reason: message.reason });
          this.log(
            "server.close",
            `disconnected ${message.reason ? `with reason: ${message.reason}` : ""}`
          );
          this.emit("close", closeEvent);
        } else if (message.type === "error") {
          const errorEvent = new ErrorEvent("error", { message: message.error });
          this.log("server.error", message.error);
          this.emit("error", errorEvent);
        } else if (message.type === "message") {
          // Process Gemini message
          this.processGeminiMessage(message.data);
        }
      } catch (error) {
        console.error("Error processing backend message:", error);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this._status = "disconnected";
    };

    this.ws.onclose = () => {
      if (this._status !== "disconnected") {
        this._status = "disconnected";
        this.emit("close", new CloseEvent("close"));
      }
    };

    return true;
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
    if (!this.ws) {
      return false;
    }

    this.ws.send(JSON.stringify({ type: "disconnect" }));
    this.ws.close();
    this.ws = null;
    this._status = "disconnected";
    this.log("client.close", "Disconnected");
    return true;
  }

  sendRealtimeInput(chunks: Array<{ mimeType: string; data: string }>) {
    if (!this.ws || this._status !== "connected") {
      return;
    }

    let hasAudio = false;
    let hasVideo = false;

    for (const ch of chunks) {
      this.ws.send(
        JSON.stringify({
          type: "realtimeInput",
          data: ch,
        })
      );

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
    if (!this.ws || this._status !== "connected") {
      return;
    }

    if (
      toolResponse.functionResponses &&
      toolResponse.functionResponses.length
    ) {
      this.ws.send(
        JSON.stringify({
          type: "toolResponse",
          data: toolResponse,
        })
      );
      this.log(`client.toolResponse`, toolResponse);
    }
  }

  send(parts: Part | Part[], turnComplete: boolean = true) {
    if (!this.ws || this._status !== "connected") {
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: "send",
        parts: Array.isArray(parts) ? parts : [parts],
        turnComplete,
      })
    );

    this.log(`client.send`, {
      turns: Array.isArray(parts) ? parts : [parts],
      turnComplete,
    });
  }
}


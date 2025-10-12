/**
 * Teaching Assistant Bridge
 *
 * Connects the frontend to the Teaching Assistant backend via WebSocket.
 * - Forwards Gemini responses to TA for analysis
 * - Receives TA prompt injections and sends them to Gemini
 * - Handles TA logs and displays them in the console
 */

import { GenAILiveClient } from "./genai-live-client";
import { LiveServerContent } from "@google/genai";

export interface TALogMessage {
  type: "ta_log";
  level: "info" | "debug" | "warning" | "error" | "success";
  message: string;
  timestamp: number;
}

export interface TAPromptInjection {
  type: "ta_inject_prompt";
  prompt: string;
  timestamp: number;
}

export interface TAConnection {
  type: "ta_connected";
  message: string;
  timestamp: number;
}

type TAMessage = TALogMessage | TAPromptInjection | TAConnection | { type: "pong" };

export class TeachingAssistantBridge {
  private ws: WebSocket | null = null;
  private geminiClient: GenAILiveClient | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private isConnecting = false;
  private onLogCallback: ((log: TALogMessage) => void) | null = null;

  constructor(
    private taServerUrl: string = "ws://localhost:9000",
    private studentName: string = "Student"
  ) {
    console.log("[TA Bridge] Initializing...");
  }

  /**
   * Connect to the Teaching Assistant backend
   */
  public async connect(): Promise<boolean> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log("[TA Bridge] Already connected");
      return true;
    }

    if (this.isConnecting) {
      console.log("[TA Bridge] Connection already in progress");
      return false;
    }

    this.isConnecting = true;
    console.log(`[TA Bridge] Connecting to ${this.taServerUrl}...`);

    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(this.taServerUrl);

        this.ws.onopen = () => {
          console.log("[TA Bridge] ✅ Connected to Teaching Assistant");
          this.isConnecting = false;
          this.reconnectAttempts = 0;

          // Start session
          this.sendMessage({
            type: "session_start",
            session_id: `session_${Date.now()}`,
            student_name: this.studentName,
            timestamp: Date.now(),
          });

          resolve(true);
        };

        this.ws.onmessage = (event) => {
          this.handleTAMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error("[TA Bridge] WebSocket error:", error);
          this.isConnecting = false;
          resolve(false);
        };

        this.ws.onclose = () => {
          console.log("[TA Bridge] Connection closed");
          this.isConnecting = false;
          this.ws = null;
          this.attemptReconnect();
        };
      } catch (error) {
        console.error("[TA Bridge] Failed to create WebSocket:", error);
        this.isConnecting = false;
        resolve(false);
      }
    });
  }

  /**
   * Attach to Gemini client to intercept messages
   */
  public attachToGeminiClient(client: GenAILiveClient) {
    if (this.geminiClient === client) {
      return; // Already attached
    }

    this.geminiClient = client;
    console.log("[TA Bridge] Attached to Gemini client");

    // Forward Gemini content to TA
    client.on("content", (data: LiveServerContent) => {
      this.forwardGeminiResponseToTA(data);
    });

    // Forward other events for context
    client.on("turncomplete", () => {
      this.sendMessage({
        type: "gemini_turn_complete",
        timestamp: Date.now(),
      });
    });
  }

  /**
   * Set callback for TA logs to be displayed in console
   */
  public setLogCallback(callback: (log: TALogMessage) => void) {
    this.onLogCallback = callback;
  }

  /**
   * Forward Gemini response to Teaching Assistant for analysis
   */
  private forwardGeminiResponseToTA(content: LiveServerContent) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      // Extract text from content
      const modelTurn = (content as any).modelTurn;
      if (!modelTurn || !modelTurn.parts) {
        return;
      }

      const textParts = modelTurn.parts
        .filter((part: any) => part.text)
        .map((part: any) => part.text);

      if (textParts.length === 0) {
        return;
      }

      const fullText = textParts.join(" ");

      // Send to TA
      this.sendMessage({
        type: "gemini_response",
        text: fullText,
        timestamp: Date.now(),
      });

      console.log(`[TA Bridge] Forwarded Gemini response to TA (${fullText.length} chars)`);
    } catch (error) {
      console.error("[TA Bridge] Error forwarding Gemini response:", error);
    }
  }

  /**
   * Handle incoming message from Teaching Assistant
   */
  private handleTAMessage(data: string) {
    try {
      const message: TAMessage = JSON.parse(data);

      switch (message.type) {
        case "ta_inject_prompt":
          this.injectPromptToGemini((message as TAPromptInjection).prompt);
          break;

        case "ta_log":
          this.handleTALog(message as TALogMessage);
          break;

        case "ta_connected":
          console.log(`[TA Bridge] ${(message as TAConnection).message}`);
          break;

        case "pong":
          // Health check response
          break;

        default:
          console.log("[TA Bridge] Unknown message type:", (message as any).type);
      }
    } catch (error) {
      console.error("[TA Bridge] Error parsing TA message:", error);
    }
  }

  /**
   * Inject TA prompt into Gemini conversation
   */
  private injectPromptToGemini(prompt: string) {
    if (!this.geminiClient) {
      console.error("[TA Bridge] No Gemini client attached");
      return;
    }

    console.log(`[TA Bridge] 🤖 Injecting TA prompt: ${prompt.slice(0, 60)}...`);

    try {
      // Send the prompt to Gemini
      this.geminiClient.send([{ text: prompt }]);
    } catch (error) {
      console.error("[TA Bridge] Error injecting prompt to Gemini:", error);
    }
  }

  /**
   * Handle TA log messages
   */
  private handleTALog(log: TALogMessage) {
    const emoji = {
      info: "ℹ️",
      debug: "🐛",
      warning: "⚠️",
      error: "❌",
      success: "✅",
    }[log.level];

    console.log(`[TA Bridge] ${emoji} ${log.message}`);

    // Forward to callback for UI display
    if (this.onLogCallback) {
      this.onLogCallback(log);
    }
  }

  /**
   * Send a message to the TA backend
   */
  private sendMessage(message: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[TA Bridge] Cannot send message: WebSocket not open");
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error("[TA Bridge] Error sending message:", error);
    }
  }

  /**
   * Attempt to reconnect to TA server
   */
  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("[TA Bridge] Max reconnection attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    console.log(
      `[TA Bridge] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Notify TA when student sends a message
   */
  public notifyStudentMessage(text: string) {
    this.sendMessage({
      type: "student_message",
      text,
      timestamp: Date.now(),
    });
  }

  /**
   * Notify TA when student answers a question
   */
  public notifyAnswerResult(isCorrect: boolean) {
    this.sendMessage({
      type: "answer_result",
      is_correct: isCorrect,
      timestamp: Date.now(),
    });
  }

  /**
   * Notify TA when student uses a hint
   */
  public notifyHintUsed() {
    this.sendMessage({
      type: "hint_used",
      timestamp: Date.now(),
    });
  }

  /**
   * End the session
   */
  public async endSession() {
    console.log("[TA Bridge] Ending session...");

    this.sendMessage({
      type: "session_end",
      timestamp: Date.now(),
    });

    // Give time for message to send
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Disconnect from TA
   */
  public disconnect() {
    console.log("[TA Bridge] Disconnecting...");
    this.endSession();
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

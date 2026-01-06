/**
 * Instruction SSE Service (jitter/lag + reconnect hardened)
 *
 * Improvements:
 *  - Single active connection, idempotent connect()
 *  - Prevent reconnect storms + ignore reconnect after intentional disconnect
 *  - Optional coalescing to avoid UI thrash when instructions burst
 *  - Heartbeat watchdog (based on keepalive events)
 *  - Uses lastEventId when available for resume
 */

import { jwtUtils } from "../lib/jwt-utils";

const TEACHING_ASSISTANT_API_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || "http://localhost:8002";

type InstructionCallback = (instruction: string) => void;
type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";
type StatusCallback = (status: ConnectionStatus) => void;

class InstructionSSEService {
  private eventSource: EventSource | null = null;

  private instructionCallbacks: Set<InstructionCallback> = new Set();
  private statusCallbacks: Set<StatusCallback> = new Set();

  private _status: ConnectionStatus = "disconnected";
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;

  private reconnectTimer: number | null = null;
  private intentionalClose = false;

  // Resume support (if server sets event.id / lastEventId)
  private lastEventId: string | null = null;

  // Optional burst coalescing (prevents UI jitter)
  private pendingInstructions: string[] = [];
  private instructionFlushTimer: number | null = null;
  private readonly INSTRUCTION_FLUSH_MS = 30; // small delay to coalesce bursts

  // Heartbeat watchdog (requires server keepalive events)
  private lastHeartbeatAt = 0;
  private heartbeatTimer: number | null = null;
  private readonly HEARTBEAT_CHECK_MS = 10_000;
  private readonly HEARTBEAT_STALE_MS = 35_000; // > typical keepalive interval

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

  onInstruction(callback: InstructionCallback): () => void {
    this.instructionCallbacks.add(callback);
    return () => this.instructionCallbacks.delete(callback);
  }

  connect(): void {
    // Idempotent: if connected/connecting, do nothing
    if (this.eventSource) return;

    this.intentionalClose = false;
    this.clearReconnectTimer();

    const token = jwtUtils.getToken();
    if (!token) {
      this.status = "error";
      return;
    }

    this.status = "connecting";

    const params = new URLSearchParams({ token });
    // Resume if server supports Last-Event-ID semantics via query
    if (this.lastEventId) params.set("lastEventId", this.lastEventId);

    const url = `${TEACHING_ASSISTANT_API_URL}/sse/instructions?${params.toString()}`;

    const es = new EventSource(url);
    this.eventSource = es;

    es.onopen = () => {
      this.status = "connected";
      this.reconnectAttempts = 0;

      // Initialize heartbeat timestamps when opened
      this.lastHeartbeatAt = Date.now();
      this.startHeartbeatWatchdog();
    };

    es.onerror = () => {
      // EventSource will retry internally sometimes, but behavior varies.
      // We do a controlled close + exponential backoff reconnect.
      this.status = "error";
      this.teardownEventSource();
      if (!this.intentionalClose) this.attemptReconnect();
    };

    // Instruction events
    es.addEventListener("instruction", (event: MessageEvent) => {
      // Keep handler light
      queueMicrotask(() => {
        const data = String(event.data ?? "");

        // track lastEventId if present
        const anyEvent: any = event;
        if (anyEvent?.lastEventId) this.lastEventId = String(anyEvent.lastEventId);

        // Coalesce bursts to avoid UI thrash
        this.pendingInstructions.push(data);
        if (this.instructionFlushTimer == null) {
          this.instructionFlushTimer = window.setTimeout(() => {
            this.instructionFlushTimer = null;
            const batch = this.pendingInstructions;
            this.pendingInstructions = [];

            // Deliver in order
            for (let i = 0; i < batch.length; i++) {
              for (const cb of this.instructionCallbacks) cb(batch[i]);
            }
          }, this.INSTRUCTION_FLUSH_MS);
        }
      });
    });

    // Keepalive events (heartbeat)
    es.addEventListener("keepalive", (event: MessageEvent) => {
      // Minimal work
      this.lastHeartbeatAt = Date.now();

      // Also capture lastEventId if server sets it
      const anyEvent: any = event;
      if (anyEvent?.lastEventId) this.lastEventId = String(anyEvent.lastEventId);
    });
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    this.stopHeartbeatWatchdog();
    this.clearInstructionFlush();

    this.teardownEventSource();
    this.status = "disconnected";
    this.reconnectAttempts = 0;
  }

  cleanup(): void {
    this.disconnect();
    this.instructionCallbacks.clear();
    this.statusCallbacks.clear();
  }

  // ----- internals -----

  private teardownEventSource(): void {
    if (this.eventSource) {
      try {
        this.eventSource.close();
      } catch {
        // ignore
      }
      this.eventSource = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30_000);

    this.clearReconnectTimer();
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      // Only reconnect if user didn't intentionally disconnect in the meantime
      if (!this.intentionalClose) this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer != null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearInstructionFlush(): void {
    if (this.instructionFlushTimer != null) {
      clearTimeout(this.instructionFlushTimer);
      this.instructionFlushTimer = null;
    }
    this.pendingInstructions = [];
  }

  private startHeartbeatWatchdog(): void {
    if (this.heartbeatTimer != null) return;

    this.heartbeatTimer = window.setInterval(() => {
      if (!this.eventSource) return;
      if (this.intentionalClose) return;

      const now = Date.now();
      const age = now - this.lastHeartbeatAt;

      // If server stopped sending keepalive (or connection went half-dead),
      // force reconnect.
      if (age > this.HEARTBEAT_STALE_MS) {
        this.status = "error";
        this.teardownEventSource();
        this.attemptReconnect();
      }
    }, this.HEARTBEAT_CHECK_MS);
  }

  private stopHeartbeatWatchdog(): void {
    if (this.heartbeatTimer != null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

export const instructionSSEService = new InstructionSSEService();

/**
 * Instruction SSE Service
 *
 * SSE client for receiving instructions from TeachingAssistant.
 * Replaces the legacy POST polling of /send_instruction_to_tutor.
 */

import { jwtUtils } from '../lib/jwt-utils';

const TEACHING_ASSISTANT_API_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

type InstructionCallback = (instruction: string) => void;
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type StatusCallback = (status: ConnectionStatus) => void;

class InstructionSSEService {
  private eventSource: EventSource | null = null;
  private instructionCallbacks: Set<InstructionCallback> = new Set();
  private statusCallbacks: Set<StatusCallback> = new Set();
  private _status: ConnectionStatus = 'disconnected';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: number | null = null;

  private set status(value: ConnectionStatus) {
    this._status = value;
    this.statusCallbacks.forEach(cb => cb(value));
  }

  get connectionStatus(): ConnectionStatus {
    return this._status;
  }

  onStatusChange(callback: StatusCallback): () => void {
    this.statusCallbacks.add(callback);
    return () => this.statusCallbacks.delete(callback);
  }

  connect(): void {
    if (this.eventSource) {
      return;
    }

    this.status = 'connecting';
    const token = jwtUtils.getToken();

    if (!token) {
      this.status = 'error';
      console.error('[InstructionSSE] No authentication token available');
      return;
    }

    const url = `${TEACHING_ASSISTANT_API_URL}/sse/instructions?token=${encodeURIComponent(token)}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      console.log('[InstructionSSE] Connected');
      this.status = 'connected';
      this.reconnectAttempts = 0;
    };

    this.eventSource.onerror = (error) => {
      console.error('[InstructionSSE] Error:', error);
      this.status = 'error';
      this.eventSource?.close();
      this.eventSource = null;
      this.attemptReconnect();
    };

    // Listen for instruction events
    this.eventSource.addEventListener('instruction', (event: MessageEvent) => {
      const instruction = event.data;
      console.log('[InstructionSSE] 📝 Received instruction:', instruction);
      this.instructionCallbacks.forEach(cb => cb(instruction));
    });

    // Listen for intervention events (struggle detection)
    this.eventSource.addEventListener('intervention', (event: MessageEvent) => {
      console.log('%c[InstructionSSE] 🆘 INTERVENTION RECEIVED', 'color: #FF6B6B; font-weight: bold; font-size: 14px;');
      try {
        const data = JSON.parse(event.data);
        console.log('%c  Type: ' + data.type, 'color: #4ECDC4; font-weight: bold;');
        console.log('%c  Message: ' + data.message, 'color: #FFE66D; font-weight: bold;');
        console.log('%c  Timestamp: ' + data.timestamp, 'color: #95E1D3;');
        console.log('%c  Full data:', 'color: #95E1D3;', data);
      } catch (e) {
        console.log('[InstructionSSE] 🆘 Intervention (raw):', event.data);
      }
    });

    // Listen for keepalive (just to confirm connection is alive)
    this.eventSource.addEventListener('keepalive', () => {
      console.log('[InstructionSSE] 💓 Keepalive received');
    });
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.status = 'disconnected';
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[InstructionSSE] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`[InstructionSSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }

  onInstruction(callback: InstructionCallback): () => void {
    this.instructionCallbacks.add(callback);
    return () => this.instructionCallbacks.delete(callback);
  }

  cleanup(): void {
    this.disconnect();
    this.instructionCallbacks.clear();
    this.statusCallbacks.clear();
  }
}

export const instructionSSEService = new InstructionSSEService();

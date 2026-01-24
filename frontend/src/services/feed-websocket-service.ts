/**
 * Feed WebSocket Service
 *
 * WebSocket client for streaming audio/video/transcript to TeachingAssistant.
 * Replaces the legacy POST-based feed-webhook-service.
 */

import { jwtUtils } from '../lib/jwt-utils';

const TEACHING_ASSISTANT_WS_URL =
  import.meta.env.VITE_TEACHING_ASSISTANT_WS_URL ||
  (import.meta.env.VITE_TEACHING_ASSISTANT_API_URL?.replace('http', 'ws') || 'ws://localhost:8002');

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type StatusCallback = (status: ConnectionStatus) => void;

class FeedWebSocketService {
  private socket: WebSocket | null = null;
  private audioBuffer: string[] = [];
  private batchInterval: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private statusCallbacks: Set<StatusCallback> = new Set();
  private _status: ConnectionStatus = 'disconnected';
  private pingInterval: number | null = null;

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

  async connect(): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.status = 'connecting';
    const token = jwtUtils.getToken();

    if (!token) {
      this.status = 'error';
      throw new Error('No authentication token available');
    }

    return new Promise((resolve, reject) => {
      const url = `${TEACHING_ASSISTANT_WS_URL}/ws/feed?token=${encodeURIComponent(token)}`;
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log('[FeedWebSocket] Connected');
        this.status = 'connected';
        this.reconnectAttempts = 0;
        this.startAudioBatching();
        this.startPingInterval();
        resolve();
      };

      this.socket.onclose = (event) => {
        console.log(`[FeedWebSocket] Closed: ${event.code} ${event.reason}`);
        this.status = 'disconnected';
        this.stopAudioBatching();
        this.stopPingInterval();

        // Only attempt reconnect if not a normal closure
        if (event.code !== 1000) {
          this.attemptReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error('[FeedWebSocket] Error:', error);
        this.status = 'error';
        reject(error);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle pong (existing)
          if (data.type === 'pong') {
            // Keepalive response - connection is healthy
            return;
          }
          
          // Handle disconnect signal from backend
          if (data.type === 'disconnect') {
            console.warn('[FeedWebSocket] Received disconnect signal:', data.reason);
            
            // Emit custom event for FloatingControlPanel to handle
            const disconnectEvent = new CustomEvent('backend-disconnect', {
              detail: {
                reason: data.reason,
                message: data.message
              }
            });
            window.dispatchEvent(disconnectEvent);
            
            // Show toast notification
            import('@/components/ui/sonner').then(({ toast }) => {
              toast.error("⏱️ Session Auto-Ended", {
                description: data.message || "Your tutoring session has ended.",
                duration: 8000,
                action: {
                  label: "Buy More",
                  onClick: () => {
                    window.location.href = '/pricing';
                  }
                }
              });
            });
            
            // Close the connection
            this.disconnect();
            return;
          }
        } catch (e) {
          console.warn('[FeedWebSocket] Failed to parse message:', e);
        }
      };
    });
  }

  disconnect(): void {
    this.stopAudioBatching();
    this.stopPingInterval();
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this.status = 'disconnected';
    this.reconnectAttempts = 0;
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[FeedWebSocket] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`[FeedWebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect().catch(console.error), delay);
  }

  private startAudioBatching(): void {
    if (this.batchInterval) return;

    this.batchInterval = window.setInterval(() => {
      this.flushAudioBuffer();
    }, 2000); // 2 second batching
  }

  private stopAudioBatching(): void {
    if (this.batchInterval) {
      clearInterval(this.batchInterval);
      this.batchInterval = null;
    }
    this.flushAudioBuffer(); // Send any remaining audio
  }

  private startPingInterval(): void {
    if (this.pingInterval) return;

    // Send ping every 25 seconds to keep connection alive
    this.pingInterval = window.setInterval(() => {
      this.sendMessage({ type: 'ping' });
    }, 25000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private flushAudioBuffer(): void {
    if (this.audioBuffer.length === 0) return;
    if (this.socket?.readyState !== WebSocket.OPEN) return;

    const combinedAudio = this.audioBuffer.join('');
    this.audioBuffer = [];

    this.sendMessage({
      type: 'audio',
      timestamp: new Date().toISOString(),
      data: { audio: combinedAudio }
    });
  }

  private sendMessage(message: object): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  sendAudio(base64: string): void {
    this.audioBuffer.push(base64);
  }

  sendMedia(base64: string): void {
    this.sendMessage({
      type: 'media',
      timestamp: new Date().toISOString(),
      data: { media: base64 }
    });
  }

  sendTranscript(transcript: string, speaker: 'user' | 'tutor' = 'tutor'): void {
    this.sendMessage({
      type: 'transcript',
      timestamp: new Date().toISOString(),
      data: { transcript, speaker }
    });
  }

  // Cleanup method
  cleanup(): void {
    this.disconnect();
    this.statusCallbacks.clear();
  }
}

export const feedWebSocketService = new FeedWebSocketService();

/**
 * HeyGen Streaming Avatar Component
 *
 * Displays a real-time video avatar that can speak text with lip-sync.
 * Uses WebRTC to receive video/audio from HeyGen's servers.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { apiUtils } from '@/lib/api-utils';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface HeyGenSession {
  session_id: string;
  sdp: { type: string; sdp: string };
  access_token: string;
  url: string;
  ice_servers: RTCIceServer[];
  realtime_endpoint: string;
  session_duration_limit: number;
}

interface HeyGenAvatarProps {
  onReady?: () => void;
  onSpeakingChange?: (isSpeaking: boolean) => void;
  onError?: (error: string) => void;
  className?: string;
  autoStart?: boolean;
}

export function HeyGenAvatar({
  onReady,
  onSpeakingChange,
  onError,
  className = '',
  autoStart = true,
}: HeyGenAvatarProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const sessionRef = useRef<HeyGenSession | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<number>(600);

  // Create HeyGen session
  const createSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/heygen/session`, { quality: 'medium' });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create HeyGen session');
      }

      const session: HeyGenSession = await response.json();
      sessionRef.current = session;
      setTimeRemaining(session.session_duration_limit);

      console.log('[HeyGen] Session created:', session.session_id);

      // Set up WebRTC connection
      await setupWebRTC(session);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      console.error('[HeyGen] Session creation failed:', message);
      setError(message);
      onError?.(message);
    } finally {
      setIsLoading(false);
    }
  }, [onError]);

  // Set up WebRTC peer connection
  const setupWebRTC = async (session: HeyGenSession) => {
    try {
      // Create peer connection with ICE servers
      const pc = new RTCPeerConnection({
        iceServers: session.ice_servers.length > 0
          ? session.ice_servers
          : [{ urls: 'stun:stun.l.google.com:19302' }],
      });
      peerConnectionRef.current = pc;

      // Handle incoming video/audio tracks
      pc.ontrack = (event) => {
        console.log('[HeyGen] Received track:', event.track.kind);
        if (videoRef.current && event.streams[0]) {
          videoRef.current.srcObject = event.streams[0];
        }
      };

      // Handle ICE connection state
      pc.oniceconnectionstatechange = () => {
        console.log('[HeyGen] ICE state:', pc.iceConnectionState);
        if (pc.iceConnectionState === 'connected') {
          setIsConnected(true);
          onReady?.();
        } else if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
          setIsConnected(false);
        }
      };

      // Set remote description (HeyGen's offer)
      await pc.setRemoteDescription(new RTCSessionDescription(session.sdp));

      // Create and set local description (our answer)
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      // Send answer to HeyGen to start the session
      const startResponse = await apiUtils.post(
        `${DASH_API_URL}/api/heygen/session/${session.session_id}/start`,
        { sdp: answer }
      );

      if (!startResponse.ok) {
        throw new Error('Failed to start HeyGen session');
      }

      console.log('[HeyGen] Session started successfully');

    } catch (err) {
      const message = err instanceof Error ? err.message : 'WebRTC setup failed';
      console.error('[HeyGen] WebRTC setup failed:', message);
      setError(message);
      onError?.(message);
    }
  };

  // Make avatar speak
  const speak = useCallback(async (text: string) => {
    if (!sessionRef.current || !isConnected) {
      console.warn('[HeyGen] Cannot speak: not connected');
      return;
    }

    try {
      setIsSpeaking(true);
      onSpeakingChange?.(true);

      const response = await apiUtils.post(
        `${DASH_API_URL}/api/heygen/session/${sessionRef.current.session_id}/speak`,
        { text, task_type: 'talk' }
      );

      if (!response.ok) {
        throw new Error('Failed to send speak command');
      }

      console.log('[HeyGen] Speak command sent');

      // Estimate speaking duration (rough: 150 words per minute)
      const wordCount = text.split(/\s+/).length;
      const estimatedDuration = (wordCount / 150) * 60 * 1000;

      setTimeout(() => {
        setIsSpeaking(false);
        onSpeakingChange?.(false);
      }, Math.max(estimatedDuration, 1000));

    } catch (err) {
      console.error('[HeyGen] Speak failed:', err);
      setIsSpeaking(false);
      onSpeakingChange?.(false);
    }
  }, [isConnected, onSpeakingChange]);

  // Close session
  const closeSession = useCallback(async () => {
    if (sessionRef.current) {
      try {
        await apiUtils.authenticatedFetch(
          `${DASH_API_URL}/api/heygen/session/${sessionRef.current.session_id}`,
          { method: 'DELETE' }
        );
        console.log('[HeyGen] Session closed');
      } catch (err) {
        console.error('[HeyGen] Failed to close session:', err);
      }
    }

    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    sessionRef.current = null;
    setIsConnected(false);
  }, []);

  // Auto-start on mount
  useEffect(() => {
    if (autoStart) {
      createSession();
    }

    return () => {
      closeSession();
    };
  }, [autoStart, createSession, closeSession]);

  // Session timer
  useEffect(() => {
    if (!isConnected || timeRemaining <= 0) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          closeSession();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isConnected, timeRemaining, closeSession]);

  // Expose speak method via ref
  useEffect(() => {
    // @ts-ignore - attach speak method to window for debugging
    window.heygenSpeak = speak;
  }, [speak]);

  return (
    <div className={`heygen-avatar ${className}`}>
      {isLoading && (
        <div className="heygen-loading">
          <div className="spinner" />
          <span>Loading avatar...</span>
        </div>
      )}

      {error && (
        <div className="heygen-error">
          <span className="material-symbols-outlined">error</span>
          <span>{error}</span>
          <button onClick={createSession}>Retry</button>
        </div>
      )}

      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={false}
        className={`heygen-video ${isConnected ? 'connected' : ''}`}
        style={{ display: isLoading || error ? 'none' : 'block' }}
      />

      {isConnected && (
        <div className="heygen-status">
          <span className={`status-dot ${isSpeaking ? 'speaking' : 'idle'}`} />
          <span className="time-remaining">
            {Math.floor(timeRemaining / 60)}:{(timeRemaining % 60).toString().padStart(2, '0')}
          </span>
        </div>
      )}
    </div>
  );
}

// Export hook for external control
export function useHeyGenAvatar() {
  const speak = useCallback((text: string) => {
    // @ts-ignore
    if (window.heygenSpeak) {
      // @ts-ignore
      window.heygenSpeak(text);
    }
  }, []);

  return { speak };
}

export default HeyGenAvatar;

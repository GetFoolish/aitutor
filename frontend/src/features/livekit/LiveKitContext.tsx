/**
 * LiveKit Context Provider
 *
 * Manages LiveKit room connection state and provides
 * hooks for voice/video tutoring sessions.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  ReactNode,
} from 'react';
import { Room, ConnectionState, RoomEvent } from 'livekit-client';
import { apiUtils } from '../../lib/api-utils';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface LiveKitContextType {
  room: Room | null;
  connectionState: ConnectionState;
  token: string | null;
  serverUrl: string | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  fetchToken: () => Promise<{ token: string; url: string } | undefined>;
}

const LiveKitContext = createContext<LiveKitContextType | undefined>(undefined);

interface LiveKitProviderProps {
  children: ReactNode;
  roomName?: string;
}

export function LiveKitProvider({
  children,
  roomName = 'tutoring-session',
}: LiveKitProviderProps) {
  const [room, setRoom] = useState<Room | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    ConnectionState.Disconnected
  );
  const [token, setToken] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  // Fetch token from DASH API
  const fetchToken = useCallback(async () => {
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/livekit-token`, {
        room_name: roomName,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch token: ${response.status}`);
      }

      const data = await response.json();
      setToken(data.token);
      setServerUrl(data.url);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch LiveKit token';
      setError(message);
      console.error('[LiveKit] Token fetch error:', message);
      throw err;
    }
  }, [roomName]);

  // Connect to LiveKit room
  const connect = useCallback(async () => {
    if (isConnecting || connectionState === ConnectionState.Connected) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Fetch fresh token
      const { token: freshToken, url } = await fetchToken();

      // Create new room
      const newRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
        // Enable video receiving for agent's potential video
        videoCaptureDefaults: {
          resolution: { width: 640, height: 480 },
        },
      });

      // Set up event listeners
      newRoom.on(RoomEvent.ConnectionStateChanged, (state) => {
        console.log('[LiveKit] Connection state:', state);
        setConnectionState(state);
      });

      newRoom.on(RoomEvent.Disconnected, () => {
        console.log('[LiveKit] Disconnected from room');
        setRoom(null);
      });

      newRoom.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('[LiveKit] Participant connected:', participant.identity);
      });

      newRoom.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log('[LiveKit] Participant disconnected:', participant.identity);
      });

      // Connect to room
      await newRoom.connect(url, freshToken);
      setRoom(newRoom);
      console.log('[LiveKit] Connected to room:', newRoom.name);

      // Enable microphone so agent can hear user
      try {
        await newRoom.localParticipant.setMicrophoneEnabled(true);
        console.log('[LiveKit] Microphone enabled');
      } catch (micError) {
        console.error('[LiveKit] Failed to enable microphone:', micError);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect to LiveKit';
      setError(message);
      console.error('[LiveKit] Connection error:', err);
    } finally {
      setIsConnecting(false);
    }
  }, [fetchToken, isConnecting, connectionState]);

  // Disconnect from room
  const disconnect = useCallback(() => {
    if (room) {
      room.disconnect();
      setRoom(null);
      setConnectionState(ConnectionState.Disconnected);
      console.log('[LiveKit] Disconnected');
    }
  }, [room]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (room) {
        room.disconnect();
      }
    };
  }, [room]);

  const value: LiveKitContextType = {
    room,
    connectionState,
    token,
    serverUrl,
    isConnected: connectionState === ConnectionState.Connected,
    isConnecting,
    error,
    connect,
    disconnect,
    fetchToken,
  };

  return (
    <LiveKitContext.Provider value={value}>{children}</LiveKitContext.Provider>
  );
}

export function useLiveKit() {
  const context = useContext(LiveKitContext);
  if (!context) {
    throw new Error('useLiveKit must be used within a LiveKitProvider');
  }
  return context;
}

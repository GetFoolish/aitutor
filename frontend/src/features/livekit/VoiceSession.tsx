/**
 * Voice Session Component
 *
 * Handles the voice AI tutoring session with LiveKit.
 * Provides visual feedback for agent state and controls.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
  VoiceAssistantControlBar,
  AgentState,
  useRoomContext,
} from '@livekit/components-react';
import '@livekit/components-styles';
import './VoiceSession.css';

// Alias for clarity
const useLiveKitRoom = useRoomContext;

interface VoiceSessionProps {
  token: string;
  serverUrl: string;
  onConnectionChange?: (connected: boolean) => void;
  onAgentStateChange?: (state: AgentState) => void;
  onRoomChange?: (room: import('livekit-client').Room | null) => void;
}

/**
 * Agent visualizer showing current speaking state
 */
function AgentVisualizer() {
  const { state, audioTrack } = useVoiceAssistant();

  const getStateLabel = (state: AgentState) => {
    switch (state) {
      case 'listening':
        return 'Listening...';
      case 'thinking':
        return 'Thinking...';
      case 'speaking':
        return 'Speaking';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Ready';
    }
  };

  const getStateColor = (state: AgentState) => {
    switch (state) {
      case 'listening':
        return '#22c55e'; // green
      case 'thinking':
        return '#eab308'; // yellow
      case 'speaking':
        return '#3b82f6'; // blue
      case 'connecting':
        return '#f97316'; // orange
      case 'disconnected':
        return '#ef4444'; // red
      default:
        return '#6b7280'; // gray
    }
  };

  return (
    <div className="agent-visualizer">
      <div className="visualizer-container">
        <BarVisualizer
          state={state}
          barCount={5}
          trackRef={audioTrack}
          className="audio-visualizer"
          options={{
            minHeight: 10,
            maxHeight: 60,
          }}
        />
      </div>
      <div
        className="agent-state-label"
        style={{ color: getStateColor(state) }}
      >
        <span
          className="state-indicator"
          style={{ backgroundColor: getStateColor(state) }}
        />
        {getStateLabel(state)}
      </div>
    </div>
  );
}

/**
 * Session content - rendered inside LiveKitRoom
 */
function SessionContent({
  onConnectionChange,
  onAgentStateChange,
  onRoomChange,
}: Pick<VoiceSessionProps, 'onConnectionChange' | 'onAgentStateChange' | 'onRoomChange'>) {
  const { state } = useVoiceAssistant();
  const room = useLiveKitRoom();

  useEffect(() => {
    onAgentStateChange?.(state);
  }, [state, onAgentStateChange]);

  // Pass room reference to parent
  useEffect(() => {
    onRoomChange?.(room);
    return () => {
      onRoomChange?.(null);
    };
  }, [room, onRoomChange]);

  return (
    <div className="voice-session-content">
      {/* Audio renderer for agent voice */}
      <RoomAudioRenderer />

      {/* Visual feedback */}
      <AgentVisualizer />

      {/* Control bar for mic toggle */}
      <VoiceAssistantControlBar
        className="voice-control-bar"
        controls={{
          microphone: true,
          leave: false, // We handle disconnect separately
        }}
      />
    </div>
  );
}

/**
 * Main Voice Session component
 */
export function VoiceSession({
  token,
  serverUrl,
  onConnectionChange,
  onAgentStateChange,
  onRoomChange,
}: VoiceSessionProps) {
  const [isConnected, setIsConnected] = useState(false);

  const handleConnected = useCallback(() => {
    setIsConnected(true);
    onConnectionChange?.(true);
    console.log('[VoiceSession] Connected to room');
  }, [onConnectionChange]);

  const handleDisconnected = useCallback(() => {
    setIsConnected(false);
    onConnectionChange?.(false);
    onRoomChange?.(null);
    console.log('[VoiceSession] Disconnected from room');
  }, [onConnectionChange, onRoomChange]);

  const handleError = useCallback((error: Error) => {
    console.error('[VoiceSession] Error:', error);
  }, []);

  if (!token || !serverUrl) {
    return (
      <div className="voice-session voice-session-loading">
        <span className="loading-text">Initializing voice session...</span>
      </div>
    );
  }

  return (
    <div className="voice-session">
      <LiveKitRoom
        token={token}
        serverUrl={serverUrl}
        connect={true}
        audio={true}
        video={false}
        onConnected={handleConnected}
        onDisconnected={handleDisconnected}
        onError={handleError}
        options={{
          adaptiveStream: true,
          dynacast: true,
        }}
      >
        <SessionContent
          onConnectionChange={onConnectionChange}
          onAgentStateChange={onAgentStateChange}
          onRoomChange={onRoomChange}
        />
      </LiveKitRoom>
    </div>
  );
}

export default VoiceSession;

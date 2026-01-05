/**
 * HeyGen Bridge Component
 *
 * Connects the voice AI system to the HeyGen avatar.
 * Supports both LiveKit agent responses and legacy TutorContext responses.
 * When the AI agent responds, this component sends the text to HeyGen for lip-synced speech.
 */

import { useEffect, useCallback, useRef } from 'react';
import { RoomEvent, DataPacket_Kind } from 'livekit-client';
import { useLiveKit } from '../livekit';
import { useTutorContext } from '../tutor';
import { useHeyGenAvatar } from './HeyGenAvatar';

// Feature flags
const USE_LIVEKIT = import.meta.env.VITE_USE_LIVEKIT === 'true';

interface HeyGenBridgeProps {
  enabled?: boolean;
}

export function HeyGenBridge({ enabled = true }: HeyGenBridgeProps) {
  const { speak } = useHeyGenAvatar();
  const lastResponseRef = useRef<string>('');
  const pendingTextRef = useRef<string>('');

  // LiveKit room for listening to agent transcriptions
  const liveKitContext = USE_LIVEKIT ? useLiveKit() : null;
  const room = liveKitContext?.room;

  // TutorContext for legacy Gemini client support
  const tutorContext = useTutorContext();
  const { client, connected } = tutorContext;

  // Send text to HeyGen avatar
  const handleAgentResponse = useCallback((text: string) => {
    if (!enabled || !text || text.trim().length === 0) return;

    // Avoid duplicate responses
    if (text === lastResponseRef.current) return;
    lastResponseRef.current = text;

    console.log('[HeyGenBridge] Sending to avatar:', text.substring(0, 50) + '...');
    speak(text);
  }, [enabled, speak]);

  // LiveKit: Listen for agent transcriptions via data messages
  useEffect(() => {
    if (!USE_LIVEKIT || !room || !enabled) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: DataPacket_Kind
    ) => {
      // Only process reliable messages (text data)
      if (kind !== DataPacket_Kind.RELIABLE) return;

      try {
        const decoder = new TextDecoder();
        const data = JSON.parse(decoder.decode(payload));

        // Handle transcription messages from agent
        if (data.type === 'transcription' && data.participant === 'agent') {
          if (data.isFinal && data.text) {
            // Final transcription - send to avatar
            handleAgentResponse(data.text);
          } else if (!data.isFinal && data.text) {
            // Partial transcription - accumulate
            pendingTextRef.current = data.text;
          }
        }

        // Handle direct speech messages from agent
        if (data.type === 'agent_speech' && data.text) {
          handleAgentResponse(data.text);
        }
      } catch (e) {
        // Not JSON or not a transcription message, ignore
      }
    };

    // Listen for track subscribed to get agent audio transcriptions
    const handleTrackSubscribed = (track: any, publication: any, participant: any) => {
      // Check if this is from an agent (non-local participant)
      if (participant.identity?.includes('agent') || participant.identity?.includes('tutor')) {
        console.log('[HeyGenBridge] Agent track subscribed:', track.kind);
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    room.on(RoomEvent.TrackSubscribed, handleTrackSubscribed);

    console.log('[HeyGenBridge] Listening for LiveKit agent responses');

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
      room.off(RoomEvent.TrackSubscribed, handleTrackSubscribed);
    };
  }, [room, enabled, handleAgentResponse]);

  // TutorContext: Listen for legacy Gemini client responses
  useEffect(() => {
    // Only use TutorContext if LiveKit is not enabled
    if (USE_LIVEKIT || !connected || !client || !enabled) return;

    // Listen for tool responses or text responses from the AI
    const handleLog = (log: any) => {
      // Check if this is an agent response
      if (log.type === 'server.content' && log.message?.parts) {
        const textParts = log.message.parts
          .filter((p: any) => p.text)
          .map((p: any) => p.text)
          .join(' ');

        if (textParts) {
          handleAgentResponse(textParts);
        }
      }
    };

    client.on('log', handleLog);

    return () => {
      client.off('log', handleLog);
    };
  }, [connected, client, enabled, handleAgentResponse]);

  // This component doesn't render anything visible
  return null;
}

export default HeyGenBridge;

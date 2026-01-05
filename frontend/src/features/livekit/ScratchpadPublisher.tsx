/**
 * Scratchpad Publisher Component
 *
 * Publishes the scratchpad canvas as a video track to LiveKit
 * so the AI agent can see the student's work.
 */

import { useEffect, useRef, useCallback } from 'react';
import {
  LocalVideoTrack,
  Room,
  Track,
  VideoPresets,
} from 'livekit-client';

interface ScratchpadPublisherProps {
  room: Room | null;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  enabled: boolean;
  fps?: number;
}

/**
 * Publishes scratchpad canvas as video track to LiveKit room
 */
export function ScratchpadPublisher({
  room,
  canvasRef,
  enabled,
  fps = 2,
}: ScratchpadPublisherProps) {
  const trackRef = useRef<LocalVideoTrack | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const publishScratchpad = useCallback(async () => {
    if (!room || !canvasRef.current || !enabled) {
      return;
    }

    // Don't republish if already published
    if (trackRef.current) {
      return;
    }

    try {
      const canvas = canvasRef.current;

      // Create a media stream from the canvas
      const stream = canvas.captureStream(fps);
      streamRef.current = stream;

      const videoTrack = stream.getVideoTracks()[0];
      if (!videoTrack) {
        console.warn('[ScratchpadPublisher] No video track from canvas');
        return;
      }

      // Create LiveKit local video track
      const localTrack = new LocalVideoTrack(videoTrack, {
        loggerName: 'scratchpad',
      });

      // Publish to room
      await room.localParticipant.publishTrack(localTrack, {
        name: 'scratchpad',
        source: Track.Source.ScreenShare, // Use screen share source for scratchpad
        videoEncoding: VideoPresets.h360.encoding,
        simulcast: false,
      });

      trackRef.current = localTrack;
      console.log('[ScratchpadPublisher] Published scratchpad track');
    } catch (error) {
      console.error('[ScratchpadPublisher] Failed to publish:', error);
    }
  }, [room, canvasRef, enabled, fps]);

  const unpublishScratchpad = useCallback(async () => {
    if (trackRef.current && room) {
      try {
        await room.localParticipant.unpublishTrack(trackRef.current);
        trackRef.current.stop();
        trackRef.current = null;
        console.log('[ScratchpadPublisher] Unpublished scratchpad track');
      } catch (error) {
        console.error('[ScratchpadPublisher] Failed to unpublish:', error);
      }
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, [room]);

  // Publish/unpublish based on enabled state
  useEffect(() => {
    if (enabled && room?.state === 'connected') {
      publishScratchpad();
    } else {
      unpublishScratchpad();
    }
  }, [enabled, room?.state, publishScratchpad, unpublishScratchpad]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      unpublishScratchpad();
    };
  }, [unpublishScratchpad]);

  // This is a utility component, no visual output
  return null;
}

export default ScratchpadPublisher;

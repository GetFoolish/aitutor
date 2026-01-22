import React from "react";
import { VideoTrack, isTrackReference } from "@livekit/components-react";

export interface AvatarLiveVideoProps {
  videoTrack?: any; // LiveKit video track reference
  agentState?: string; // 'speaking' | 'listening' | 'thinking' | 'connecting' | 'disconnected'
  isLive?: boolean;
}

/**
 * Avatar Live Video Component
 *
 * Displays the live avatar video from LiveKit/Hedra when session is active.
 * Falls back to placeholder if video track is not available.
 */
export default function AvatarLiveVideo({
  videoTrack,
  agentState = "disconnected",
  isLive = false,
}: AvatarLiveVideoProps) {
  // Check if videoTrack is a valid LiveKit TrackReference
  const hasValidTrack = videoTrack && isTrackReference(videoTrack);

  console.log('[AvatarLiveVideo] Rendering with track:', hasValidTrack ? 'VALID' : 'INVALID', videoTrack);

  return (
    <div className="w-full h-full flex items-center justify-center bg-black relative">
      {hasValidTrack ? (
        <VideoTrack
          trackRef={videoTrack}
          className="w-full h-full object-cover object-top"
        />
      ) : (
        /* Placeholder when video track is not available */
        <div className="w-full h-full flex items-center justify-center">
          <div className="w-14 h-14 rounded-full bg-[#C4B5FD] flex items-center justify-center animate-pulse">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
        </div>
      )}

      {/* Live indicator bar */}
      {isLive && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#4ADE80] animate-pulse" />
      )}

      {/* Connecting overlay */}
      {agentState === 'connecting' && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span className="text-white text-[10px] font-medium">Connecting...</span>
          </div>
        </div>
      )}
    </div>
  );
}


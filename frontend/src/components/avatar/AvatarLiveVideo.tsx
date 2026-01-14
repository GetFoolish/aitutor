import React, { useEffect, useRef, useState } from "react";

export interface AvatarLiveVideoProps {
  videoTrack?: any; // LiveKit video track
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
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  
  // Check if videoTrack is a valid LiveKit TrackReference
  const hasValidTrack = videoTrack && videoTrack.track;

  // Attach/detach video track when it changes
  useEffect(() => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    if (hasValidTrack && videoTrack.track) {
      console.log('[AvatarLiveVideo] Attaching video track to element');
      setPlaybackError(null);

      // Autoplay policies are stricter when audio is enabled.
      // This avatar feed is video-only for UI purposes, so keep it muted.
      videoEl.muted = true;
      videoEl.playsInline = true;
      videoEl.autoplay = true;

      videoTrack.track.attach(videoEl);

      // Some browsers still require an explicit play() after attaching.
      // Ignore failures (we show a fallback state).
      const tryPlay = () => {
        try {
          const maybePromise = videoEl.play();
          if (maybePromise && typeof (maybePromise as any).catch === 'function') {
            (maybePromise as Promise<void>).catch((e) => {
              const msg = e instanceof Error ? e.message : String(e);
              setPlaybackError(msg);
            });
          }
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          setPlaybackError(msg);
        }
      };

      // Wait for metadata so play() has enough info.
      const onLoadedMetadata = () => tryPlay();
      videoEl.addEventListener('loadedmetadata', onLoadedMetadata);
      tryPlay();
      
      return () => {
        console.log('[AvatarLiveVideo] Detaching video track');
        videoEl.removeEventListener('loadedmetadata', onLoadedMetadata);
        videoTrack.track.detach(videoEl);
      };
    }
  }, [videoTrack, hasValidTrack]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-black relative">
      {hasValidTrack && !playbackError ? (
        <video
          ref={videoRef}
          className="w-full h-full object-cover object-top"
          autoPlay
          playsInline
          muted
          onError={() => setPlaybackError('Video element error')}
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

      {playbackError && hasValidTrack && (
        <div className="absolute inset-x-2 bottom-2 bg-black/70 text-white text-[9px] px-2 py-1 rounded border border-white/20">
          Video connected, waiting to play…
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


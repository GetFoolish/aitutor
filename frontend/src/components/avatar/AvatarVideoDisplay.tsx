import React, { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import cn from "classnames";
import AvatarLiveVideo from "./AvatarLiveVideo";

export interface AvatarVideoDisplayProps {
  isConnected: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  videoTrack?: any; // LiveKit video track
  agentState?: string; // 'speaking' | 'listening' | 'thinking' | 'connecting' | 'disconnected'
}

/**
 * Avatar Video Display Component
 *
 * Displays the avatar video with the following features:
 * - Live video when session is connected (from Hedra via LiveKit)
 * - Idle video loop when session is stopped/paused
 * - Speaker button to hear intro greeting with lip-synced video
 * - Click to expand (2x size)
 */
export default function AvatarVideoDisplay({
  isConnected,
  isExpanded,
  onToggleExpand,
  videoTrack,
  agentState = "disconnected",
}: AvatarVideoDisplayProps) {
  const isLive = isConnected && (agentState === 'listening' || agentState === 'speaking' || agentState === 'thinking');
  const containerRef = useRef<HTMLDivElement>(null);
  const idleVideoRef = useRef<HTMLVideoElement | null>(null);
  const greetingVideoRef = useRef<HTMLVideoElement | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [showGreeting, setShowGreeting] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [videoLoaded, setVideoLoaded] = useState(false);

  // Try to play idle video when component mounts
  useEffect(() => {
    const video = idleVideoRef.current;
    if (video && !showGreeting && !videoTrack && !videoError) {
      // Reset video error state on mount
      setVideoError(false);
      setVideoLoaded(false);

      video.load();
      video.play().then(() => {
        setVideoLoaded(true);
        console.log('[AvatarVideoDisplay] Idle video playing successfully');
      }).catch((err) => {
        console.warn('[AvatarVideoDisplay] Idle video autoplay failed:', err.name, err.message);
        // Don't set error if it's just an autoplay policy issue - video will show but paused
        if (err.name !== 'NotAllowedError' && err.name !== 'AbortError') {
          setVideoError(true);
        }
      });
    }
  }, [showGreeting, videoTrack]);

  // Size classes based on expanded state
  const sizeClasses = isExpanded
    ? 'w-[320px] h-[320px] md:w-[360px] md:h-[360px]'
    : 'w-full aspect-square max-w-[180px] md:max-w-[200px]';

  // Handle speaker click - play greeting with lip sync
  const handleSpeakerClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    // Don't play greeting if we're in a live session
    if (isConnected && videoTrack) {
      return;
    }

    if (!isPlaying) {
      // Create audio element if needed
      if (!audioElementRef.current) {
        const audio = document.createElement('audio');
        audio.src = '/avatar-greeting.mp3';
        audio.preload = 'auto';
        document.body.appendChild(audio);
        audioElementRef.current = audio;

        audio.onended = () => {
          setIsPlaying(false);
          setShowGreeting(false);
        };
      }

      const audio = audioElementRef.current;
      audio.currentTime = 0;
      audio.volume = 1.0;

      // Switch to greeting video
      setShowGreeting(true);

      try {
        setTimeout(async () => {
          const greetingVideo = greetingVideoRef.current;
          if (greetingVideo) {
            greetingVideo.currentTime = 0;
            await greetingVideo.play();
          }
          await audio.play();
          setIsPlaying(true);
        }, 50);
      } catch (err) {
        console.error('[AvatarVideoDisplay] Play failed:', err);
        setShowGreeting(false);
      }
    } else {
      // Stop playback
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current.currentTime = 0;
      }
      if (greetingVideoRef.current) {
        greetingVideoRef.current.pause();
      }
      setIsPlaying(false);
      setShowGreeting(false);
    }
  };

  // Stop greeting immediately when session connects (don't wait for video track)
  useEffect(() => {
    if (isConnected) {
      console.log('[AvatarVideoDisplay] Session connected - stopping greeting, waiting for video track');
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current.currentTime = 0;
      }
      if (greetingVideoRef.current) {
        greetingVideoRef.current.pause();
      }
      setIsPlaying(false);
      setShowGreeting(false);
    }
  }, [isConnected]);

  // Log when video track arrives
  useEffect(() => {
    if (videoTrack) {
      console.log('[AvatarVideoDisplay] Video track received - switching to live view');
    }
  }, [videoTrack]);

  // Ensure idle video plays when switching back
  useEffect(() => {
    if (!showGreeting && !videoTrack && idleVideoRef.current) {
      idleVideoRef.current.play().catch(() => {});
    }
  }, [showGreeting, videoTrack]);

  useEffect(() => {
    if (isExpanded && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [isExpanded]);

  // Determine what to show
  const showLiveVideo = isConnected && videoTrack;
  const showConnecting = isConnected && !videoTrack; // Waiting for Hedra video
  const showIdleVideo = !videoError && !showGreeting && !showLiveVideo && !showConnecting;
  const showGreetingVideo = !videoError && showGreeting && !showLiveVideo && !showConnecting;

  return (
    <motion.div
      ref={containerRef}
      className={cn(
        "relative bg-gradient-to-b from-gray-100 to-gray-200 dark:from-neutral-800 dark:to-neutral-900 rounded-lg overflow-hidden cursor-pointer transition-all duration-300 border-[2px] border-black dark:border-white",
        sizeClasses
      )}
      onClick={onToggleExpand}
      title={isExpanded ? "Click to shrink" : "Click to expand (2x)"}
      whileHover={{ scale: isExpanded ? 1 : 1.02 }}
      whileTap={{ scale: isExpanded ? 0.98 : 0.98 }}
    >
      {/* Live Avatar Video (when connected) */}
      {showLiveVideo && (
        <AvatarLiveVideo
          videoTrack={videoTrack}
          agentState={agentState}
          isLive={isLive}
        />
      )}

      {/* Connecting state - waiting for Hedra video track */}
      {showConnecting && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#FFFDF5] dark:bg-neutral-900">
          {/* Avatar silhouette placeholder */}
          <div className="relative mb-3">
            <div className="w-16 h-16 rounded-full bg-gray-200 dark:bg-neutral-700 flex items-center justify-center">
              <svg className="w-10 h-10 text-gray-400 dark:text-neutral-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            </div>
            {/* Spinning ring around avatar */}
            <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-[#4ADE80] rounded-full animate-spin" />
          </div>
          <span className="text-black dark:text-white text-[10px] font-black uppercase tracking-wider">
            Connecting...
          </span>
        </div>
      )}

      {/* Static idle video - loops */}
      {showIdleVideo && (
        <video
          ref={idleVideoRef}
          src="/avatar-idle-static.mp4"
          autoPlay
          loop
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover object-top"
          onLoadedData={() => {
            console.log('[AvatarVideoDisplay] Idle video loaded successfully');
            setVideoError(false);
            setVideoLoaded(true);
          }}
          onError={(e) => {
            const video = e.currentTarget;
            console.error('[AvatarVideoDisplay] Video error:', video.error?.code, video.error?.message);
            // Only show error state for actual errors (not range issues)
            if (video.error && video.error.code !== 2) { // MEDIA_ERR_NETWORK is 2
              setVideoError(true);
            }
          }}
        />
      )}

      {/* Greeting video - lip sync, plays once */}
      {showGreetingVideo && (
        <video
          ref={greetingVideoRef}
          src="/avatar-greeting.mp4"
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover object-top"
          onLoadedData={() => console.log('[AvatarVideoDisplay] Greeting video loaded')}
          onError={(e) => {
            console.error('[AvatarVideoDisplay] Greeting video error:', e.currentTarget.error);
            setShowGreeting(false);
          }}
        />
      )}

      {/* Fallback placeholder - shows static avatar image */}
      {videoError && !showLiveVideo && (
        <div className="absolute inset-0">
          <img
            src="/avatar-ms-davis-clean.png"
            alt="Ms. Davis AI Tutor"
            className="w-full h-full object-cover object-top"
          />
        </div>
      )}

      {/* Connection status indicator */}
      <div className="absolute bottom-2 left-2 right-2">
        <div
          className={cn(
            "h-1 rounded-full transition-colors",
            isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
          )}
        />
      </div>

      {/* Status label */}
      <div className="absolute top-2 left-2">
        <span
          className={cn(
            "px-2 py-0.5 text-[8px] font-black uppercase border-[2px] border-black",
            isConnected
              ? agentState === 'speaking' ? "bg-[#3b82f6] text-white" :
                agentState === 'listening' ? "bg-[#4ADE80] text-black" :
                agentState === 'thinking' ? "bg-[#eab308] text-black" :
                "bg-[#4ADE80] text-black"
              : "bg-[#FFFDF5] text-black"
          )}
        >
          {isConnected
            ? agentState === 'speaking' ? "SPEAKING" :
              agentState === 'listening' ? "LISTENING" :
              agentState === 'thinking' ? "THINKING" :
              "LIVE"
            : "IDLE"}
        </span>
      </div>

      {/* Speaker button - click to hear intro greeting */}
      {!showLiveVideo && (
        <button
          onClick={handleSpeakerClick}
          className="absolute bottom-8 right-2 w-9 h-9 bg-white hover:bg-gray-100 rounded-full flex items-center justify-center transition-all z-20 border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
          title={isPlaying ? "Stop" : "Click to hear greeting"}
        >
          {isPlaying ? (
            <svg className="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" fill="currentColor"/>
              <rect x="14" y="4" width="4" height="16" fill="currentColor"/>
            </svg>
          ) : (
            <svg className="w-4 h-4 text-black" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
            </svg>
          )}
        </button>
      )}

      {/* Expand/collapse hint */}
      <div className="absolute top-2 right-2 opacity-0 hover:opacity-100 transition-opacity">
        <div className="w-6 h-6 bg-black/50 rounded flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {isExpanded ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            )}
          </svg>
        </div>
      </div>
    </motion.div>
  );
}

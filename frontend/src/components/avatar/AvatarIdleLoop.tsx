import React, { useRef, useEffect, useState } from "react";

export interface AvatarIdleLoopProps {}

/**
 * Avatar Idle Loop Component
 * 
 * Plays an idle animation when the avatar session is stopped/paused.
 * Idle video (2 minutes): frontend/public/videos/avatar-idle-loop.mp4
 * Falls back to animated gradient if the video can't be loaded/played.
 */
export default function AvatarIdleLoop({}: AvatarIdleLoopProps) {
  const videoLoopRef = useRef<HTMLVideoElement>(null);
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    if (videoLoopRef.current && !videoError) {
      videoLoopRef.current.playbackRate = 1; // Ensure normal speed
      videoLoopRef.current.play().catch(error => {
        // Silently handle autoplay errors - fallback will show
        if (error.name !== 'AbortError') {
          setVideoError(true);
        }
      });
    }
  }, [videoError]);

  // Handle video load error (suppress 416 and other errors)
  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const video = e.currentTarget;
    // Suppress 416 (Range Not Satisfiable) and other video errors
    // The fallback UI will handle the display
    if (video.error) {
      // Only log if it's not a 416 error (empty file)
      if (video.error.code !== 16) { // 16 = MEDIA_ERR_SRC_NOT_SUPPORTED
        console.debug('Video load error (handled gracefully):', video.error.code);
      }
    }
    setVideoError(true);
  };

  // If video error or video not available, show animated gradient fallback
  if (videoError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#C4B5FD] via-[#A78BFA] to-[#7C3AED] relative overflow-hidden">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#C4B5FD] via-[#A78BFA] to-[#7C3AED] animate-pulse" />
        
        {/* Avatar placeholder */}
        <div className="relative z-10 w-24 h-24 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm shadow-lg">
          <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
        </div>
        
        {/* Subtle shimmer animation */}
        <div 
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
          style={{
            animation: 'shimmer 3s ease-in-out infinite',
          }}
        />
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <video
        ref={videoLoopRef}
        className="w-full h-full object-cover"
        loop
        muted
        playsInline
        autoPlay
        preload="auto"
        onError={handleVideoError}
        onAbort={() => {
          // Handle abort (e.g., 416 Range Not Satisfiable) gracefully
          setVideoError(true);
        }}
        onLoadedData={() => {
          // Video loaded successfully
          setVideoError(false);
        }}
      >
        <source src="/videos/avatar-idle-loop.mp4" type="video/mp4" />
      </video>
      
      {/* Fallback overlay (hidden if video loads) */}
      {videoError && (
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[#C4B5FD] to-[#7C3AED]">
          <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}


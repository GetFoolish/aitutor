import React, { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import cn from "classnames";
import AvatarLiveVideo from "./AvatarLiveVideo";
import AvatarIdleLoop from "./AvatarIdleLoop";

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
 * - Live video when session is connected
 * - 2-minute idle loop when session is stopped/paused
 * - Click to expand (2x size)
 * - Smooth animations
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

  useEffect(() => {
    if (isExpanded && containerRef.current) {
      // Scroll the expanded video into view
      containerRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [isExpanded]);

  return (
    <motion.div
      ref={containerRef}
      className={cn(
        "relative w-full aspect-square bg-gradient-to-b from-gray-100 to-gray-200 dark:from-neutral-800 dark:to-neutral-900 rounded-lg overflow-hidden cursor-pointer transition-all duration-300",
        isExpanded ? "scale-[2] z-[1001] mb-4" : "mb-2"
      )}
      onClick={onToggleExpand}
      title={isExpanded ? "Click to shrink" : "Click to expand (2x)"}
      whileHover={{ scale: isExpanded ? 2 : 1.02 }}
      whileTap={{ scale: isExpanded ? 1.95 : 0.98 }}
    >
      {/* Live Avatar Video (when connected) */}
      {isConnected ? (
        <AvatarLiveVideo
          videoTrack={videoTrack}
          agentState={agentState}
          isLive={isLive}
        />
      ) : (
        /* Video Loop (2 minutes) when session is stopped/paused */
        <AvatarIdleLoop />
      )}

      {/* Expansion indicator */}
      <div className="absolute top-2 right-2 bg-black/50 text-white text-[8px] px-1.5 py-0.5 rounded font-bold uppercase backdrop-blur-sm">
        {isExpanded ? "2x" : "Click to expand"}
      </div>

      {/* Status indicator */}
      {isConnected && (
        <div className="absolute bottom-2 left-2 bg-black/50 text-white text-[8px] px-1.5 py-0.5 rounded font-bold uppercase backdrop-blur-sm">
          {agentState === 'speaking' ? "Speaking" :
           agentState === 'listening' ? "Listening" :
           agentState === 'thinking' ? "Thinking" :
           agentState === 'connecting' ? "Connecting..." :
           "Ready"}
        </div>
      )}
    </motion.div>
  );
}

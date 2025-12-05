import React, { useEffect, useState, RefObject, useRef } from "react";
import cn from "classnames";

interface MediaMixerDisplayProps {
  canvasRef: RefObject<HTMLCanvasElement>;
  onStatusChange?: (status: {
    isConnected: boolean;
    error: string | null;
  }) => void;
  isCameraEnabled?: boolean;
  isScreenShareEnabled?: boolean;
  isCanvasEnabled?: boolean;
}

const MediaMixerDisplay: React.FC<MediaMixerDisplayProps> = ({
  canvasRef,
  onStatusChange,
  isCameraEnabled = true,
  isScreenShareEnabled = true,
  isCanvasEnabled = true,
}) => {
  const [isConnected, setIsConnected] = useState(true); // Frontend-based, always "connected"
  const [error, setError] = useState<string | null>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (onStatusChange) {
      onStatusChange({ isConnected, error });
    }
  }, [isConnected, error, onStatusChange]);

  // Mirror the MediaMixer canvas to the display canvas
  useEffect(() => {
    const sourceCanvas = canvasRef.current;
    const displayCanvas = displayCanvasRef.current;

    if (!sourceCanvas || !displayCanvas) {
      return;
    }

    const ctx = displayCanvas.getContext('2d');
    if (!ctx) {
      setError('Failed to get canvas context');
      return;
    }

    // Set display canvas size to match source
    displayCanvas.width = sourceCanvas.width;
    displayCanvas.height = sourceCanvas.height;

    let lastDrawTime = 0;
    const targetFPS = 10; // Match MediaMixer FPS
    const frameInterval = 1000 / targetFPS;

    const drawFrame = (timestamp: number) => {
      if (timestamp - lastDrawTime >= frameInterval) {
        // Only draw if source canvas has content
        if (sourceCanvas.width > 0 && sourceCanvas.height > 0) {
          // Update display canvas size if source changed
          if (displayCanvas.width !== sourceCanvas.width || displayCanvas.height !== sourceCanvas.height) {
            displayCanvas.width = sourceCanvas.width;
            displayCanvas.height = sourceCanvas.height;
          }

          // Draw the source canvas onto the display canvas
          ctx.drawImage(sourceCanvas, 0, 0);
        }
        lastDrawTime = timestamp;
      }

      animationFrameRef.current = requestAnimationFrame(drawFrame);
    };

    // Start the render loop
    animationFrameRef.current = requestAnimationFrame(drawFrame);
    setIsConnected(true);
    setError(null);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [canvasRef]);

  return (
    <div className="flex flex-col w-full bg-white dark:bg-[#000000] text-black dark:text-white overflow-hidden transition-colors duration-300">
      <div className="flex flex-col items-center justify-center p-0 bg-white dark:bg-[#000000] relative overflow-hidden group transition-colors duration-300">
        {error && (
          <div className="text-sm text-center p-4 border-[3px] border-black dark:border-white bg-[#FF006E] text-white max-w-[90%] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] z-20 absolute">
            <span className="material-symbols-outlined text-2xl mb-2 block font-bold">
              error
            </span>
            {error}
          </div>
        )}
        {!isConnected && !error && (
          <div className="flex flex-col items-center gap-3 text-black dark:text-white animate-pulse z-20 py-12">
            <span className="material-symbols-outlined text-4xl opacity-50 font-bold">
              connecting_airports
            </span>
            <div className="text-sm font-black uppercase">Initializing...</div>
          </div>
        )}
        {isConnected && (
          <div className="w-full h-auto flex items-center justify-center bg-white dark:bg-[#000000]">
            <canvas
              ref={displayCanvasRef}
              className="w-full h-auto object-contain"
              style={{ maxHeight: '600px' }}
            />
          </div>
        )}

        {/* Status indicators - Neo-Brutalist style */}
        <div className="absolute bottom-2 left-2 flex gap-2 z-10">
          {isCameraEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#C4B5FD] text-black dark:text-white text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
              <span className="w-1.5 h-1.5 bg-black dark:bg-white animate-pulse" />
              Camera
            </div>
          )}
          {isScreenShareEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#FFD93D] text-black text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
              <span className="w-1.5 h-1.5 bg-black dark:bg-white animate-pulse" />
              Screen
            </div>
          )}
          {isCanvasEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#FF6B6B] text-white text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
              <span className="w-1.5 h-1.5 bg-white animate-pulse" />
              Canvas
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaMixerDisplay;

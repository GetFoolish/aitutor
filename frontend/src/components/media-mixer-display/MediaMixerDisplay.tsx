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
    <div className="flex flex-col w-full bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white overflow-hidden transition-colors duration-300">
      <div className="flex flex-col items-center justify-center p-0 bg-neutral-50 dark:bg-black/95 relative overflow-hidden group transition-colors duration-300">
        {error && (
          <div className="text-sm text-center p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400 max-w-[90%] backdrop-blur-md shadow-lg z-20 absolute">
            <span className="material-symbols-outlined text-2xl mb-2 block">
              error
            </span>
            {error}
          </div>
        )}
        {!isConnected && !error && (
          <div className="flex flex-col items-center gap-3 text-neutral-500 dark:text-neutral-400 animate-pulse z-20 py-12">
            <span className="material-symbols-outlined text-4xl opacity-50">
              connecting_airports
            </span>
            <div className="text-sm font-medium">Initializing...</div>
          </div>
        )}
        {isConnected && (
          <div className="w-full h-auto flex items-center justify-center bg-white dark:bg-black">
            <canvas
              ref={displayCanvasRef}
              className="w-full h-auto object-contain"
              style={{ maxHeight: '600px' }}
            />
          </div>
        )}

        {/* Status indicators */}
        <div className="absolute bottom-2 left-2 flex gap-2 z-10">
          {isCameraEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-purple-500/20 text-purple-600 dark:text-purple-400 text-[10px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
              Camera
            </div>
          )}
          {isScreenShareEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/20 text-green-600 dark:text-green-400 text-[10px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Screen
            </div>
          )}
          {isCanvasEnabled && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 text-[10px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Canvas
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaMixerDisplay;

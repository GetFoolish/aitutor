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
  privacyMode?: boolean;
  processedEdgesRef?: RefObject<ImageData | null>;
}

const MediaMixerDisplay: React.FC<MediaMixerDisplayProps> = ({
  canvasRef,
  onStatusChange,
  isCameraEnabled = true,
  isScreenShareEnabled = true,
  isCanvasEnabled = true,
  privacyMode = false,
  processedEdgesRef,
}) => {
  const [isConnected, setIsConnected] = useState(true); // Frontend-based, always "connected"
  const [error, setError] = useState<string | null>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (onStatusChange) {
      onStatusChange({ isConnected, error });
    }
  }, [isConnected, error, onStatusChange]);

  // Mirror the MediaMixer canvas to the display canvas
  useEffect(() => {
    // Function to calculate optimal canvas size maintaining aspect ratio
    // Uses "cover" behavior: fills entire container, maintains aspect ratio, may crop edges
    const calculateCanvasSize = (
      sourceWidth: number,
      sourceHeight: number,
      containerWidth: number,
      containerHeight: number
    ) => {
      if (sourceWidth === 0 || sourceHeight === 0) {
        return { width: containerWidth, height: containerHeight };
      }

      const sourceAspect = sourceWidth / sourceHeight;
      const containerAspect = containerWidth / containerHeight;

      let displayWidth: number;
      let displayHeight: number;

      // Fill entire container while maintaining aspect ratio (cover behavior - fills all space, may crop)
      if (sourceAspect > containerAspect) {
        // Source is wider than container - fit to height (fills height, may crop left/right)
        displayHeight = containerHeight;
        displayWidth = containerHeight * sourceAspect;
      } else {
        // Source is taller than container - fit to width (fills width, may crop top/bottom)
        displayWidth = containerWidth;
        displayHeight = containerWidth / sourceAspect;
      }

      return { width: displayWidth, height: displayHeight };
    };
    const sourceCanvas = canvasRef.current;
    const displayCanvas = displayCanvasRef.current;
    const container = containerRef.current;

    if (!sourceCanvas || !displayCanvas || !container) {
      return;
    }

    const ctx = displayCanvas.getContext('2d', { willReadFrequently: false });
    if (!ctx) {
      setError('Failed to get canvas context');
      return;
    }

    // Set display canvas internal size to match source (for quality)
    displayCanvas.width = sourceCanvas.width;
    displayCanvas.height = sourceCanvas.height;

    // Function to update canvas display size
    const updateDisplaySize = (width: number, height: number) => {
      if (width > 0 && height > 0 && container) {
        const containerRect = container.getBoundingClientRect();
        const { width: displayWidth, height: displayHeight } = calculateCanvasSize(
          width,
          height,
          containerRect.width,
          containerRect.height
        );
        
        // Set CSS size for display (fills container completely, maintains aspect ratio)
        // Position absolutely to fill container with no white space
        displayCanvas.style.width = `${displayWidth}px`;
        displayCanvas.style.height = `${displayHeight}px`;
        displayCanvas.style.position = 'absolute';
        displayCanvas.style.top = '50%';
        displayCanvas.style.left = '50%';
        displayCanvas.style.transform = 'translate(-50%, -50%)';
        displayCanvas.style.display = 'block';
        displayCanvas.style.margin = '0';
        displayCanvas.style.padding = '0';
        displayCanvas.style.objectFit = 'cover';
      }
    };

    let lastDrawTime = 0;
    const targetFPS = 10; // Match MediaMixer FPS
    const frameInterval = 1000 / targetFPS;

    const drawFrame = (timestamp: number) => {
      if (timestamp - lastDrawTime >= frameInterval) {
        // Always use source canvas dimensions (1280x2160) to maintain layout
        if (displayCanvas.width !== sourceCanvas.width || displayCanvas.height !== sourceCanvas.height) {
          displayCanvas.width = sourceCanvas.width;
          displayCanvas.height = sourceCanvas.height;
          updateDisplaySize(sourceCanvas.width, sourceCanvas.height);
        }

        // Clear canvas
        ctx.clearRect(0, 0, displayCanvas.width, displayCanvas.height);

        // If privacy mode is ON and we have processed edges, display edges in camera section only
        if (privacyMode && processedEdgesRef?.current) {
          const edges = processedEdgesRef.current;
          const sectionHeight = sourceCanvas.height / 3;

          // Draw the source canvas normally (all three sections)
          ctx.drawImage(sourceCanvas, 0, 0, displayCanvas.width, displayCanvas.height);

          // Overlay processed edges in the camera section (bottom third) only
          if (edges.width > 0 && edges.height > 0) {
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = edges.width;
            tempCanvas.height = edges.height;
            const tempCtx = tempCanvas.getContext('2d');
            if (tempCtx) {
              tempCtx.putImageData(edges, 0, 0);
              // Draw edges in the camera section (bottom third)
              ctx.drawImage(tempCanvas, 0, 2 * sectionHeight, sourceCanvas.width, sectionHeight);
            }
          }
        } else {
          // Normal mode: display MediaMixer canvas at full resolution (1280x2160)
          ctx.drawImage(sourceCanvas, 0, 0, displayCanvas.width, displayCanvas.height);
        }
        lastDrawTime = timestamp;
      }

      animationFrameRef.current = requestAnimationFrame(drawFrame);
    };

    // Initial size update - always use source canvas (privacy mode doesn't affect display)
    if (sourceCanvas.width > 0 && sourceCanvas.height > 0) {
      displayCanvas.width = sourceCanvas.width;
      displayCanvas.height = sourceCanvas.height;
      updateDisplaySize(sourceCanvas.width, sourceCanvas.height);
    }

    // Resize observer to handle container size changes
    const resizeObserver = new ResizeObserver(() => {
      // Always use source canvas dimensions to maintain layout (1280x2160)
      if (sourceCanvas.width > 0 && sourceCanvas.height > 0) {
        displayCanvas.width = sourceCanvas.width;
        displayCanvas.height = sourceCanvas.height;
        updateDisplaySize(sourceCanvas.width, sourceCanvas.height);
      }
    });
    resizeObserver.observe(container);

    // Start the render loop
    animationFrameRef.current = requestAnimationFrame(drawFrame);
    setIsConnected(true);
    setError(null);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      resizeObserver.disconnect();
    };
  }, [canvasRef, privacyMode, processedEdgesRef]);

  return (
    <div className="flex flex-col w-full h-full bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white overflow-hidden transition-colors duration-300 p-0 m-0">
      <div 
        ref={containerRef}
        className="flex flex-col w-full h-full min-h-[500px] md:min-h-[500px] bg-[#FFFDF5] dark:bg-[#000000] relative overflow-hidden group transition-colors duration-300 p-0 m-0"
      >
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
          <canvas
            ref={displayCanvasRef}
            style={{ 
              display: 'block'
            }}
          />
        )}

        {/* Status indicators - Neo-Brutalist style */}
        <div className="absolute bottom-2 left-2 flex gap-2 z-10">
          {privacyMode && (
            <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#FF6B6B] text-white text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
              <span className="w-1.5 h-1.5 bg-white animate-pulse" />
              Privacy
            </div>
          )}
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

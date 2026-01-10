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
    const updateDisplaySize = () => {
      if (sourceCanvas.width > 0 && sourceCanvas.height > 0 && container) {
        const containerRect = container.getBoundingClientRect();
        const { width, height } = calculateCanvasSize(
          sourceCanvas.width,
          sourceCanvas.height,
          containerRect.width,
          containerRect.height
        );

        // Set CSS size for display (fills container completely, maintains aspect ratio)
        // Position absolutely to fill container with no white space
        displayCanvas.style.width = `${width}px`;
        displayCanvas.style.height = `${height}px`;
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

    // Initial size update
    updateDisplaySize();

    // Resize observer to handle container size changes
    const resizeObserver = new ResizeObserver(() => {
      updateDisplaySize();
    });
    resizeObserver.observe(container);

    let lastDrawTime = 0;
    const targetFPS = 10; // Match MediaMixer FPS
    const frameInterval = 1000 / targetFPS;

    const drawFrame = (timestamp: number) => {
      if (timestamp - lastDrawTime >= frameInterval) {
        // Only draw if source canvas has content
        if (sourceCanvas.width > 0 && sourceCanvas.height > 0) {
          // Update display canvas internal size if source changed
          if (displayCanvas.width !== sourceCanvas.width || displayCanvas.height !== sourceCanvas.height) {
            displayCanvas.width = sourceCanvas.width;
            displayCanvas.height = sourceCanvas.height;
            updateDisplaySize();
          }

          // Clear and draw the source canvas onto the display canvas
          ctx.clearRect(0, 0, displayCanvas.width, displayCanvas.height);
          ctx.drawImage(sourceCanvas, 0, 0, displayCanvas.width, displayCanvas.height);
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
      resizeObserver.disconnect();
    };
  }, [canvasRef]);

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

        {/* Segment Labels - Positioned in each 1/3 section */}
        <div className="absolute inset-0 pointer-events-none z-10">
          {/* Top 1/3: Question Page */}
          <div className="absolute bottom-[69%] left-2 mb-2">
            <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#FF6B6B] text-black dark:text-white text-[8px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
              <span className="w-1.5 h-1.5 bg-black dark:bg-white animate-pulse" />
              Question Page
            </div>
          </div>

          {/* Middle 1/3: Screen Share */}
          <div className="absolute bottom-[32%] left-2 mb-2">
            {isScreenShareEnabled && (
              <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#FFD93D] text-black text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                <span className="w-1.5 h-1.5 bg-black animate-pulse" />
                Screen Share
              </div>
            )}
          </div>

          {/* Bottom 1/3: Camera Feed */}
          <div className="absolute bottom-2 left-2">
            {isCameraEnabled && (
              <div className="flex items-center gap-1 px-2 py-1 border-[2px] border-black dark:border-white bg-[#C4B5FD] text-black dark:text-white text-[10px] font-black uppercase shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                <span className="w-1.5 h-1.5 bg-black dark:bg-white animate-pulse" />
                Camera Feed
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MediaMixerDisplay;

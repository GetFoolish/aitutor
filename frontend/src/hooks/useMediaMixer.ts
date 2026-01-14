import { useRef, useCallback, useState, useEffect, RefObject } from 'react';
import { CannyEdgeFilter } from '../utils/CannyEdgeFilter';

interface MediaMixerConfig {
  width: number;      // 1280
  height: number;     // 2160
  fps: number;        // 10
  quality: number;    // 0.85 (not used in canvas mixing)
  cameraEnabled?: boolean;
  screenEnabled?: boolean;
  privacyEnabled?: boolean;
  cameraVideoRef?: RefObject<HTMLVideoElement>;
  screenVideoRef?: RefObject<HTMLVideoElement>;
}

export const useMediaMixer = (config: MediaMixerConfig) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scratchpadCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const filterRef = useRef<CannyEdgeFilter | null>(null);

  // Initialize filter
  useEffect(() => {
    filterRef.current = new CannyEdgeFilter();
  }, []);

  // State for UI control - controlled by props
  const showCamera = config.cameraEnabled || false;
  const showScreen = config.screenEnabled || false;
  const [isRunning, setIsRunning] = useState(false);

  // Mix frames using Canvas 2D API
  const mixFrames = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false }); // Optimize for no alpha
    if (!ctx) return;

    const sectionHeight = config.height / 3;

    // Clear canvas with appropriate backgrounds
    // We can skip clearing if we are going to overwrite everything, but let's keep it for safety
    // or just fill the whole thing once if we want to be super optimized, but sections have different colors.

    // Scratchpad Section
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, config.width, sectionHeight);

    if (scratchpadCanvasRef.current) {
      try {
        ctx.drawImage(scratchpadCanvasRef.current, 0, 0, config.width, sectionHeight);
      } catch (error) {
        // console.error('Error drawing scratchpad frame:', error);
      }
    }

    // Screen Section
    ctx.fillStyle = 'black';
    ctx.fillRect(0, sectionHeight, config.width, sectionHeight);

    if (showScreen && config.screenVideoRef?.current) {
      try {
        const video = config.screenVideoRef.current;
        if (video.readyState >= 2) { // HAVE_CURRENT_DATA
          // Draw directly from video element
          // Maintain aspect ratio or fill? The original code did a resize via temp canvas.
          // We'll draw to fill the section (1280x720)
          ctx.drawImage(video, 0, sectionHeight, config.width, sectionHeight);
        }
      } catch (error) {
        // console.error('Error drawing screen frame:', error);
      }
    }

    // Camera Section
    ctx.fillStyle = '#404040';
    ctx.fillRect(0, 2 * sectionHeight, config.width, sectionHeight);

    if (showCamera && config.cameraVideoRef?.current) {
      try {
        const video = config.cameraVideoRef.current;
        if (video.readyState >= 2) {
          if (config.privacyEnabled && filterRef.current) {
            // Apply Canny Edge Filter
            const filteredCanvas = filterRef.current.process(video);
            ctx.drawImage(filteredCanvas, 0, 2 * sectionHeight, config.width, sectionHeight);
          } else {
            // Normal Camera Feed
            ctx.drawImage(video, 0, 2 * sectionHeight, config.width, sectionHeight);
          }
        }
      } catch (error) {
        // console.error('Error drawing camera frame:', error);
      }
    }
  }, [config.width, config.height, showCamera, showScreen, config.cameraVideoRef, config.screenVideoRef, config.privacyEnabled]);

  // Update frame buffers
  const updateScratchpadFrame = useCallback((canvas: HTMLCanvasElement) => {
    // Instead of copying ImageData, we just store the reference to the latest canvas
    // Or we could draw it to an offscreen canvas if the source canvas is reused/cleared.
    // Assuming ScratchpadCapture creates a new canvas or we can just draw from it.
    // If ScratchpadCapture reuses the same canvas, we might get tearing if we draw while it's updating.
    // But for now, let's just store the ref.
    scratchpadCanvasRef.current = canvas;
  }, []);

  // Mixing loop using requestAnimationFrame
  useEffect(() => {
    if (!isRunning) {
      return;
    }

    let animationId: number;
    const targetInterval = 1000 / config.fps; // Target frame interval
    let lastFrameTime = 0;

    const mixLoop = (currentTime: number) => {
      if (currentTime - lastFrameTime >= targetInterval) {
        mixFrames();
        lastFrameTime = currentTime;
      }

      if (isRunning) {
        animationId = requestAnimationFrame(mixLoop);
      }
    };

    animationId = requestAnimationFrame(mixLoop);

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [isRunning, mixFrames, config.fps]);

  return {
    canvasRef,
    updateScratchpadFrame,
    setIsRunning,
    mixFrames: () => mixFrames() // Manual trigger
  };
};


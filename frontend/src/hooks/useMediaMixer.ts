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

    // 1. Draw Section Backgrounds and Media

    // Scratchpad Section
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, config.width, sectionHeight);
    if (scratchpadCanvasRef.current) {
      try {
        ctx.drawImage(scratchpadCanvasRef.current, 0, 0, config.width, sectionHeight);
      } catch (error) { }
    }

    // Screen Section
    ctx.fillStyle = 'black';
    ctx.fillRect(0, sectionHeight, config.width, sectionHeight);
    if (showScreen && config.screenVideoRef?.current) {
      try {
        const video = config.screenVideoRef.current;
        if (video.readyState >= 2) {
          ctx.drawImage(video, 0, sectionHeight, config.width, sectionHeight);
        }
      } catch (error) { }
    }

    // Camera Section
    ctx.fillStyle = '#404040';
    ctx.fillRect(0, 2 * sectionHeight, config.width, sectionHeight);
    if (showCamera && config.cameraVideoRef?.current) {
      try {
        const video = config.cameraVideoRef.current;
        if (video.readyState >= 2) {
          if (config.privacyEnabled && filterRef.current) {
            const filteredCanvas = filterRef.current.process(video);
            ctx.drawImage(filteredCanvas, 0, 2 * sectionHeight, config.width, sectionHeight);
          } else {
            ctx.drawImage(video, 0, 2 * sectionHeight, config.width, sectionHeight);
          }
        }
      } catch (error) { }
    }

    // 2. Draw Overlays (Borders and Labels) - Draw LAST

    // Draw Separator Borders (Red)
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 14;

    ctx.beginPath();
    ctx.moveTo(0, sectionHeight);
    ctx.lineTo(config.width, sectionHeight);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, 2 * sectionHeight);
    ctx.lineTo(config.width, 2 * sectionHeight);
    ctx.stroke();

    // Draw Stickers (Bottom-Left of each section) removed per user request to avoid double labeling.
    // The red separator lines remain for LLM to identify segments.
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


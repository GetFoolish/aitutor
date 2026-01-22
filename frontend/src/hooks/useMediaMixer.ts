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

    // ============================================================================
    // DRAW LABELS AND BOUNDARIES ON TOP (AFTER all content is drawn)
    // This ensures stickers and boundaries are visible and not covered by content
    // ============================================================================

    // Save canvas state to avoid interference
    ctx.save();

    // Draw colored bounding boxes around each section (so LLM can see clear boundaries)
    // Draw complete rectangles for each section including all 4 borders
    ctx.lineWidth = 8; // Thick lines for visibility
    ctx.setLineDash([]); // Solid line (no dashes)

    // Box around QuestionPane section (RED border) - complete rectangle
    ctx.strokeStyle = '#FF0000';
    ctx.strokeRect(4, 4, config.width - 8, sectionHeight - 8);

    // Box around Screenshare section (YELLOW border) - complete rectangle
    ctx.strokeStyle = '#FFD700';
    ctx.strokeRect(4, sectionHeight + 4, config.width - 8, sectionHeight - 8);

    // Box around Camera Feed section (PURPLE border) - complete rectangle
    ctx.strokeStyle = '#9F7AEA';
    ctx.strokeRect(4, 2 * sectionHeight + 4, config.width - 8, sectionHeight - 8);

    // Draw neo-brutalist stickers for each section (so LLM can identify them)
    // Position stickers at BOTTOM of each section to avoid content overlap
    const drawSectionSticker = (label: string, yOffset: number, bgColor: string, textColor: string = '#000000') => {
      const paddingX = 15; // Horizontal padding from left edge
      const paddingY = 15; // Vertical padding from bottom edge
      const stickerX = paddingX;

      // Moderate font size for visibility
      const fontSize = 40;
      ctx.font = `bold ${fontSize}px Arial`;
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const stickerWidth = textWidth + 40; // Padding inside sticker
      const stickerHeight = 60; // Sticker height

      // Position at BOTTOM of section (yOffset + sectionHeight - stickerHeight - paddingY)
      const stickerY = yOffset + sectionHeight - stickerHeight - paddingY;

      // Draw shadow first (neo-brutalist shadow effect)
      ctx.fillStyle = '#000000';
      ctx.fillRect(stickerX + 4, stickerY + 4, stickerWidth, stickerHeight);

      // Draw sticker background on top of shadow
      ctx.fillStyle = bgColor;
      ctx.fillRect(stickerX, stickerY, stickerWidth, stickerHeight);

      // Draw sticker border (neo-brutalist thick black border)
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 3;
      ctx.setLineDash([]);
      ctx.strokeRect(stickerX, stickerY, stickerWidth, stickerHeight);

      // Draw sticker text
      ctx.fillStyle = textColor;
      ctx.font = `bold ${fontSize}px Arial`;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'left';
      ctx.fillText(label, stickerX + 20, stickerY + stickerHeight / 2);
    };

    // Add stickers for each section (matching MediaMixerDisplay style)
    // Position at BOTTOM of each section for better visibility
    // QUESTIONPANE gets red background with white text (same as Canvas/Privacy stickers)
    drawSectionSticker('QUESTIONPANE', 0, '#FF6B6B', '#FFFFFF');

    // SCREENSHARE gets yellow background with black text
    drawSectionSticker('SCREENSHARE', sectionHeight, '#FFD93D', '#000000');

    // CAMERA FEED gets purple background with black text
    drawSectionSticker('CAMERA FEED', 2 * sectionHeight, '#C4B5FD', '#000000');

    // Restore canvas state
    ctx.restore();
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


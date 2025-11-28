import { useRef, useCallback, useState, useEffect } from 'react';

interface MediaMixerConfig {
  width: number;      // 1280
  height: number;     // 2160
  fps: number;        // 10
  quality: number;    // 0.85 (not used in canvas mixing)
  cameraEnabled?: boolean;
  screenEnabled?: boolean;
}

export const useMediaMixer = (config: MediaMixerConfig) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scratchpadFrameRef = useRef<ImageData | null>(null);
  const cameraFrameRef = useRef<ImageData | null>(null);
  const screenFrameRef = useRef<ImageData | null>(null);

  // State for UI control - controlled by props
  const showCamera = config.cameraEnabled || false;
  const showScreen = config.screenEnabled || false;
  const [isRunning, setIsRunning] = useState(false);

  // Mix frames using Canvas 2D API
  const mixFrames = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;


    const sectionHeight = config.height / 3;

    // Clear canvas with appropriate backgrounds
    ctx.fillStyle = 'white';  // Scratchpad background
    ctx.fillRect(0, 0, config.width, sectionHeight);

    ctx.fillStyle = 'black';  // Screen background
    ctx.fillRect(0, sectionHeight, config.width, sectionHeight);

    ctx.fillStyle = '#404040'; // Camera background
    ctx.fillRect(0, 2 * sectionHeight, config.width, sectionHeight);


    // Draw scratchpad frame if available
    if (scratchpadFrameRef.current) {
      try {
        // Create a temporary canvas to convert ImageData to drawable format
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = config.width;
        tempCanvas.height = sectionHeight;
        const tempCtx = tempCanvas.getContext('2d');

        if (tempCtx) {
          tempCtx.putImageData(scratchpadFrameRef.current, 0, 0);
          ctx.drawImage(tempCanvas, 0, 0);
        }
      } catch (error) {
        console.error('Error drawing scratchpad frame:', error);
      }
    }

    // Draw screen frame if available and enabled
    if (showScreen && screenFrameRef.current) {
      try {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = config.width;
        tempCanvas.height = sectionHeight;
        const tempCtx = tempCanvas.getContext('2d');

        if (tempCtx) {
          tempCtx.putImageData(screenFrameRef.current, 0, 0);
          ctx.drawImage(tempCanvas, 0, sectionHeight);
        }
      } catch (error) {
        console.error('Error drawing screen frame:', error);
      }
    }

    // Draw camera frame if available and enabled
    if (showCamera && cameraFrameRef.current) {
      try {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = config.width;
        tempCanvas.height = sectionHeight;
        const tempCtx = tempCanvas.getContext('2d');

        if (tempCtx) {
          tempCtx.putImageData(cameraFrameRef.current, 0, 0);
          ctx.drawImage(tempCanvas, 0, 2 * sectionHeight);
        }
      } catch (error) {
        console.error('Error drawing camera frame:', error);
      }
    }
  }, [config.width, config.height, showCamera, showScreen]);

  // Update frame buffers
  const updateScratchpadFrame = useCallback((imageData: ImageData) => {
    scratchpadFrameRef.current = imageData;
  }, []);

  const updateCameraFrame = useCallback((imageData: ImageData) => {
    cameraFrameRef.current = imageData;
  }, []);

  const updateScreenFrame = useCallback((imageData: ImageData) => {
    screenFrameRef.current = imageData;
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
    updateCameraFrame,
    updateScreenFrame,
    setIsRunning,
    mixFrames: () => mixFrames() // Manual trigger
  };
};

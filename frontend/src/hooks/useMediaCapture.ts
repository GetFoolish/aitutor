import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

interface UseMediaCaptureProps {
  onCameraFrame?: (imageData: ImageData) => void;
  onScreenFrame?: (imageData: ImageData) => void;
}

export const useMediaCapture = ({ onCameraFrame, onScreenFrame }: UseMediaCaptureProps) => {
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [screenEnabled, setScreenEnabled] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(false);

  const cameraStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const cameraCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const screenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const screenVideoRef = useRef<HTMLVideoElement | null>(null);
  const processedEdgesRef = useRef<ImageData | null>(null);
  const privacyCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Initialize canvases
  useEffect(() => {
    cameraCanvasRef.current = document.createElement('canvas');
    screenCanvasRef.current = document.createElement('canvas');
    privacyCanvasRef.current = document.createElement('canvas');
    cameraVideoRef.current = document.createElement('video');
    cameraVideoRef.current.autoplay = true;
    cameraVideoRef.current.playsInline = true;
    screenVideoRef.current = document.createElement('video');
    screenVideoRef.current.autoplay = true;
    screenVideoRef.current.playsInline = true;

    return () => {
      stopCamera();
      stopScreen();
    };
  }, []);

  // Create Web Worker for Canny edge detection (lazy initialization)
  const cannyWorker = useMemo(() => {
    if (typeof Worker === 'undefined') {
      console.warn('Web Workers not supported');
      return null;
    }
    try {
      const worker = new Worker(new URL('../workers/canny-filter.worker.ts', import.meta.url), { type: 'module' });
      return worker;
    } catch (error) {
      console.error('Failed to create Canny filter worker:', error);
      return null;
    }
  }, []);

  // Cleanup worker on unmount
  useEffect(() => {
    return () => {
      if (cannyWorker) {
        cannyWorker.terminate();
      }
    };
  }, [cannyWorker]);

  // Process video frames with Canny edge detection when privacy mode is ON
  useEffect(() => {
    if (!privacyMode || !cannyWorker || !cameraEnabled || !cameraVideoRef.current) {
      processedEdgesRef.current = null;
      return;
    }

    let isProcessing = false;
    let frameInterval: number | null = null;

    const processFrame = () => {
      if (isProcessing || !cameraVideoRef.current || !privacyMode) {
        return;
      }

      const video = cameraVideoRef.current;
      if (video.readyState !== video.HAVE_ENOUGH_DATA) {
        return;
      }

      isProcessing = true;

      try {
        // Create temporary canvas to capture frame
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = video.videoWidth || 1280;
        tempCanvas.height = video.videoHeight || 720;
        const tempCtx = tempCanvas.getContext('2d');

        if (!tempCtx) {
          isProcessing = false;
          return;
        }

        tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
        const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);

        // Send width, height, and data using ArrayBuffer for efficient zero-copy transfer
        // Create a copy of the buffer to transfer (original buffer remains in main thread)
        const dataBuffer = imageData.data.buffer.slice(0);
        cannyWorker.postMessage({
          width: imageData.width,
          height: imageData.height,
          data: dataBuffer,
          lowThreshold: 50,
          highThreshold: 100
        }, [dataBuffer]); // Transfer ownership for zero-copy performance
      } catch (error) {
        console.error('Error processing frame for privacy mode:', error);
        isProcessing = false;
      }
    };

    // Handle worker response
    const handleWorkerMessage = (e: MessageEvent) => {
      isProcessing = false;

      if (e.data.success && e.data.width && e.data.height && e.data.data) {
        // Reconstruct ImageData from width, height, and ArrayBuffer
        try {
          const dataArray = e.data.data instanceof ArrayBuffer
            ? new Uint8ClampedArray(e.data.data)
            : Array.isArray(e.data.data)
            ? new Uint8ClampedArray(e.data.data)
            : new Uint8ClampedArray(e.data.data);

          const reconstructedEdges = new ImageData(
            dataArray,
            e.data.width,
            e.data.height
          );
          processedEdgesRef.current = reconstructedEdges;
        } catch (error) {
          console.error('Error reconstructing ImageData from worker:', error);
        }
      } else if (e.data.error) {
        console.error('Canny edge detection error:', e.data.error);
      }
    };

    cannyWorker.addEventListener('message', handleWorkerMessage);

    // Process frames at 2 FPS (500ms interval) when privacy mode is ON
    frameInterval = window.setInterval(processFrame, 500);

    return () => {
      if (frameInterval !== null) {
        clearInterval(frameInterval);
      }
      cannyWorker.removeEventListener('message', handleWorkerMessage);
      processedEdgesRef.current = null;
    };
  }, [privacyMode, cannyWorker, cameraEnabled, cameraVideoRef]);

  const stopCamera = useCallback(() => {
    console.log('Stopping camera...');
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach(track => track.stop());
      cameraStreamRef.current = null;
    }
    console.log('Camera stopped');
  }, []);

  const stopScreen = useCallback(() => {
    console.log('Stopping screen...');
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
      screenStreamRef.current = null;
    }
    console.log('Screen share stopped');
  }, []);

  const startCamera = useCallback(async () => {
    try {
      console.log('Starting camera capture...');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 }
      });

      cameraStreamRef.current = stream;
      const video = cameraVideoRef.current!;
      video.srcObject = stream;

      // Wait for video to be ready
      await new Promise<void>((resolve) => {
        video.onloadedmetadata = () => {
          const canvas = cameraCanvasRef.current!;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          console.log(`Camera video ready: ${canvas.width}x${canvas.height}`);
          resolve();
        };
      });

      // Start the capture loop
      const captureLoop = () => {
        if (!cameraStreamRef.current) return;

        const canvas = cameraCanvasRef.current!;
        const ctx = canvas.getContext('2d')!;

        ctx.drawImage(video, 0, 0);

        // Resize to section dimensions and get ImageData
        const sectionCanvas = document.createElement('canvas');
        sectionCanvas.width = 1280;
        sectionCanvas.height = 720;
        const sectionCtx = sectionCanvas.getContext('2d');

        if (sectionCtx) {
          sectionCtx.drawImage(canvas, 0, 0, 1280, 720);
          const imageData = sectionCtx.getImageData(0, 0, 1280, 720);
          onCameraFrame?.(imageData);
        }

        // Continue loop - reduced to ~2 FPS for better performance (500ms)
        setTimeout(() => requestAnimationFrame(captureLoop), 500);
      };

      captureLoop();
      console.log('Camera started');

    } catch (error) {
      console.error('Error starting camera:', error);
      setCameraEnabled(false);
    }
  }, [onCameraFrame]);

  const startScreen = useCallback(async () => {
    try {
      console.log('Starting screen capture...');
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { width: 1280, height: 720 }
      });

      screenStreamRef.current = stream;
      const video = screenVideoRef.current!;
      video.srcObject = stream;

      // Handle when user stops sharing via browser UI
      stream.getVideoTracks()[0].onended = () => {
        console.log('User stopped screen sharing via browser');
        setScreenEnabled(false);
        stopScreen();
      };

      // Wait for video to be ready
      await new Promise<void>((resolve) => {
        video.onloadedmetadata = () => {
          const canvas = screenCanvasRef.current!;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          console.log(`Screen video ready: ${canvas.width}x${canvas.height}`);
          resolve();
        };
      });

      // Start the capture loop
      const captureLoop = () => {
        if (!screenStreamRef.current) return;

        const canvas = screenCanvasRef.current!;
        const ctx = canvas.getContext('2d')!;

        ctx.drawImage(video, 0, 0);

        // Resize to section dimensions and get ImageData
        const sectionCanvas = document.createElement('canvas');
        sectionCanvas.width = 1280;
        sectionCanvas.height = 720;
        const sectionCtx = sectionCanvas.getContext('2d');

        if (sectionCtx) {
          sectionCtx.drawImage(canvas, 0, 0, 1280, 720);
          const imageData = sectionCtx.getImageData(0, 0, 1280, 720);
          onScreenFrame?.(imageData);
        }

        // Continue loop - reduced to ~2 FPS for better performance (500ms)
        setTimeout(() => requestAnimationFrame(captureLoop), 500);
      };

      captureLoop();
      console.log('Screen share started');

    } catch (error) {
      console.error('Error starting screen share:', error);
      setScreenEnabled(false);
    }
  }, [onScreenFrame, stopScreen]);

  const toggleCamera = useCallback(async (enabled: boolean) => {
    console.log(`toggleCamera called with enabled=${enabled}`);

    setCameraEnabled(enabled);

    if (enabled) {
      await startCamera();
    } else {
      stopCamera();
    }
  }, [startCamera, stopCamera]);

  const toggleScreen = useCallback(async (enabled: boolean) => {
    console.log(`toggleScreen called with enabled=${enabled}`);

    setScreenEnabled(enabled);

    if (enabled) {
      await startScreen();
    } else {
      stopScreen();
    }
  }, [startScreen, stopScreen]);

  // Expose video refs for direct consumption by MediaMixer
  return {
    cameraEnabled,
    screenEnabled,
    toggleCamera,
    toggleScreen,
    cameraVideoRef,
    screenVideoRef,
    privacyMode,
    setPrivacyMode,
    processedEdgesRef
  };
};

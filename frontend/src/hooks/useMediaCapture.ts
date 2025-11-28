import { useEffect, useRef, useState, useCallback } from 'react';

interface UseMediaCaptureProps {
  onCameraFrame?: (imageData: ImageData) => void;
  onScreenFrame?: (imageData: ImageData) => void;
}

export const useMediaCapture = ({ onCameraFrame, onScreenFrame }: UseMediaCaptureProps) => {
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [screenEnabled, setScreenEnabled] = useState(false);

  const cameraStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const cameraCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const screenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const screenVideoRef = useRef<HTMLVideoElement | null>(null);

  // Initialize canvases
  useEffect(() => {
    cameraCanvasRef.current = document.createElement('canvas');
    screenCanvasRef.current = document.createElement('canvas');
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

        // Continue loop - reduced to ~5 FPS for better performance
        setTimeout(() => requestAnimationFrame(captureLoop), 200);
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

        // Continue loop - reduced to ~5 FPS for better performance
        setTimeout(() => requestAnimationFrame(captureLoop), 200);
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

  return {
    cameraEnabled,
    screenEnabled,
    toggleCamera,
    toggleScreen
  };
};


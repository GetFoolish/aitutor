import React, { useRef, useEffect, ReactNode } from 'react';
import * as htmlToImage from 'html-to-image';

interface ScratchpadCaptureProps {
  children: ReactNode;
  onFrameCaptured: (canvas: HTMLCanvasElement) => void;
  scratchpadRef?: React.RefObject<{ 
    getCanvas: () => HTMLCanvasElement | null;
    exportCanvas?: () => Promise<HTMLCanvasElement | null>;  // Support for tldraw/Excalidraw
  }>;
}

const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({ children, onFrameCaptured, scratchpadRef }) => {
  const captureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let intervalId: number;
    let isCapturing = false;
    let lastCaptureTime = 0;

    const captureFrame = async () => {  // Make async for tldraw exportCanvas
      // Skip if already capturing or too soon since last capture
      const now = Date.now();
      if (isCapturing || (now - lastCaptureTime < 4500)) {
        return;
      }

      isCapturing = true;
      lastCaptureTime = now;

      try {
        // Priority 1: Check if scratchpad has exportCanvas method (tldraw/Excalidraw)
        if (scratchpadRef?.current?.exportCanvas) {
          const canvas = await scratchpadRef.current.exportCanvas();
          if (canvas) {
            // Canvas is already 1280x720 from exportCanvas
            onFrameCaptured(canvas);
            return;
          }
        }

        // Priority 2: Check if scratchpad canvas is available (old react-canvas-draw)
        const scratchpadCanvas = scratchpadRef?.current?.getCanvas();
        if (scratchpadCanvas) {
          // Resize scratchpad canvas to 1280×720 section size
          const resizedCanvas = document.createElement('canvas');
          resizedCanvas.width = 1280;
          resizedCanvas.height = 720;
          const resizedCtx = resizedCanvas.getContext('2d');

          if (resizedCtx) {
            // Fill with white background
            resizedCtx.fillStyle = 'white';
            resizedCtx.fillRect(0, 0, 1280, 720);
            // Draw scratchpad canvas, maintaining aspect ratio or filling
            resizedCtx.drawImage(scratchpadCanvas, 0, 0, 1280, 720);
            onFrameCaptured(resizedCanvas);
          }
          return;
        }

        // Priority 3: Fallback to question content (original behavior)
        const questionContent = document.querySelector('#question-content-container') as HTMLElement;

        if (questionContent) {
          const canvas = await htmlToImage.toCanvas(questionContent, {
            quality: 0.7,  // Reduced quality for better performance
            skipFonts: true,
            pixelRatio: 1.0,  // Reduced to 1x for much better performance
            cacheBust: false,  // Don't bust cache for better performance
          });

          // Resize canvas to 1280×720 section size
          const resizedCanvas = document.createElement('canvas');
          resizedCanvas.width = 1280;
          resizedCanvas.height = 720;
          const resizedCtx = resizedCanvas.getContext('2d');

          if (resizedCtx) {
            resizedCtx.drawImage(canvas, 0, 0, 1280, 720);
            onFrameCaptured(resizedCanvas);
          }
        } else {
          // Create error message on a canvas
          const canvas = document.createElement('canvas');
          canvas.width = 1280;
          canvas.height = 720;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, 1280, 720);
            ctx.fillStyle = 'red';
            ctx.font = '24px Arial';
            ctx.fillText('ERROR: #question-content-container not found!', 50, 100);
            onFrameCaptured(canvas);
          }
        }
      } catch (error) {
        console.error('Error capturing frame:', error);
      } finally {
        isCapturing = false;
      }
    };

    // Wait for question-content-container to load before starting capture
    const waitForQuestionContent = () => {
      const questionContent = document.querySelector('#question-content-container');
      if (questionContent) {
        console.log('✅ Question content found, starting capture at reduced rate');
        // Much more conservative: 5 seconds between captures (0.2 FPS)
        intervalId = window.setInterval(captureFrame, 5000);
      } else {
        // Check again in 100ms
        setTimeout(waitForQuestionContent, 100);
      }
    };

    waitForQuestionContent();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [onFrameCaptured, scratchpadRef]);

  useEffect(() => {
    if (captureRef.current) {
      const rect = captureRef.current.getBoundingClientRect();
      const style = window.getComputedStyle(captureRef.current);
      console.log('📸 ScratchpadCapture Wrapper:', {
        dimensions: { width: rect.width, height: rect.height },
        pointerEvents: style.pointerEvents,
        display: style.display,
        position: style.position,
        zIndex: style.zIndex
      });
    }
  }, []);

  return (
    <div
      ref={captureRef}
      className="scratchpad-capture-wrapper"
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        pointerEvents: 'auto'
      }}
    >
      {children}
    </div>
  );
};

export default ScratchpadCapture;

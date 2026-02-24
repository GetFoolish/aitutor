import React, { useRef, useEffect, ReactNode } from 'react';
import * as htmlToImage from 'html-to-image';

interface ScratchpadCaptureProps {
  children: ReactNode;
  onFrameCaptured: (canvas: HTMLCanvasElement) => void;
}

const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({ children, onFrameCaptured }) => {
  const captureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let intervalId: number;
    let isCapturing = false;
    let lastCaptureTime = 0;

    const captureFrame = () => {
      // Skip if already capturing or too soon since last capture
      const now = Date.now();
      if (isCapturing || (now - lastCaptureTime < 4500)) {
        return;
      }

      isCapturing = true;
      lastCaptureTime = now;

      const questionContent = document.querySelector('#question-content-container') as HTMLElement;

      if (questionContent) {
        htmlToImage.toCanvas(questionContent, {
          quality: 0.7,  // Reduced quality for better performance
          skipFonts: true,
          pixelRatio: 1.0,  // Reduced to 1x for much better performance
          cacheBust: false,  // Don't bust cache for better performance
        })
          .then((canvas) => {
            // Resize canvas to 1280×720 section size
            // We create a new canvas here because html-to-image gives us a new one anyway.
            // Ideally we'd reuse a canvas for resizing to avoid GC, but let's keep it simple for now as it's 1 FPS.
            // Optimization: Reuse a single canvas for resizing if this becomes a bottleneck.
            const resizedCanvas = document.createElement('canvas');
            resizedCanvas.width = 1280;
            resizedCanvas.height = 720;
            const resizedCtx = resizedCanvas.getContext('2d');

            if (resizedCtx) {
              resizedCtx.drawImage(canvas, 0, 0, 1280, 720);
              // Pass the canvas directly instead of ImageData
              onFrameCaptured(resizedCanvas);
            }
          })
          .catch(error => {
            console.error('html-to-image failed:', error);
          })
          .finally(() => {
            isCapturing = false;
          });
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
        isCapturing = false;
      }
    };

    // Wait for question-content-container to load before starting capture
    let waitTimerId: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;
    const waitForQuestionContent = () => {
      if (stopped) return;
      const questionContent = document.querySelector('#question-content-container');
      if (questionContent) {
        console.log('✅ Question content found, starting capture at reduced rate');
        // Much more conservative: 5 seconds between captures (0.2 FPS)
        intervalId = window.setInterval(captureFrame, 5000);
      } else {
        // Check again in 100ms
        waitTimerId = setTimeout(waitForQuestionContent, 100);
      }
    };

    waitForQuestionContent();

    return () => {
      stopped = true;
      if (waitTimerId) clearTimeout(waitTimerId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [onFrameCaptured]);

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

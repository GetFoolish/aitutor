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

      // Try to capture the scratchpad first (tldraw canvas), then fall back to question content
      const scratchpadContainer = document.querySelector('.scratchpad-container') as HTMLElement;
      const questionContent = document.querySelector('#question-content-container') as HTMLElement;

      // Determine what to capture - prefer scratchpad if visible, otherwise question
      const targetElement = scratchpadContainer || questionContent;

      if (targetElement) {
        htmlToImage.toCanvas(targetElement, {
          quality: 0.7,  // Reduced quality for better performance
          skipFonts: true,
          pixelRatio: 1.0,  // Reduced to 1x for much better performance
          cacheBust: false,  // Don't bust cache for better performance
          filter: (node) => {
            // Skip hidden elements and certain UI elements that shouldn't be captured
            if (node instanceof Element) {
              const tagName = node.tagName?.toLowerCase();
              // Skip script, style, and some tldraw UI elements we don't need
              if (tagName === 'script' || tagName === 'style') return false;
            }
            return true;
          }
        })
          .then((canvas) => {
            // Resize canvas to 1280×720 section size
            const resizedCanvas = document.createElement('canvas');
            resizedCanvas.width = 1280;
            resizedCanvas.height = 720;
            const resizedCtx = resizedCanvas.getContext('2d');

            if (resizedCtx) {
              // Fill white background first
              resizedCtx.fillStyle = 'white';
              resizedCtx.fillRect(0, 0, 1280, 720);
              // Draw captured content maintaining aspect ratio
              const scale = Math.min(1280 / canvas.width, 720 / canvas.height);
              const x = (1280 - canvas.width * scale) / 2;
              const y = (720 - canvas.height * scale) / 2;
              resizedCtx.drawImage(canvas, x, y, canvas.width * scale, canvas.height * scale);
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
          ctx.fillStyle = 'gray';
          ctx.font = '24px Arial';
          ctx.fillText('Waiting for content...', 50, 100);

          onFrameCaptured(canvas);
        }
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

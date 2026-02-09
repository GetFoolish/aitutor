import React, { useRef, useEffect, ReactNode, useCallback } from 'react';
import * as htmlToImage from 'html-to-image';
import type { TeachingCanvasHandle } from '../teaching-canvas';

interface ScratchpadCaptureProps {
  children: ReactNode;
  onFrameCaptured: (canvas: HTMLCanvasElement) => void;
  /** Teaching canvas ref for capturing drawings */
  teachingCanvasRef?: TeachingCanvasHandle | null;
  /** Whether the scratchpad/canvas is currently visible */
  isScratchpadOpen?: boolean;
}

/**
 * ScratchpadCapture — captures question content + teaching canvas drawings
 * and composites them into a single canvas that gets sent to the media mixer
 * (and ultimately to Gemini for visual understanding).
 *
 * Updated for native HTML5 Canvas: uses canvas.toDataURL() directly
 * instead of react-sketch-canvas exportImage / exportPaths.
 */
const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({
  children,
  onFrameCaptured,
  teachingCanvasRef,
  isScratchpadOpen = false,
}) => {
  const captureRef = useRef<HTMLDivElement>(null);
  const isCapturingRef = useRef(false);
  const lastCaptureTimeRef = useRef(0);

  // Store mutable refs so the capture interval never needs to restart
  const onFrameCapturedRef = useRef(onFrameCaptured);
  const teachingCanvasRefRef = useRef(teachingCanvasRef);
  const isScratchpadOpenRef = useRef(isScratchpadOpen);

  // Keep refs in sync with props (no interval restart needed)
  useEffect(() => { onFrameCapturedRef.current = onFrameCaptured; }, [onFrameCaptured]);
  useEffect(() => { teachingCanvasRefRef.current = teachingCanvasRef; }, [teachingCanvasRef]);
  useEffect(() => { isScratchpadOpenRef.current = isScratchpadOpen; }, [isScratchpadOpen]);

  const captureFrame = useCallback(async () => {
    // Skip if already capturing
    if (isCapturingRef.current) return;

    // Throttle: minimum 5 seconds between captures
    const minInterval = 5000;
    const now = Date.now();
    if (now - lastCaptureTimeRef.current < minInterval) return;

    isCapturingRef.current = true;
    lastCaptureTimeRef.current = now;

    try {
      const questionContent = document.querySelector('#question-content-container') as HTMLElement;

      // Create the final composite canvas
      const compositeCanvas = document.createElement('canvas');
      compositeCanvas.width = 1280;
      compositeCanvas.height = 720;
      const ctx = compositeCanvas.getContext('2d');

      if (!ctx) {
        isCapturingRef.current = false;
        return;
      }

      // Fill with white background
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, 1280, 720);

      // Capture question content
      if (questionContent) {
        try {
          const questionCanvas = await htmlToImage.toCanvas(questionContent, {
            quality: 0.7,
            skipFonts: true,
            pixelRatio: 1.0,
            cacheBust: false,
          });
          ctx.drawImage(questionCanvas, 0, 0, 1280, 720);
        } catch (error) {
          // html-to-image can fail intermittently; just log and continue
          console.warn('ScratchpadCapture: html-to-image failed:', error);
        }
      } else {
        ctx.fillStyle = '#888';
        ctx.font = '20px Arial';
        ctx.fillText('Waiting for question content...', 50, 100);
      }

      // Capture teaching canvas if it has content
      const canvasHandle = teachingCanvasRefRef.current;
      if (isScratchpadOpenRef.current && canvasHandle) {
        try {
          // Get the raw canvas element directly — no async export needed
          const rawCanvas = canvasHandle.getCanvas();
          if (rawCanvas && rawCanvas.width > 0 && rawCanvas.height > 0) {
            // Draw teaching canvas in the bottom-right corner with a border
            const drawingX = 1280 - 640 - 20;
            const drawingY = 720 - 360 - 20;

            // Semi-transparent white background
            ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
            ctx.fillRect(drawingX - 4, drawingY - 4, 648, 368);
            ctx.strokeStyle = '#4ADE80';
            ctx.lineWidth = 3;
            ctx.strokeRect(drawingX - 4, drawingY - 4, 648, 368);

            // Draw the canvas content directly (synchronous, fast)
            ctx.drawImage(rawCanvas, drawingX, drawingY, 640, 360);

            ctx.fillStyle = '#4ADE80';
            ctx.font = 'bold 12px Arial';
            ctx.fillText('Whiteboard', drawingX, drawingY - 8);
          }
        } catch (error) {
          console.warn('ScratchpadCapture: canvas capture error:', error);
        }
      }

      // Send composite to media mixer
      onFrameCapturedRef.current(compositeCanvas);
    } catch (error) {
      console.error('ScratchpadCapture: Frame capture failed:', error);
    } finally {
      isCapturingRef.current = false;
    }
  }, []); // No dependencies — reads from refs

  // Single stable interval that never restarts
  useEffect(() => {
    let intervalId: number | undefined;
    let isMounted = true;

    const waitForQuestionContent = () => {
      if (!isMounted) return;
      const questionContent = document.querySelector('#question-content-container');
      if (questionContent) {
        console.log('✅ ScratchpadCapture: Question content found, starting capture');
        intervalId = window.setInterval(captureFrame, 2000);
        captureFrame(); // Immediate first capture
      } else {
        setTimeout(waitForQuestionContent, 500);
      }
    };

    waitForQuestionContent();

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [captureFrame]); // captureFrame is stable (no deps)

  return (
    <div
      ref={captureRef}
      className="scratchpad-capture-wrapper"
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        pointerEvents: 'auto',
      }}
    >
      {children}
    </div>
  );
};

export default ScratchpadCapture;

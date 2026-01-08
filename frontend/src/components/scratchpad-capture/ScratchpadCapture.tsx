import React, { useRef, useEffect, ReactNode } from 'react';
import * as htmlToImage from 'html-to-image';

interface ScratchpadCaptureProps {
  children: ReactNode;
  onFrameCaptured: (canvas: HTMLCanvasElement) => void;
  /** Sketch canvas ref for capturing drawings */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sketchCanvasRef?: any;
  /** Whether the scratchpad is currently open */
  isScratchpadOpen?: boolean;
}

const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({
  children,
  onFrameCaptured,
  sketchCanvasRef,
  isScratchpadOpen = false,
}) => {
  const captureRef = useRef<HTMLDivElement>(null);
  const isCapturingRef = useRef(false);
  const lastCaptureTimeRef = useRef(0);

  useEffect(() => {
    let intervalId: number;
    let isMounted = true;

    const captureFrame = async () => {
      // Skip if unmounted or already capturing
      if (!isMounted || isCapturingRef.current) {
        return;
      }

      // Use slower rate to avoid overwhelming Gemini
      const minInterval = 5000;

      const now = Date.now();
      if (now - lastCaptureTimeRef.current < minInterval) {
        return;
      }

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

            // Draw question content (full width, top portion)
            ctx.drawImage(questionCanvas, 0, 0, 1280, 720);
          } catch (error) {
            console.error('html-to-image failed:', error);
          }
        } else {
          // Show error message if question container not found
          ctx.fillStyle = 'red';
          ctx.font = '24px Arial';
          ctx.fillText('ERROR: #question-content-container not found!', 50, 100);
        }

        // Capture sketch canvas drawings if scratchpad is open
        if (isScratchpadOpen && sketchCanvasRef) {
          try {
            // Check if canvas is ready by checking for exportPaths first
            const paths = await sketchCanvasRef.exportPaths();

            // Only capture if there are actual drawings
            if (!paths || paths.length === 0) {
              // No drawings yet, skip capture
              onFrameCaptured(compositeCanvas);
              return;
            }

            // Export the sketch canvas as a data URL
            const dataUrl = await sketchCanvasRef.exportImage('png');

            if (dataUrl) {
              // Load the image
              const img = new Image();
              await new Promise<void>((resolve, reject) => {
                img.onload = () => resolve();
                img.onerror = reject;
                img.src = dataUrl;
              });

              // Draw sketch content in the bottom-right corner with a border
              const drawingX = 1280 - 640 - 20; // 20px margin from right
              const drawingY = 720 - 360 - 20;  // 20px margin from bottom

              // Draw a subtle border/background for the drawing overlay
              ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
              ctx.fillRect(drawingX - 4, drawingY - 4, 648, 368);
              ctx.strokeStyle = '#4ADE80'; // Green border to indicate "visible to tutor"
              ctx.lineWidth = 3;
              ctx.strokeRect(drawingX - 4, drawingY - 4, 648, 368);

              // Draw the sketch canvas
              ctx.drawImage(img, drawingX, drawingY, 640, 360);

              // Add a small label
              ctx.fillStyle = '#4ADE80';
              ctx.font = 'bold 12px Arial';
              ctx.fillText('Your Drawing', drawingX, drawingY - 8);

              console.log('✅ Scratchpad frame captured with drawings');
            }
          } catch (error) {
            // Silently ignore canvas not ready errors
            if (error instanceof Error && error.message.includes('before canvas loaded')) {
              // Canvas not ready yet, skip this capture
            } else {
              console.error('Failed to capture sketch canvas:', error);
            }
          }
        }

        // Pass the composite canvas to the media mixer
        onFrameCaptured(compositeCanvas);
      } catch (error) {
        console.error('Frame capture failed:', error);
      } finally {
        isCapturingRef.current = false;
      }
    };

    // Wait for question-content-container to load before starting capture
    const waitForQuestionContent = () => {
      const questionContent = document.querySelector('#question-content-container');
      if (questionContent) {
        console.log('✅ Question content found, starting capture');
        // Use 2 second interval - actual capture rate is controlled by minInterval check
        intervalId = window.setInterval(captureFrame, 2000);
        // Capture immediately on start
        captureFrame();
      } else {
        // Check again in 100ms
        setTimeout(waitForQuestionContent, 100);
      }
    };

    waitForQuestionContent();

    return () => {
      isMounted = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [onFrameCaptured, sketchCanvasRef, isScratchpadOpen]);

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

import React, { useRef, useEffect, ReactNode } from 'react';
import * as htmlToImage from 'html-to-image';

interface ScratchpadCaptureProps {
  children: ReactNode;
  onFrameCaptured: (imageData: ImageData) => void;
}

const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({ children, onFrameCaptured }) => {
  const captureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let intervalId: number;

    const captureFrame = () => {
      const questionPanel = document.querySelector('.question-panel') as HTMLElement;

      if (questionPanel) {
        htmlToImage.toCanvas(questionPanel, {
          quality: 0.9,  // Increased quality for better image clarity
          skipFonts: true,
          pixelRatio: 1.5  // Balanced quality and size (1.5x instead of 2x for better performance)
        })
          .then((canvas) => {
            // Resize canvas to 1280×720 section size
            const resizedCanvas = document.createElement('canvas');
            resizedCanvas.width = 1280;
            resizedCanvas.height = 720;
            const resizedCtx = resizedCanvas.getContext('2d');

            if (resizedCtx) {
              resizedCtx.drawImage(canvas, 0, 0, 1280, 720);
              const imageData = resizedCtx.getImageData(0, 0, 1280, 720);
              onFrameCaptured(imageData);
            }
          })
          .catch(error => {
            console.error('html-to-image failed:', error);
          });
      } else {
        // Create error message as ImageData
        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, 1280, 720);
          ctx.fillStyle = 'red';
          ctx.font = '24px Arial';
          ctx.fillText('ERROR: .question-panel not found!', 50, 100);

          const imageData = ctx.getImageData(0, 0, 1280, 720);
          onFrameCaptured(imageData);
        }
      }
    };

    // Wait for question-panel to load before starting capture
    const waitForQuestionPanel = () => {
      const questionPanel = document.querySelector('.question-panel');
      if (questionPanel) {
        console.log('✅ Question panel found, starting capture');
        intervalId = window.setInterval(captureFrame, 1000);  // Reduced from 500ms to 1000ms (1 FPS) to reduce load
      } else {
        // Check again in 100ms
        setTimeout(waitForQuestionPanel, 100);
      }
    };

    waitForQuestionPanel();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [onFrameCaptured]);

  return (
    <div
      ref={captureRef}
      className="scratchpad-capture-wrapper"
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {children}
    </div>
  );
};

export default ScratchpadCapture;

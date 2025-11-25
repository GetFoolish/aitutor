import React, { useRef, useEffect, ReactNode } from 'react';
import * as htmlToImage from 'html-to-image';

interface ScratchpadCaptureProps {
  children: ReactNode;
  socket: WebSocket | null;
}

const ScratchpadCapture: React.FC<ScratchpadCaptureProps> = ({ children, socket }) => {
  const captureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!socket) return;

    let intervalId: number;

    const captureFrame = () => {
      if (!socket || socket.readyState !== WebSocket.OPEN) return;

      const questionPanel = document.querySelector('.question-panel') as HTMLElement;

      if (questionPanel) {
        htmlToImage.toJpeg(questionPanel, {
          quality: 0.9,  // Increased quality for better image clarity
          skipFonts: true,
          pixelRatio: 1.5  // Balanced quality and size (1.5x instead of 2x for better performance)
        })
          .then((dataUrl) => {
            const payload = JSON.stringify({ type: 'scratchpad_frame', data: dataUrl });
            socket.send(payload);
          })
          .catch(error => {
            console.error('html-to-image failed:', error);
          });
      } else {
        // Send error message to MediaMixer top panel
        const canvas = document.createElement('canvas');
        canvas.width = 800;
        canvas.height = 200;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, 800, 200);
          ctx.fillStyle = 'red';
          ctx.font = '24px Arial';
          ctx.fillText('ERROR: .question-panel not found!', 50, 100);

          const imageData = canvas.toDataURL('image/jpeg', 0.8);
          const payload = JSON.stringify({ type: 'scratchpad_frame', data: imageData });
          socket.send(payload);
        }
      }
    };

    // Wait for question-panel to load before starting capture
    const waitForQuestionPanel = () => {
      const questionPanel = document.querySelector('.question-panel');
      if (questionPanel && socket && socket.readyState === WebSocket.OPEN) {
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
  }, [socket]);

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

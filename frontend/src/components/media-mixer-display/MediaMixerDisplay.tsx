import React, { useEffect, useState, RefObject } from "react";
import cn from "classnames";

interface MediaMixerDisplayProps {
  socket: WebSocket | null;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
  onStatusChange?: (status: {
    isConnected: boolean;
    error: string | null;
  }) => void;
  isCameraEnabled?: boolean;
  isScreenShareEnabled?: boolean;
  isCanvasEnabled?: boolean;
}

const MediaMixerDisplay: React.FC<MediaMixerDisplayProps> = ({
  socket,
  renderCanvasRef,
  onStatusChange,
  isCameraEnabled = true,
  isScreenShareEnabled = true,
  isCanvasEnabled = true,
}) => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (onStatusChange) {
      onStatusChange({ isConnected, error });
    }
  }, [isConnected, error, onStatusChange]);

  useEffect(() => {
    if (!socket) return;

    console.log("MediaMixerDisplay: Setting up video WebSocket connection");

    const image = new Image();
    image.onload = () => {
      const canvas = renderCanvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          canvas.width = image.width;
          canvas.height = image.height;
          ctx.drawImage(image, 0, 0);
        }
      }
    };

    socket.onopen = () => {
      console.log("MediaMixerDisplay: Connected to video WebSocket");
      setIsConnected(true);
      setError(null);
    };

    // Check if already open
    if (socket.readyState === WebSocket.OPEN) {
      console.log("MediaMixerDisplay: WebSocket already open");
      setIsConnected(true);
      setError(null);
    } else if (
      socket.readyState === WebSocket.CLOSED ||
      socket.readyState === WebSocket.CLOSING
    ) {
      console.log("MediaMixerDisplay: WebSocket already closed");
      setError("Connection failed. Please refresh.");
      setIsConnected(false);
    }

    socket.onmessage = (event) => {
      // Match the original, working behavior: assume the MediaMixer sends
      // raw base64-encoded JPEG frame data (no JSON wrapper).
      const frame = event.data;

      // Debug logging: verify we are receiving streaming frame data
      try {
        const length = typeof frame === "string" ? frame.length : 0;
        console.log(
          "[MediaMixerDisplay] Received frame from /video WebSocket",
          "type:",
          typeof frame,
          "length:",
          length,
          "time:",
          new Date().toISOString(),
        );
      } catch {
        // Ignore logging errors so we never break rendering
      }

      const imageUrl = `data:image/jpeg;base64,${frame}`;
      setImageData(imageUrl);
      image.src = imageUrl;
    };

    socket.onerror = (err) => {
      console.error("MediaMixerDisplay: WebSocket error:", err);
      setError("Failed to connect to MediaMixer video stream. Is it running?");
      setIsConnected(false);
    };

    socket.onclose = () => {
      console.log("MediaMixerDisplay: Disconnected from video WebSocket");
      setIsConnected(false);
    };

    return () => {
      console.log("MediaMixerDisplay: Cleaning up video WebSocket");
    };
  }, [socket, renderCanvasRef]);

  return (
    <div className="flex flex-col w-full bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white overflow-hidden transition-colors duration-300">
      <div className="flex flex-col items-center justify-center p-0 bg-neutral-50 dark:bg-black/95 relative overflow-hidden group transition-colors duration-300">
        {error && (
          <div className="text-sm text-center p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400 max-w-[90%] backdrop-blur-md shadow-lg z-20 absolute">
            <span className="material-symbols-outlined text-2xl mb-2 block">
              error
            </span>
            {error}
          </div>
        )}
        {!isConnected && !error && (
          <div className="flex flex-col items-center gap-3 text-neutral-500 dark:text-neutral-400 animate-pulse z-20 py-12">
            <span className="material-symbols-outlined text-4xl opacity-50">
              connecting_airports
            </span>
            <div className="text-sm font-medium">Connecting to Stream...</div>
          </div>
        )}
        {isConnected && imageData && (
          <div className="w-full h-auto flex items-center justify-center bg-white dark:bg-black">
            <img
              src={imageData}
              alt="Media Mixer Feed"
              className="w-full h-auto object-contain"
            />

            {/* <canvas */}
            {/*   ref={renderCanvasRef} */}
            {/*   className="w-full h-full object-contain" */}
            {/* /> */}
          </div>
        )}
      </div>
    </div>
  );
};

export default MediaMixerDisplay;

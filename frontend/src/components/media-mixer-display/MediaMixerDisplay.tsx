import React, { useEffect, useState, RefObject } from "react";
import cn from "classnames";

interface MediaMixerDisplayProps {
  socket: WebSocket | null;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
}

const MediaMixerDisplay: React.FC<MediaMixerDisplayProps> = ({
  socket,
  renderCanvasRef,
}) => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const frame = event.data;
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
    <div className="flex flex-col h-full w-full bg-card text-card-foreground rounded-xl overflow-hidden">
      <header className="flex justify-between items-center p-4 border-b border-white/10 bg-black text-white">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="p-1.5 bg-white/10 rounded-lg">
            <span className="material-symbols-outlined text-white text-xl">
              cast
            </span>
          </div>
          <h2 className="font-semibold text-base tracking-tight truncate">
            Media Mixer
          </h2>
          <span
            className={cn(
              "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
              {
                "bg-green-500/20 text-green-400 border-green-500/30":
                  isConnected && !error,
                "bg-red-500/20 text-red-400 border-red-500/30": !!error,
                "bg-yellow-500/20 text-yellow-400 border-yellow-500/30":
                  !isConnected && !error,
              },
            )}
          >
            {error ? "Offline" : isConnected ? "Live" : "Connecting"}
          </span>
        </div>
      </header>
      <div className="flex-1 flex flex-col items-center justify-center p-0 bg-black/95 relative overflow-hidden group">
        {error && (
          <div className="text-sm text-center p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 max-w-[90%] backdrop-blur-md shadow-lg">
            <span className="material-symbols-outlined text-2xl mb-2 block">
              error
            </span>
            {error}
          </div>
        )}
        {!isConnected && !error && (
          <div className="flex flex-col items-center gap-3 text-muted-foreground animate-pulse">
            <span className="material-symbols-outlined text-4xl opacity-50">
              connecting_airports
            </span>
            <div className="text-sm font-medium">Connecting to Stream...</div>
          </div>
        )}
        {isConnected && imageData && (
          <div className="w-full h-full flex items-center justify-center bg-zinc-900 relative">
            <img
              src={imageData}
              alt="MediaMixer Stream"
              className="w-full h-full object-contain"
            />
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <span className="px-2 py-1 bg-black/50 text-white text-xs rounded-md backdrop-blur-md">
                Live Feed
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MediaMixerDisplay;

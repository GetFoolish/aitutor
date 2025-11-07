import React, { useEffect, useState, useRef } from "react";
import {
  ConnectButton,
  UserAudioControl,
  Conversation,
} from "@pipecat-ai/voice-ui-kit";
import {
  usePipecatClient,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { TransportState } from "@pipecat-ai/client-js";
import { FaVideo, FaDesktop, FaMicrophone, FaExpand, FaCompress, FaTimes, FaPencilAlt, FaChevronLeft, FaChevronRight } from "react-icons/fa";

interface FloatingVideoWidgetProps {
  onConnect?: () => void | Promise<void>;
  onDisconnect?: () => void | Promise<void>;
  commandSocket?: WebSocket | null;
}

export const FloatingVideoWidget: React.FC<FloatingVideoWidgetProps> = ({
  onConnect,
  onDisconnect,
  commandSocket,
}) => {
  const client = usePipecatClient();
  const [transportState, setTransportState] = useState<TransportState>("disconnected");
  const [mediaMixerScreen, setMediaMixerScreen] = useState(true); // Default ON to match MediaMixer
  const [mediaMixerCamera, setMediaMixerCamera] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHidden, setIsHidden] = useState(false);
  const [position, setPosition] = useState({ x: window.innerWidth - 200, y: window.innerHeight - 200 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [mediaFrame, setMediaFrame] = useState<string | null>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const widgetRef = useRef<HTMLDivElement>(null);
  const videoSocketRef = useRef<WebSocket | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);

  // Track connection state
  useRTVIClientEvent("transportStateChanged", (state) => {
    console.log("[FloatingWidget] Transport state changed:", state);
    setTransportState(state);
  });

  // Track errors
  useRTVIClientEvent("error", (error) => {
    console.error("[FloatingWidget] Error event:", error);
  });

  // Start local webcam
  const startLocalWebcam = async () => {
    try {
      console.log("[FloatingWidget] Starting local webcam...");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false  // Audio is handled by Pipecat
      });
      setLocalStream(stream);
      console.log("[FloatingWidget] Local webcam started");
    } catch (err) {
      console.error("[FloatingWidget] Failed to start webcam:", err);
    }
  };

  // Stop local webcam
  const stopLocalWebcam = () => {
    if (localStream) {
      console.log("[FloatingWidget] Stopping local webcam...");
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
    }
  };

  // Attach local stream to video element
  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  // Connect to MediaMixer video stream (port 8766)
  useEffect(() => {
    console.log("[FloatingWidget] Connecting to MediaMixer video stream...");
    const videoWs = new WebSocket('ws://localhost:8766');

    videoWs.onopen = () => {
      console.log("[FloatingWidget] MediaMixer video stream connected");
    };

    videoWs.onmessage = (event) => {
      // Receive base64 JPEG frame from MediaMixer
      setMediaFrame(`data:image/jpeg;base64,${event.data}`);
    };

    videoWs.onerror = (err) => {
      console.error("[FloatingWidget] MediaMixer video stream error:", err);
    };

    videoWs.onclose = () => {
      console.log("[FloatingWidget] MediaMixer video stream disconnected");
    };

    videoSocketRef.current = videoWs;

    return () => {
      console.log("[FloatingWidget] Closing MediaMixer video stream");
      videoWs.close();
    };
  }, []);

  // Dragging logic
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.widget-controls')) return; // Don't drag when clicking controls

    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    });
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      const newX = e.clientX - dragOffset.x;
      const newY = e.clientY - dragOffset.y;

      // Keep widget within viewport bounds
      const maxX = window.innerWidth - (widgetRef.current?.offsetWidth || 0);
      const maxY = window.innerHeight - (widgetRef.current?.offsetHeight || 0);

      setPosition({
        x: Math.max(0, Math.min(newX, maxX)),
        y: Math.max(0, Math.min(newY, maxY)),
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  // Initialize MediaMixer to match frontend default state
  useEffect(() => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      console.log('[FloatingWidget] Initializing MediaMixer state: screen=ON, camera=OFF');
      // Ensure screen is ON to match default
      commandSocket.send(JSON.stringify({
        type: 'toggle_screen',
        data: { enabled: true }
      }));
      // Ensure camera is OFF to match default
      commandSocket.send(JSON.stringify({
        type: 'toggle_camera',
        data: { enabled: false }
      }));
    }
  }, [commandSocket]);

  // MediaMixer controls
  const toggleMediaMixerScreen = () => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      const newState = !mediaMixerScreen;
      setMediaMixerScreen(newState);
      console.log(`[FloatingWidget] Toggling MediaMixer screen: ${newState}`);
      commandSocket.send(JSON.stringify({
        type: 'toggle_screen',
        data: { enabled: newState }
      }));
    }
  };

  const toggleMediaMixerCamera = () => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      const newState = !mediaMixerCamera;
      setMediaMixerCamera(newState);
      console.log(`[FloatingWidget] Toggling MediaMixer camera: ${newState}`);
      commandSocket.send(JSON.stringify({
        type: 'toggle_camera',
        data: { enabled: newState }
      }));
    }
  };

  const isConnected = transportState === "connected" || transportState === "ready";

  if (!client) return null;

  return (
    <div
      ref={widgetRef}
      className="floating-video-widget"
      style={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y}px`,
        zIndex: 9999,
        cursor: isDragging ? 'grabbing' : 'grab',
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Hidden State - Just a small tab */}
      {isHidden && (
        <button
          onClick={() => setIsHidden(false)}
          style={{
            background: '#6366F1',
            border: 'none',
            borderRadius: '8px 0 0 8px',
            padding: '12px 8px',
            color: 'white',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
            transition: 'all 0.2s',
          }}
          title="Show controls"
          aria-label="Show controls"
        >
          <FaChevronLeft size={16} />
        </button>
      )}

      {/* Minimized State - Circular Video */}
      {!isExpanded && !isHidden && (
        <div className="widget-minimized">
          {/* Circular Video Preview - Shows YOUR webcam when connected, MediaMixer otherwise */}
          <div className="circular-video">
            {localStream ? (
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '50%',
                  transform: 'scaleX(-1)'  // Mirror like Loom
                }}
              />
            ) : mediaFrame ? (
              <img
                src={mediaFrame}
                alt="MediaMixer preview"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  borderRadius: '50%'
                }}
              />
            ) : (
              <div className="video-placeholder">
                <span style={{ fontSize: '32px' }}>📹</span>
              </div>
            )}
          </div>

          {/* Status Indicator */}
          <div className="status-indicator" style={{
            background: isConnected ? '#2ed573' : '#ff5d5d'
          }}></div>

          {/* Quick Controls */}
          <div className="widget-controls quick-controls">
            <ConnectButton
              onConnect={onConnect}
              onDisconnect={onDisconnect}
            />
            <button
              onClick={localStream ? stopLocalWebcam : startLocalWebcam}
              className={`control-btn ${localStream ? 'active' : ''}`}
              aria-label={localStream ? "Disconnect webcam" : "Connect webcam"}
              title={localStream ? "Disconnect webcam" : "Connect webcam"}
            >
              <FaVideo size={14} />
            </button>
            <button
              onClick={toggleMediaMixerScreen}
              className={`control-btn ${mediaMixerScreen ? 'active' : ''}`}
              aria-label="Toggle screen share"
              title="Toggle screen share"
            >
              <FaDesktop size={14} />
            </button>
            <button
              onClick={() => {
                // Find the scratchpad and scroll to it smoothly
                const scratchpadElement = document.querySelector('.scratchpad-container');
                if (scratchpadElement) {
                  scratchpadElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                  // Fallback: try to find by any element with "scratchpad" text
                  const allElements = Array.from(document.querySelectorAll('div'));
                  const scratchpad = allElements.find(el =>
                    el.textContent?.toLowerCase().includes('scratchpad') &&
                    el.querySelector('canvas')
                  );
                  if (scratchpad) {
                    scratchpad.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }
                }
              }}
              className="control-btn active"
              aria-label="Go to scratchpad"
              title="Click to scroll to scratchpad"
              style={{ cursor: 'pointer' }}
            >
              <FaPencilAlt size={14} />
            </button>
            <button
              onClick={() => setIsExpanded(true)}
              className="control-btn"
              aria-label="Expand controls"
              title="Expand controls"
            >
              <FaExpand size={12} />
            </button>
            <button
              onClick={() => setIsHidden(true)}
              className="control-btn"
              aria-label="Hide controls"
              title="Hide controls"
            >
              <FaChevronRight size={12} />
            </button>
          </div>
        </div>
      )}

      {/* Expanded State - Full Controls */}
      {isExpanded && !isHidden && (
        <div className="widget-expanded">
          <div className="expanded-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="status-indicator" style={{
                background: isConnected ? '#2ed573' : '#ff5d5d'
              }}></div>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={() => setIsExpanded(false)}
                className="control-btn"
                aria-label="Minimize"
                title="Minimize"
              >
                <FaCompress size={12} />
              </button>
              <button
                onClick={() => setIsHidden(true)}
                className="control-btn"
                aria-label="Hide controls"
                title="Hide controls"
              >
                <FaChevronRight size={12} />
              </button>
            </div>
          </div>

          <div className="expanded-content">
            {/* Video Preview - Shows MediaMixer Stream */}
            <div className="expanded-video">
              {mediaFrame ? (
                <img
                  src={mediaFrame}
                  alt="MediaMixer preview"
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain'
                  }}
                />
              ) : (
                <div className="video-placeholder">
                  <span style={{ fontSize: '48px' }}>📹</span>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                    MediaMixer stream loading...
                  </p>
                </div>
              )}
            </div>

            {/* Conversation */}
            <div style={{ flex: 1, minHeight: '200px', overflow: 'auto', background: 'var(--surface-light)', borderRadius: '8px', padding: '12px' }}>
              <Conversation
                assistantLabel="Tutor"
                clientLabel="You"
                textMode="tts"
              />
            </div>

            {/* Control Buttons */}
            <div className="widget-controls expanded-controls">
              <UserAudioControl />

              <button
                onClick={toggleMediaMixerCamera}
                className={`control-btn ${mediaMixerCamera ? 'active' : ''}`}
                aria-label="Toggle camera"
                title="Toggle camera"
              >
                <FaVideo size={14} />
                <span>Camera</span>
              </button>

              <button
                onClick={toggleMediaMixerScreen}
                className={`control-btn ${mediaMixerScreen ? 'active' : ''}`}
                aria-label="Toggle screen"
                title="Toggle screen"
              >
                <FaDesktop size={14} />
                <span>Screen</span>
              </button>

              <button
                onClick={() => {
                  // Find the scratchpad and scroll to it smoothly
                  const scratchpadElement = document.querySelector('.scratchpad-container');
                  if (scratchpadElement) {
                    scratchpadElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  } else {
                    // Fallback: try to find by any element with "scratchpad" text
                    const allElements = Array.from(document.querySelectorAll('div'));
                    const scratchpad = allElements.find(el =>
                      el.textContent?.toLowerCase().includes('scratchpad') &&
                      el.querySelector('canvas')
                    );
                    if (scratchpad) {
                      scratchpad.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                  }
                }}
                className="control-btn active"
                aria-label="Go to scratchpad"
                title="Click to scroll to scratchpad"
                style={{ cursor: 'pointer' }}
              >
                <FaPencilAlt size={14} />
                <span>Scratchpad</span>
              </button>

              <ConnectButton
                onConnect={onConnect}
                onDisconnect={onDisconnect}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

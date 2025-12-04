import React, {
  memo,
  RefObject,
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import Draggable from "react-draggable";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { useMediaCapture } from "../../hooks/useMediaCapture";
import { AudioRecorder } from "../../lib/audio-recorder";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import cn from "classnames";
import MediaMixerDisplay from "../media-mixer-display/MediaMixerDisplay";
import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  Monitor,
  MonitorOff,
  PlayCircle,
  StopCircle,
  Settings,
  PenTool,
  Image as ImageIcon,
  MoreHorizontal,
  ChevronDown,
  ChevronUp,
  Home,
  X,
  Eye,
} from "lucide-react";

export type FloatingControlPanelProps = {
  socket: WebSocket | null;
  videoRef: RefObject<HTMLVideoElement>;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
  supportsVideo: boolean;
  onVideoStreamChange?: (stream: MediaStream | null) => void;
  onMixerStreamChange?: (stream: MediaStream | null) => void;
  enableEditingSettings?: boolean;
  onPaintClick: () => void;
  isPaintActive: boolean;
  videoSocket: WebSocket | null;
};

function FloatingControlPanel({
  socket,
  videoRef,
  renderCanvasRef,
  supportsVideo,
  enableEditingSettings,
  onPaintClick,
  isPaintActive,
  videoSocket,
}: FloatingControlPanelProps) {
  const { client, connected, connect, disconnect } = useLiveAPIContext();
  const { cameraEnabled, screenEnabled, toggleCamera, toggleScreen } =
    useMediaCapture({ socket });
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("");
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const [activeVideoStream] = useState<MediaStream | null>(null);
  const [sharedMediaOpen, setSharedMediaOpen] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [popoverPosition, setPopoverPosition] = useState<"left" | "right">(
    "right",
  );
  const [isDragging, setIsDragging] = useState(false);
  const [mediaMixerStatus, setMediaMixerStatus] = useState<{
    isConnected: boolean;
    error: string | null;
  }>({ isConnected: false, error: null });

  // Timer for session duration
  useEffect(() => {
    if (!connected) {
      setSessionTime(0);
      return;
    }

    const interval = setInterval(() => {
      setSessionTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [connected]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }, []);

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((devices) => {
      const audioInputs = devices.filter(
        (device) => device.kind === "audioinput",
      );
      setAudioDevices(audioInputs);
      if (audioInputs.length > 0) {
        setSelectedAudioDevice(audioInputs[0].deviceId);
      }
    });
  }, []);

  useEffect(() => {
    const onData = (base64: string) => {
      client.sendRealtimeInput([
        {
          mimeType: "audio/pcm;rate=16000",
          data: base64,
        },
      ]);
    };
    if (connected && !muted && audioRecorder) {
      audioRecorder.on("data", onData).start(selectedAudioDevice);
    } else {
      audioRecorder.stop();
    }
    return () => {
      audioRecorder.off("data", onData);
    };
  }, [connected, client, muted, audioRecorder, selectedAudioDevice]);

  // Video handling (similar to ControlTray)
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId = -1;

    function sendVideoFrame() {
      const canvas = renderCanvasRef.current;

      if (!canvas) {
        return;
      }

      if (canvas.width + canvas.height > 0) {
        const base64 = canvas.toDataURL("image/jpeg", 1.0);
        const data = base64.slice(base64.indexOf(",") + 1, Infinity);
        client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);
      }
      if (connected) {
        timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
      }
    }
    if (connected) {
      requestAnimationFrame(sendVideoFrame);
    }
    return () => {
      clearTimeout(timeoutId);
    };
  }, [connected, activeVideoStream, client, videoRef, renderCanvasRef]);

  // // Video handling - capture full MediaMixer canvas and send to tutor as JPEG
  // useEffect(() => {
  //   if (videoRef.current) {
  //     videoRef.current.srcObject = activeVideoStream;
  //   }
  //
  //   // Only send frames if camera or screen is enabled
  //   if (!connected || (!cameraEnabled && !screenEnabled)) {
  //     return;
  //   }
  //
  //   let rafId: number;
  //   let lastFrameTime = 0;
  //   const frameInterval = 1000 / 0.5; // 0.5 FPS (every 2 seconds)
  //
  //   function sendVideoFrame(timestamp: number) {
  //     const canvas = renderCanvasRef.current;
  //
  //     if (!canvas) {
  //       rafId = requestAnimationFrame(sendVideoFrame);
  //       return;
  //     }
  //
  //     // Throttle to desired FPS
  //     if (timestamp - lastFrameTime < frameInterval) {
  //       rafId = requestAnimationFrame(sendVideoFrame);
  //       return;
  //     }
  //
  //     lastFrameTime = timestamp;
  //
  //     if (canvas.width + canvas.height > 0) {
  //       // Capture the exact MediaMixer output at full resolution for the tutor
  //       const base64 = canvas.toDataURL("image/jpeg", 1.0);
  //       const data = base64.slice(base64.indexOf(",") + 1, Infinity);
  //       client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);
  //     }
  //
  //     if (connected) {
  //       rafId = requestAnimationFrame(sendVideoFrame);
  //     }
  //   }
  //
  //   if (connected) {
  //     rafId = requestAnimationFrame(sendVideoFrame);
  //   }
  //
  //   return () => {
  //     if (rafId) {
  //       cancelAnimationFrame(rafId);
  //     }
  //   };
  // }, [connected, activeVideoStream, cameraEnabled, screenEnabled, client, videoRef, renderCanvasRef]);

  const handleConnect = useCallback(async () => {
    if (connected) {
      disconnect();
    } else {
      await connect();
    }
  }, [connected, connect, disconnect]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize position on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      // Adjust for smaller panel width (320px on desktop, 280px on mobile)
      const panelWidth = window.innerWidth >= 768 ? 340 : 300;
      setPosition({ x: window.innerWidth - panelWidth, y: 72 });
      setHasInitialized(true);
    }
  }, []);

  // Memoize popover position calculation to avoid expensive DOM queries
  const calculatePopoverPosition = useCallback(() => {
    if (!panelRef.current) return { side: "right" as const, vertical: "top" as const };

    const panelRect = panelRef.current.getBoundingClientRect();
    const popoverWidth = 360;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const spaceOnRight = viewportWidth - panelRect.right;
    const spaceOnLeft = panelRect.left;
    const preferredMargin = 16;

    let side: "left" | "right" = "right";
    if (spaceOnRight >= popoverWidth + preferredMargin) {
      side = "right";
    } else if (spaceOnLeft >= popoverWidth + preferredMargin) {
      side = "left";
    }

    // Calculate vertical alignment based on panel's center relative to screen center
    const panelCenterY = panelRect.top + panelRect.height / 2;
    const screenCenterY = viewportHeight / 2;
    const vertical: "top" | "bottom" = panelCenterY > screenCenterY ? "bottom" : "top";

    return { side, vertical };
  }, []);

  const updatePopoverPosition = useCallback(() => {
    const { side, vertical } = calculatePopoverPosition();
    setPopoverPosition(side);
    setVerticalAlign(vertical);
  }, [calculatePopoverPosition]);

  const toggleSharedMedia = useCallback(() => {
    if (!sharedMediaOpen) {
      // Opening
      updatePopoverPosition();
      setSharedMediaOpen(true);
      setIsAnimatingOut(false);
    } else {
      // Closing
      setIsAnimatingOut(true);
      setTimeout(() => {
        setSharedMediaOpen(false);
        setIsAnimatingOut(false);
      }, 200); // Match CSS animation duration
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  const handleCollapse = useCallback(() => {
    setIsCollapsed(!isCollapsed);
  }, [isCollapsed]);

  // Adjust position when collapsing/expanding to prevent overflow
  useEffect(() => {
    if (!hasInitialized || !panelRef.current) return;

    // Use setTimeout to allow layout to update (height change)
    const timer = setTimeout(() => {
      if (!panelRef.current) return;
      const rect = panelRef.current.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;
      const margin = 16;

      let newY = position.y;
      let newX = position.x;

      // Check bottom overflow
      if (rect.bottom > viewportHeight - margin) {
        newY = viewportHeight - rect.height - margin;
      }
      // Check top overflow
      if (newY < margin) {
        newY = margin;
      }

      // Check right overflow
      if (rect.right > viewportWidth - margin) {
        newX = viewportWidth - rect.width - margin;
      }
      // Check left overflow
      if (newX < margin) {
        newX = margin;
      }

      if (newY !== position.y || newX !== position.x) {
        setPosition({ x: newX, y: newY });
      }
    }, 50); // Small delay for transition

    return () => clearTimeout(timer);
  }, [isCollapsed, hasInitialized]); // Removed 'position' dependency to avoid loops, relying on rect reading

  const handleMute = useCallback(() => {
    setMuted(!muted);
  }, [muted]);

  // Memoize drag handlers to avoid re-creating functions
  const handleDragStart = useCallback(() => {
    setIsDragging(true);
  }, []);

  const handleDrag = useCallback((e: any, data: { x: number; y: number }) => {
    if (!panelRef.current) return;

    const rect = panelRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Clamp values to keep panel within viewport
    let newX = data.x;
    let newY = data.y;

    // Horizontal boundaries
    if (newX < 0) newX = 0;
    else if (newX + rect.width > viewportWidth) newX = viewportWidth - rect.width;

    // Vertical boundaries
    if (newY < 0) newY = 0;
    else if (newY + rect.height > viewportHeight) newY = viewportHeight - rect.height;

    setPosition({ x: newX, y: newY });
  }, []);

  const handleDragStop = useCallback(() => {
    setIsDragging(false);
    // Recalculate position after drag ends
    if (sharedMediaOpen) {
      updatePopoverPosition();
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  // Memoize panel classes to avoid recalculating on every render
  const panelClasses = useMemo(
    () =>
      cn(
        "fixed z-[1000] bg-[#FFFDF5] border-[2px] md:border-[3px] border-black rounded-lg md:rounded-xl",
        // GPU acceleration hints
        "will-change-transform transform-gpu",
        // Only apply transitions when NOT dragging to prevent layout thrashing
        !isDragging &&
        "transition-all duration-200 ease-out",
        isCollapsed
          ? "w-[50px] md:w-[55px] py-2 md:py-2.5 px-1 md:px-1.5 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)]"
          : "w-[220px] md:w-[250px] p-2.5 md:p-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)]",
        // Ensure origin is top-left for controlled positioning
        "top-0 left-0",
        // Hover effect
        !isDragging &&
        "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)] md:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_8px_8px_20px_rgba(0,0,0,0.18),_16px_16px_40px_rgba(0,0,0,0.12)]",
      ),
    [isCollapsed, isDragging],
  );

  if (!hasInitialized) return null; // Prevent hydration mismatch

  return (
    <Draggable
      handle=".drag-handle"
      nodeRef={panelRef}
      position={position}
      onStart={handleDragStart}
      onDrag={handleDrag}
      onStop={handleDragStop}
    >
      <div
        ref={panelRef}
        className={panelClasses}
        style={{
          // Use transform3d for GPU acceleration
          transform: "translate3d(0, 0, 0)",
        }}
      >
        {/* Drag Handle & Header */}
        <div
          className={cn(
            "drag-handle cursor-grab active:cursor-grabbing flex items-center mb-1.5 md:mb-2",
            !isDragging && "transition-all duration-200 ease-out",
            isCollapsed ? "justify-center mb-1 md:mb-1.5" : "justify-between",
          )}
        >
          {!isCollapsed && (
            <div className="flex items-center gap-1.5 md:gap-2">
              <div className="flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black bg-[#FFD93D]">
                <span className="material-symbols-outlined text-sm md:text-base text-black font-black">
                  smart_toy
                </span>
              </div>
              <div>
                <div className="font-black text-[10px] md:text-xs text-black leading-none mb-0 md:mb-0.5 uppercase">
                  AI TUTOR
                </div>
                <div className="text-[7px] md:text-[8px] text-black font-bold uppercase tracking-wide bg-[#C4B5FD] px-1 md:px-1.5 py-0 border-[1.5px] border-black inline-block">
                  CONTROL
                </div>
              </div>
            </div>
          )}
          <button
            onClick={handleCollapse}
            className="w-5 h-5 md:w-6 md:h-6 flex items-center justify-center border-[2px] border-black bg-[#FFFDF5] hover:bg-[#FFD93D] text-black hover:translate-x-0.5 hover:translate-y-0.5 transition-all duration-100"
          >
            {isCollapsed ? (
              <ChevronDown className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
            ) : (
              <ChevronUp className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
            )}
          </button>
        </div>

        {isCollapsed ? (
          // COLLAPSED VIEW
          <div className="flex flex-col items-center gap-1.5 md:gap-2">
            <button
              onClick={handleCollapse}
              className="w-8 h-8 md:w-9 md:h-9 border-[2px] border-black bg-[#FFFDF5] hover:bg-[#FFD93D] flex items-center justify-center text-black transition-all hover:translate-x-0.5 hover:translate-y-0.5 duration-100 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none"
              title="Expand"
            >
              <Home className="w-4 h-4 font-bold" />
            </button>

            {/* Start/End Session Button */}
            <button
              onClick={handleConnect}
              className={cn(
                "w-9 h-9 md:w-10 md:h-10 border-[2px] border-black flex items-center justify-center transition-all transform active:translate-x-1 active:translate-y-1 relative group font-black",
                connected
                  ? "bg-[#FF6B6B] hover:bg-[#FF6B6B] text-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]"
                  : "bg-[#4ADE80] hover:bg-[#4ADE80] text-black shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
              )}
              title={connected ? "End Session" : "Start Session"}
            >
              {connected ? (
                <div className="w-3 h-3 bg-white border-2 border-black" />
              ) : (
                <PlayCircle className="w-5 h-5" />
              )}
              {connected && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#FFD93D] border-2 border-black animate-pulse" />
              )}
            </button>

            <div className="w-7 h-[2px] bg-black my-0.5" />

            <button
              onClick={handleMute}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                muted
                  ? "bg-[#FF6B6B] text-white"
                  : "bg-[#FFFDF5] text-black hover:bg-[#FFD93D]",
              )}
              title={muted ? "Unmute" : "Mute"}
            >
              {muted ? (
                <MicOff className="w-3.5 h-3.5 font-bold" />
              ) : (
                <Mic className="w-3.5 h-3.5 font-bold" />
              )}
            </button>

            {supportsVideo && (
              <button
                onClick={() => toggleCamera(!cameraEnabled)}
                className={cn(
                  "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                  cameraEnabled
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] text-black hover:bg-[#FFD93D]",
                )}
                title="Toggle Camera"
              >
                {cameraEnabled ? (
                  <Video className="w-3.5 h-3.5 font-bold" />
                ) : (
                  <VideoOff className="w-3.5 h-3.5 font-bold" />
                )}
              </button>
            )}

            {supportsVideo && (
              <button
                onClick={() => toggleScreen(!screenEnabled)}
                className={cn(
                  "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                  screenEnabled
                    ? "bg-[#FFD93D] text-black"
                    : "bg-[#FFFDF5] text-black hover:bg-[#FFD93D]",
                )}
                title="Share Screen"
              >
                {screenEnabled ? (
                  <Monitor className="w-3.5 h-3.5 font-bold" />
                ) : (
                  <MonitorOff className="w-3.5 h-3.5 font-bold" />
                )}
              </button>
            )}

            <div className="w-7 h-[2px] bg-black my-0.5" />

            {enableEditingSettings && (
              <SettingsDialog
                className="!h-auto !block"
                trigger={
                  <button className="w-8 h-8 md:w-9 md:h-9 border-[2px] border-black bg-[#FFFDF5] hover:bg-[#FF6B6B] flex items-center justify-center text-black hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100">
                    <Settings className="w-3.5 h-3.5 font-bold" />
                  </button>
                }
              />
            )}

            <button
              onClick={onPaintClick}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                isPaintActive
                  ? "bg-[#FFD93D] text-black"
                  : "bg-[#FFFDF5] text-black hover:bg-[#FFD93D]",
              )}
              title="Canvas"
            >
              <PenTool className="w-3.5 h-3.5 font-bold" />
            </button>

            <button
              onClick={toggleSharedMedia}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                sharedMediaOpen
                  ? "bg-[#C4B5FD] text-black"
                  : "bg-[#FFFDF5] text-black hover:bg-[#C4B5FD]",
              )}
              title="View"
            >
              <Eye className="w-3.5 h-3.5 font-bold" />
            </button>

            <div
              className={cn(
                "w-10 h-8 flex items-center justify-center text-[9px] font-mono font-black mt-1 transition-colors border-[2px] border-black",
                connected
                  ? "bg-[#FFD93D] text-black"
                  : "bg-[#FFFDF5] text-black",
              )}
            >
              {connected ? formatTime(sessionTime) : "--:--"}
            </div>
          </div>
        ) : (
          // EXPANDED VIEW
          <div className="flex flex-col gap-1.5 md:gap-2">
            {/* Audio Control */}
            <div
              onClick={handleMute}
              className={cn(
                "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black transition-all duration-100 group cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                !muted
                  ? "bg-[#FFFDF5]"
                  : "bg-[#FF6B6B]",
              )}
            >
              <div className="flex items-center gap-1.5 md:gap-2 overflow-hidden">
                <div
                  className={cn(
                    "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black transition-colors",
                    !muted
                      ? "bg-[#C4B5FD] text-black"
                      : "bg-white text-black",
                  )}
                >
                  {muted ? (
                    <MicOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                  ) : (
                    <Mic className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span className={cn("text-[8px] md:text-[9px] font-bold uppercase tracking-wide", muted ? "text-white" : "text-black")}>
                    Mic
                  </span>
                  <select
                    className={cn("bg-transparent border-none text-[10px] md:text-xs outline-none cursor-pointer w-[85px] md:w-[100px] truncate p-0 font-black", muted ? "text-white" : "text-black")}
                    value={selectedAudioDevice}
                    onChange={(e) => {
                      e.stopPropagation();
                      setSelectedAudioDevice(e.target.value);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    disabled={connected}
                  >
                    {audioDevices.map((device) => (
                      <option
                        key={device.deviceId}
                        value={device.deviceId}
                        className="bg-white text-black font-bold"
                      >
                        {device.label || `Mic ${device.deviceId.slice(0, 4)}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleMute();
                }}
                className={cn(
                  "text-[9px] md:text-[10px] font-black px-2 md:px-2.5 py-1 md:py-1.5 transition-all border-[2px] border-black uppercase tracking-wide",
                  !muted
                    ? "bg-[#FFD93D] text-black hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none"
                    : "bg-white text-black hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none",
                )}
              >
                {muted ? "On" : "Off"}
              </button>
            </div>

            {/* Camera Control */}
            {supportsVideo && (
              <div
                onClick={() => toggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                  cameraEnabled
                    ? "bg-[#FFD93D]"
                    : "bg-[#FFFDF5]",
                )}
              >
                <div className="flex items-center gap-1.5 md:gap-2">
                  <div
                    className={cn(
                      "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black transition-colors",
                      cameraEnabled
                        ? "bg-white text-black"
                        : "bg-[#C4B5FD] text-black",
                    )}
                  >
                    {cameraEnabled ? (
                      <Video className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <VideoOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[10px] md:text-xs font-black text-black uppercase tracking-wide">
                    Camera
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleCamera(!cameraEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-2.5 py-1 md:py-1.5 transition-all border-[2px] border-black uppercase tracking-wide",
                    cameraEnabled
                      ? "bg-[#FF6B6B] text-white hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none"
                      : "bg-[#FFD93D] text-black hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none",
                  )}
                >
                  {cameraEnabled ? "Off" : "On"}
                </button>
              </div>
            )}

            {/* Screen Share Control */}
            {supportsVideo && (
              <div
                onClick={() => toggleScreen(!screenEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                  screenEnabled
                    ? "bg-[#FFD93D]"
                    : "bg-[#FFFDF5]",
                )}
              >
                <div className="flex items-center gap-1.5 md:gap-2">
                  <div
                    className={cn(
                      "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black transition-colors",
                      screenEnabled
                        ? "bg-white text-black"
                        : "bg-[#FFD93D] text-black",
                    )}
                  >
                    {screenEnabled ? (
                      <Monitor className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <MonitorOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[10px] md:text-xs font-black text-black uppercase tracking-wide">
                    Screen
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleScreen(!screenEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-2.5 py-1 md:py-1.5 transition-all border-[2px] border-black uppercase tracking-wide",
                    screenEnabled
                      ? "bg-[#FF6B6B] text-white hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none"
                      : "bg-[#C4B5FD] text-black hover:translate-x-0.5 hover:translate-y-0.5 shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none",
                  )}
                >
                  {screenEnabled ? "Stop" : "On"}
                </button>
              </div>
            )}

            {/* Main Action Button */}
            <button
              onClick={handleConnect}
              className={cn(
                "w-full py-2 md:py-2.5 font-black border-[2px] border-black transition-all transform active:translate-x-1 active:translate-y-1 active:shadow-none flex items-center justify-center gap-1.5 mt-1 md:mt-1.5 uppercase tracking-wide text-xs md:text-sm",
                connected
                  ? "bg-[#FF6B6B] text-white hover:bg-[#FF6B6B] shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]"
                  : "bg-[#4ADE80] text-black hover:bg-[#4ADE80] shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
              )}
            >
              {connected ? (
                <>
                  <div className="w-3 h-3 bg-white border-2 border-black" />
                  <span>End</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 md:w-4.5 md:h-4.5" />
                  <span>Start Session</span>
                </>
              )}
            </button>

            {/* Bottom Actions */}
            <div className="grid grid-cols-4 gap-1.5 md:gap-2 pt-2 md:pt-2.5 border-t-[2px] border-black">
              {enableEditingSettings && (
                <SettingsDialog
                  className="!h-auto !block"
                  trigger={
                    <button className="flex flex-col items-center gap-0.5 md:gap-1 p-1 md:p-1.5 transition-all group hover:translate-y-0.5">
                      <div className="p-1 md:p-1.5 border-[2px] border-black bg-[#FFFDF5] group-hover:bg-[#FF6B6B] transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] group-hover:shadow-none">
                        <Settings className="w-3 h-3 md:w-3.5 md:h-3.5 text-black group-hover:text-white font-bold" />
                      </div>
                      <span className="text-[7px] md:text-[8px] font-black uppercase">Set</span>
                    </button>
                  }
                />
              )}
              <button
                onClick={onPaintClick}
                className={cn(
                  "flex flex-col items-center gap-0.5 md:gap-1 p-1 md:p-1.5 transition-all group hover:translate-y-0.5",
                )}
              >
                <div
                  className={cn(
                    "p-1 md:p-1.5 border-[2px] border-black transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] group-hover:shadow-none",
                    isPaintActive
                      ? "bg-[#FFD93D] text-black"
                      : "bg-[#FFFDF5] text-black group-hover:bg-[#FFD93D]",
                  )}
                >
                  <PenTool className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black text-black uppercase">Draw</span>
              </button>
              <button
                onClick={toggleSharedMedia}
                className={cn(
                  "flex flex-col items-center gap-0.5 md:gap-1 p-1 md:p-1.5 transition-all group hover:translate-y-0.5",
                )}
              >
                <div
                  className={cn(
                    "p-1 md:p-1.5 border-[2px] border-black transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] group-hover:shadow-none",
                    sharedMediaOpen
                      ? "bg-[#C4B5FD] text-black"
                      : "bg-[#FFFDF5] text-black group-hover:bg-[#C4B5FD]",
                  )}
                >
                  <Eye className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black text-black uppercase">View</span>
              </button>
              <button className="flex flex-col items-center gap-0.5 md:gap-1 p-1 md:p-1.5 transition-all group hover:translate-y-0.5">
                <div className="p-1 md:p-1.5 border-[2px] border-black bg-[#FFFDF5] group-hover:bg-[#FFD93D] transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] group-hover:shadow-none">
                  <MoreHorizontal className="w-3 h-3 md:w-3.5 md:h-3.5 text-black font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black text-black uppercase">More</span>
              </button>
            </div>
          </div>
        )}

        {/* Popover for Shared Media */}
        {sharedMediaOpen && (
          <div
            className={cn(
              "absolute w-[320px] md:w-[360px] h-auto flex flex-col bg-white border-[3px] md:border-[4px] border-black rounded-xl md:rounded-2xl shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[3px_3px_0_0_rgba(0,0,0,1)] overflow-hidden z-[1001]",
              isAnimatingOut ? "animate-popover-out" : "animate-popover-in",
              popoverPosition === "right"
                ? "left-full ml-4 md:ml-6"
                : "right-full mr-4 md:mr-6",
              verticalAlign === "bottom" ? "bottom-0" : "top-0",
            )}
          >
            <div className="flex items-center justify-between p-3 md:p-3.5 border-b-[3px] md:border-b-[4px] border-black bg-[#FFE500]">
              <div className="flex items-center gap-2 md:gap-3">
                <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black bg-white">
                  <ImageIcon className="w-4 h-4 md:w-5 md:h-5 text-black font-bold" />
                </div>
                <h3 className="font-black text-black uppercase text-xs md:text-sm">
                  ADAM'S VIEW
                </h3>
                <span
                  className={cn(
                    "px-2 md:px-3 py-0.5 md:py-1 text-[9px] md:text-[10px] font-black uppercase tracking-wider border-[2px] md:border-[3px] border-black",
                    {
                      "bg-[#ADFF2F] text-black":
                        mediaMixerStatus.isConnected && !mediaMixerStatus.error,
                      "bg-[#FF006E] text-white":
                        !!mediaMixerStatus.error,
                      "bg-white text-black":
                        !mediaMixerStatus.isConnected &&
                        !mediaMixerStatus.error,
                    },
                  )}
                >
                  {mediaMixerStatus.error
                    ? "OFF"
                    : mediaMixerStatus.isConnected
                      ? "LIVE"
                      : "..."}
                </span>
              </div>
              <button
                onClick={toggleSharedMedia}
                className="w-8 h-8 md:w-9 md:h-9 flex items-center justify-center border-[2px] md:border-[3px] border-black bg-white hover:bg-[#FF006E] text-black hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
              >
                <X className="w-4 h-4 md:w-5 md:h-5 font-bold" />
              </button>
            </div>
            <div className="flex-1 h-auto w-full">
              <MediaMixerDisplay
                socket={videoSocket}
                renderCanvasRef={renderCanvasRef}
                onStatusChange={setMediaMixerStatus}
                isCameraEnabled={cameraEnabled}
                isScreenShareEnabled={screenEnabled}
                isCanvasEnabled={isPaintActive}
              />
            </div>
          </div>
        )}
      </div>
    </Draggable>
  );
}
export default memo(FloatingControlPanel);

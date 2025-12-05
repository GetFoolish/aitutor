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
import { AudioRecorder } from "../../lib/audio-recorder";
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";
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

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

export type FloatingControlPanelProps = {
  videoRef: RefObject<HTMLVideoElement>;
  renderCanvasRef: ((canvas: HTMLCanvasElement | null) => void) | RefObject<HTMLCanvasElement>;
  supportsVideo: boolean;
  onVideoStreamChange?: (stream: MediaStream | null) => void;
  onMixerStreamChange?: (stream: MediaStream | null) => void;
  enableEditingSettings?: boolean;
  onPaintClick: () => void;
  isPaintActive: boolean;
  // Camera/screen control props (from parent)
  cameraEnabled: boolean;
  screenEnabled: boolean;
  onToggleCamera: (enabled: boolean) => void;
  onToggleScreen: (enabled: boolean) => void;
  // MediaMixer canvas ref for display
  mediaMixerCanvasRef: RefObject<HTMLCanvasElement>;
};

function FloatingControlPanel({
  videoRef,
  renderCanvasRef,
  supportsVideo,
  enableEditingSettings,
  onPaintClick,
  isPaintActive,
  cameraEnabled,
  screenEnabled,
  onToggleCamera,
  onToggleScreen,
  mediaMixerCanvasRef,
}: FloatingControlPanelProps) {
  const { client, connected, connect, disconnect, interruptAudio } = useLiveAPIContext();
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
  }>({ isConnected: true, error: null }); // Default to connected since it's frontend-based now
  const turnCompleteRef = useRef(false);

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

  // Record conversation turns for TeachingAssistant
  useEffect(() => {
    const onTurnComplete = () => {
      turnCompleteRef.current = true;
      
      if (connected) {
        const token = jwtUtils.getToken();
        if (token) {
          apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`).catch((error) => {
            console.error('Failed to record conversation turn:', error);
          });
        }
      }
    };

    const onInterrupted = () => {
      turnCompleteRef.current = true;
      
      if (connected) {
        const token = jwtUtils.getToken();
        if (token) {
          apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`).catch((error) => {
            console.error('Failed to record conversation turn:', error);
          });
        }
      }
    };

    client.on('turncomplete', onTurnComplete);
    client.on('interrupted', onInterrupted);

    return () => {
      client.off('turncomplete', onTurnComplete);
      client.off('interrupted', onInterrupted);
    };
  }, [client, connected]);

  // Video handling - capture full MediaMixer canvas and send to tutor as JPEG
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId = -1;

    function sendVideoFrame() {
      const canvas = mediaMixerCanvasRef.current;

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
  }, [connected, activeVideoStream, client, videoRef, mediaMixerCanvasRef]);

  const handleConnect = useCallback(async () => {
    if (connected) {
      // Handle disconnect with TeachingAssistant session end
      try {
        interruptAudio();
        
        await new Promise((resolve) => setTimeout(resolve, 300));

        const token = jwtUtils.getToken();
        if (token) {
          const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/end`, { interrupt_audio: true });

          if (response.ok) {
            const data = await response.json();
            if (data.prompt && client.status === 'connected') {
              const goodbyeTurnComplete = { current: false };
              const goodbyeAudioReceived = { current: false };
              let lastAudioTime = 0;
              
              const onAudio = () => {
                goodbyeAudioReceived.current = true;
                lastAudioTime = Date.now();
              };
              
              const onTurnComplete = () => {
                if (goodbyeAudioReceived.current) {
                  goodbyeTurnComplete.current = true;
                }
              };
              
              client.on('audio', onAudio);
              client.on('turncomplete', onTurnComplete);
              
              client.send({ text: data.prompt }, true);
              
              const maxWaitTime = 30000;
              const startTime = Date.now();
              const audioSilenceTimeout = 5000;
              
              while (!goodbyeTurnComplete.current && (Date.now() - startTime) < maxWaitTime) {
                await new Promise((resolve) => setTimeout(resolve, 100));
                
                if (goodbyeAudioReceived.current && lastAudioTime > 0) {
                  const timeSinceLastAudio = Date.now() - lastAudioTime;
                  if (timeSinceLastAudio > audioSilenceTimeout && goodbyeTurnComplete.current) {
                    break;
                  }
                }
              }
              
              if (goodbyeAudioReceived.current) {
                await new Promise((resolve) => setTimeout(resolve, 1500));
              }
              
              client.off('audio', onAudio);
              client.off('turncomplete', onTurnComplete);
            }
          }
        }
      } catch (error) {
        console.error('Failed to get goodbye from TeachingAssistant:', error);
      }

      disconnect();
    } else {
      // Handle connect with TeachingAssistant session start
      let setupCompleteReceived = false;
      let setupCompleteResolver: (() => void) | null = null;
      
      const onSetupComplete = () => {
        setupCompleteReceived = true;
        if (setupCompleteResolver) {
          setupCompleteResolver();
          setupCompleteResolver = null;
        }
        client.off('setupcomplete', onSetupComplete);
      };
      client.on('setupcomplete', onSetupComplete);
      
      await connect();
      
      // Wait for connection to be established
      const waitForConnection = () => {
        return new Promise<void>((resolve) => {
          if (client.status === 'connected') {
            resolve();
            return;
          }
          const checkConnection = () => {
            if (client.status === 'connected') {
              client.off('open', checkConnection);
              resolve();
            }
          };
          client.on('open', checkConnection);
        });
      };

      // Wait for setupComplete with timeout fallback
      const waitForSetupComplete = () => {
        return new Promise<void>((resolve) => {
          if (setupCompleteReceived) {
            resolve();
            return;
          }
          
          setupCompleteResolver = resolve;
          
          setTimeout(() => {
            if (setupCompleteResolver === resolve) {
              setupCompleteResolver = null;
              resolve();
            }
          }, 2000);
        });
      };

      try {
        await waitForConnection();
        await waitForSetupComplete();
        await new Promise((resolve) => setTimeout(resolve, 500));
        
        const token = jwtUtils.getToken();
        if (!token) {
          console.error('No authentication token for TeachingAssistant session start');
          return;
        }

        const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/start`);

        if (response.ok) {
          const data = await response.json();
          if (data.prompt && client.status === 'connected') {
            client.send({ text: data.prompt });
          }
        }
      } catch (error) {
        console.error('Failed to get greeting from TeachingAssistant:', error);
      } finally {
        client.off('setupcomplete', onSetupComplete);
        setupCompleteResolver = null;
      }
    }
  }, [connected, connect, disconnect, client, interruptAudio]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [hasInitialized, setHasInitialized] = useState(false);

  // Initialize position on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      setPosition({ x: window.innerWidth - 380, y: 96 });
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
        {/* Hidden canvas for MediaMixer - will be set by parent */}
        <canvas
          ref={(canvas) => {
            if (typeof renderCanvasRef === 'function') {
              renderCanvasRef(canvas);
            } else if (renderCanvasRef && 'current' in renderCanvasRef) {
              // For RefObject, we need to cast it as mutable
              (renderCanvasRef as React.MutableRefObject<HTMLCanvasElement | null>).current = canvas;
            }
          }}
          width={1280}
          height={2160}
          style={{ display: 'none' }}
        />
        
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
                onClick={() => onToggleCamera(!cameraEnabled)}
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
                onClick={() => onToggleScreen(!screenEnabled)}
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
                  <span className="text-[9px] md:text-[10px] font-black text-black uppercase tracking-wide">
                    Microphone
                  </span>
                  <select
                    className="bg-transparent border-none text-[9px] md:text-[10px] text-black outline-none cursor-pointer w-[100px] md:w-[120px] truncate p-0 font-bold uppercase"
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
                        className="bg-[#FFFDF5] text-black"
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
                  "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                  !muted
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] text-black",
                )}
              >
                {muted ? "Unmute" : "Mute"}
              </button>
            </div>

            {/* Camera Control */}
            {supportsVideo && (
              <div
                onClick={() => onToggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                  cameraEnabled
                    ? "bg-[#C4B5FD]"
                    : "bg-[#FFFDF5]",
                )}
              >
                <div className="flex items-center gap-1.5 md:gap-2">
                  <div
                    className={cn(
                      "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black transition-colors",
                      cameraEnabled
                        ? "bg-[#FFFDF5] text-black"
                        : "bg-[#FFFDF5] text-black",
                    )}
                  >
                    {cameraEnabled ? (
                      <Video className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <VideoOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[9px] md:text-[10px] font-black text-black uppercase tracking-wide">
                    Camera
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleCamera(!cameraEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                    cameraEnabled
                      ? "bg-[#FFFDF5] text-black"
                      : "bg-[#C4B5FD] text-black",
                  )}
                >
                  {cameraEnabled ? "Off" : "On"}
                </button>
              </div>
            )}

            {/* Screen Share Control */}
            {supportsVideo && (
              <div
                onClick={() => onToggleScreen(!screenEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
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
                        ? "bg-[#FFFDF5] text-black"
                        : "bg-[#FFFDF5] text-black",
                    )}
                  >
                    {screenEnabled ? (
                      <Monitor className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <MonitorOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[9px] md:text-[10px] font-black text-black uppercase tracking-wide">
                    Screen Share
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleScreen(!screenEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                    screenEnabled
                      ? "bg-[#FFFDF5] text-black"
                      : "bg-[#FFD93D] text-black",
                  )}
                >
                  {screenEnabled ? "Stop" : "Share"}
                </button>
              </div>
            )}

            {/* Main Action Button */}
            <button
              onClick={handleConnect}
              className={cn(
                "w-full py-2.5 md:py-3 font-black text-white transition-all transform active:translate-x-1 active:translate-y-1 active:shadow-none flex items-center justify-center gap-2 mt-1 border-[2px] md:border-[3px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] uppercase text-[10px] md:text-xs",
                connected
                  ? "bg-[#FF6B6B] hover:bg-[#FF6B6B]"
                  : "bg-[#4ADE80] hover:bg-[#4ADE80]",
              )}
            >
              {connected ? (
                <>
                  <div className="w-3 h-3 bg-white border-2 border-black" />
                  End Session
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 md:w-5 md:h-5" />
                  Start Session
                </>
              )}
            </button>

            {/* Bottom Actions */}
            <div className="grid grid-cols-4 gap-1.5 md:gap-2 pt-2 md:pt-3 border-t-[2px] border-black">
              {enableEditingSettings && (
                <SettingsDialog
                  className="!h-auto !block"
                  trigger={
                    <button className="flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black bg-[#FFFDF5] hover:bg-[#FF6B6B] text-black hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none group">
                      <div className="p-1 border-[2px] border-black bg-[#FFFDF5] group-hover:bg-[#FF6B6B] transition-colors">
                        <Settings className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                      </div>
                      <span className="text-[8px] md:text-[9px] font-black uppercase">Settings</span>
                    </button>
                  }
                />
              )}
              <button
                onClick={onPaintClick}
                className={cn(
                  "flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none group",
                  isPaintActive
                    ? "bg-[#FFD93D] text-black"
                    : "bg-[#FFFDF5] text-black hover:bg-[#FFD93D]",
                )}
              >
                <div
                  className={cn(
                    "p-1 border-[2px] border-black transition-colors",
                    isPaintActive
                      ? "bg-[#FFFDF5] text-black"
                      : "bg-[#FFFDF5] group-hover:bg-[#FFD93D]",
                  )}
                >
                  <PenTool className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[8px] md:text-[9px] font-black uppercase">Canvas</span>
              </button>
              <button
                onClick={toggleSharedMedia}
                className={cn(
                  "flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none group",
                  sharedMediaOpen
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] text-black hover:bg-[#C4B5FD]",
                )}
              >
                <div
                  className={cn(
                    "p-1 border-[2px] border-black transition-colors",
                    sharedMediaOpen
                      ? "bg-[#FFFDF5] text-black"
                      : "bg-[#FFFDF5] group-hover:bg-[#C4B5FD]",
                  )}
                >
                  <Eye className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[8px] md:text-[9px] font-black uppercase">View</span>
              </button>
              <button className="flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black bg-[#FFFDF5] hover:bg-[#C4B5FD] text-black transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none group">
                <div className="p-1 border-[2px] border-black bg-[#FFFDF5] group-hover:bg-[#C4B5FD] transition-colors">
                  <MoreHorizontal className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[8px] md:text-[9px] font-black uppercase">More</span>
              </button>
            </div>
          </div>
        )}

        {/* Popover for Shared Media */}
        {sharedMediaOpen && (
          <div
            className={cn(
              "absolute w-[320px] md:w-[360px] h-auto flex flex-col bg-white dark:bg-[#000000] border-[3px] md:border-[4px] border-black dark:border-white rounded-xl md:rounded-2xl shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] overflow-hidden z-[1001]",
              isAnimatingOut ? "animate-popover-out" : "animate-popover-in",
              popoverPosition === "right"
                ? "left-full ml-4 md:ml-6"
                : "right-full mr-4 md:mr-6",
              verticalAlign === "bottom" ? "bottom-0" : "top-0",
            )}
          >
            <div className="flex items-center justify-between p-3 md:p-3.5 border-b-[3px] md:border-b-[4px] border-black dark:border-white bg-[#FFE500]">
              <div className="flex items-center gap-2 md:gap-3">
                <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-[#000000]">
                  <ImageIcon className="w-4 h-4 md:w-5 md:h-5 text-black dark:text-white font-bold" />
                </div>
                <h3 className="font-black text-black dark:text-white uppercase text-xs md:text-sm">
                  ADAM'S VIEW
                </h3>
                <span
                  className={cn(
                    "px-2 md:px-3 py-0.5 md:py-1 text-[9px] md:text-[10px] font-black uppercase tracking-wider border-[2px] md:border-[3px] border-black dark:border-white",
                    {
                      "bg-[#ADFF2F] text-black":
                        mediaMixerStatus.isConnected && !mediaMixerStatus.error,
                      "bg-[#FF006E] text-white":
                        !!mediaMixerStatus.error,
                      "bg-white dark:bg-[#000000] text-black dark:text-white":
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
                className="w-8 h-8 md:w-9 md:h-9 flex items-center justify-center border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-[#000000] hover:bg-[#FF006E] text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
              >
                <X className="w-4 h-4 md:w-5 md:h-5 font-bold" />
              </button>
            </div>
            <div className="flex-1 h-auto w-full">
              <MediaMixerDisplay
                canvasRef={mediaMixerCanvasRef}
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

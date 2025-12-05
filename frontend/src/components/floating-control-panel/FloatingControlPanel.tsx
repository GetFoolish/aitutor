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
        "fixed z-[1000] bg-white/90 dark:bg-neutral-900/90 backdrop-blur-xl border border-neutral-200 dark:border-white/10 shadow-2xl",
        // GPU acceleration hints
        "will-change-transform transform-gpu",
        // Only apply transitions when NOT dragging to prevent layout thrashing
        !isDragging &&
        "transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1)",
        isCollapsed
          ? "w-[64px] rounded-full py-4 px-2"
          : "w-[340px] rounded-3xl p-5",
        // Ensure origin is top-left for controlled positioning
        "top-0 left-0",
        // Hover effect
        !isDragging &&
        "hover:border-neutral-300 dark:hover:border-white/20 hover:shadow-3xl",
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
            "drag-handle cursor-grab active:cursor-grabbing flex items-center mb-5",
            !isDragging && "transition-all duration-200 ease-out",
            isCollapsed ? "justify-center mb-3" : "justify-between",
          )}
        >
          {!isCollapsed && (
            <div className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <span className="material-symbols-outlined text-lg text-blue-500 dark:text-blue-400">
                  smart_toy
                </span>
              </div>
              <div>
                <div className="font-semibold text-sm text-neutral-900 dark:text-white leading-none mb-0.5">
                  AI Tutor
                </div>
                <div className="text-[10px] text-neutral-500 dark:text-neutral-400 font-medium uppercase tracking-wider">
                  Control Center
                </div>
              </div>
            </div>
          )}
          <button
            onClick={handleCollapse}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-neutral-100 dark:hover:bg-white/10 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            {isCollapsed ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronUp className="w-5 h-5" />
            )}
          </button>
        </div>

        {isCollapsed ? (
          // COLLAPSED VIEW
          <div className="flex flex-col items-center gap-3">
            <button
              onClick={handleCollapse}
              className="w-10 h-10 rounded-full bg-neutral-100 dark:bg-white/5 hover:bg-neutral-200 dark:hover:bg-white/10 flex items-center justify-center text-neutral-900 dark:text-white transition-colors"
              title="Expand"
            >
              <Home className="w-5 h-5" />
            </button>

            {/* Start/End Session Button */}
            <button
              onClick={handleConnect}
              className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center transition-all transform active:scale-95 shadow-lg relative group",
                connected
                  ? "bg-red-500 hover:bg-red-600 text-white shadow-red-500/30"
                  : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/30",
              )}
              title={connected ? "End Session" : "Start Session"}
            >
              {connected ? (
                <div className="w-4 h-4 rounded-sm bg-white" />
              ) : (
                <PlayCircle className="w-7 h-7" />
              )}
              {connected && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 border-2 border-white dark:border-neutral-900 rounded-full animate-pulse" />
              )}
            </button>

            <div className="w-8 h-[1px] bg-neutral-200 dark:bg-white/10 my-1" />

            <button
              onClick={handleMute}
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                muted
                  ? "bg-red-500/10 text-red-500 dark:bg-red-500/20 dark:text-red-400"
                  : "bg-neutral-100 dark:bg-white/5 text-neutral-700 dark:text-white hover:bg-neutral-200 dark:hover:bg-white/10",
              )}
              title={muted ? "Unmute" : "Mute"}
            >
              {muted ? (
                <MicOff className="w-5 h-5" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </button>

            {supportsVideo && (
              <button
                onClick={() => onToggleCamera(!cameraEnabled)}
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                  cameraEnabled
                    ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                    : "bg-neutral-100 dark:bg-white/5 text-neutral-700 dark:text-white hover:bg-neutral-200 dark:hover:bg-white/10",
                )}
                title="Toggle Camera"
              >
                {cameraEnabled ? (
                  <Video className="w-5 h-5" />
                ) : (
                  <VideoOff className="w-5 h-5" />
                )}
              </button>
            )}

            {supportsVideo && (
              <button
                onClick={() => onToggleScreen(!screenEnabled)}
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                  screenEnabled
                    ? "bg-green-500/10 text-green-500 dark:bg-green-500/20 dark:text-green-400"
                    : "bg-neutral-100 dark:bg-white/5 text-neutral-700 dark:text-white hover:bg-neutral-200 dark:hover:bg-white/10",
                )}
                title="Share Screen"
              >
                {screenEnabled ? (
                  <Monitor className="w-5 h-5" />
                ) : (
                  <MonitorOff className="w-5 h-5" />
                )}
              </button>
            )}

            <div className="w-8 h-[1px] bg-neutral-200 dark:bg-white/10 my-1" />

            {enableEditingSettings && (
              <SettingsDialog
                className="!h-auto !block"
                trigger={
                  <button className="w-10 h-10 rounded-full bg-neutral-100 dark:bg-white/5 hover:bg-neutral-200 dark:hover:bg-white/10 flex items-center justify-center text-neutral-700 dark:text-white transition-colors">
                    <Settings className="w-5 h-5" />
                  </button>
                }
              />
            )}

            <button
              onClick={onPaintClick}
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                isPaintActive
                  ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                  : "bg-neutral-100 dark:bg-white/5 text-neutral-700 dark:text-white hover:bg-neutral-200 dark:hover:bg-white/10",
              )}
              title="Canvas"
            >
              <PenTool className="w-5 h-5" />
            </button>

            <button
              onClick={toggleSharedMedia}
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                sharedMediaOpen
                  ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                  : "bg-neutral-100 dark:bg-white/5 text-neutral-700 dark:text-white hover:bg-neutral-200 dark:hover:bg-white/10",
              )}
              title="View"
            >
              <Eye className="w-5 h-5" />
            </button>

            <div
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-[10px] font-mono font-bold mt-2 transition-colors border",
                connected
                  ? "bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400"
                  : "bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-white/5 text-neutral-500",
              )}
            >
              {connected ? formatTime(sessionTime) : "--:--"}
            </div>
          </div>
        ) : (
          // EXPANDED VIEW
          <div className="flex flex-col gap-3">
            {/* Audio Control */}
            <div
              onClick={handleMute}
              className={cn(
                "flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-200 group cursor-pointer",
                !muted
                  ? "bg-gradient-to-r from-blue-500/5 to-blue-600/5 border-blue-500/20 hover:border-blue-500/30"
                  : "bg-neutral-50 dark:bg-neutral-800/50 border-neutral-200 dark:border-white/5 hover:border-neutral-300 dark:hover:border-white/10",
              )}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full transition-colors",
                    !muted
                      ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                      : "bg-neutral-200 dark:bg-white/5 text-neutral-500 dark:text-neutral-400",
                  )}
                >
                  {muted ? (
                    <MicOff className="w-4 h-4" />
                  ) : (
                    <Mic className="w-4 h-4" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                    Microphone
                  </span>
                  <select
                    className="bg-transparent border-none text-sm text-neutral-900 dark:text-white outline-none cursor-pointer w-[140px] truncate p-0 font-medium"
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
                        className="bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white"
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
                  "text-xs font-semibold px-3 py-1.5 rounded-full transition-all",
                  !muted
                    ? "bg-blue-500 text-white hover:bg-blue-600 shadow-lg shadow-blue-500/20"
                    : "bg-neutral-200 dark:bg-white/10 text-neutral-700 dark:text-white hover:bg-neutral-300 dark:hover:bg-white/20",
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
                  "flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer",
                  cameraEnabled
                    ? "bg-gradient-to-r from-purple-500/5 to-purple-600/5 border-purple-500/20 hover:border-purple-500/30"
                    : "bg-neutral-50 dark:bg-neutral-800/50 border-neutral-200 dark:border-white/5 hover:border-neutral-300 dark:hover:border-white/10",
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "flex items-center justify-center w-8 h-8 rounded-full transition-colors",
                      cameraEnabled
                        ? "bg-purple-500/10 text-purple-500 dark:bg-purple-500/20 dark:text-purple-400"
                        : "bg-neutral-200 dark:bg-white/5 text-neutral-500 dark:text-neutral-400",
                    )}
                  >
                    {cameraEnabled ? (
                      <Video className="w-4 h-4" />
                    ) : (
                      <VideoOff className="w-4 h-4" />
                    )}
                  </div>
                  <span className="text-sm font-medium text-neutral-900 dark:text-white">
                    Camera
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleCamera(!cameraEnabled);
                  }}
                  className={cn(
                    "text-xs font-semibold px-3 py-1.5 rounded-full transition-all",
                    cameraEnabled
                      ? "bg-purple-500 text-white hover:bg-purple-600 shadow-lg shadow-purple-500/20"
                      : "bg-neutral-200 dark:bg-white/10 text-neutral-700 dark:text-white hover:bg-neutral-300 dark:hover:bg-white/20",
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
                  "flex items-center justify-between p-3.5 rounded-2xl border transition-all duration-200 cursor-pointer",
                  screenEnabled
                    ? "bg-gradient-to-r from-green-500/5 to-green-600/5 border-green-500/20 hover:border-green-500/30"
                    : "bg-neutral-50 dark:bg-neutral-800/50 border-neutral-200 dark:border-white/5 hover:border-neutral-300 dark:hover:border-white/10",
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "flex items-center justify-center w-8 h-8 rounded-full transition-colors",
                      screenEnabled
                        ? "bg-green-500/10 text-green-500 dark:bg-green-500/20 dark:text-green-400"
                        : "bg-neutral-200 dark:bg-white/5 text-neutral-500 dark:text-neutral-400",
                    )}
                  >
                    {screenEnabled ? (
                      <Monitor className="w-4 h-4" />
                    ) : (
                      <MonitorOff className="w-4 h-4" />
                    )}
                  </div>
                  <span className="text-sm font-medium text-neutral-900 dark:text-white">
                    Screen Share
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleScreen(!screenEnabled);
                  }}
                  className={cn(
                    "text-xs font-semibold px-3 py-1.5 rounded-full transition-all",
                    screenEnabled
                      ? "bg-green-500 text-white hover:bg-green-600 shadow-lg shadow-green-500/20"
                      : "bg-neutral-200 dark:bg-white/10 text-neutral-700 dark:text-white hover:bg-neutral-300 dark:hover:bg-white/20",
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
                "w-full py-3.5 rounded-xl font-bold text-white shadow-lg transition-all transform active:scale-[0.98] flex items-center justify-center gap-2 mt-1",
                connected
                  ? "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-red-500/25"
                  : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-blue-500/25",
              )}
            >
              {connected ? (
                <>
                  <div className="w-3 h-3 rounded-sm bg-white" />
                  End Session
                </>
              ) : (
                <>
                  <PlayCircle className="w-5 h-5" />
                  Start Session
                </>
              )}
            </button>

            {/* Bottom Actions */}
            <div className="grid grid-cols-4 gap-2 pt-3 border-t border-neutral-200 dark:border-white/10">
              {enableEditingSettings && (
                <SettingsDialog
                  className="!h-auto !block"
                  trigger={
                    <button className="flex flex-col items-center gap-1.5 p-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-white/5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors group">
                      <div className="p-1.5 rounded-lg bg-neutral-100 dark:bg-white/5 group-hover:bg-neutral-200 dark:group-hover:bg-white/10 transition-colors">
                        <Settings className="w-4 h-4" />
                      </div>
                      <span className="text-[10px] font-medium">Settings</span>
                    </button>
                  }
                />
              )}
              <button
                onClick={onPaintClick}
                className={cn(
                  "flex flex-col items-center gap-1.5 p-2 rounded-xl transition-colors group",
                  isPaintActive
                    ? "text-blue-500 dark:text-blue-400"
                    : "hover:bg-neutral-100 dark:hover:bg-white/5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white",
                )}
              >
                <div
                  className={cn(
                    "p-1.5 rounded-lg transition-colors",
                    isPaintActive
                      ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                      : "bg-neutral-100 dark:bg-white/5 group-hover:bg-neutral-200 dark:group-hover:bg-white/10",
                  )}
                >
                  <PenTool className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-medium">Canvas</span>
              </button>
              <button
                onClick={toggleSharedMedia}
                className={cn(
                  "flex flex-col items-center gap-1.5 p-2 rounded-xl transition-colors group",
                  sharedMediaOpen
                    ? "text-blue-500 dark:text-blue-400"
                    : "hover:bg-neutral-100 dark:hover:bg-white/5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white",
                )}
              >
                <div
                  className={cn(
                    "p-1.5 rounded-lg transition-colors",
                    sharedMediaOpen
                      ? "bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400"
                      : "bg-neutral-100 dark:bg-white/5 group-hover:bg-neutral-200 dark:group-hover:bg-white/10",
                  )}
                >
                  <Eye className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-medium">View</span>
              </button>
              <button className="flex flex-col items-center gap-1.5 p-2 rounded-xl hover:bg-neutral-100 dark:hover:bg-white/5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors group">
                <div className="p-1.5 rounded-lg bg-neutral-100 dark:bg-white/5 group-hover:bg-neutral-200 dark:group-hover:bg-white/10 transition-colors">
                  <MoreHorizontal className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-medium">More</span>
              </button>
            </div>
          </div>
        )}

        {/* Popover for Shared Media */}
        {sharedMediaOpen && (
          <div
            className={cn(
              "absolute w-[360px] h-auto flex flex-col bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xl border border-neutral-200 dark:border-white/10 rounded-3xl shadow-2xl overflow-hidden z-[1001]",
              isAnimatingOut ? "animate-popover-out" : "animate-popover-in",
              popoverPosition === "right"
                ? "left-full ml-4"
                : "right-full mr-4",
              verticalAlign === "bottom" ? "bottom-0" : "top-0",
            )}
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-white/10 bg-neutral-50/50 dark:bg-white/5">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-blue-500 dark:text-blue-400" />
                <h3 className="font-semibold text-neutral-900 dark:text-white">
                  What Adam Can See
                </h3>
                <span
                  className={cn(
                    "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ml-2",
                    {
                      "bg-green-500/10 dark:bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/20 dark:border-green-500/30":
                        mediaMixerStatus.isConnected && !mediaMixerStatus.error,
                      "bg-red-500/10 dark:bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/20 dark:border-red-500/30":
                        !!mediaMixerStatus.error,
                      "bg-yellow-500/10 dark:bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/20 dark:border-yellow-500/30":
                        !mediaMixerStatus.isConnected &&
                        !mediaMixerStatus.error,
                    },
                  )}
                >
                  {mediaMixerStatus.error
                    ? "Offline"
                    : mediaMixerStatus.isConnected
                      ? "Live"
                      : "Connecting"}
                </span>
              </div>
              <button
                onClick={toggleSharedMedia}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-neutral-200 dark:hover:bg-white/10 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
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

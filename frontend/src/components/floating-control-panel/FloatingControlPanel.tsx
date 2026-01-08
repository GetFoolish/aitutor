import React, {
  memo,
  RefObject,
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import { motion, useDragControls } from "framer-motion";
import { useTutorContext, AudioRecorder } from "../../features/tutor";
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import cn from "classnames";
import MediaMixerDisplay from "../media-mixer-display/MediaMixerDisplay";
import { useTheme } from "../theme/theme-provier";
import { feedWebSocketService } from "../../services/feed-websocket-service";
import { instructionSSEService } from "../../services/instruction-sse-service";
import { LiveServerContent } from '@google/genai';

function extractTranscriptFromContent(content: LiveServerContent): string | null {
  const parts = content.modelTurn?.parts || [];
  const textParts = parts
    .filter((p: any) => p.text && p.text.trim().length > 0)
    .map((p: any) => p.text.trim());
  return textParts.length > 0 ? textParts.join(' ') : null;
}

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
  ToggleLeft,
  ToggleRight,
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
  cameraEnabled: boolean;
  screenEnabled: boolean;
  onToggleCamera: (enabled: boolean) => void;
  onToggleScreen: (enabled: boolean) => void;
  mediaMixerCanvasRef: RefObject<HTMLCanvasElement>;
  privacyMode: boolean;
  onTogglePrivacy: (enabled: boolean) => void;
  processedEdgesRef: RefObject<ImageData | null>;
  assessmentMode?: boolean;
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
  privacyMode,
  onTogglePrivacy,
  processedEdgesRef,
  assessmentMode = false,
}: FloatingControlPanelProps) {
  const { client, connected, connect, disconnect, interruptAudio } = useTutorContext();
  const { theme } = useTheme();
  const dragControls = useDragControls();
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
  const [popoverPosition, setPopoverPosition] = useState<"left" | "right">("right");
  const [mediaMixerStatus, setMediaMixerStatus] = useState<{
    isConnected: boolean;
    error: string | null;
  }>({ isConnected: true, error: null });
  const turnCompleteRef = useRef(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    const checkDarkMode = () => {
      if (theme === 'dark') {
        setIsDarkMode(true);
      } else if (theme === 'light') {
        setIsDarkMode(false);
      } else if (theme === 'system') {
        setIsDarkMode(document.documentElement.classList.contains('dark'));
      }
    };

    checkDarkMode();

    if (theme === 'system') {
      const observer = new MutationObserver(checkDarkMode);
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
      });

      return () => observer.disconnect();
    }
  }, [theme]);

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

  const userTranscriptBuffer = useRef('');
  const userTranscriptTimer = useRef<number | null>(null);
  const tutorTranscriptBuffer = useRef('');
  const tutorTranscriptTimer = useRef<number | null>(null);

  const isSentenceComplete = useCallback((text: string): boolean => {
    const trimmed = text.trim();
    return /[.!?;]$/.test(trimmed) && trimmed.length > 10;
  }, []);

  const flushUserTranscript = useCallback(() => {
    const text = userTranscriptBuffer.current.trim();
    if (text && connected) {
      feedWebSocketService.sendTranscript(text, 'user');
      userTranscriptBuffer.current = '';
    }
    if (userTranscriptTimer.current) {
      clearTimeout(userTranscriptTimer.current);
      userTranscriptTimer.current = null;
    }
  }, [connected]);

  const flushTutorTranscript = useCallback(() => {
    const text = tutorTranscriptBuffer.current.trim();
    if (text && connected) {
      feedWebSocketService.sendTranscript(text, 'tutor');
      tutorTranscriptBuffer.current = '';
    }
    if (tutorTranscriptTimer.current) {
      clearTimeout(tutorTranscriptTimer.current);
      tutorTranscriptTimer.current = null;
    }
  }, [connected]);

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

      feedWebSocketService.sendAudio(base64);
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

  useEffect(() => {
    const unsubscribe = instructionSSEService.onInstruction((instruction) => {
      if (client && client.status === "connected") {
        client.send({ text: instruction });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [client]);

  useEffect(() => {
    const onTurnComplete = () => {
      turnCompleteRef.current = true;
      
      if (connected) {
        const token = jwtUtils.getToken();
        if (token) {
          apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`).catch((error: any) => {
            if (!error.message?.includes('Failed to fetch') && !error.message?.includes('ERR_CONNECTION_REFUSED')) {
              console.error('Failed to record conversation turn:', error);
            }
          });
        }
      }
    };

    const onInterrupted = () => {
      turnCompleteRef.current = true;
      
      if (connected) {
        const token = jwtUtils.getToken();
        if (token) {
          apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`).catch((error: any) => {
            if (!error.message?.includes('Failed to fetch') && !error.message?.includes('ERR_CONNECTION_REFUSED')) {
              console.error('Failed to record conversation turn:', error);
            }
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

  useEffect(() => {
    const onContent = (content: any) => {
      if (!connected) return;

      const transcript = extractTranscriptFromContent(content);
      if (transcript) {
        feedWebSocketService.sendTranscript(transcript, 'tutor');
      }
    };

    client.on('content', onContent);

    return () => {
      client.off('content', onContent);
    };
  }, [client, connected]);

  useEffect(() => {
    const onInputTranscript = (data: TranscriptionData) => {
      if (!connected) return;

      if (data.text) {
        userTranscriptBuffer.current += data.text;

        if (isSentenceComplete(userTranscriptBuffer.current)) {
          flushUserTranscript();
        } else {
          if (userTranscriptTimer.current) {
            clearTimeout(userTranscriptTimer.current);
          }
          userTranscriptTimer.current = window.setTimeout(() => {
            flushUserTranscript();
          }, 3000);
        }
      }
    };

    client.on('inputTranscript', onInputTranscript);

    return () => {
      client.off('inputTranscript', onInputTranscript);
      if (userTranscriptTimer.current) {
        clearTimeout(userTranscriptTimer.current);
      }
      flushUserTranscript();
    };
  }, [client, connected, isSentenceComplete, flushUserTranscript]);

  useEffect(() => {
    const onOutputTranscript = (data: TranscriptionData) => {
      if (!connected) return;

      if (data.text) {
        tutorTranscriptBuffer.current += data.text;

        if (isSentenceComplete(tutorTranscriptBuffer.current)) {
          flushTutorTranscript();
        } else {
          if (tutorTranscriptTimer.current) {
            clearTimeout(tutorTranscriptTimer.current);
          }
          tutorTranscriptTimer.current = window.setTimeout(() => {
            flushTutorTranscript();
          }, 3000);
        }
      }
    };

    client.on('outputTranscript', onOutputTranscript);

    return () => {
      client.off('outputTranscript', onOutputTranscript);
      if (tutorTranscriptTimer.current) {
        clearTimeout(tutorTranscriptTimer.current);
      }
      flushTutorTranscript();
    };
  }, [client, connected, isSentenceComplete, flushTutorTranscript]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId: number | null = null;
    let rafId: number | null = null;
    let isRunning = false;

    function sendVideoFrame() {
      if (!connected || !isRunning) {
        return;
      }

      if (privacyMode && processedEdgesRef.current) {
        const edges = processedEdgesRef.current;
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = edges.width;
        tempCanvas.height = edges.height;
        const tempCtx = tempCanvas.getContext('2d');
        
        if (tempCtx) {
          tempCtx.putImageData(edges, 0, 0);
          const base64 = tempCanvas.toDataURL("image/jpeg", 1.0);
          const data = base64.slice(base64.indexOf(",") + 1, Infinity);
          
          client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);

          feedWebSocketService.sendMedia(data);
        }
      } else {
        const canvas = mediaMixerCanvasRef.current;
        if (canvas && canvas.width + canvas.height > 0) {
          const base64 = canvas.toDataURL("image/jpeg", 1.0);
          const data = base64.slice(base64.indexOf(",") + 1, Infinity);
          
          client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);

          feedWebSocketService.sendMedia(data);
        }
      }
      
      if (connected && isRunning) {
        timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
      }
    }
    
    if (connected && !isRunning) {
      isRunning = true;
      rafId = requestAnimationFrame(sendVideoFrame);
    }
    
    return () => {
      isRunning = false;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [connected, activeVideoStream, client, privacyMode, processedEdgesRef]);

  const handleConnect = useCallback(async () => {
    if (connected) {
      try {
        flushUserTranscript();
        flushTutorTranscript();

        interruptAudio();

        try {
          feedWebSocketService.disconnect();
        } catch (e) {}

        try {
          instructionSSEService.disconnect();
        } catch (e) {}

        await new Promise((resolve) => setTimeout(resolve, 300));

        const token = jwtUtils.getToken();
        if (token) {
          try {
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
          } catch (taError: any) {
            if (taError.message?.includes('Failed to fetch') || taError.message?.includes('ERR_CONNECTION_REFUSED')) {
              console.warn('TeachingAssistant service is not available during disconnect - continuing');
            } else {
              console.error('Failed to get goodbye from TeachingAssistant:', taError);
            }
          }
        }
      } catch (error) {
        console.error('Error during disconnect:', error);
      }

      disconnect();
    } else {
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

        try {
          const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/start`);

          if (response.ok) {
            const data = await response.json();

            try {
              await feedWebSocketService.connect();
            } catch (wsError) {
              console.warn('Failed to connect WebSocket feed service (optional):', wsError);
            }

            try {
              instructionSSEService.connect();
            } catch (sseError) {
              console.warn('Failed to connect SSE instruction service (optional):', sseError);
            }

            if (data.prompt && client.status === 'connected') {
              client.send({ text: data.prompt });
            }
          } else {
            console.warn(`TeachingAssistant service returned status ${response.status} - continuing without it`);
          }
        } catch (taError: any) {
          if (taError.message?.includes('Failed to fetch') || taError.message?.includes('ERR_CONNECTION_REFUSED')) {
            console.warn('TeachingAssistant service is not available - continuing without advanced features');
          } else {
            console.error('Failed to connect to TeachingAssistant:', taError);
          }
        }
      } catch (error) {
        console.error('Failed to get greeting from TeachingAssistant:', error);
      } finally {
        client.off('setupcomplete', onSetupComplete);
        setupCompleteResolver = null;
      }
    }
  }, [connected, connect, disconnect, client, interruptAudio, flushUserTranscript, flushTutorTranscript]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  const initialPosition = useMemo(() => {
    if (typeof window === "undefined") return { x: 0, y: 0 };
    return { x: window.innerWidth - 380, y: 96 };
  }, []);

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
      updatePopoverPosition();
      setSharedMediaOpen(true);
      setIsAnimatingOut(false);
    } else {
      setIsAnimatingOut(true);
      setTimeout(() => {
        setSharedMediaOpen(false);
        setIsAnimatingOut(false);
      }, 200);
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  const handleCollapse = useCallback(() => {
    setIsCollapsed(!isCollapsed);
  }, [isCollapsed]);

  const handleMute = useCallback(() => {
    setMuted(!muted);
  }, [muted]);

  const handleDragEnd = useCallback(() => {
    if (sharedMediaOpen) {
      updatePopoverPosition();
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  const panelClasses = useMemo(
    () =>
      cn(
        "fixed z-[1000] bg-[#FFFDF5] dark:bg-[#000000] border-[2px] md:border-[3px] border-black dark:border-white rounded-lg md:rounded-xl",
        isCollapsed
          ? "w-[50px] md:w-[55px] py-2 md:py-2.5 px-1 md:px-1.5 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)]"
          : "w-[220px] md:w-[250px] p-2.5 md:p-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)]",
        "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)] md:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_8px_8px_20px_rgba(0,0,0,0.18),_16px_16px_40px_rgba(0,0,0,0.12)]",
      ),
    [isCollapsed],
  );

  return (
    <motion.div
      ref={panelRef}
      className={panelClasses}
      drag
      dragControls={dragControls}
      dragListener={false}
      dragMomentum={false}
      dragElastic={0}
      dragConstraints={{
        left: 0,
        top: 0,
        right: typeof window !== "undefined" ? window.innerWidth - (isCollapsed ? 55 : 250) : 1000,
        bottom: typeof window !== "undefined" ? window.innerHeight - 100 : 800,
      }}
      onDragEnd={handleDragEnd}
      initial={initialPosition}
      whileDrag={{ 
        cursor: "grabbing",
        scale: 1.0,
      }}
      dragTransition={{
        bounceStiffness: 600,
        bounceDamping: 20,
        power: 0.1,
      }}
      style={{
        left: 0,
        top: 0,
        x: initialPosition.x,
        y: initialPosition.y,
      }}
    >
        <canvas
          ref={(canvas) => {
            if (typeof renderCanvasRef === 'function') {
              renderCanvasRef(canvas);
            } else if (renderCanvasRef && 'current' in renderCanvasRef) {
              (renderCanvasRef as React.MutableRefObject<HTMLCanvasElement | null>).current = canvas;
            }
          }}
          width={1280}
          height={2160}
          style={{ display: 'none' }}
        />
        
        <div
          className={cn(
            "cursor-grab active:cursor-grabbing flex items-center mb-1.5 md:mb-2",
            isCollapsed ? "justify-center mb-1 md:mb-1.5" : "justify-between",
          )}
          onPointerDown={(e) => dragControls.start(e)}
        >
          {!isCollapsed && (
            <div className="flex items-center gap-1.5 md:gap-2">
              <img 
                src={isDarkMode ? '/logo_white.png' : '/logo.png'} 
                alt="teachr" 
                className="h-6 md:h-7 w-auto"
              />
            </div>
          )}
          <button
            onClick={handleCollapse}
            className="w-5 h-5 md:w-6 md:h-6 flex items-center justify-center border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] text-black dark:text-white hover:translate-x-0.5 hover:translate-y-0.5 transition-all duration-100"
          >
            {isCollapsed ? (
              <ChevronDown className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
            ) : (
              <ChevronUp className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
            )}
          </button>
        </div>

        {isCollapsed ? (
          <div className="flex flex-col items-center gap-1.5 md:gap-2">
            <button
              onClick={handleCollapse}
              className="w-8 h-8 md:w-9 md:h-9 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] flex items-center justify-center text-black dark:text-white transition-all hover:translate-x-0.5 hover:translate-y-0.5 duration-100 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none"
              title="Expand"
            >
              <Home className="w-4 h-4 font-bold" />
            </button>

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

            <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />

            <button
              onClick={handleMute}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                muted
                  ? "bg-[#FF6B6B] text-white"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
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
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
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

            {supportsVideo && cameraEnabled && (
              <button
                onClick={() => onTogglePrivacy(!privacyMode)}
                className={cn(
                  "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black dark:border-white flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                  privacyMode
                    ? "bg-[#C4B5FD] dark:bg-[#C4B5FD] text-black dark:text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD] dark:hover:bg-[#C4B5FD] dark:hover:text-black",
                )}
                title={privacyMode ? "Disable Privacy Mode" : "Enable Privacy Mode"}
              >
                {privacyMode ? (
                  <ToggleRight className="w-3.5 h-3.5 font-bold" />
                ) : (
                  <ToggleLeft className="w-3.5 h-3.5 font-bold" />
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
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
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

            <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />

            {enableEditingSettings && (
              <SettingsDialog
                className="!h-auto !block"
                trigger={
                  <button className="w-8 h-8 md:w-9 md:h-9 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FF6B6B] flex items-center justify-center text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100">
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
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
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
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD] border-black dark:border-white",
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
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white border-black dark:border-white",
              )}
            >
              {connected ? formatTime(sessionTime) : "--:--"}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 md:gap-2">
            <div
              onClick={handleMute}
              className={cn(
                "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 group cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                !muted
                  ? "bg-[#FFFDF5] dark:bg-[#000000]"
                  : "bg-[#FF6B6B]",
              )}
            >
              <div className="flex items-center gap-1.5 md:gap-2 min-w-0 flex-1 pr-2 md:pr-3">
                <div
                  className={cn(
                    "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black dark:border-white transition-colors flex-shrink-0",
                    !muted
                      ? "bg-[#C4B5FD] text-black"
                      : "bg-white dark:bg-[#000000] text-black dark:text-white",
                  )}
                >
                  {muted ? (
                    <MicOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                  ) : (
                    <Mic className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                  )}
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide">
                    Microphone
                  </span>
                  <select
                    className="bg-transparent border-none text-[9px] md:text-[10px] text-black dark:text-white outline-none cursor-pointer w-full max-w-[100px] md:max-w-[120px] truncate p-0 font-bold uppercase pr-4"
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
                        className="bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
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
                  "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase flex-shrink-0",
                  !muted
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white",
                )}
              >
                {muted ? "Unmute" : "Mute"}
              </button>
            </div>

            {supportsVideo && (
              <div
                onClick={() => onToggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                  cameraEnabled
                    ? "bg-[#C4B5FD]"
                    : "bg-[#FFFDF5] dark:bg-[#000000]",
                )}
              >
                <div className="flex items-center gap-1.5 md:gap-2">
                  <div
                    className={cn(
                      "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black dark:border-white transition-colors",
                      cameraEnabled
                        ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                        : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white",
                    )}
                  >
                    {cameraEnabled ? (
                      <Video className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <VideoOff className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide">
                    Camera
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleCamera(!cameraEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                    cameraEnabled
                      ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                      : "bg-[#C4B5FD] text-black",
                  )}
                >
                  {cameraEnabled ? "Off" : "On"}
                </button>
              </div>
            )}

            {supportsVideo && cameraEnabled && (
              <div
                onClick={() => onTogglePrivacy(!privacyMode)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                  privacyMode
                    ? "bg-[#C4B5FD]"
                    : "bg-[#FFFDF5] dark:bg-[#000000]",
                )}
              >
                <div className="flex items-center gap-1.5 md:gap-2">
                  <div
                    className={cn(
                      "flex items-center justify-center w-6 h-6 md:w-7 md:h-7 border-[2px] border-black dark:border-white transition-colors",
                      privacyMode
                        ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                        : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white",
                    )}
                  >
                    {privacyMode ? (
                      <ToggleRight className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    ) : (
                      <ToggleLeft className="w-3 h-3 md:w-3.5 md:h-3.5 font-bold" />
                    )}
                  </div>
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide">
                    Privacy
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onTogglePrivacy(!privacyMode);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                    privacyMode
                      ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                      : "bg-[#C4B5FD] text-black",
                  )}
                >
                  {privacyMode ? "Off" : "On"}
                </button>
              </div>
            )}

            {supportsVideo && (
              <div
                onClick={() => onToggleScreen(!screenEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                  screenEnabled
                    ? "bg-[#FFD93D]"
                    : "bg-[#FFFDF5] dark:bg-[#000000]",
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
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide">
                    Screen Share
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleScreen(!screenEnabled);
                  }}
                  className={cn(
                    "text-[9px] md:text-[10px] font-black px-2 md:px-3 py-1 md:py-1.5 transition-all border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
                    screenEnabled
                      ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                      : "bg-[#FFD93D] text-black",
                  )}
                >
                  {screenEnabled ? "Stop" : "Share"}
                </button>
              </div>
            )}

            <button
              onClick={handleConnect}
              className={cn(
                "w-full py-2.5 md:py-3 font-black text-black transition-all transform active:translate-x-1 active:translate-y-1 active:shadow-none flex items-center justify-center gap-2 mt-1 border-[2px] md:border-[3px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] uppercase text-[10px] md:text-xs",
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

            <div className="grid grid-cols-4 gap-1.5 md:gap-2 pt-2 md:pt-3 border-t-[2px] border-black dark:border-white">
              {enableEditingSettings && (
                <SettingsDialog
                  className="w-full"
                  trigger={
                    <button className="flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FF6B6B] text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none group w-full">
                      <div className="p-1 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#FF6B6B] transition-colors">
                        <Settings className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                      </div>
                      <span className="text-[7px] md:text-[8px] font-black uppercase">Settings</span>
                    </button>
                  }
                />
              )}
              <button
                onClick={onPaintClick}
                className={cn(
                  "flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none group",
                  isPaintActive
                    ? "bg-[#FFD93D] text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D]",
                )}
              >
                <div
                  className={cn(
                    "p-1 border-[2px] border-black dark:border-white transition-colors",
                    isPaintActive
                      ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                      : "bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#FFD93D]",
                  )}
                >
                  <PenTool className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black uppercase">Canvas</span>
              </button>
              <button
                onClick={toggleSharedMedia}
                className={cn(
                  "flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none group",
                  sharedMediaOpen
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD]",
                )}
              >
                <div
                  className={cn(
                    "p-1 border-[2px] border-black dark:border-white transition-colors",
                    sharedMediaOpen
                      ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                      : "bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#C4B5FD]",
                  )}
                >
                  <Eye className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black uppercase">View</span>
              </button>
              <button className="flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#C4B5FD] text-black dark:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none group">
                <div className="p-1 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#C4B5FD] transition-colors">
                  <MoreHorizontal className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                </div>
                <span className="text-[7px] md:text-[8px] font-black uppercase">More</span>
              </button>
            </div>
          </div>
        )}

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
                <h3 className="font-black text-black uppercase text-xs md:text-sm">
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
            <div className="flex-1 min-h-0 bg-[#FFFDF5] dark:bg-[#000000] overflow-hidden p-0 m-0">
              <MediaMixerDisplay
                canvasRef={mediaMixerCanvasRef}
                onStatusChange={setMediaMixerStatus}
                isCameraEnabled={cameraEnabled}
                isScreenShareEnabled={screenEnabled}
                isCanvasEnabled={isPaintActive}
                privacyMode={privacyMode}
                processedEdgesRef={processedEdgesRef}
              />
            </div>
          </div>
        )}
      </motion.div>
  );
}

export default memo(FloatingControlPanel);

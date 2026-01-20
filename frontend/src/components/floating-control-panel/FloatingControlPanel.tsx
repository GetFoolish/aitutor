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
import { useTutorContext, AudioRecorder, TranscriptionData } from "../../features/tutor";
// import { useLiveAPIContext } from "../../contexts/LiveAPIContext"; // Commented out - useLiveAPIContext is an alias for useTutorContext, import from correct location
// import { AudioRecorder } from "../../lib/audio-recorder"; // Commented out - AudioRecorder is exported from ../../features/tutor, not from lib
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import cn from "classnames";
import MediaMixerDisplay from "../media-mixer-display/MediaMixerDisplay";
import { useTheme } from "../theme/theme-provier";
import { feedWebSocketService } from "../../services/feed-websocket-service";
import { instructionSSEService } from "../../services/instruction-sse-service";
import { LiveServerContent } from '@google/genai';
import { AvatarVideoDisplay } from "../avatar";
import { HomeworkPanel } from "../homework-panel/HomeworkPanel";
import { homeworkService } from "../../services/homework-service";

/**
 * Extract transcript text from Gemini content event
 */
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
  VenetianMask,
  Upload,
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
  privacyEnabled?: boolean;
  onTogglePrivacy?: (enabled: boolean) => void;
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
  privacyEnabled = false,
  onTogglePrivacy,
}: FloatingControlPanelProps) {
  const { client, connected, connect, disconnect, interruptAudio } = useTutorContext();
  const { theme } = useTheme();
  const dragControls = useDragControls();
  // const { client, connected, connect, disconnect, interruptAudio } = useTutorContext(); // Commented out - duplicate declaration, already declared above
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("");
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const [activeVideoStream] = useState<MediaStream | null>(null);
  const [sharedMediaOpen, setSharedMediaOpen] = useState(false);
  const [homeworkOpen, setHomeworkOpen] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const [isHomeworkAnimatingOut, setIsHomeworkAnimatingOut] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [popoverPosition, setPopoverPosition] = useState<"left" | "right">(
    "right",
  );
  const [mediaMixerStatus, setMediaMixerStatus] = useState<{
    isConnected: boolean;
    error: string | null;
  }>({ isConnected: true, error: null }); // Default to connected since it's frontend-based now
  const turnCompleteRef = useRef(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // Avatar video expansion state
  const [isVideoExpanded, setIsVideoExpanded] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  
  // Agent state and video track (for LiveKit integration)
  const [agentState, setAgentState] = useState<string>("disconnected");
  const [agentVideoTrack, setAgentVideoTrack] = useState<any>(null);

  // Dark mode detection for logo
  useEffect(() => {
    const checkDarkMode = () => {
      if (theme === 'dark') {
        setIsDarkMode(true);
      } else if (theme === 'light') {
        setIsDarkMode(false);
      } else if (theme === 'system') {
        // Check if dark class is applied to document root
        setIsDarkMode(document.documentElement.classList.contains('dark'));
      }
    };

    checkDarkMode();

    // Listen for theme changes when using system theme
    if (theme === 'system') {
      const observer = new MutationObserver(checkDarkMode);
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
      });

      return () => observer.disconnect();
    }
  }, [theme]);

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
    // Track if cleanup has been triggered to prevent sending
    let cleanupTriggered = false;

    const onData = (base64: string) => {
      // Validate audio data before processing
      if (!base64 || base64.length === 0) {
        return;
      }

      // Early exit if cleanup has been triggered
      if (cleanupTriggered) {
        return;
      }

      // Only send audio if client is connected and session is active
      // Add multiple checks to prevent sending when disconnected
      // CRITICAL: Never send when muted - empty/non-audio sends cause "Cannot extract voices" error
      if (!client || client.status !== "connected" || !connected || muted) {
        return;
      }

      // Additional validation: ensure we have valid audio data
      // Empty or invalid audio data can cause Gemini to reject the request
      if (!base64 || base64.length < 100) {
        // Audio chunks should be substantial - skip tiny/empty chunks
        // Minimum ~100 bytes base64 = ~25ms of PCM audio at 16kHz
        return;
      }

      // Validate base64 format - ensure it's valid base64 encoded PCM audio
      const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
      if (!base64Regex.test(base64)) {
        // Invalid base64 - skip this chunk
        console.debug('Invalid base64 audio data detected, skipping');
        return;
      }

      // Ensure audio data is not corrupted or empty
      // Base64 decoded length should be reasonable for PCM audio
      try {
        const decodedLength = Math.floor(base64.length * 3 / 4);
        if (decodedLength < 50) {
          // Too small even after decoding - skip
          return;
        }
      } catch (e) {
        // Base64 decode check failed - skip this chunk
        return;
      }

      // Additional check - if service indicates it's closing, don't send
      if (client.service && (client.service as any)._isClosing) {
        cleanupTriggered = true;
        return;
      }

      try {
        // Send to Gemini (existing functionality)
        // sendRealtimeInput handles WebSocket state errors internally
        client.sendRealtimeInput([
          {
            mimeType: "audio/pcm;rate=16000",
            data: base64,
          },
        ]);
      } catch (error) {
        // Silently handle errors (connection might be closing)
        // Most errors are already handled in sendRealtimeInput
        // This catch is a safety net for any errors that bubble up
        const errorMsg = error instanceof Error ? error.message : String(error);
        if (!errorMsg.includes("CLOSING") && 
            !errorMsg.includes("CLOSED") && 
            !errorMsg.includes("WebSocket") &&
            !errorMsg.includes("already in") &&
            !errorMsg.includes("Cannot extract voices")) {
          // Only log unexpected errors
          console.debug("Error sending audio to Gemini:", errorMsg);
        }
      }

      // Also send via WebSocket (batched, non-blocking)
      try {
        feedWebSocketService.sendAudio(base64);
      } catch (error) {
        // WebSocket errors are non-critical
        console.warn("Error sending audio to WebSocket:", error);
      }
    };

    // Register cleanup callback to stop audio recorder when WebSocket closes
    let cleanupUnregister: (() => void) | null = null;
    if (client && client.service) {
      cleanupUnregister = client.service.onCleanup(() => {
        // Mark cleanup as triggered to prevent further sends
        cleanupTriggered = true;
        // Stop audio recorder when WebSocket closes
        if (audioRecorder) {
          audioRecorder.stop();
        }
      });
    }

    // CRITICAL: Only start audio recorder AFTER connection is fully established
    // Wait a small delay to ensure Gemini is ready to receive audio
    let startDelay: NodeJS.Timeout | null = null;
    
    if (connected && !muted && audioRecorder) {
      // Small delay to ensure connection is fully ready
      // This prevents sending audio before Gemini is ready to extract voices
      startDelay = setTimeout(() => {
        if (connected && !muted && client && client.status === "connected") {
          audioRecorder.on("data", onData).start(selectedAudioDevice);
        }
      }, 500); // 500ms delay to ensure connection is ready
    } else {
      audioRecorder.stop();
    }
    
    // Single cleanup function for all cases
    return () => {
      if (startDelay) {
        clearTimeout(startDelay);
      }
      audioRecorder.off("data", onData);
      audioRecorder.stop();
      if (cleanupUnregister) {
        cleanupUnregister();
      }
    };
  }, [connected, client, muted, audioRecorder, selectedAudioDevice]);

  // Subscribe to SSE instructions from TeachingAssistant
  useEffect(() => {
    const unsubscribe = instructionSSEService.onInstruction((instruction) => {
      if (client && client.status === "connected") {
        // Send instruction to Gemini tutor
        client.send({ text: instruction });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [client]);

  // Record conversation turns for TeachingAssistant (optional - fails gracefully if service unavailable)
  useEffect(() => {
    const onTurnComplete = () => {
      turnCompleteRef.current = true;

      if (connected) {
        const token = jwtUtils.getToken();
        if (token) {
          apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`).catch((error: any) => {
            // Only log if it's not a connection refused error (service not available)
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
            // Only log if it's not a connection refused error (service not available)
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

  // Handle content events (transcript) - send via WebSocket
  useEffect(() => {
    const onContent = (content: any) => {
      if (!connected) return;

      // Extract transcript from content
      const transcript = extractTranscriptFromContent(content);
      if (transcript) {
        // Send transcript via WebSocket (fire-and-forget)
        feedWebSocketService.sendTranscript(transcript, 'tutor');
      }
    };

    client.on('content', onContent);

    return () => {
      client.off('content', onContent);
    };
  }, [client, connected]);

  // Handle input audio transcription (user's speech) - send via WebSocket
  useEffect(() => {
    const onInputTranscript = (data: TranscriptionData) => {
      if (!connected) return;

      // Send user's speech transcript via WebSocket
      if (data.text) {
        feedWebSocketService.sendTranscript(data.text, 'user');
      }
    };

    client.on('inputTranscript', onInputTranscript);

    return () => {
      client.off('inputTranscript', onInputTranscript);
    };
  }, [client, connected]);

  // Handle output audio transcription (tutor's speech) - send via WebSocket
  useEffect(() => {
    const onOutputTranscript = (data: TranscriptionData) => {
      if (!connected) return;

      // Send tutor's speech transcript via WebSocket
      if (data.text) {
        feedWebSocketService.sendTranscript(data.text, 'tutor');
      }
    };

    client.on('outputTranscript', onOutputTranscript);

    return () => {
      client.off('outputTranscript', onOutputTranscript);
    };
  }, [client, connected]);

  // Send homework to tutor when connected (works even when homework panel is closed)
  useEffect(() => {
    let cancelled = false;

    const sendHomeworkToTutor = async () => {
      if (!connected) return;

      console.log('[FloatingControlPanel] Tutor connected, checking for homework to send...');

      // Wait for connection to stabilize
      await new Promise(resolve => setTimeout(resolve, 1500));

      if (cancelled) return;

      try {
        // Fetch homework list
        const response = await homeworkService.listHomework();

        if (cancelled) return;

        if (!response.homework_items || response.homework_items.length === 0) {
          console.log('[FloatingControlPanel] No homework to send');
          return;
        }

        const latestHomework = response.homework_items[0];
        console.log('[FloatingControlPanel] Found homework to send:', latestHomework.filename);

        // Get the full homework details with extracted text
        const homeworkDetails = await homeworkService.getHomework(latestHomework.homework_id);

        if (cancelled) return;

        if (homeworkDetails.extracted_text) {
          console.log('[FloatingControlPanel] Injecting homework into tutor context:', homeworkDetails.filename);
          const success = await client.injectHomeworkContext(
            homeworkDetails.extracted_text,
            homeworkDetails.filename
          );
          if (success) {
            console.log('[FloatingControlPanel] Successfully sent homework to tutor:', homeworkDetails.filename);
          } else {
            console.warn('[FloatingControlPanel] Failed to inject homework after retries');
          }
        } else {
          console.log('[FloatingControlPanel] Homework has no extracted text:', latestHomework.filename);
        }
      } catch (err) {
        console.error('[FloatingControlPanel] Error sending homework to tutor:', err);
      }
    };

    sendHomeworkToTutor();

    return () => {
      cancelled = true;
    };
  }, [connected, client]);

  // Video handling - capture full MediaMixer canvas and send to Media Feed as JPEG
  // NOTE: We intentionally do NOT send these video frames to Gemini Live API anymore.
  // Sending non-audio media via sendRealtimeInput causes
  // "Cannot extract voices from a non-audio request" and closes the connection.
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId: number | null = null;
    let rafId: number | null = null;
    let isRunning = false; // Track if loop is running to prevent multiple concurrent loops

    function sendVideoFrame() {
      if (!connected || !isRunning) {
        return;
      }

      const canvas = mediaMixerCanvasRef.current;
      if (canvas && canvas.width + canvas.height > 0) {
        const base64 = canvas.toDataURL("image/jpeg", 1.0);
        const imageData = base64.slice(base64.indexOf(",") + 1, Infinity);

        // Send via WebSocket (fire-and-forget, non-blocking) to Media Feed / TeachingAssistant
        // We DO NOT send these frames to Gemini directly anymore to avoid
        // non-audio realtimeInput requests.
        feedWebSocketService.sendMedia(imageData);
      }

      // Schedule next frame only if still connected and running
      if (connected && isRunning) {
        timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
      }
    }

    // Start sending frames when connected
    if (connected && !isRunning) {
      isRunning = true;
      // Send first frame immediately, then schedule subsequent frames
      rafId = requestAnimationFrame(sendVideoFrame);
    }

    return () => {
      isRunning = false; // Stop the loop
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [connected, activeVideoStream, client]);

  const handleConnect = useCallback(async () => {
    if (connected) {
      // Handle disconnect with TeachingAssistant session end
      try {
        interruptAudio();

        // Disconnect WebSocket and SSE first (optional - may not be connected)
        try {
          feedWebSocketService.disconnect();
        } catch (e) {
          // WebSocket may not be connected - ignore
        }
        try {
          instructionSSEService.disconnect();
        } catch (e) {
          // SSE may not be connected - ignore
        }

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
            // Teaching Assistant service is not available - log warning but continue
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

        // Start TeachingAssistant session (creates MongoDB session)
        // Make this optional - if service is not available, continue without it
        try {
          const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/start`);

          if (response.ok) {
            const data = await response.json();

            // Connect WebSocket for feed streaming
            try {
              await feedWebSocketService.connect();
            } catch (wsError) {
              console.warn('Failed to connect WebSocket feed service (optional):', wsError);
            }

            // Connect SSE for receiving instructions
            try {
              instructionSSEService.connect();
            } catch (sseError) {
              console.warn('Failed to connect SSE instruction service (optional):', sseError);
            }

            // Send greeting if available
            if (data.prompt && client.status === 'connected') {
              client.send({ text: data.prompt });
            }
          } else {
            console.warn(`TeachingAssistant service returned status ${response.status} - continuing without it`);
          }
        } catch (taError: any) {
          // Teaching Assistant service is not available - log warning but continue
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
  }, [connected, connect, disconnect, client, interruptAudio]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  // Calculate initial position once without state
  const initialPosition = useMemo(() => {
    if (typeof window === "undefined") return { x: 0, y: 0 };
    return { x: window.innerWidth - 380, y: 96 };
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

  const toggleHomework = useCallback(() => {
    if (!homeworkOpen) {
      // Opening
      updatePopoverPosition();
      setHomeworkOpen(true);
      setIsHomeworkAnimatingOut(false);
    } else {
      // Closing
      setIsHomeworkAnimatingOut(true);
      setTimeout(() => {
        setHomeworkOpen(false);
        setIsHomeworkAnimatingOut(false);
      }, 200); // Match CSS animation duration
    }
  }, [homeworkOpen, updatePopoverPosition]);

  const handleCollapse = useCallback(() => {
    setIsCollapsed(!isCollapsed);
  }, [isCollapsed]);

  const handleVideoClick = useCallback(() => {
    setIsVideoExpanded(!isVideoExpanded);
  }, [isVideoExpanded]);

  const toggleMoreMenu = useCallback(() => {
    setMoreMenuOpen(!moreMenuOpen);
  }, [moreMenuOpen]);

  const handleMute = useCallback(() => {
    setMuted(!muted);
  }, [muted]);

  // Simplified drag end handler for Framer Motion
  const handleDragEnd = useCallback(() => {
    // Recalculate popover position after drag ends
    if (sharedMediaOpen || homeworkOpen) {
      updatePopoverPosition();
    }
  }, [sharedMediaOpen, homeworkOpen, updatePopoverPosition]);

  // Memoize panel classes to avoid recalculating on every render
  // Panel expands to 2x width when video is expanded
  const panelClasses = useMemo(
    () =>
      cn(
        "fixed z-[1000] bg-[#FFFDF5] dark:bg-[#000000] border-[2px] md:border-[3px] border-black dark:border-white rounded-lg md:rounded-xl transition-all duration-300",
        isCollapsed
          ? "w-[50px] md:w-[55px] py-2 md:py-2.5 px-1 md:px-1.5 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)]"
          : isVideoExpanded
          ? "w-[440px] md:w-[500px] p-2.5 md:p-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)]"
          : "w-[220px] md:w-[250px] p-2.5 md:p-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)]",
        "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)] md:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_8px_8px_20px_rgba(0,0,0,0.18),_16px_16px_40px_rgba(0,0,0,0.12)]",
      ),
    [isCollapsed, isVideoExpanded],
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
        right: typeof window !== "undefined" ? window.innerWidth - (isCollapsed ? 55 : isVideoExpanded ? 500 : 250) : 1000,
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
        // COLLAPSED VIEW
        <div className="flex flex-col items-center gap-1.5 md:gap-2">
          <button
            onClick={handleCollapse}
            className="w-8 h-8 md:w-9 md:h-9 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] flex items-center justify-center text-black dark:text-white transition-all hover:translate-x-0.5 hover:translate-y-0.5 duration-100 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none"
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

          {supportsVideo && cameraEnabled && onTogglePrivacy && (
            <button
              onClick={() => onTogglePrivacy(!privacyEnabled)}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                privacyEnabled
                  ? "bg-[#FF6B6B] text-white"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
              )}
              title={privacyEnabled ? "Disable Privacy Mode" : "Enable Privacy Mode"}
            >
              <VenetianMask className="w-3.5 h-3.5 font-bold" />
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

          <button
            onClick={toggleHomework}
            className={cn(
              "w-8 h-8 md:w-9 md:h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
              homeworkOpen
                ? "bg-[#FFD93D] text-black"
                : "bg-[#FFD93D] text-black hover:bg-[#FFE566] border-black",
            )}
            title="Upload Homework"
          >
            <Upload className="w-3.5 h-3.5 font-bold" />
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
        // EXPANDED VIEW
        <div className="flex flex-col gap-1.5 md:gap-2">
          {/* Avatar Video Display - Centered at top */}
          <AvatarVideoDisplay
            isConnected={connected}
            isExpanded={isVideoExpanded}
            onToggleExpand={handleVideoClick}
            videoTrack={agentVideoTrack}
            agentState={agentState}
          />

          {/* Audio Control */}
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

          {/* Camera Control */}
          {supportsVideo && (
            <>
              <div
                onClick={() => onToggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] relative",
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
                {/* Embedded Privacy Toggle */}
                {cameraEnabled && onTogglePrivacy && (
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      onTogglePrivacy(!privacyEnabled);
                    }}
                    className={cn(
                      "flex items-center border-[2px] border-black dark:border-white rounded-full p-0.5 cursor-pointer transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:scale-105 z-10 mx-2",
                      privacyEnabled ? "bg-[#4ADE80]" : "bg-[#FF6B6B]"
                    )}
                    title="Privacy Mode"
                    style={{ width: '32px', height: '18px' }}
                  >
                    <motion.div
                      className={cn("w-3 h-3 rounded-full shadow-sm border border-black",
                        privacyEnabled ? "bg-white" : "bg-black dark:bg-white"
                      )}
                      animate={{
                        x: privacyEnabled ? 14 : 0,
                      }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                  </div>
                )}

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
            </>
          )}

          {/* Screen Share Control */}
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

          {/* Main Action Button */}
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

          {/* More Menu Button and Dropdown */}
          <div className="relative pt-2 md:pt-3 border-t-[2px] border-black dark:border-white">
            <button
              onClick={toggleMoreMenu}
              className={cn(
                "w-full flex flex-col items-center gap-1 p-1.5 md:p-2 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none group",
                moreMenuOpen
                  ? "bg-[#C4B5FD] text-black"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD]",
              )}
            >
              <div
                className={cn(
                  "p-1 border-[2px] border-black dark:border-white transition-colors",
                  moreMenuOpen
                    ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                    : "bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#C4B5FD]",
                )}
              >
                <MoreHorizontal className="w-3 h-3 md:w-4 md:h-4 font-bold" />
              </div>
              <span className="text-[7px] md:text-[8px] font-black uppercase">More</span>
            </button>

            {/* More Menu Dropdown */}
            {moreMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-[#FFFDF5] dark:bg-[#000000] border-[2px] border-black dark:border-white rounded-lg shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] overflow-hidden z-[1002]">
                {enableEditingSettings && (
                  <SettingsDialog
                    className="w-full"
                    trigger={
                      <button className="w-full flex items-center gap-2 p-2 md:p-2.5 border-b-[2px] border-black dark:border-white hover:bg-[#FF6B6B] text-black dark:text-white hover:text-white transition-all group">
                        <Settings className="w-4 h-4 font-bold" />
                        <span className="text-[9px] md:text-[10px] font-black uppercase">Settings</span>
                      </button>
                    }
                  />
                )}
                <button
                  onClick={() => {
                    onPaintClick();
                    setMoreMenuOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center gap-2 p-2 md:p-2.5 border-b-[2px] border-black dark:border-white hover:bg-[#FFD93D] text-black dark:text-white transition-all group",
                    isPaintActive && "bg-[#FFD93D]",
                  )}
                >
                  <PenTool className="w-4 h-4 font-bold" />
                  <span className="text-[9px] md:text-[10px] font-black uppercase">Canvas</span>
                </button>
                <button
                  onClick={() => {
                    toggleSharedMedia();
                    setMoreMenuOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center gap-2 p-2 md:p-2.5 hover:bg-[#C4B5FD] text-black dark:text-white transition-all group",
                    sharedMediaOpen && "bg-[#C4B5FD]",
                  )}
                >
                  <Eye className="w-4 h-4 font-bold" />
                  <span className="text-[9px] md:text-[10px] font-black uppercase">View Media</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )
      }

      {/* Popover for Shared Media */}
      {
        sharedMediaOpen && (
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
                privacyMode={privacyEnabled}
              />
            </div>
          </div>
        )
      }

      {/* Popover for Homework */}
      {homeworkOpen && (
        <div
          className={cn(
            "absolute w-[320px] md:w-[360px] h-auto flex flex-col bg-white dark:bg-[#000000] border-[3px] md:border-[4px] border-black dark:border-white rounded-xl md:rounded-2xl shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] overflow-hidden z-[1001]",
            isHomeworkAnimatingOut ? "animate-popover-out" : "animate-popover-in",
            popoverPosition === "right"
              ? "left-full ml-4 md:ml-6"
              : "right-full mr-4 md:mr-6",
            verticalAlign === "bottom" ? "bottom-0" : "top-0",
          )}
        >
          <div className="flex items-center justify-between p-3 md:p-3.5 border-b-[3px] md:border-b-[4px] border-black dark:border-white bg-[#FFD93D]">
            <div className="flex items-center gap-2 md:gap-3">
              <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-[#000000]">
                <Upload className="w-4 h-4 md:w-5 md:h-5 text-black dark:text-white font-bold" />
              </div>
              <h3 className="font-black text-black uppercase text-xs md:text-sm">
                UPLOAD HOMEWORK
              </h3>
            </div>
            <button
              onClick={toggleHomework}
              className="w-8 h-8 md:w-9 md:h-9 flex items-center justify-center border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-[#000000] hover:bg-[#FF006E] text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
            >
              <X className="w-4 h-4 md:w-5 md:h-5 font-bold" />
            </button>
          </div>
          <div className="flex-1 min-h-0 bg-[#FFFDF5] dark:bg-[#000000] overflow-hidden p-3 md:p-4">
            <HomeworkPanel />
          </div>
        </div>
      )}
    </motion.div >
  );
}
export default memo(FloatingControlPanel);

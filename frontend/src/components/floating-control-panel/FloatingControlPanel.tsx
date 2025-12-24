import React, {
  memo,
  RefObject,
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
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
  Pause,
  Play,
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
  stopAllMedia: () => void;
  // MediaMixer canvas ref for display
  mediaMixerCanvasRef: RefObject<HTMLCanvasElement>;
  // Auto-start session when questions are ready
  autoStartWhenReady?: boolean;
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
  stopAllMedia,
  mediaMixerCanvasRef,
  autoStartWhenReady = false,
}: FloatingControlPanelProps) {
  const { client, connected, connect, disconnect, interruptAudio } = useTutorContext();
  const { theme } = useTheme();
  const dragControls = useDragControls();
  // const { client, connected, connect, disconnect, interruptAudio } = useTutorContext(); // Commented out - duplicate declaration, already declared above
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("");
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [activeVideoStream] = useState<MediaStream | null>(null);
  const [sharedMediaOpen, setSharedMediaOpen] = useState(false);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
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
  const hasAutoStartedRef = useRef(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [popoverHeight, setPopoverHeight] = useState<number | null>(null);
  const popoverHeaderRef = useRef<HTMLDivElement>(null);
  // Initialize mobile/tablet state immediately based on current window size
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768);
  const [isTablet, setIsTablet] = useState(() => typeof window !== 'undefined' && window.innerWidth > 768 && window.innerWidth <= 1024);

  // Mobile/Tablet detection with auto-collapse
  useEffect(() => {
    const checkDevice = () => {
      const width = window.innerWidth;
      const newIsMobile = width <= 768;
      const newIsTablet = width > 768 && width <= 1024;

      setIsMobile(newIsMobile);
      setIsTablet(newIsTablet);

      // Auto-collapse on mobile
      if (newIsMobile) {
        setIsCollapsed(true);
      }
    };

    checkDevice();
    window.addEventListener('resize', checkDevice);

    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  // Calculate popover height based on canvas dimensions
  useEffect(() => {
    if (!sharedMediaOpen) {
      return;
    }

    const calculatePopoverHeight = () => {
      const canvas = mediaMixerCanvasRef.current;
      const header = popoverHeaderRef.current;

      // Get header height dynamically
      const headerHeight = header ? header.getBoundingClientRect().height : 56;

      // Determine popover width based on screen size
      const popoverWidth = isMobile ? 320 : 360;

      if (!canvas || canvas.width === 0 || canvas.height === 0) {
        // Default fallback: canvas is 1280x2160, aspect ratio 1.6875
        const canvasAspectRatio = 2160 / 1280; // 1.6875
        const contentHeight = popoverWidth * canvasAspectRatio;
        return contentHeight + headerHeight;
      }

      // Calculate based on actual canvas dimensions
      const canvasAspectRatio = canvas.height / canvas.width;
      const contentHeight = popoverWidth * canvasAspectRatio;
      return contentHeight + headerHeight;
    };

    const updateHeight = () => {
      const height = calculatePopoverHeight();
      setPopoverHeight(height);
    };

    // Initial calculation with a small delay to ensure DOM is ready
    const timeoutId = setTimeout(updateHeight, 100);

    // Watch for canvas dimension changes
    const checkCanvas = setInterval(() => {
      const canvas = mediaMixerCanvasRef.current;
      if (canvas && canvas.width > 0 && canvas.height > 0) {
        updateHeight();
      }
    }, 500);

    // Watch for window resize
    window.addEventListener('resize', updateHeight);

    return () => {
      clearTimeout(timeoutId);
      clearInterval(checkCanvas);
      window.removeEventListener('resize', updateHeight);
    };
  }, [mediaMixerCanvasRef, sharedMediaOpen, isMobile]);

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
    const onData = (base64: string) => {
      // Send to Gemini (existing functionality)
      client.sendRealtimeInput([
        {
          mimeType: "audio/pcm;rate=16000",
          data: base64,
        },
      ]);

      // Also send via WebSocket (batched, non-blocking)
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

  // Video handling - capture full MediaMixer canvas and send to tutor as JPEG
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId: number | null = null;
    let rafId: number | null = null;
    let isRunning = false; // Track if loop is running to prevent multiple concurrent loops

    function sendVideoFrame() {
      const canvas = mediaMixerCanvasRef.current;

      if (!canvas || !connected || isPaused || !isRunning) {
        return;
      }

      if (canvas.width + canvas.height > 0) {
        const base64 = canvas.toDataURL("image/jpeg", 1.0);
        const data = base64.slice(base64.indexOf(",") + 1, Infinity);

        // Send to Gemini (existing functionality)
        client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);

        // Also send via WebSocket (fire-and-forget, non-blocking)
        feedWebSocketService.sendMedia(data);
      }

      // Schedule next frame only if still connected and running
      if (connected && !isPaused && isRunning) {
        timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
      }
    }

    // Start sending frames when connected
    if (connected && !isPaused && !isRunning) {
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
  }, [connected, activeVideoStream, client, isPaused]); // Removed refs from dependencies - they don't trigger re-renders

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
      setIsPaused(false); // Reset pause state on disconnect

      // Stop all media streams when session ends
      stopAllMedia();
      setMuted(true); // Ensure mic is muted after disconnect
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

  // Auto-start session when questions are ready (only once)
  useEffect(() => {
    if (autoStartWhenReady && !connected && !hasAutoStartedRef.current) {
      hasAutoStartedRef.current = true; // Mark as auto-started to prevent restart loop

      // Small delay to ensure everything is mounted
      const timer = setTimeout(() => {
        handleConnect();
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [autoStartWhenReady, connected, handleConnect]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  // Dynamic drag constraints that update on resize
  const [dragConstraints, setDragConstraints] = useState({
    left: 0,
    top: 0,
    right: 1000,
    bottom: 800,
  });

  // Calculate drag constraints based on current viewport and collapsed state
  const calculateDragConstraints = useCallback(() => {
    if (typeof window === "undefined") {
      return { left: 0, top: 0, right: 1000, bottom: 800 };
    }

    // Use clientWidth to exclude scrollbar width
    const viewportWidth = document.documentElement.clientWidth;
    const viewportHeight = window.innerHeight;

    // Calculate panel width based on collapsed state and screen size
    let panelWidth: number;
    if (isCollapsed) {
      panelWidth = viewportWidth <= 375 ? 45 : viewportWidth <= 640 ? 50 : 55;
    } else {
      panelWidth = viewportWidth <= 375 ? 180
        : viewportWidth <= 640 ? 200
          : viewportWidth <= 768 ? 220
            : 250;
    }

    // Calculate bottom offset based on screen size
    const bottomOffset = viewportWidth <= 375 ? 70
      : viewportWidth <= 768 ? 80
        : 100;

    return {
      left: 0,
      top: 0,
      right: viewportWidth - panelWidth - 16, // Add 16px safety margin
      bottom: viewportHeight - bottomOffset,
    };
  }, [isCollapsed]);

  // Update drag constraints when viewport size or collapsed state changes (Desktop only)
  useEffect(() => {
    // Skip drag constraints on mobile
    if (isMobile) return;

    // Simplified drag constraints or removed to prevent conflict with centering
    const updateConstraints = () => {
      // Optional: Add logic here if strict bounds are needed.
      // For now, we allow free movement but default to center.
    };

    // updateConstraints(); // constraints removed
    // window.addEventListener('resize', updateConstraints);
    // const resizeObserver = new ResizeObserver(updateConstraints);
    // resizeObserver.observe(document.body);
    return () => {
      // window.removeEventListener('resize', updateConstraints);
      // resizeObserver.disconnect();
    };
  }, [isCollapsed, calculateDragConstraints, isMobile]);

  // Ensure panel stays within bounds when constraints change (Desktop only)
  useEffect(() => {
    // Skip bounds checking on mobile - use fixed positioning instead
    if (isMobile || !panelRef.current) return;

    const checkBounds = () => {
      const panel = panelRef.current;
      if (!panel) return;

      const rect = panel.getBoundingClientRect();

      // Check if panel is outside new constraints
      const isOutOfBoundsRight = rect.left > dragConstraints.right;
      const isOutOfBoundsBottom = rect.top > dragConstraints.bottom;
      const isOutOfBoundsLeft = rect.left < 0;
      const isOutOfBoundsTop = rect.top < 0;

      if (isOutOfBoundsRight || isOutOfBoundsBottom || isOutOfBoundsLeft || isOutOfBoundsTop) {
        // Calculate safe position
        let safeX = rect.left;
        let safeY = rect.top;

        if (isOutOfBoundsRight) safeX = dragConstraints.right; // Snap to right constraint (already has margin)
        if (isOutOfBoundsLeft) safeX = 20;
        if (isOutOfBoundsBottom) safeY = dragConstraints.bottom - 20;
        if (isOutOfBoundsTop) safeY = 20;

        // Smoothly reposition panel
        panel.style.transition = 'transform 0.3s ease-out';
        panel.style.transform = `translate3d(${safeX}px, ${safeY}px, 0)`;

        // Remove transition after animation
        setTimeout(() => {
          panel.style.transition = '';
        }, 300);
      }
    };

    // Check bounds with a small delay to allow layout to settle
    const timeoutId = setTimeout(checkBounds, 100);

    return () => clearTimeout(timeoutId);
  }, [isMobile]);

  // No initial position calculation needed for centered layout
  // We use CSS centering: left: 50%, x: "-50%"

  // Memoize popover position calculation to avoid expensive DOM queries
  const calculatePopoverPosition = useCallback(() => {
    if (!panelRef.current) return { side: "right" as const, vertical: "top" as const };

    const panelRect = panelRef.current.getBoundingClientRect();
    const popoverWidth = 360;
    const viewportWidth = document.documentElement.clientWidth; // consistency
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

  // Auto-close Adam's View on mobile devices
  useEffect(() => {
    if (isMobile && sharedMediaOpen) {
      setSharedMediaOpen(false);
      setIsAnimatingOut(false);
    }
  }, [isMobile, sharedMediaOpen]);

  const handleCollapse = useCallback(() => {
    setIsCollapsed(!isCollapsed);
  }, [isCollapsed]);

  const handleMute = useCallback(() => {
    setMuted(!muted);
  }, [muted]);

  const handlePause = useCallback(() => {
    if (isPaused) {
      // Resume: Unmute microphone
      setMuted(false);
      setIsPaused(false);
    } else {
      // Pause: Interrupt audio and mute microphone
      interruptAudio();
      setMuted(true);
      setIsPaused(true);
    }
  }, [isPaused, interruptAudio]);

  // Simplified drag end handler for Framer Motion
  const handleDragEnd = useCallback(() => {
    // Recalculate popover position after drag ends
    if (sharedMediaOpen) {
      updatePopoverPosition();
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  // Memoize panel classes to avoid recalculating on every render
  const panelClasses = useMemo(
    () =>
      cn(
        "bg-[#FFFDF5] dark:bg-[#000000] border-[2px] md:border-[3px] border-black dark:border-white rounded-lg md:rounded-xl",
        // Mobile: Fixed at bottom, horizontal layout (positioning via inline styles)
        isMobile && "w-auto max-w-[calc(100vw-16px)]",
        // Desktop: Draggable floating panel
        !isMobile && "fixed z-[1000]",
        isCollapsed
          ? isMobile
            ? "py-2 px-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12)]" // Mobile collapsed: horizontal
            : "w-[45px] sm:w-[50px] md:w-[55px] py-1.5 sm:py-2 md:py-2.5 px-1 md:px-1.5 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)]" // Desktop collapsed: vertical
          : "w-[180px] sm:w-[200px] md:w-[220px] lg:w-[250px] p-1.5 sm:p-2 md:p-2.5 lg:p-3 shadow-[1px_1px_0_0_rgba(0,0,0,1),_4px_4px_12px_rgba(0,0,0,0.12),_8px_8px_24px_rgba(0,0,0,0.08)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)]",
        !isMobile && "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_6px_6px_16px_rgba(0,0,0,0.15),_12px_12px_32px_rgba(0,0,0,0.1)] md:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1),_8px_8px_20px_rgba(0,0,0,0.18),_16px_16px_40px_rgba(0,0,0,0.12)]",
      ),
    [isCollapsed, isMobile],
  );

  return (
    <motion.div
      ref={panelRef}
      className={panelClasses}
      drag={!isMobile} // Disable drag on mobile
      dragControls={!isMobile ? dragControls : undefined}
      dragListener={!isMobile}
      dragMomentum={false}
      dragElastic={0}
      dragConstraints={!isMobile && !isCollapsed ? undefined : undefined} // Removed strict constraints for now
      onDragEnd={!isMobile ? handleDragEnd : undefined}
      initial={isMobile ? false : { x: "-50%", y: 0 }}
      animate={isMobile ? false : undefined}
      whileDrag={!isMobile ? {
        cursor: "grabbing",
        scale: 1.0,
      } : undefined}
      dragTransition={!isMobile ? {
        bounceStiffness: 600,
        bounceDamping: 20,
        power: 0.1,
      } : undefined}
      style={isMobile ? {
        position: 'fixed',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
      } : {
        position: 'absolute',
        top: '24px',
        left: '50%',
        zIndex: 1000,
      }}
    >
      {/* Hidden canvas for MediaMixer - will be set by parent */}
      < canvas
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

      {/* Drag Handle & Header - Only show on desktop */}
      {
        !isMobile && (
          <div
            className={cn(
              "cursor-grab active:cursor-grabbing flex items-center mb-1.5 md:mb-2",
              isCollapsed ? "justify-center mb-1 md:mb-1.5" : "justify-between",
            )}
            onPointerDown={(e) => !isMobile && dragControls.start(e)}
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
            <Button
              variant="neo"
              size="sm"
              onClick={handleCollapse}
              className="w-6 h-6 md:w-6 md:h-6 p-0"
            >
              {isCollapsed ? (
                <ChevronDown className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
              ) : (
                <ChevronUp className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
              )}
            </Button>
          </div>
        )
      }

      {
        isCollapsed ? (
          // COLLAPSED VIEW
          <div className={cn(
            "flex items-center",
            isMobile ? "flex-row gap-2" : "flex-col gap-1.5 md:gap-2"
          )}>
            {/* Home/Expand Button - Desktop only */}
            {!isMobile && (
              <Button
                variant="neo"
                size="icon"
                onClick={handleCollapse}
                className="shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]"
                title="Expand"
              >
                <Home className="w-4 h-4 font-bold" />
              </Button>
            )}

            {/* Microphone Button */}
            <Button
              variant={muted ? "neo-destructive" : "neo"}
              size="icon"
              onClick={() => connected && handleMute()}
              disabled={!connected}
              className={cn(
                !connected && "opacity-50 cursor-not-allowed"
              )}
              title={muted ? "Unmute" : "Mute"}
            >
              {muted ? (
                <MicOff className="w-4 h-4 font-bold" />
              ) : (
                <Mic className="w-4 h-4 font-bold" />
              )}
            </Button>

            {/* Start/Stop Session Button */}
            <Button
              variant={connected ? "neo-destructive" : "neo-success"}
              size="icon"
              onClick={handleConnect}
              className="relative group font-black"
              title={connected ? "Stop Session" : "Start Session"}
            >
              {connected ? (
                <StopCircle className="w-5 h-5" />
              ) : (
                <PlayCircle className="w-5 h-5" />
              )}
              {connected && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#FFD93D] border-2 border-black animate-pulse" />
              )}
            </Button>

            {/* Pause/Resume Button (only show when connected) */}
            {/* Pause/Resume Button (only show when connected) */}
            {connected && (
              <Button
                variant={isPaused ? "neo-success" : "neo-warning"}
                size="icon"
                onClick={handlePause}
                title={isPaused ? "Resume Session" : "Pause Session"}
              >
                {isPaused ? (
                  <Play className="w-4 h-4 font-bold" />
                ) : (
                  <Pause className="w-4 h-4 font-bold" />
                )}
              </Button>
            )}

            {/* Separator - Desktop only */}
            {!isMobile && <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />}

            {/* Additional controls - Desktop only */}
            {!isMobile && (
              <>
                {supportsVideo && (
                  <Button
                    variant="neo"
                    size="icon"
                    onClick={() => connected && onToggleCamera(!cameraEnabled)}
                    disabled={!connected}
                    className={cn(
                      cameraEnabled && "bg-[#C4B5FD]",
                      !connected && "opacity-50 cursor-not-allowed"
                    )}
                    title="Toggle Camera"
                  >
                    {cameraEnabled ? (
                      <Video className="w-3.5 h-3.5 font-bold" />
                    ) : (
                      <VideoOff className="w-3.5 h-3.5 font-bold" />
                    )}
                  </Button>
                )}

                {supportsVideo && (
                  <Button
                    variant={screenEnabled ? "neo-warning" : "neo"}
                    size="icon"
                    onClick={() => connected && onToggleScreen(!screenEnabled)}
                    disabled={!connected}
                    className={cn(
                      !connected && "opacity-50 cursor-not-allowed"
                    )}
                    title="Share Screen"
                  >
                    {screenEnabled ? (
                      <Monitor className="w-3.5 h-3.5 font-bold" />
                    ) : (
                      <MonitorOff className="w-3.5 h-3.5 font-bold" />
                    )}
                  </Button>
                )}

                <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />

                {enableEditingSettings && (
                  <SettingsDialog
                    className="!h-auto !block"
                    trigger={
                      <Button
                        variant="neo"
                        size="icon"
                        className="hover:bg-[#FF6B6B] hover:text-white"
                      >
                        <Settings className="w-3.5 h-3.5 font-bold" />
                      </Button>
                    }
                  />
                )}

                <Button
                  variant={isPaintActive ? "neo-warning" : "neo"}
                  size="icon"
                  onClick={onPaintClick}
                  title="Canvas"
                >
                  <PenTool className="w-3.5 h-3.5 font-bold" />
                </Button>

                <Button
                  variant="neo"
                  size="icon"
                  onClick={toggleSharedMedia}
                  className={cn(
                    sharedMediaOpen && "bg-[#C4B5FD] hover:bg-[#C4B5FD]",
                    !sharedMediaOpen && "hover:bg-[#C4B5FD]"
                  )}
                  title="View"
                >
                  <Eye className="w-3.5 h-3.5 font-bold" />
                </Button>

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
              </>
            )}
          </div>
        ) : (
          // EXPANDED VIEW
          <div className="flex flex-col gap-1.5 md:gap-2">
            {/* Audio Control */}
            <div
              onClick={() => connected && handleMute()}
              className={cn(
                "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 group shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                !muted
                  ? "bg-[#FFFDF5] dark:bg-[#000000]"
                  : "bg-[#FF6B6B]",
                connected ? "cursor-pointer" : "opacity-50 cursor-not-allowed"
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
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide leading-none mt-[1px]">
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
              <Button
                variant={!muted ? "neo" : "neo"}
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleMute();
                }}
                className={cn(
                  "px-2 md:px-3 uppercase flex-shrink-0",
                  !muted && "bg-[#C4B5FD] hover:bg-[#C4B5FD] text-black"
                )}
              >
                {muted ? "Unmute" : "Mute"}
              </Button>
            </div>

            {/* Camera Control */}
            {supportsVideo && (
              <div
                onClick={() => connected && onToggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                  cameraEnabled
                    ? "bg-[#C4B5FD]"
                    : "bg-[#FFFDF5] dark:bg-[#000000]",
                  connected ? "cursor-pointer" : "opacity-50 cursor-not-allowed"
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
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide leading-none mt-[1px]">
                    Camera
                  </span>
                </div>
                <Button
                  variant={cameraEnabled ? "neo" : "neo"}
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (connected) onToggleCamera(!cameraEnabled);
                  }}
                  disabled={!connected}
                  className={cn(
                    "px-2 md:px-3 uppercase",
                    !cameraEnabled && "bg-[#C4B5FD] hover:bg-[#C4B5FD] text-black",
                    !connected && "opacity-50 cursor-not-allowed"
                  )}
                >
                  {cameraEnabled ? "Off" : "On"}
                </Button>
              </div>
            )}

            {/* Screen Share Control */}
            {supportsVideo && (
              <div
                onClick={() => connected && onToggleScreen(!screenEnabled)}
                className={cn(
                  "flex items-center justify-between p-2 md:p-2.5 border-[2px] border-black dark:border-white transition-all duration-100 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                  screenEnabled
                    ? "bg-[#FFD93D]"
                    : "bg-[#FFFDF5] dark:bg-[#000000]",
                  connected ? "cursor-pointer" : "opacity-50 cursor-not-allowed"
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
                  <span className="text-[9px] md:text-[10px] font-black text-black dark:text-white uppercase tracking-wide leading-none mt-[1px]">
                    Screen Share
                  </span>
                </div>
                <Button
                  variant={screenEnabled ? "neo" : "neo-warning"}
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (connected) onToggleScreen(!screenEnabled);
                  }}
                  disabled={!connected}
                  className={cn(
                    "px-2 md:px-3 uppercase",
                    !connected && "opacity-50 cursor-not-allowed"
                  )}
                >
                  {screenEnabled ? "Stop" : "Share"}
                </Button>
              </div>
            )}

            {/* Main Action Buttons */}
            {connected ? (
              // When connected: Show Pause and Stop buttons
              <div className="flex gap-1.5 md:gap-2 mt-1">
                <Button
                  variant={isPaused ? "neo-success" : "neo-warning"}
                  onClick={handlePause}
                  className="flex-1 uppercase text-[10px] md:text-xs"
                >
                  {isPaused ? (
                    <>
                      <Play className="w-4 h-4 md:w-5 md:h-5" />
                      Resume
                    </>
                  ) : (
                    <>
                      <Pause className="w-4 h-4 md:w-5 md:h-5" />
                      Pause
                    </>
                  )}
                </Button>
                <Button
                  variant="neo-destructive"
                  onClick={handleConnect}
                  className="flex-1 uppercase text-[10px] md:text-xs"
                >
                  <StopCircle className="w-4 h-4 md:w-5 md:h-5" />
                  Stop
                </Button>
              </div>
            ) : (
              // When disconnected: Show Start Session button
              <Button
                variant="neo-success"
                onClick={handleConnect}
                className="w-full mt-1 uppercase text-[10px] md:text-xs"
              >
                <PlayCircle className="w-4 h-4 md:w-5 md:h-5" />
                Start Session
              </Button>
            )}

            {/* Bottom Actions */}
            {/* Bottom Actions */}
            <div className="grid grid-cols-4 gap-1 md:gap-2 pt-2 md:pt-3 border-t-[2px] border-black dark:border-white">
              {enableEditingSettings && (
                <SettingsDialog
                  className="w-full"
                  trigger={
                    <Button
                      variant="neo"
                      className="flex flex-col h-auto items-center justify-center gap-0.5 p-1 md:p-2 hover:bg-[#FF6B6B] hover:text-white group w-full min-w-0"
                    >
                      <div className="p-1 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-[#FF6B6B] transition-colors">
                        <Settings className="w-3 h-3 md:w-4 md:h-4 font-bold" />
                      </div>
                      <span className="text-[6px] xs:text-[7px] md:text-[8px] font-black uppercase truncate w-full text-center">Settings</span>
                    </Button>
                  }
                />
              )}
              <Button
                variant={isPaintActive ? "neo-warning" : "neo"}
                onClick={onPaintClick}
                className={cn(
                  "flex flex-col h-auto items-center justify-center gap-0.5 p-1 md:p-2 group w-full min-w-0",
                  !isPaintActive && "hover:bg-[#FFD93D] hover:text-black"
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
                <span className="text-[6px] xs:text-[7px] md:text-[8px] font-black uppercase truncate w-full text-center">Canvas</span>
              </Button>
              <Button
                variant={sharedMediaOpen ? "neo" : "neo"}
                onClick={toggleSharedMedia}
                className={cn(
                  "flex flex-col h-auto items-center justify-center gap-0.5 p-1 md:p-2 hover:bg-[#C4B5FD] hover:text-black group w-full min-w-0",
                  sharedMediaOpen
                    ? "bg-[#C4B5FD] text-black"
                    : "hover:bg-[#C4B5FD] hover:text-black"
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
                <span className="text-[6px] xs:text-[7px] md:text-[8px] font-black uppercase truncate w-full text-center">View</span>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="neo" className="flex flex-col h-auto items-center justify-center gap-0.5 p-1 md:p-2 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black group w-full min-w-0">
                    <div className="p-1 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] group-hover:bg-black dark:group-hover:bg-white transition-colors">
                      <MoreHorizontal className="w-3 h-3 md:w-4 md:h-4 font-bold group-hover:text-white dark:group-hover:text-black" />
                    </div>
                    <span className="text-[6px] xs:text-[7px] md:text-[8px] font-black uppercase truncate w-full text-center">More</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuLabel>More Options</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem disabled>
                    <span>Keyboard Shortcuts</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem disabled>
                    <span>Help & Support</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        )
      }

      {/* Popover for Shared Media */}
      {
        sharedMediaOpen && (
          <div
            className={cn(
              "absolute w-[320px] md:w-[360px] flex flex-col bg-white dark:bg-[#000000] border-[3px] md:border-[4px] border-black dark:border-white rounded-xl md:rounded-2xl shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] overflow-hidden z-[1001]",
              isAnimatingOut ? "animate-popover-out" : "animate-popover-in",
              popoverPosition === "right"
                ? "left-full ml-4 md:ml-6"
                : "right-full mr-4 md:mr-6",
              verticalAlign === "bottom" ? "bottom-0" : "top-0",
            )}
            style={{
              height: popoverHeight ? `${popoverHeight}px` : 'auto',
            }}
          >
            <div ref={popoverHeaderRef} className="flex items-center justify-between p-3 md:p-3.5 border-b-[3px] md:border-b-[4px] border-black dark:border-white bg-[#FFE500]">
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
              <Button
                variant="neo"
                size="icon"
                onClick={toggleSharedMedia}
                className="hover:bg-[#FF006E] hover:text-white"
              >
                <X className="w-4 h-4 md:w-5 md:h-5 font-bold" />
              </Button>
            </div>
            <div className="flex-1 min-h-0 bg-[#FFFDF5] dark:bg-[#000000] overflow-hidden p-0 m-0">
              <MediaMixerDisplay
                canvasRef={mediaMixerCanvasRef}
                onStatusChange={setMediaMixerStatus}
                isCameraEnabled={cameraEnabled}
                isScreenShareEnabled={screenEnabled}
                isCanvasEnabled={isPaintActive}
              />
            </div>
          </div>
        )
      }
    </motion.div >
  );
}
export default memo(FloatingControlPanel);

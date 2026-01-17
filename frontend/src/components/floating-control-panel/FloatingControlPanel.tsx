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
// NOTE: Gemini Live API imports removed - using LiveKit for voice AI
// import { useTutorContext, AudioRecorder, TranscriptionData } from "../../features/tutor";
import { useLiveKit } from "../../features/livekit";
import { RoomAudioRenderer, useVoiceAssistant, AgentState, RoomContext, VideoTrack, useTracks, useParticipants, isTrackReference } from '@livekit/components-react';
import { Track } from 'livekit-client';
import '@livekit/components-styles';
// import { useLiveAPIContext } from "../../contexts/LiveAPIContext"; // Commented out - useLiveAPIContext is an alias for useTutorContext, import from correct location
// import { AudioRecorder } from "../../lib/audio-recorder"; // Commented out - AudioRecorder is exported from ../../features/tutor, not from lib
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import cn from "classnames";
import MediaMixerDisplay from "../media-mixer-display/MediaMixerDisplay";
import { ScratchpadPublisher } from "../../features/livekit/ScratchpadPublisher";
import { useTheme } from "../theme/theme-provier";
import { feedWebSocketService } from "../../services/feed-websocket-service";
import { instructionSSEService } from "../../services/instruction-sse-service";
// NOTE: Gemini types removed - using LiveKit for voice AI
// import { LiveServerContent } from '@google/genai';
// function extractTranscriptFromContent removed - no longer needed
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

// LiveKit Audio + Video Renderer component - renders inside RoomContext
function LiveKitAudioRenderer({
  onAgentStateChange,
  onVideoTrackChange
}: {
  onAgentStateChange?: (state: AgentState) => void;
  onVideoTrackChange?: (track: any) => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();

  // Debug: Log all participants when connected
  const participants = useParticipants();

  useEffect(() => {
    console.log('[LiveKit] Audio renderer mounted, agent state:', state);
    console.log('[LiveKit] Room participants:', participants.map(p => ({
      identity: p.identity,
      name: p.name,
      isLocal: p.isLocal,
      trackCount: p.trackPublications.size
    })));
  }, [state, participants]);

  // Get ALL video tracks (Hedra avatar publishes as ScreenShare or Unknown, not Camera)
  // Set onlySubscribed to false to see all available tracks, then auto-subscribe
  const videoTracks = useTracks(
    [Track.Source.Camera, Track.Source.ScreenShare, Track.Source.Unknown],
    { onlySubscribed: false }
  );

  // Log all available tracks for debugging
  useEffect(() => {
    console.log('[LiveKit] All video tracks available:', videoTracks.length);
  }, [videoTracks]);

  // Find the Hedra avatar video track
  // IMPORTANT: Hedra creates a SEPARATE participant with identity "hedra-avatar-agent"
  // The video comes from that participant, not from our main agent
  const agentVideoTrack = videoTracks.find(
    (track) => {
      const identity = track.participant.identity || '';
      const trackName = track.publication?.trackName || '';

      // Hedra avatar participant identity
      const isHedraAvatar = identity === 'hedra-avatar-agent' || identity.includes('hedra');
      // Also check for our agent or any avatar track name
      const isAgent = identity.startsWith('agent') || identity.startsWith('ai-tutor');
      const isAvatarTrack = trackName.toLowerCase().includes('avatar');
      const isNotLocalUser = !identity.startsWith('user_');

      console.log('[LiveKit] Video track candidate:', {
        identity,
        trackName,
        source: track.source,
        isHedraAvatar,
        isAgent,
        isAvatarTrack,
        isNotLocalUser,
        subscribed: track.publication?.isSubscribed
      });

      // Accept Hedra avatar, agent, or any avatar track (not from local user)
      return isNotLocalUser && (isHedraAvatar || isAgent || isAvatarTrack);
    }
  );

  useEffect(() => {
    onAgentStateChange?.(state);
    console.log('[LiveKit] Agent state:', state);
  }, [state, onAgentStateChange]);

  useEffect(() => {
    console.log('[LiveKit] Agent video track changed:', agentVideoTrack ? 'FOUND' : 'NOT FOUND');
    if (agentVideoTrack) {
      console.log('[LiveKit] Using video track:', {
        participant: agentVideoTrack.participant.identity,
        trackName: agentVideoTrack.publication?.trackName,
        source: agentVideoTrack.source,
        isSubscribed: agentVideoTrack.publication?.isSubscribed
      });

      // Auto-subscribe to the track if not already subscribed
      if (agentVideoTrack.publication && !agentVideoTrack.publication.isSubscribed) {
        console.log('[LiveKit] Auto-subscribing to avatar video track...');
        agentVideoTrack.publication.setSubscribed(true);
      }
    }
    onVideoTrackChange?.(agentVideoTrack);
  }, [agentVideoTrack, onVideoTrackChange]);

  return (
    <>
      <RoomAudioRenderer />
      {/* Video is now rendered inline in the panel, not as a floating element */}
    </>
  );
}

// Embedded Avatar Video Frame component - Compact & Clean
function AvatarVideoFrame({
  videoTrack,
  isConnected,
  agentState,
  isSpeaking
}: {
  videoTrack: any;
  isConnected: boolean;
  agentState: AgentState;
  isSpeaking: boolean;
}) {
  const isLive = isConnected && (agentState === 'listening' || agentState === 'speaking' || agentState === 'thinking');
  const hasValidTrack = videoTrack && isTrackReference(videoTrack);

  return (
    <div className="relative w-full aspect-square bg-gradient-to-b from-gray-100 to-gray-200 dark:from-neutral-800 dark:to-neutral-900 rounded-lg overflow-hidden">
      {/* Avatar Video or Placeholder */}
      {hasValidTrack ? (
        <VideoTrack
          trackRef={videoTrack}
          className="w-full h-full object-cover object-top"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <div className="w-14 h-14 rounded-full bg-[#C4B5FD] flex items-center justify-center">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
        </div>
      )}

      {/* Live indicator */}
      {isLive && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#4ADE80]" />
      )}

      {/* Connecting overlay */}
      {isConnected && agentState === 'connecting' && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <span className="text-white text-[10px] font-medium animate-pulse">Connecting...</span>
        </div>
      )}
    </div>
  );
}

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
  // NOTE: Gemini Live API removed - now using LiveKit for voice AI
  // const { client, connected, connect, disconnect, interruptAudio } = useTutorContext();

  // LiveKit integration - get room from context
  const {
    room: liveKitRoom,
    isConnected: liveKitConnected,
    isConnecting: liveKitConnecting,
    connect: connectLiveKit,
    disconnect: disconnectLiveKit,
    error: liveKitError
  } = useLiveKit();
  const [agentState, setAgentState] = useState<AgentState>('disconnected');
  const [agentVideoTrack, setAgentVideoTrack] = useState<any>(null);
  const { theme } = useTheme();
  const dragControls = useDragControls();
  // NOTE: Gemini Live API removed - using LiveKit for voice AI
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("");
  // NOTE: AudioRecorder removed - LiveKit handles audio capture
  // const [audioRecorder] = useState(() => new AudioRecorder());
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
  const [mediaMixerStatus, setMediaMixerStatus] = useState<{
    isConnected: boolean;
    error: string | null;
  }>({ isConnected: true, error: null }); // Default to connected since it's frontend-based now
  // NOTE: turnCompleteRef removed - not needed with LiveKit
  // const turnCompleteRef = useRef(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

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

  // Timer for session duration - now uses LiveKit connection state
  useEffect(() => {
    if (!liveKitConnected) {
      setSessionTime(0);
      return;
    }

    const interval = setInterval(() => {
      setSessionTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [liveKitConnected]);

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

  // NOTE: Audio is now handled by LiveKit - no need to send to Gemini directly
  // The LiveKit room captures microphone audio and streams it to the agent
  // useEffect(() => {
  //   const onData = (base64: string) => {
  //     client.sendRealtimeInput([{ mimeType: "audio/pcm;rate=16000", data: base64 }]);
  //     feedWebSocketService.sendAudio(base64);
  //   };
  //   if (connected && !muted && audioRecorder) {
  //     audioRecorder.on("data", onData).start(selectedAudioDevice);
  //   } else {
  //     audioRecorder.stop();
  //   }
  //   return () => { audioRecorder.off("data", onData); };
  // }, [connected, client, muted, audioRecorder, selectedAudioDevice]);

  // NOTE: SSE instructions are now handled by the LiveKit agent
  // useEffect(() => {
  //   const unsubscribe = instructionSSEService.onInstruction((instruction) => {
  //     if (client && client.status === "connected") {
  //       client.send({ text: instruction });
  //     }
  //   });
  //   return () => { unsubscribe(); };
  // }, [client]);

  // NOTE: Conversation turns are now handled by the LiveKit agent
  // useEffect(() => {
  //   const onTurnComplete = () => { turnCompleteRef.current = true; /* ... */ };
  //   const onInterrupted = () => { turnCompleteRef.current = true; /* ... */ };
  //   client.on('turncomplete', onTurnComplete);
  //   client.on('interrupted', onInterrupted);
  //   return () => { client.off('turncomplete', onTurnComplete); client.off('interrupted', onInterrupted); };
  // }, [client, connected]);

  // NOTE: Transcripts are now handled by the LiveKit agent
  // useEffect(() => {
  //   const onContent = (content: any) => {
  //     if (!connected) return;
  //     const transcript = extractTranscriptFromContent(content);
  //     if (transcript) { feedWebSocketService.sendTranscript(transcript, 'tutor'); }
  //   };
  //   client.on('content', onContent);
  //   return () => { client.off('content', onContent); };
  // }, [client, connected]);

  // NOTE: User/tutor transcripts are now handled by the LiveKit agent
  // useEffect(() => {
  //   const onInputTranscript = (data: TranscriptionData) => {
  //     if (!connected) return;
  //     if (data.text) { feedWebSocketService.sendTranscript(data.text, 'user'); }
  //   };
  //   client.on('inputTranscript', onInputTranscript);
  //   return () => { client.off('inputTranscript', onInputTranscript); };
  // }, [client, connected]);

  // NOTE: Output transcripts now handled by LiveKit agent
  // useEffect(() => {
  //   const onOutputTranscript = (data: TranscriptionData) => {
  //     if (!connected) return;
  //     if (data.text) { feedWebSocketService.sendTranscript(data.text, 'tutor'); }
  //   };
  //   client.on('outputTranscript', onOutputTranscript);
  //   return () => { client.off('outputTranscript', onOutputTranscript); };
  // }, [client, connected]);

  // NOTE: Video is now handled by LiveKit room - agent receives video through RoomInputOptions
  // The video_enabled: true in agent.py allows agent to receive video from the room
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }
  }, [activeVideoStream]);

  // Gemini video sending removed - LiveKit handles video streaming to agent
  // useEffect(() => {
  //   let timeoutId: number | null = null;
  //   let isRunning = false;
  //   function sendVideoFrame() {
  //     if (!connected || !isRunning) return;
  //     const canvas = mediaMixerCanvasRef.current;
  //     if (canvas && canvas.width + canvas.height > 0) {
  //       const base64 = canvas.toDataURL("image/jpeg", 1.0);
  //       const data = base64.slice(base64.indexOf(",") + 1, Infinity);
  //       client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);
  //     }
  //     if (connected && isRunning) {
  //       timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
  //     }
  //   }
  //   if (connected && !isRunning) { isRunning = true; requestAnimationFrame(sendVideoFrame); }
  //   return () => { isRunning = false; if (timeoutId !== null) clearTimeout(timeoutId); };
  // }, [connected, activeVideoStream, client]);

  // Handle session connect/disconnect - now using LiveKit only (Gemini removed)
  const handleConnect = useCallback(async () => {
    if (liveKitConnected) {
      // Handle disconnect
      console.log('[FloatingControlPanel] Disconnecting LiveKit session...');
      disconnectLiveKit();

      // Optionally disconnect optional services
      try { feedWebSocketService.disconnect(); } catch (e) { /* ignore */ }
      try { instructionSSEService.disconnect(); } catch (e) { /* ignore */ }

      // Notify TeachingAssistant of session end (optional)
      const token = jwtUtils.getToken();
      if (token) {
        try {
          await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/end`, { interrupt_audio: true });
        } catch (e) {
          // TeachingAssistant service may not be running - ignore
        }
      }
    } else {
      // Handle connect - start LiveKit voice session
      console.log('[FloatingControlPanel] Starting LiveKit voice session...');

      try {
        await connectLiveKit();
        console.log('[FloatingControlPanel] LiveKit connected, agent will auto-dispatch');

        // Optionally start TeachingAssistant session
        const token = jwtUtils.getToken();
        if (token) {
          try {
            const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/start`);
            if (response.ok) {
              try { await feedWebSocketService.connect(); } catch (e) { /* optional */ }
              try { instructionSSEService.connect(); } catch (e) { /* optional */ }
            }
          } catch (e) {
            console.warn('TeachingAssistant service not available - continuing without it');
          }
        }
      } catch (lkError) {
        console.error('[FloatingControlPanel] LiveKit connection failed:', lkError);
      }
    }
  }, [liveKitConnected, connectLiveKit, disconnectLiveKit]);

  const [verticalAlign, setVerticalAlign] = useState<"top" | "bottom">("top");

  // Calculate initial position once without state
  const initialPosition = useMemo(() => {
    if (typeof window === "undefined") return { x: 0, y: 0 };
    return { x: window.innerWidth - 200, y: 64 };
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

  const handleMute = useCallback(() => {
    setMuted(!muted);
  }, [muted]);

  // Simplified drag end handler for Framer Motion
  const handleDragEnd = useCallback(() => {
    // Recalculate popover position after drag ends
    if (sharedMediaOpen) {
      updatePopoverPosition();
    }
  }, [sharedMediaOpen, updatePopoverPosition]);

  // Memoize panel classes to avoid recalculating on every render
  // Panel width reduced ~35% to be more subordinate to content
  const panelClasses = useMemo(
    () =>
      cn(
        "fixed z-[1000] bg-[#FFFDF5] dark:bg-[#0a0a0a] border border-gray-200 dark:border-neutral-700 rounded-lg",
        isCollapsed
          ? "w-[44px] md:w-[48px] py-2 px-1 shadow-md"
          : "w-[160px] md:w-[180px] p-2 md:p-2.5 shadow-lg",
        "hover:shadow-xl transition-shadow duration-200",
      ),
    [isCollapsed],
  );

  return (
    <>
      {/* LiveKit audio rendering - uses room from context (no duplicate connection) */}
      {liveKitRoom && liveKitConnected && (
        <RoomContext.Provider value={liveKitRoom}>
          <LiveKitAudioRenderer
            onAgentStateChange={setAgentState}
            onVideoTrackChange={setAgentVideoTrack}
          />
        </RoomContext.Provider>
      )}

      {/* Publish media mixer canvas to LiveKit so agent can see student's work */}
      <ScratchpadPublisher
        room={liveKitRoom}
        canvasRef={mediaMixerCanvasRef}
        enabled={liveKitConnected}
        fps={2}
      />

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
          right: typeof window !== "undefined" ? window.innerWidth - (isCollapsed ? 48 : 180) : 1000,
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

      {/* Drag Handle & Header - Collapsed only */}
      {isCollapsed && (
        <div
          className="cursor-grab active:cursor-grabbing flex items-center justify-center mb-1 md:mb-1.5"
          onPointerDown={(e) => dragControls.start(e)}
        >
          <button
            onClick={handleCollapse}
            className="w-5 h-5 md:w-6 md:h-6 flex items-center justify-center border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] text-black dark:text-white hover:translate-x-0.5 hover:translate-y-0.5 transition-all duration-100"
          >
            <ChevronDown className="w-3 h-3 md:w-3.5 md:h-3.5 font-black" />
          </button>
        </div>
      )}

      {/* Avatar Video Frame - Expanded only */}
      {!isCollapsed && (
        <div
          className="cursor-grab active:cursor-grabbing mb-2"
          onPointerDown={(e) => dragControls.start(e)}
        >
          {/* Header row - compact */}
          <div className="flex items-center justify-end mb-1.5">
            <button
              onClick={handleCollapse}
              className="w-5 h-5 flex items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-neutral-800 text-gray-500"
            >
              <ChevronUp className="w-3 h-3" />
            </button>
          </div>

          {/* Avatar Video Frame */}
          <AvatarVideoFrame
            videoTrack={agentVideoTrack}
            isConnected={liveKitConnected}
            agentState={agentState}
            isSpeaking={agentState === 'speaking'}
          />

          {/* Status row - minimal */}
          <div className="flex items-center justify-center gap-1 mt-1.5">
            {(agentState === 'speaking' || agentState === 'listening' || agentState === 'thinking') && (
              <span className="w-1.5 h-1.5 rounded-full bg-[#4ADE80] animate-pulse" />
            )}
            <span className={cn(
              "text-[9px] font-medium",
              agentState === 'speaking' ? "text-[#16A34A]" :
              agentState === 'listening' ? "text-[#2563EB]" :
              agentState === 'thinking' ? "text-[#D97706]" :
              "text-gray-400"
            )}>
              {agentState === 'speaking' ? "Explaining" :
               agentState === 'listening' ? "Listening" :
               agentState === 'thinking' ? "Thinking" :
               agentState === 'connecting' ? "Connecting..." :
               liveKitConnected ? "Ready" : "Offline"}
            </span>
          </div>
        </div>
      )}

      {isCollapsed ? (
        // COLLAPSED VIEW - Neo-brutalist style
        <div className="flex flex-col items-center gap-1">
          {/* Start/End Session Button */}
          <button
            onClick={handleConnect}
            className={cn(
              "w-9 h-9 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none relative",
              liveKitConnected
                ? "bg-[#FF6B6B] hover:bg-[#FF6B6B] text-white"
                : "bg-[#4ADE80] hover:bg-[#4ADE80] text-black",
            )}
            title={liveKitConnected ? "End Session" : "Start Session"}
          >
            {liveKitConnected ? (
              <div className="w-3 h-3 bg-white border-2 border-black" />
            ) : (
              <PlayCircle className="w-5 h-5" />
            )}
            {liveKitConnected && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#FFD93D] border-2 border-black animate-pulse" />
            )}
          </button>

          <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />

          <button
            onClick={handleMute}
            className={cn(
              "w-8 h-8 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
              muted
                ? "bg-[#FF6B6B] text-white"
                : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
            )}
            title={muted ? "Unmute" : "Mute"}
          >
            {muted ? <MicOff className="w-3.5 h-3.5 font-bold" /> : <Mic className="w-3.5 h-3.5 font-bold" />}
          </button>

          {supportsVideo && (
            <button
              onClick={() => onToggleCamera(!cameraEnabled)}
              className={cn(
                "w-8 h-8 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                cameraEnabled
                  ? "bg-[#C4B5FD] text-black"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
              )}
              title="Toggle Camera"
            >
              {cameraEnabled ? <Video className="w-3.5 h-3.5 font-bold" /> : <VideoOff className="w-3.5 h-3.5 font-bold" />}
            </button>
          )}

          {supportsVideo && (
            <button
              onClick={() => onToggleScreen(!screenEnabled)}
              className={cn(
                "w-8 h-8 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
                screenEnabled
                  ? "bg-[#FFD93D] text-black"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D] border-black dark:border-white",
              )}
              title="Share Screen"
            >
              {screenEnabled ? <Monitor className="w-3.5 h-3.5 font-bold" /> : <MonitorOff className="w-3.5 h-3.5 font-bold" />}
            </button>
          )}

          <div className="w-7 h-[2px] bg-black dark:bg-white my-0.5" />

          <button
            onClick={onPaintClick}
            className={cn(
              "w-8 h-8 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
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
              "w-8 h-8 border-[2px] border-black flex items-center justify-center transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 duration-100",
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
              liveKitConnected
                ? "bg-[#FFD93D] text-black"
                : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white border-black dark:border-white",
            )}
          >
            {liveKitConnected ? formatTime(sessionTime) : "--:--"}
          </div>
        </div>
      ) : (
        // EXPANDED VIEW - Full Controls
        <div className="flex flex-col gap-1.5">
          {/* Main Action Button */}
          <button
            onClick={handleConnect}
            className={cn(
              "w-full py-2 font-black text-[10px] transition-all flex items-center justify-center gap-1.5 border-[2px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none uppercase",
              liveKitConnected
                ? "bg-[#FF6B6B] hover:bg-[#FF6B6B] text-black"
                : "bg-[#4ADE80] hover:bg-[#4ADE80] text-black",
            )}
          >
            {liveKitConnected ? (
              <>
                <div className="w-2.5 h-2.5 bg-white border-2 border-black" />
                End Session
              </>
            ) : (
              <>
                <PlayCircle className="w-3.5 h-3.5" />
                Start Session
              </>
            )}
          </button>

          {/* Control Grid - 2 columns */}
          <div className="grid grid-cols-2 gap-1.5 pt-1.5 border-t border-gray-200 dark:border-neutral-700">
            {/* Microphone */}
            <button
              onClick={handleMute}
              className={cn(
                "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                muted
                  ? "bg-[#FF6B6B] text-white"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD]",
              )}
              title={muted ? "Unmute" : "Mute"}
            >
              {muted ? <MicOff className="w-3 h-3" /> : <Mic className="w-3 h-3" />}
              <span className="text-[8px] font-black uppercase">{muted ? "Muted" : "Mic"}</span>
            </button>

            {/* Camera */}
            {supportsVideo && (
              <button
                onClick={() => onToggleCamera(!cameraEnabled)}
                className={cn(
                  "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                  cameraEnabled
                    ? "bg-[#C4B5FD] text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD]",
                )}
                title="Toggle Camera"
              >
                {cameraEnabled ? <Video className="w-3 h-3" /> : <VideoOff className="w-3 h-3" />}
                <span className="text-[8px] font-black uppercase">Cam</span>
              </button>
            )}

            {/* Screen Share */}
            {supportsVideo && (
              <button
                onClick={() => onToggleScreen(!screenEnabled)}
                className={cn(
                  "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                  screenEnabled
                    ? "bg-[#FFD93D] text-black"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D]",
                )}
                title="Share Screen"
              >
                {screenEnabled ? <Monitor className="w-3 h-3" /> : <MonitorOff className="w-3 h-3" />}
                <span className="text-[8px] font-black uppercase">Screen</span>
              </button>
            )}

            {/* Privacy Toggle */}
            {supportsVideo && cameraEnabled && onTogglePrivacy && (
              <button
                onClick={() => onTogglePrivacy(!privacyEnabled)}
                className={cn(
                  "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                  privacyEnabled
                    ? "bg-[#FF6B6B] text-white"
                    : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FF6B6B]",
                )}
                title={privacyEnabled ? "Disable Privacy" : "Enable Privacy"}
              >
                <VenetianMask className="w-3 h-3" />
                <span className="text-[8px] font-black uppercase">Privacy</span>
              </button>
            )}

            {/* Canvas/Paint */}
            <button
              onClick={onPaintClick}
              className={cn(
                "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                isPaintActive
                  ? "bg-[#FFD93D] text-black"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#FFD93D]",
              )}
              title="Canvas"
            >
              <PenTool className="w-3 h-3" />
              <span className="text-[8px] font-black uppercase">Canvas</span>
            </button>

            {/* View Media */}
            <button
              onClick={toggleSharedMedia}
              className={cn(
                "flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                sharedMediaOpen
                  ? "bg-[#C4B5FD] text-black"
                  : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:bg-[#C4B5FD]",
              )}
              title="View Media"
            >
              <Eye className="w-3 h-3" />
              <span className="text-[8px] font-black uppercase">View</span>
            </button>

            {/* Settings */}
            {enableEditingSettings && (
              <SettingsDialog
                className="!h-auto !block"
                trigger={
                  <button
                    className="flex items-center gap-1.5 p-1.5 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FF6B6B] text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                    title="Settings"
                  >
                    <Settings className="w-3 h-3" />
                    <span className="text-[8px] font-black uppercase">Settings</span>
                  </button>
                }
              />
            )}
          </div>

          {/* Timer row */}
          {liveKitConnected && (
            <div className="flex justify-center pt-1.5 border-t border-gray-200 dark:border-neutral-700">
              <div className={cn(
                "flex items-center gap-1 px-2 py-1 border-[2px] border-black text-[9px] font-mono font-black",
                "bg-[#FFD93D] text-black"
              )}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF6B6B] animate-pulse" />
                {formatTime(sessionTime)}
              </div>
            </div>
          )}
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
    </motion.div>
    </>
  );
}
export default memo(FloatingControlPanel);

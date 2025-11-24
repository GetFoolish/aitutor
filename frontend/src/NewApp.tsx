import { useState, useEffect, useRef } from "react";
import { LiveAPIProvider, useLiveAPIContext } from "./contexts/LiveAPIContext";
import { LiveClientOptions } from "./types";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import Scratchpad from "./components/scratchpad/Scratchpad";
import MediaMixerDisplay from "./components/media-mixer-display/MediaMixerDisplay";
import SidePanel from "./components/side-panel/SidePanel";
import { useMediaMixer } from "./hooks/use-media-mixer";
import { AudioRecorder } from "./lib/audio-recorder";
import AudioPulse from "./components/audio-pulse/AudioPulse";
import "./NewApp.scss";

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY as string;
if (typeof API_KEY !== "string") {
  throw new Error("set VITE_GEMINI_API_KEY in .env");
}

const apiOptions: LiveClientOptions = {
  apiKey: API_KEY,
};

// Type definitions
interface MediaDeviceOption {
  deviceId: string;
  label: string;
}

// Skill data for Learning Journey
interface Skill {
  id: string;
  name: string;
  mastery: number; // 0 to 1
}

const mockSkills: Skill[] = [
  { id: "add_2digit", name: "Addition (2 digits)", mastery: 0.67 },
  { id: "add_3digit", name: "Addition (3 digits)", mastery: 0.71 },
  { id: "mult_1digit", name: "Multiplication (1 digit)", mastery: 0.55 },
  { id: "sub_2digit", name: "Subtraction (2 digits)", mastery: 0.82 },
  { id: "div_1digit", name: "Division (1 digit)", mastery: 0.45 },
];

function NewAppContent() {
  const { client, connected, connect, disconnect, volume } = useLiveAPIContext();

  // Widget state
  const [isExpanded, setIsExpanded] = useState(true);
  const [sessionTime, setSessionTime] = useState(0);
  const [showMixerPanel, setShowMixerPanel] = useState(false);

  // Device states
  const [audioDevices, setAudioDevices] = useState<MediaDeviceOption[]>([]);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceOption[]>([]);
  const [selectedAudio, setSelectedAudio] = useState<string>("");
  const [selectedVideo, setSelectedVideo] = useState<string>("");
  const [inVolume, setInVolume] = useState(0);

  // Control states
  const [muted, setMuted] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isScreenShareOn, setIsScreenShareOn] = useState(false);
  const [isScratchpadOpen, setIsScratchpadOpen] = useState(false);

  // WebSocket for MediaMixer
  const [commandSocket, setCommandSocket] = useState<WebSocket | null>(null);
  const [videoSocket, setVideoSocket] = useState<WebSocket | null>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);

  // MediaMixer controls
  const { toggleCamera, toggleScreen } = useMediaMixer({ socket: commandSocket });

  // Audio recorder
  const [audioRecorder] = useState(() => new AudioRecorder());

  // Dragging state
  const [position, setPosition] = useState({ x: window.innerWidth - 420, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });
  const widgetRef = useRef<HTMLDivElement>(null);


  // Initialize WebSocket connections
  useEffect(() => {
    // Command WebSocket for sending frames/commands TO MediaMixer
    const commandWs = new WebSocket('ws://localhost:8765');
    setCommandSocket(commandWs);

    // Video WebSocket for receiving video FROM MediaMixer
    const videoWs = new WebSocket('ws://localhost:8766');
    setVideoSocket(videoWs);

    return () => {
      commandWs.close();
      videoWs.close();
    };
  }, []);

  // Timer for session
  useEffect(() => {
    if (connected) {
      const interval = window.setInterval(() => {
        setSessionTime((prev) => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setSessionTime(0);
    }
  }, [connected]);

  // Audio recording and sending to Gemini
  useEffect(() => {
    const onData = (base64: string) => {
      client.sendRealtimeInput([
        {
          mimeType: 'audio/pcm;rate=16000',
          data: base64,
        },
      ]);
    };
    if (connected && !muted && audioRecorder) {
      audioRecorder.on('data', onData).on('volume', setInVolume).start();
    } else {
      audioRecorder.stop();
    }
    return () => {
      audioRecorder.off('data', onData).off('volume', setInVolume);
    };
  }, [connected, client, muted, audioRecorder]);

  // Send video frames to Gemini
  useEffect(() => {
    let timeoutId = -1;

    function sendVideoFrame() {
      const canvas = renderCanvasRef.current;
      if (!canvas) return;

      if (canvas.width + canvas.height > 0) {
        const base64 = canvas.toDataURL('image/jpeg', 1.0);
        const data = base64.slice(base64.indexOf(',') + 1, Infinity);
        client.sendRealtimeInput([{ mimeType: 'image/jpeg', data }]);
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
  }, [connected, client, renderCanvasRef]);

  // Get available devices
  useEffect(() => {
    async function getDevices() {
      try {
        // First try to enumerate without permissions to see what's available
        let devices = await navigator.mediaDevices.enumerateDevices();

        // If labels are empty, we need to request permissions
        const needsPermission = devices.some(d => !d.label && d.deviceId);

        if (needsPermission) {
          try {
            // Request permissions
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
            // Stop the tracks immediately - we just needed permission
            stream.getTracks().forEach(track => track.stop());
            // Re-enumerate with permissions
            devices = await navigator.mediaDevices.enumerateDevices();
          } catch (permErr) {
            console.warn("Could not get media permissions:", permErr);
          }
        }

        const audioInputs = devices
          .filter((d) => d.kind === "audioinput")
          .map((d, index) => ({
            deviceId: d.deviceId,
            label: d.label || `Microphone ${index + 1}`,
          }));

        const videoInputs = devices
          .filter((d) => d.kind === "videoinput")
          .map((d, index) => ({
            deviceId: d.deviceId,
            label: d.label || `Camera ${index + 1}`,
          }));

        console.log("Found audio devices:", audioInputs);
        console.log("Found video devices:", videoInputs);

        setAudioDevices(audioInputs);
        setVideoDevices(videoInputs);

        if (audioInputs.length > 0 && !selectedAudio) setSelectedAudio(audioInputs[0].deviceId);
        if (videoInputs.length > 0 && !selectedVideo) setSelectedVideo(videoInputs[0].deviceId);
      } catch (err) {
        console.error("Error getting devices:", err);
      }
    }

    getDevices();

    // Listen for device changes
    navigator.mediaDevices.addEventListener('devicechange', getDevices);
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', getDevices);
    };
  }, []);


  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.widget-controls')) return;
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      // Get widget dimensions
      const widgetWidth = isExpanded ? 340 : 60;
      const widgetHeight = isExpanded ? 400 : 300;

      // Calculate new position
      let newX = e.clientX - dragOffset.current.x;
      let newY = e.clientY - dragOffset.current.y;

      // Constrain to viewport
      newX = Math.max(0, Math.min(newX, window.innerWidth - widgetWidth));
      newY = Math.max(0, Math.min(newY, window.innerHeight - widgetHeight));

      setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, isExpanded]);


  // Format session time
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Handle connect/disconnect
  const handleToggleConnection = () => {
    if (connected) {
      disconnect();
      setIsExpanded(true);
    } else {
      connect();
      setIsExpanded(false);
    }
  };

  return (
    <div className="new-app">
      {/* Main Content Area - Horizontal Layout */}
      <div className="main-content-area">
        {/* Gemini Console (SidePanel) */}
        <SidePanel />

        {/* Learning Journey Sidebar */}
        <aside className="learning-journey">
          <div className="journey-header">
            <h3>Learning Journey</h3>
            <span className="grade-badge">Grade 3</span>
          </div>
          <div className="skills-list">
            {mockSkills.map((skill) => (
              <div key={skill.id} className="skill-item">
                <div className="skill-info">
                  <span className="skill-name">{skill.name}</span>
                  <span className={`skill-value ${skill.mastery < 0.6 ? 'low' : ''}`}>
                    {(skill.mastery * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="skill-bar">
                  <div
                    className={`skill-progress ${skill.mastery < 0.6 ? 'low' : ''}`}
                    style={{ width: `${skill.mastery * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Question Area */}
        <main className="question-area">
          <ScratchpadCapture socket={commandSocket}>
            <QuestionDisplay />
            {isScratchpadOpen && (
              <div className="scratchpad-overlay">
                <Scratchpad />
              </div>
            )}
          </ScratchpadCapture>
        </main>

      </div>

      {/* Hidden canvas for rendering frames to send to Gemini */}
      <canvas ref={renderCanvasRef} style={{ display: 'none' }} />

      {/* Floating Loom-style Widget - Central Control Hub */}
      <div
        ref={widgetRef}
        className={`tutor-widget ${isDragging ? "dragging" : ""}`}
        style={{ left: position.x, top: position.y }}
        onMouseDown={handleMouseDown}
      >
        {isExpanded ? (
          <div className="widget-expanded">
            <div className="widget-header">
              <h2>AI TUTOR</h2>
            </div>

            <div className="widget-controls">
              {/* Microphone Selection */}
              <div className="control-row">
                <div className="control-icon">
                  <span className="material-symbols-outlined">mic</span>
                </div>
                <select
                  className="device-select"
                  value={selectedAudio}
                  onChange={(e) => setSelectedAudio(e.target.value)}
                >
                  {audioDevices.length === 0 ? (
                    <option value="">No microphones found</option>
                  ) : (
                    audioDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label}
                      </option>
                    ))
                  )}
                </select>
                <div className="audio-meter">
                  <div className="audio-level" style={{ width: `${Math.min(inVolume * 200, 100)}%` }} />
                </div>
              </div>

              {/* Camera Selection */}
              <div className="control-row">
                <div className="control-icon">
                  <span className="material-symbols-outlined">videocam</span>
                </div>
                <select
                  className="device-select"
                  value={selectedVideo}
                  onChange={(e) => setSelectedVideo(e.target.value)}
                >
                  {videoDevices.length === 0 ? (
                    <option value="">No cameras found</option>
                  ) : (
                    videoDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label}
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Screen Share */}
              <div className="control-row">
                <div className="control-icon">
                  <span className="material-symbols-outlined">screen_share</span>
                </div>
                <button
                  className="screen-share-btn"
                  onClick={() => {
                    const newState = !isScreenShareOn;
                    setIsScreenShareOn(newState);
                    toggleScreen(newState);
                  }}
                >
                  {isScreenShareOn ? "Stop sharing" : "Share screen..."}
                </button>
              </div>

              {/* Start/Connect Button */}
              <button className="start-btn" onClick={handleToggleConnection}>
                <span className="material-symbols-outlined">
                  {connected ? "stop" : "play_arrow"}
                </span>
                {connected ? "Stop Session" : "Start Session"}
              </button>
            </div>

            {/* Quick Actions */}
            <div className="widget-actions">
              <button
                className={`action-btn ${!muted ? "active" : ""}`}
                onClick={() => setMuted(!muted)}
                title="Toggle microphone"
              >
                <span className="material-symbols-outlined">
                  {!muted ? "mic" : "mic_off"}
                </span>
              </button>
              <button
                className={`action-btn ${isCameraOn ? "active" : ""}`}
                onClick={() => {
                  const newState = !isCameraOn;
                  setIsCameraOn(newState);
                  toggleCamera(newState);
                }}
                title="Toggle camera"
              >
                <span className="material-symbols-outlined">
                  {isCameraOn ? "videocam" : "videocam_off"}
                </span>
              </button>
              <button
                className={`action-btn ${isScratchpadOpen ? "active" : ""}`}
                onClick={() => setIsScratchpadOpen(!isScratchpadOpen)}
                title="Toggle scratchpad"
              >
                <span className="material-symbols-outlined">draw</span>
              </button>
              <button
                className={`action-btn ${showMixerPanel ? "active" : ""}`}
                onClick={() => setShowMixerPanel(!showMixerPanel)}
                title="Toggle media mixer"
              >
                <span className="material-symbols-outlined">grid_view</span>
              </button>
            </div>

            {/* AI Avatar */}
            <div className={`ai-avatar ${connected ? "active" : ""}`}>
              <span className="material-symbols-outlined">smart_toy</span>
              <div className="avatar-pulse" />
            </div>
          </div>
        ) : (
          /* Collapsed View - Active Session */
          <div className="widget-collapsed">
            <button
              className={`collapsed-btn ${!muted ? "active" : ""}`}
              onClick={() => setMuted(!muted)}
              title="Toggle microphone"
            >
              <span className="material-symbols-outlined">
                {!muted ? "mic" : "mic_off"}
              </span>
              {!muted && <div className="mic-indicator" />}
            </button>
            <button
              className={`collapsed-btn ${isCameraOn ? "active" : ""}`}
              onClick={() => {
                const newState = !isCameraOn;
                setIsCameraOn(newState);
                toggleCamera(newState);
              }}
              title="Toggle camera"
            >
              <span className="material-symbols-outlined">
                {isCameraOn ? "videocam" : "videocam_off"}
              </span>
            </button>
            <button
              className={`collapsed-btn ${isScratchpadOpen ? "active" : ""}`}
              onClick={() => setIsScratchpadOpen(!isScratchpadOpen)}
              title="Toggle scratchpad"
            >
              <span className="material-symbols-outlined">draw</span>
            </button>
            <button
              className={`collapsed-btn ${showMixerPanel ? "active" : ""}`}
              onClick={() => setShowMixerPanel(!showMixerPanel)}
              title="Toggle media mixer"
            >
              <span className="material-symbols-outlined">grid_view</span>
            </button>

            {/* Audio Visualizer */}
            <div className="audio-visualizer">
              <AudioPulse volume={volume} active={connected} hover={false} />
            </div>

            <div className="session-timer">{formatTime(sessionTime)}</div>
            <button className="collapsed-btn stop-btn" onClick={handleToggleConnection} title="Stop session">
              <span className="material-symbols-outlined">stop</span>
            </button>
          </div>
        )}

        {/* Media Mixer Panel - appears to the right of widget */}
        {showMixerPanel && (
          <div className="widget-mixer-panel">
            <div className="mixer-header">
              <span className="material-symbols-outlined">grid_view</span>
              <h3>Media Mixer</h3>
            </div>
            <MediaMixerDisplay socket={videoSocket} renderCanvasRef={renderCanvasRef} />
          </div>
        )}
      </div>
    </div>
  );
}

function NewApp() {
  return (
    <LiveAPIProvider options={apiOptions}>
      <NewAppContent />
    </LiveAPIProvider>
  );
}

export default NewApp;

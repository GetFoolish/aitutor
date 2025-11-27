import React, {
  memo,
  ReactNode,
  RefObject,
  useEffect,
  useRef,
  useState,
} from "react";
import Draggable from "react-draggable";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { useMediaCapture } from "../../hooks/useMediaCapture";
import { AudioRecorder } from "../../lib/audio-recorder";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import { Button } from "../ui/button";
import cn from "classnames";

import MediaMixerDisplay from "../media-mixer-display/MediaMixerDisplay";

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
  const { client, connected, connect, disconnect, volume } =
    useLiveAPIContext();
  const { cameraEnabled, screenEnabled, toggleCamera, toggleScreen } =
    useMediaCapture({ socket });
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("");
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeVideoStream, setActiveVideoStream] =
    useState<MediaStream | null>(null);
  const [sharedMediaOpen, setSharedMediaOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [popoverPosition, setPopoverPosition] = useState<{
    top?: number | string;
    left?: number | string;
    right?: number | string;
    bottom?: number | string;
  }>({});

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

  const handleConnect = async () => {
    if (connected) {
      disconnect();
    } else {
      await connect();
    }
  };

  const toggleSharedMedia = () => {
    if (!sharedMediaOpen) {
      calculatePopoverPosition();
    }
    setSharedMediaOpen(!sharedMediaOpen);
  };

  const calculatePopoverPosition = () => {
    if (!panelRef.current) return;
    const rect = panelRef.current.getBoundingClientRect();
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const popoverWidth = 480; // Increased width
    const popoverHeight = 560; // Increased height

    let pos: {
      top?: number | string;
      left?: number | string;
      right?: number | string;
      bottom?: number | string;
    } = {};

    // Horizontal positioning
    if (rect.right + popoverWidth < windowWidth) {
      pos.left = "100%"; // Open to the right
      pos.right = "auto";
    } else {
      pos.right = "100%"; // Open to the left
      pos.left = "auto";
    }

    // Vertical positioning
    // Default to aligning top, but check if it overflows bottom
    if (rect.top + popoverHeight > windowHeight) {
      pos.bottom = 0;
      pos.top = "auto";
    } else {
      pos.top = 0;
      pos.bottom = "auto";
    }

    setPopoverPosition(pos);
  };

  return (
    <Draggable handle=".panel-header" nodeRef={panelRef}>
      <div
        className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-popover border border-border rounded-3xl p-4 flex flex-col gap-4 shadow-2xl z-[1000] w-[320px] backdrop-blur-md text-popover-foreground"
        ref={panelRef}
      >
        <div className="flex justify-between items-center pb-2 border-b border-border mb-2 cursor-grab active:cursor-grabbing panel-header">
          <div className="flex items-center gap-2 font-semibold text-sm text-primary">
            <span className="material-symbols-outlined text-xl">smart_toy</span>
            AI Tutor
          </div>
          <button className="bg-transparent border-none text-muted-foreground cursor-pointer p-1 rounded-full flex items-center justify-center hover:bg-accent hover:text-accent-foreground">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {/* Audio Selector */}
          <div
            className={cn(
              "flex justify-between items-center p-2 px-3 bg-background rounded-xl border border-transparent transition-all duration-200",
              { "border-primary bg-accent": !muted },
            )}
          >
            <div
              className={cn(
                "flex items-center gap-2 text-sm font-medium text-muted-foreground",
                { "text-primary": !muted },
              )}
            >
              <span className="material-symbols-outlined text-xl">
                {muted ? "mic_off" : "mic"}
              </span>
              <select
                className="bg-transparent border-none text-inherit text-inherit font-inherit max-w-[120px] outline-none cursor-pointer truncate"
                value={selectedAudioDevice}
                onChange={(e) => setSelectedAudioDevice(e.target.value)}
                disabled={connected} // Disable changing while connected for simplicity for now
              >
                {audioDevices.map((device) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label ||
                      `Microphone ${device.deviceId.slice(0, 5)}...`}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="bg-transparent border-none text-xs font-semibold text-muted-foreground cursor-pointer p-1 px-2 rounded hover:bg-accent hover:text-accent-foreground"
              onClick={() => setMuted(!muted)}
            >
              {muted ? "Unmute" : "Mute"}
            </button>
          </div>

          {/* Camera Toggle */}
          {supportsVideo && (
            <div
              className={cn(
                "flex justify-between items-center p-2 px-3 bg-background rounded-xl border border-transparent transition-all duration-200",
                { "border-primary bg-accent": cameraEnabled },
              )}
            >
              <div
                className={cn(
                  "flex items-center gap-2 text-sm font-medium text-muted-foreground",
                  { "text-primary": cameraEnabled },
                )}
              >
                <span className="material-symbols-outlined text-xl">
                  {cameraEnabled ? "videocam" : "videocam_off"}
                </span>
                Camera
              </div>
              <button
                className="bg-transparent border-none text-xs font-semibold text-muted-foreground cursor-pointer p-1 px-2 rounded hover:bg-accent hover:text-accent-foreground"
                onClick={() => toggleCamera(!cameraEnabled)}
              >
                {cameraEnabled ? "Off" : "On"}
              </button>
            </div>
          )}

          {/* Screen Share Toggle */}
          {supportsVideo && (
            <div
              className={cn(
                "flex justify-between items-center p-2 px-3 bg-background rounded-xl border border-transparent transition-all duration-200",
                { "border-primary bg-accent": screenEnabled },
              )}
            >
              <div
                className={cn(
                  "flex items-center gap-2 text-sm font-medium text-muted-foreground",
                  { "text-primary": screenEnabled },
                )}
              >
                <span className="material-symbols-outlined text-xl">
                  {screenEnabled ? "present_to_all" : "cancel_presentation"}
                </span>
                Screen
              </div>
              <button
                className="bg-transparent border-none text-xs font-semibold text-muted-foreground cursor-pointer p-1 px-2 rounded hover:bg-accent hover:text-accent-foreground"
                onClick={() => toggleScreen(!screenEnabled)}
              >
                {screenEnabled ? "Stop" : "Share"}
              </button>
            </div>
          )}
        </div>

        {/* Main Action Button */}
        <button
          className={cn(
            "w-full p-3 rounded-xl border-none font-semibold text-base cursor-pointer transition-all duration-200",
            connected
              ? "bg-destructive text-destructive-foreground hover:opacity-90 hover:shadow-md"
              : "bg-primary text-primary-foreground hover:opacity-90 hover:shadow-md",
          )}
          onClick={handleConnect}
        >
          {connected ? "Stop Session" : "Start Session"}
        </button>

        {/* Bottom Actions */}
        <div className="flex justify-around pt-2 border-t border-border">
          {enableEditingSettings && (
            <SettingsDialog
              trigger={
                <button className="bg-transparent border-none flex flex-col items-center gap-1 text-muted-foreground text-[0.7rem] cursor-pointer p-2 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground">
                  <span className="material-symbols-outlined text-xl">
                    settings
                  </span>
                  Settings
                </button>
              }
            />
          )}
          <button
            className={cn(
              "bg-transparent border-none flex flex-col items-center gap-1 text-muted-foreground text-[0.7rem] cursor-pointer p-2 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground",
              { "text-primary bg-accent": isPaintActive },
            )}
            onClick={onPaintClick}
          >
            <span className="material-symbols-outlined text-xl">draw</span>
            Canvas
          </button>
          <button
            className={cn(
              "bg-transparent border-none flex flex-col items-center gap-1 text-muted-foreground text-[0.7rem] cursor-pointer p-2 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground",
              { "text-primary bg-accent": sharedMediaOpen },
            )}
            onClick={toggleSharedMedia}
          >
            <span className="material-symbols-outlined text-xl">
              perm_media
            </span>
            Shared Media
          </button>
          {/* Placeholder for 'More' or other actions */}
          <button className="bg-transparent border-none flex flex-col items-center gap-1 text-muted-foreground text-[0.7rem] cursor-pointer p-2 rounded-lg transition-all duration-200 hover:bg-accent hover:text-accent-foreground">
            <span className="material-symbols-outlined text-xl">
              more_horiz
            </span>
            More
          </button>
        </div>

        {sharedMediaOpen && (
          <div
            className="absolute w-[480px] h-[560px] bg-popover border border-border rounded-2xl shadow-2xl overflow-hidden z-[1001] flex flex-col animate-in fade-in zoom-in-95 duration-200"
            style={popoverPosition}
          >
            <MediaMixerDisplay
              socket={videoSocket}
              renderCanvasRef={renderCanvasRef}
            />
          </div>
        )}
      </div>
    </Draggable>
  );
}

export default memo(FloatingControlPanel);

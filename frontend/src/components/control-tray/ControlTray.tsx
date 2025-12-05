import cn from "classnames";
import { memo, ReactNode, RefObject, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { AudioRecorder } from "../../lib/audio-recorder";
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";
import AudioPulse from "../audio-pulse/AudioPulse";
import "./control-tray.scss";
import SettingsDialog from "../settings-dialog/SettingsDialog";

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

export type ControlTrayProps = {
  videoRef: RefObject<HTMLVideoElement>;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
  children?: ReactNode;
  supportsVideo: boolean;
  onVideoStreamChange?: (stream: MediaStream | null) => void;
  onMixerStreamChange?: (stream: MediaStream | null) => void;
  enableEditingSettings?: boolean;
  // Add camera/screen control props
  cameraEnabled: boolean;
  screenEnabled: boolean;
  onToggleCamera: (enabled: boolean) => void;
  onToggleScreen: (enabled: boolean) => void;
};

type MediaStreamButtonProps = {
  isStreaming: boolean;
  onIcon: string;
  offIcon: string;
  start: () => Promise<any>;
  stop: () => any;
};

const MediaStreamButton = memo(
  ({ isStreaming, onIcon, offIcon, start, stop }: MediaStreamButtonProps) =>
    isStreaming ? (
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="action-button"
        onClick={stop}
      >
        <span className="material-symbols-outlined">{onIcon}</span>
      </Button>
    ) : (
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="action-button"
        onClick={start}
      >
        <span className="material-symbols-outlined">{offIcon}</span>
      </Button>
    ),
);

function ControlTray({
  videoRef,
  renderCanvasRef,
  children,
  onVideoStreamChange = () => { },
  onMixerStreamChange = () => { },
  supportsVideo,
  enableEditingSettings,
  cameraEnabled,
  screenEnabled,
  onToggleCamera,
  onToggleScreen,
}: ControlTrayProps) {
  const { client, connected, connect, disconnect, interruptAudio, volume } =
    useLiveAPIContext();
  const [activeVideoStream, setActiveVideoStream] =
    useState<MediaStream | null>(null);
  const [inVolume, setInVolume] = useState(0);
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const connectButtonRef = useRef<HTMLButtonElement>(null);
  const turnCompleteRef = useRef(false);

  useEffect(() => {
    if (!connected && connectButtonRef.current) {
      connectButtonRef.current.focus();
    }
  }, [connected]);

  useEffect(() => {
    document.documentElement.style.setProperty(
      "--volume",
      `${Math.max(5, Math.min(inVolume * 200, 8))}px`,
    );
  }, [inVolume]);

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
      audioRecorder.on("data", onData).on("volume", setInVolume).start();
    } else {
      audioRecorder.stop();
    }
    return () => {
      audioRecorder.off("data", onData).off("volume", setInVolume);
    };
  }, [connected, client, muted, audioRecorder]);

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

    client.on("turncomplete", onTurnComplete);
    client.on("interrupted", onInterrupted);

    return () => {
      client.off("turncomplete", onTurnComplete);
      client.off("interrupted", onInterrupted);
    };
  }, [client, connected]);

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

  const handleToggleWebcam = async () => {
    await onToggleCamera(!cameraEnabled);
  };

  const handleToggleScreenShare = async () => {
    await onToggleScreen(!screenEnabled);
  };

  const handleConnect = async () => {
    // Set up setupComplete listener BEFORE connecting to avoid race condition
    let setupCompleteReceived = false;
    let setupCompleteResolver: (() => void) | null = null;

    const onSetupComplete = () => {
      setupCompleteReceived = true;
      if (setupCompleteResolver) {
        setupCompleteResolver();
        setupCompleteResolver = null;
      }
      client.off("setupcomplete", onSetupComplete);
    };
    client.on("setupcomplete", onSetupComplete);

    await connect();

    // Wait for connection to be established
    const waitForConnection = () => {
      return new Promise<void>((resolve) => {
        if (client.status === "connected") {
          resolve();
          return;
        }
        const checkConnection = () => {
          if (client.status === "connected") {
            client.off("open", checkConnection);
            resolve();
          }
        };
        client.on("open", checkConnection);
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
        if (data.prompt && client.status === "connected") {
          client.send({ text: data.prompt });
        }
      }
    } catch (error) {
      console.error("Failed to get greeting from TeachingAssistant:", error);
    } finally {
      client.off("setupcomplete", onSetupComplete);
      setupCompleteResolver = null;
    }
  };

  const handleDisconnect = async () => {
    if (!connected) return;

    try {
      interruptAudio();
      await new Promise((resolve) => setTimeout(resolve, 300));

      const token = jwtUtils.getToken();
      if (token) {
        const response = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/session/end`, { interrupt_audio: true });
        if (response.ok) {
          const data = await response.json();
          if (data.prompt && client.status === "connected") {
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

            client.on("audio", onAudio);
            client.on("turncomplete", onTurnComplete);

            client.send({ text: data.prompt }, true);

            const maxWaitTime = 30000;
            const startTime = Date.now();
            const audioSilenceTimeout = 5000;

            while (
              !goodbyeTurnComplete.current &&
              Date.now() - startTime < maxWaitTime
            ) {
              await new Promise((resolve) => setTimeout(resolve, 100));

              if (goodbyeAudioReceived.current && lastAudioTime > 0) {
                const timeSinceLastAudio = Date.now() - lastAudioTime;
                if (
                  timeSinceLastAudio > audioSilenceTimeout &&
                  goodbyeTurnComplete.current
                ) {
                  break;
                }
              }
            }

            if (goodbyeAudioReceived.current) {
              await new Promise((resolve) => setTimeout(resolve, 1500));
            }

            client.off("audio", onAudio);
            client.off("turncomplete", onTurnComplete);
          }
        }
      }
    } catch (error) {
      console.error("Failed to get goodbye from TeachingAssistant:", error);
    }

    disconnect();
  };

  return (
    <section className="control-tray">
      <canvas style={{ display: "none" }} ref={renderCanvasRef} />
      <nav className="actions-nav">
        {connected && (
          <>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className={cn("action-button mic-button")}
              onClick={() => setMuted(!muted)}
            >
              {!muted ? (
                <span className="material-symbols-outlined filled">mic</span>
              ) : (
                <span className="material-symbols-outlined filled">
                  mic_off
                </span>
              )}
            </Button>

            <div className="action-button no-action outlined">
              <AudioPulse volume={volume} active={connected} hover={false} />
            </div>
          </>
        )}

        {supportsVideo && (
          <>
            <MediaStreamButton
              isStreaming={screenEnabled}
              start={handleToggleScreenShare}
              stop={handleToggleScreenShare}
              onIcon="cancel_presentation"
              offIcon="present_to_all"
            />
            <MediaStreamButton
              isStreaming={cameraEnabled}
              start={handleToggleWebcam}
              stop={handleToggleWebcam}
              onIcon="videocam_off"
              offIcon="videocam"
            />
          </>
        )}
        {children}
      </nav>

      <div className={cn("connection-container", { connected })}>
        <div className="connection-button-container">
          <Button
            ref={connectButtonRef}
            type="button"
            size="icon"
            variant={connected ? "secondary" : "default"}
            className={cn("action-button connect-toggle", { connected })}
            onClick={connected ? handleDisconnect : handleConnect}
          >
            <span className="material-symbols-outlined filled">
              {connected ? "pause" : "play_arrow"}
            </span>
          </Button>
        </div>
        <span className="text-indicator">Streaming</span>
      </div>
      {enableEditingSettings ? <SettingsDialog /> : ""}
    </section>
  );
}

export default memo(ControlTray);

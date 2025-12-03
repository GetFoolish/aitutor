import cn from "classnames";
import { memo, ReactNode, RefObject, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { useMediaCapture } from "../../hooks/useMediaCapture";
import { AudioRecorder } from "../../lib/audio-recorder";
import AudioPulse from "../audio-pulse/AudioPulse";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import {
  useRecordConversationTurn,
  useStartTeachingSession,
  useEndTeachingSession,
  useTeachingSessionInfo,
  useTeachingInactivityCheck,
} from "@/hooks/query-hooks/useTeachingAssistantSession";

const USER_ID = "mongodb_test_user";

export type ControlTrayProps = {
  socket: WebSocket | null;
  videoRef: RefObject<HTMLVideoElement>;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
  children?: ReactNode;
  supportsVideo: boolean;
  onVideoStreamChange?: (stream: MediaStream | null) => void;
  onMixerStreamChange?: (stream: MediaStream | null) => void;
  enableEditingSettings?: boolean;
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
  socket,
  videoRef,
  renderCanvasRef,
  children,
  onVideoStreamChange = () => { },
  onMixerStreamChange = () => { },
  supportsVideo,
  enableEditingSettings,
}: ControlTrayProps) {
  const { client, connected, connect, disconnect, interruptAudio, volume } =
    useLiveAPIContext();
  const { cameraEnabled, screenEnabled, toggleCamera, toggleScreen } =
    useMediaCapture({ socket });
  const [activeVideoStream, setActiveVideoStream] =
    useState<MediaStream | null>(null);
  const [inVolume, setInVolume] = useState(0);
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const connectButtonRef = useRef<HTMLButtonElement>(null);
  const turnCompleteRef = useRef(false);

  const recordConversationTurn = useRecordConversationTurn();
  const startTeachingSession = useStartTeachingSession(USER_ID);
  const endTeachingSession = useEndTeachingSession();
  const teachingSessionInfo = useTeachingSessionInfo();
  const teachingInactivityCheck = useTeachingInactivityCheck();

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

  useEffect(() => {
    const onTurnComplete = () => {
      turnCompleteRef.current = true;

      if (connected) {
        recordConversationTurn.mutate();
      }
    };

    const onInterrupted = () => {
      turnCompleteRef.current = true;

      if (connected) {
        recordConversationTurn.mutate();
      }
    };

    client.on("turncomplete", onTurnComplete);
    client.on("interrupted", onInterrupted);

    return () => {
      client.off("turncomplete", onTurnComplete);
      client.off("interrupted", onInterrupted);
    };
  }, [client, connected, recordConversationTurn]);

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

  useEffect(() => {
    if (!connected) {
      return;
    }

    let sessionStarted = false;
    const checkSessionStart = async () => {
      try {
        const data = await teachingSessionInfo.mutateAsync();
        if (data.session_active) {
          sessionStarted = true;
        }
      } catch (error) {
        console.error("Failed to check session info:", error);
      }
    };

    const checkInactivity = async () => {
      if (!sessionStarted) {
        await checkSessionStart();
        if (!sessionStarted) {
          return;
        }
      }

      try {
        const data = await teachingInactivityCheck.mutateAsync();
        if (data.prompt && client.status === "connected") {
          client.send({ text: data.prompt });
        }
      } catch (error) {
        console.error("Failed to check inactivity:", error);
      }
    };

    const initialDelay = setTimeout(() => {
      checkInactivity();
    }, 2000);

    const intervalId = setInterval(checkInactivity, 5000);

    return () => {
      clearTimeout(initialDelay);
      clearInterval(intervalId);
    };
  }, [connected, client, teachingSessionInfo, teachingInactivityCheck]);

  const handleToggleWebcam = async () => {
    await toggleCamera(!cameraEnabled);
  };

  const handleToggleScreenShare = async () => {
    await toggleScreen(!screenEnabled);
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

    // Wait for setupComplete with timeout fallback (matches variant's approach)
    const waitForSetupComplete = () => {
      return new Promise<void>((resolve) => {
        // If already received, resolve immediately
        if (setupCompleteReceived) {
          resolve();
          return;
        }

        // Store resolver for early event handler
        setupCompleteResolver = resolve;

        // Timeout fallback: if setupComplete doesn't arrive in 2 seconds, proceed anyway
        setTimeout(() => {
          if (setupCompleteResolver === resolve) {
            setupCompleteResolver = null;
            resolve();
          }
        }, 2000);
      });
    };

    try {
      // Wait for connection
      await waitForConnection();

      // Wait for audio pipeline to be ready (with timeout fallback)
      await waitForSetupComplete();

      // Small delay like variant uses (500ms) to ensure audio pipeline is fully ready
      await new Promise((resolve) => setTimeout(resolve, 500));

      const data = await startTeachingSession.mutateAsync();
      if (data.prompt && client.status === "connected") {
        client.send({ text: data.prompt });
      }
    } catch (error) {
      console.error("Failed to get greeting from TeachingAssistant:", error);
    } finally {
      // Clean up listener if still attached
      client.off("setupcomplete", onSetupComplete);
      setupCompleteResolver = null;
    }
  };

  const handleDisconnect = async () => {
    if (!connected) return;

    try {
      interruptAudio();

      await new Promise((resolve) => setTimeout(resolve, 300));

      const data = await endTeachingSession.mutateAsync();
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

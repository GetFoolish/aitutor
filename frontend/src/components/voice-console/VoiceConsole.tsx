import React, { useEffect, useState } from "react";
import {
  ConnectButton,
  Conversation,
  Panel,
  PanelContent,
  PanelHeader,
  PanelTitle,
  UserAudioControl,
  UserScreenControl,
  UserVideoControl,
  Button,
} from "@pipecat-ai/voice-ui-kit";
import {
  PipecatClientVideo,
  usePipecatClient,
  usePipecatClientCamControl,
  usePipecatClientScreenShareControl,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { TransportState } from "@pipecat-ai/client-js";
import { MonitorOff } from "lucide-react";

interface VoiceConsoleProps {
  onConnect?: () => void | Promise<void>;
  onDisconnect?: () => void | Promise<void>;
  statusEndpoint?: string;
  commandSocket?: WebSocket | null;
}

export const VoiceConsole: React.FC<VoiceConsoleProps> = ({
  onConnect,
  onDisconnect,
  statusEndpoint,
  commandSocket,
}) => {
  const client = usePipecatClient();
  const [transportState, setTransportState] = useState<TransportState>("disconnected");
  const { isCamEnabled } = usePipecatClientCamControl();
  const { isScreenShareEnabled } = usePipecatClientScreenShareControl();
  const [showPreview, setShowPreview] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [mediaMixerScreen, setMediaMixerScreen] = useState(false);
  const [mediaMixerCamera, setMediaMixerCamera] = useState(false);

  // Debug: Log client availability
  useEffect(() => {
    console.log("[VoiceConsole] Client available:", !!client);
    console.log("[VoiceConsole] Client state:", client?.state);
  }, [client]);

  // Track connection state via events
  useRTVIClientEvent("transportStateChanged", (state) => {
    console.log("[VoiceConsole] Transport state changed:", state);
    setTransportState(state);
  });

  // Track errors
  useRTVIClientEvent("error", (error) => {
    console.error("[VoiceConsole] Error event:", error);
    console.error("[VoiceConsole] Error details:", JSON.stringify(error, null, 2));
    console.error("[VoiceConsole] Error message:", error?.message);
    console.error("[VoiceConsole] Error type:", error?.type);
    console.error("[VoiceConsole] Error code:", error?.code);
    setConnectionError(error?.message || "Connection error");
  });

  // Track connection events
  useRTVIClientEvent("connected", () => {
    console.log("[VoiceConsole] Connected!");
    setConnectionError(null);
  });

  useRTVIClientEvent("disconnected", () => {
    console.log("[VoiceConsole] Disconnected");
  });

  // Function to toggle MediaMixer screen capture
  const toggleMediaMixerScreen = () => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      const newState = !mediaMixerScreen;
      setMediaMixerScreen(newState);
      console.log(`[VoiceConsole] Toggling MediaMixer screen: ${newState}`);
      commandSocket.send(JSON.stringify({
        type: 'toggle_screen',
        data: { enabled: newState }
      }));
    }
  };

  // Function to toggle MediaMixer camera
  const toggleMediaMixerCamera = () => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      const newState = !mediaMixerCamera;
      setMediaMixerCamera(newState);
      console.log(`[VoiceConsole] Toggling MediaMixer camera: ${newState}`);
      commandSocket.send(JSON.stringify({
        type: 'toggle_camera',
        data: { enabled: newState }
      }));
    }
  };

  const isConnecting = transportState === "initializing" || transportState === "authenticating";
  const isDisconnected = transportState === "disconnected";
  const [voiceStatus, setVoiceStatus] = useState<
    "checking" | "ok" | "reachable" | "error"
  >("checking");
  const [statusDetail, setStatusDetail] = useState<string | null>(null);

  useEffect(() => {
    if (!statusEndpoint) {
      return;
    }

    let cancelled = false;

    const checkStatus = async () => {
      try {
        setStatusDetail(null);
        const response = await fetch(statusEndpoint);
        if (!response.ok) {
          const payload = await response
            .json()
            .catch(() => ({ detail: response.statusText }));
          if (!cancelled) {
            setVoiceStatus("error");
            setStatusDetail(payload?.detail ?? "Unable to reach Pipecat");
          }
          return;
        }
        const payload = await response.json().catch(() => ({}));
        if (!cancelled) {
          if (payload?.status === "reachable" && payload?.detail) {
            setVoiceStatus("reachable");
            setStatusDetail(payload.detail);
          } else {
            setVoiceStatus("ok");
            setStatusDetail(null);
          }
        }
      } catch (error: any) {
        if (!cancelled) {
          setVoiceStatus("error");
          setStatusDetail(error?.message ?? "Unable to reach Pipecat");
        }
      }
    };

    const interval = window.setInterval(checkStatus, 15000);
    checkStatus();

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [statusEndpoint]);

  const statusLabel = {
    checking: "Checking…",
    ok: "Ready",
    reachable: "Reachable",
    error: "Offline",
  }[voiceStatus];

  if (!client) {
    return (
      <div className="voice-console-panel items-center justify-center flex">
        <MonitorOff size={24} />
      </div>
    );
  }

  return (
    <Panel className="voice-console-panel">
      <PanelHeader style={{ background: 'var(--panel)', padding: '12px', borderBottom: '1px solid #1e2a3a' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Status Row */}
          <div className="status">
            <span className="status-dot" style={{ background: voiceStatus === 'ok' || voiceStatus === 'reachable' ? 'var(--success)' : 'var(--danger)' }}></span>
            <span style={{ fontWeight: 600, fontSize: '14px' }}>Tutor:</span>
            <span className={voiceStatus === 'ok' || voiceStatus === 'reachable' ? 'online' : 'offline'}>
              {transportState === 'disconnected' ? 'Offline' : transportState}
            </span>
          </div>

          {/* Control Bar */}
          <div className="controls">
            <div className="left">
              <UserAudioControl />
              <button
                onClick={toggleMediaMixerCamera}
                className="btn"
                style={{
                  padding: '6px 10px',
                  background: mediaMixerCamera ? '#0d2818' : 'var(--panel)',
                  borderColor: mediaMixerCamera ? '#2ed573' : '#2a3647',
                  fontSize: '12px',
                  minHeight: '36px'
                }}
                aria-label={mediaMixerCamera ? "Camera on" : "Camera off"}
              >
                📹 Camera
              </button>
              <button
                onClick={toggleMediaMixerScreen}
                className="btn"
                style={{
                  padding: '6px 10px',
                  background: mediaMixerScreen ? '#0d2818' : 'var(--panel)',
                  borderColor: mediaMixerScreen ? '#2ed573' : '#2a3647',
                  fontSize: '12px',
                  minHeight: '36px'
                }}
                aria-label={mediaMixerScreen ? "Screen share on" : "Screen share off"}
              >
                🖥 Screen
              </button>
            </div>
            <div className="right">
              <ConnectButton
                disabled={isConnecting}
                onConnect={onConnect}
                onDisconnect={onDisconnect}
              />
            </div>
          </div>
        </div>
      </PanelHeader>
      <PanelContent className="flex flex-col gap-4 h-full">
        <Conversation assistantLabel="Tutor" clientLabel="You" textMode="tts" />
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h2 style={{ fontSize: '14px', margin: 0 }}>
              Local preview
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview((value) => !value)}
            >
              {showPreview ? "Hide" : "Show"}
            </Button>
          </div>
          {showPreview ? (
            <div style={{ borderRadius: '12px', border: '1px solid #1e2a3a', overflow: 'hidden' }}>
              <PipecatClientVideo
                participant="local"
                trackType={isScreenShareEnabled ? "screenVideo" : "camera"}
                fit="contain"
                className="w-full aspect-video bg-black"
              />
            </div>
          ) : (
            <p className="subtle" style={{ fontSize: '12px' }}>
              {isScreenShareEnabled
                ? "Screen share ready."
                : isCamEnabled
                  ? "Camera ready."
                  : "Enable camera or screen to preview."}
            </p>
          )}
        </div>
      </PanelContent>
    </Panel>
  );
};

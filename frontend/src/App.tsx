/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState, useEffect } from "react";
import "./App.scss";
import "@pipecat-ai/voice-ui-kit/styles.scoped";
import { PipecatAppBase } from "@pipecat-ai/voice-ui-kit";
import { useAuth } from "./contexts/AuthContext";
import { LoginSignup } from "./components/auth/LoginSignup";
import { Header } from "./components/header/Header";
import { LearningPathSidebar } from "./components/learning-path/LearningPathSidebar";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import { FloatingVideoWidget } from "./components/floating-recorder/FloatingVideoWidget";

// Pipecat endpoints (not Gemini Live API)
const voiceStartEndpoint =
  (import.meta.env.VITE_VOICE_START_ENDPOINT as string) ||
  "http://localhost:7860/start";

const voiceStatusEndpoint = voiceStartEndpoint.replace("/start", "/status");

function App() {
  const { user, isLoading } = useAuth();
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  const [commandSocket, setCommandSocket] = useState<WebSocket | null>(null);
  const [videoSocket, setVideoSocket] = useState<WebSocket | null>(null);

  // Debug logging for connection - MUST be before early returns (Rules of Hooks)
  useEffect(() => {
    console.log("[App] Voice start endpoint:", voiceStartEndpoint);
    console.log("[App] Voice status endpoint:", voiceStatusEndpoint);
  }, []);

  // WebSocket setup - MUST be before early returns (Rules of Hooks)
  useEffect(() => {
    // Only create WebSocket connections when user is authenticated
    if (!user) return;

    console.log('[App] Creating MediaMixer WebSocket connections...');

    // Command WebSocket for sending frames/commands TO MediaMixer
    const commandWs = new WebSocket('ws://localhost:8765');

    commandWs.onopen = () => {
      console.log('[App] Command WebSocket (8765) connected');
    };

    commandWs.onerror = (err) => {
      console.error('[App] Command WebSocket (8765) error:', err);
    };

    commandWs.onclose = () => {
      console.log('[App] Command WebSocket (8765) closed');
    };

    setCommandSocket(commandWs);

    // Video WebSocket for receiving video FROM MediaMixer
    const videoWs = new WebSocket('ws://localhost:8766');

    videoWs.onopen = () => {
      console.log('[App] Video WebSocket (8766) connected');
    };

    videoWs.onerror = (err) => {
      console.error('[App] Video WebSocket (8766) error:', err);
    };

    videoWs.onclose = () => {
      console.log('[App] Video WebSocket (8766) closed');
    };

    setVideoSocket(videoWs);

    return () => {
      console.log('[App] Closing MediaMixer WebSockets');
      commandWs.close();
      videoWs.close();
    };
  }, [user]);

  console.log('[App] Render - isLoading:', isLoading, 'user:', user?.email);

  // Show login if not authenticated
  if (isLoading) {
    console.log('[App] Showing loading state');
    return <div style={{color: 'white', padding: '20px'}}>Loading...</div>;
  }

  if (!user) {
    console.log('[App] No user, showing LoginSignup');
    return <LoginSignup />;
  }

  console.log('[App] User authenticated, rendering main app');

  return (
    <PipecatAppBase
      transportType="daily"
      connectParams={{
        endpoint: voiceStartEndpoint,
        config: {
          enableMic: true,
          enableCam: false,
        },
        requestData: {
          createDailyRoom: true,
          user_id: user?.user_id || "demo_user",  // Pass user_id to Pipecat
          dailyRoomProperties: {
            start_video_off: true,
            start_audio_off: false,
          },
        },
      }}
      debug={true}
    >
      {({ handleConnect, handleDisconnect }) => {
        const onConnect = async () => {
          console.log("[App] Connect button clicked");
          try {
            await handleConnect();
            console.log("[App] Connection initiated");
          } catch (error) {
            console.error("[App] Connection error:", error);
          }
        };

        const onDisconnect = async () => {
          console.log("[App] Disconnect button clicked");
          try {
            await handleDisconnect();
            console.log("[App] Disconnection initiated");
          } catch (error) {
            console.error("[App] Disconnection error:", error);
          }
        };

        return (
          <div className="container">
            <div className="layout">
              {/* Header with Credits and User Profile */}
              <Header />

              {/* Main Content Grid - 2 Column Layout */}
              <div className="main">
                {/* Learning Path Sidebar */}
                <div className="sidebar">
                  <LearningPathSidebar />
                </div>

                {/* Main Content Area */}
                <div className="content">
                  {/* Question Display */}
                  <QuestionDisplay />
                </div>
              </div>
            </div>

            {/* Floating Video Widget */}
            <FloatingVideoWidget
              onConnect={onConnect}
              onDisconnect={onDisconnect}
              commandSocket={commandSocket}
            />
          </div>
        );
      }}
    </PipecatAppBase>
  );
}

export default App;

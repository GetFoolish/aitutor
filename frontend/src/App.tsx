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
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import GradingSidebar from "./components/grading-sidebar/GradingSidebar";
import Header from "./components/header/Header";
import MediaMixerDisplay from "./components/media-mixer-display/MediaMixerDisplay";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import ControlTray from "./components/control-tray/ControlTray";
import FloatingControlPanel from "./components/floating-control-panel/FloatingControlPanel";
import Scratchpad from "./components/scratchpad/Scratchpad";
import { ThemeProvider } from "./components/theme/theme-provier";
import { Toaster } from "@/components/ui/sonner";

function App() {
  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  // either the screen capture, the video or null, if null we hide it
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const mixerVideoRef = useRef<HTMLVideoElement>(null);
  const [commandSocket, setCommandSocket] = useState<WebSocket | null>(null);
  const [videoSocket, setVideoSocket] = useState<WebSocket | null>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isGradingSidebarOpen, setIsGradingSidebarOpen] = useState(false);
  const [currentSkill, setCurrentSkill] = useState<string | null>(null);

  const toggleSidebar = () => {
    if (!isSidebarOpen) setIsGradingSidebarOpen(false);
    setIsSidebarOpen(!isSidebarOpen);
  };

  const toggleGradingSidebar = () => {
    if (!isGradingSidebarOpen) setIsSidebarOpen(false);
    setIsGradingSidebarOpen(!isGradingSidebarOpen);
  };

  useEffect(() => {
    let commandWs: WebSocket | null = null;
    let videoWs: WebSocket | null = null;
    let reconnectTimeout: number | undefined;

    const connectWebSockets = () => {
      // Command WebSocket
      commandWs = new WebSocket("ws://localhost:8765/command");
      commandWs.onopen = () => {
        console.log("Command WebSocket connected");
        setCommandSocket(commandWs);
      };
      commandWs.onclose = () => {
        console.log("Command WebSocket disconnected");
        setCommandSocket(null);
      };
      commandWs.onerror = (error) => {
        console.error("Command WebSocket error:", error);
      };

      // Video WebSocket
      videoWs = new WebSocket("ws://localhost:8765/video");
      videoWs.onopen = () => {
        console.log("Video WebSocket connected");
        setVideoSocket(videoWs);
      };
      videoWs.onclose = () => {
        console.log("Video WebSocket disconnected");
        setVideoSocket(null);
        // Try to reconnect both if video fails (assuming they go down together)
        clearTimeout(reconnectTimeout);
        reconnectTimeout = window.setTimeout(connectWebSockets, 3000);
      };
      videoWs.onerror = (error) => {
        console.error("Video WebSocket error:", error);
      };
    };

    connectWebSockets();

    return () => {
      clearTimeout(reconnectTimeout);
      if (commandWs) commandWs.close();
      if (videoWs) videoWs.close();
    };
  }, []);

  useEffect(() => {
    if (mixerVideoRef.current && mixerStream) {
      mixerVideoRef.current.srcObject = mixerStream;
    }
  }, [mixerStream]);

  return (
    <ThemeProvider defaultTheme="light" storageKey="ai-tutor-theme">
      <div className="App">
        <LiveAPIProvider>
          <Header
            sidebarOpen={isSidebarOpen}
            onToggleSidebar={toggleSidebar}
          />
          <div className="streaming-console">
            <SidePanel
              open={isSidebarOpen}
              onToggle={toggleSidebar}
            />
            <GradingSidebar
              open={isGradingSidebarOpen}
              onToggle={toggleGradingSidebar}
              currentSkill={currentSkill}
            />
            <main style={{
              marginRight: isSidebarOpen ? "420px" : "0",
              marginLeft: isGradingSidebarOpen ? "420px" : "60px",
              transition: "all 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
            }}>
              <div className="main-app-area">
                <div className="question-panel">
                  <ScratchpadCapture socket={commandSocket}>
                    <QuestionDisplay onSkillChange={setCurrentSkill} />
                    {isScratchpadOpen && (
                      <div className="scratchpad-container">
                        <Scratchpad />
                      </div>
                    )}
                  </ScratchpadCapture>
                </div>
                <FloatingControlPanel
                  socket={commandSocket}
                  renderCanvasRef={renderCanvasRef}
                  videoRef={videoRef}
                  supportsVideo={true}
                  onVideoStreamChange={setVideoStream}
                  onMixerStreamChange={setMixerStream}
                  enableEditingSettings={true}
                  onPaintClick={() => setScratchpadOpen(!isScratchpadOpen)}
                  isPaintActive={isScratchpadOpen}
                  videoSocket={videoSocket}
                />
              </div>
            </main>
          </div>
          <Toaster richColors closeButton />
        </LiveAPIProvider>
      </div>
    </ThemeProvider>
  );
}

export default App;

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
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import AuthGuard from "./components/auth/AuthGuard";
import SidePanel from "./components/side-panel/SidePanel";
import GradingSidebar from "./components/grading-sidebar/GradingSidebar";
import Header from "./components/header/Header";
import BackgroundShapes from "./components/background-shapes/BackgroundShapes";
import ScratchpadCapture from "./components/scratchpad-capture/ScratchpadCapture";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import FloatingControlPanel from "./components/floating-control-panel/FloatingControlPanel";
import Scratchpad from "./components/scratchpad/Scratchpad";
import { ThemeProvider } from "./components/theme/theme-provier";
import { Toaster } from "@/components/ui/sonner";
import { useMediaMixer } from "./hooks/useMediaMixer";
import { useMediaCapture } from "./hooks/useMediaCapture";

function App() {
  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  // either the screen capture, the video or null, if null we hide it
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const mixerVideoRef = useRef<HTMLVideoElement>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isGradingSidebarOpen, setIsGradingSidebarOpen] = useState(false);
  const [currentSkill, setCurrentSkill] = useState<string | null>(null);

  // Ref to hold mediaMixer instance for use in callbacks
  const mediaMixerRef = useRef<any>(null);

  // Media capture with frame callbacks - must be called before useMediaMixer
  const { cameraEnabled, screenEnabled, toggleCamera, toggleScreen } = useMediaCapture({
    onCameraFrame: (imageData) => {
      mediaMixerRef.current?.updateCameraFrame(imageData);
    },
    onScreenFrame: (imageData) => {
      mediaMixerRef.current?.updateScreenFrame(imageData);
    }
  });

  // MediaMixer hook for local video mixing - uses state from useMediaCapture
  const mediaMixer = useMediaMixer({
    width: 1280,
    height: 2160,
    fps: 10,
    quality: 0.85,
    cameraEnabled: cameraEnabled,
    screenEnabled: screenEnabled
  });

  // Store mediaMixer in ref for use in callbacks
  useEffect(() => {
    mediaMixerRef.current = mediaMixer;
  }, [mediaMixer]);

  // Start mixer when component mounts and canvas is available
  useEffect(() => {
    if (mediaMixer.canvasRef.current) {
      mediaMixer.setIsRunning(true);
      return () => {
        mediaMixer.setIsRunning(false);
      };
    }
  }, [mediaMixer]);

  const toggleSidebar = () => {
    if (!isSidebarOpen) setIsGradingSidebarOpen(false);
    setIsSidebarOpen(!isSidebarOpen);
  };

  const toggleGradingSidebar = () => {
    if (!isGradingSidebarOpen) setIsSidebarOpen(false);
    setIsGradingSidebarOpen(!isGradingSidebarOpen);
  };

  useEffect(() => {
    if (mixerVideoRef.current && mixerStream) {
      mixerVideoRef.current.srcObject = mixerStream;
    }
  }, [mixerStream]);

  return (
    <ThemeProvider defaultTheme="light" storageKey="ai-tutor-theme">
      <div className="App">
        <AuthGuard>
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
                marginRight: isSidebarOpen ? "260px" : "0",
                marginLeft: isGradingSidebarOpen ? "260px" : "40px",
                transition: "all 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
              }}>
                <div className="main-app-area">
                  <div className="question-panel">
                    <BackgroundShapes />
                    <ScratchpadCapture onFrameCaptured={(imageData) => {
                      mediaMixer.updateScratchpadFrame(imageData);
                    }}>
                      <QuestionDisplay onSkillChange={setCurrentSkill} />
                      {isScratchpadOpen && (
                        <div className="scratchpad-container">
                          <Scratchpad />
                        </div>
                      )}
                    </ScratchpadCapture>
                  </div>
                  <FloatingControlPanel
                    renderCanvasRef={mediaMixer.canvasRef}
                    videoRef={videoRef}
                    supportsVideo={true}
                    onVideoStreamChange={setVideoStream}
                    onMixerStreamChange={setMixerStream}
                    enableEditingSettings={true}
                    onPaintClick={() => setScratchpadOpen(!isScratchpadOpen)}
                    isPaintActive={isScratchpadOpen}
                    cameraEnabled={cameraEnabled}
                    screenEnabled={screenEnabled}
                    onToggleCamera={toggleCamera}
                    onToggleScreen={toggleScreen}
                    mediaMixerCanvasRef={mediaMixer.canvasRef}
                  />
                </div>
              </main>
            </div>
            <Toaster richColors closeButton />
          </LiveAPIProvider>
        </AuthGuard>
      </div>
    </ThemeProvider>
  );
}

export default App;

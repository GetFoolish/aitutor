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

import { useRef, useState, useEffect, Suspense, lazy } from "react";
import "./App.scss";
import "./styles/mobile-fixes.css"; // Mobile UI fixes
import { TutorProvider } from "./features/tutor";
import AuthGuard from "./components/auth/AuthGuard";
import AssessmentGuard from "./components/auth/AssessmentGuard";
import Header from "./components/header/Header";
import BackgroundShapes from "./components/background-shapes/BackgroundShapes";
import QuestionDisplay from "./components/question-display/QuestionDisplay";
import Scratchpad from "./components/scratchpad/Scratchpad";
import { ThemeProvider } from "./components/theme/theme-provier";
import { HintProvider } from "./contexts/HintContext";
import { Toaster } from "@/components/ui/sonner";
import { useMediaMixer } from "./hooks/useMediaMixer";
import { useMediaCapture } from "./hooks/useMediaCapture";
import { useDeveloperMode } from "./hooks/use-developer-mode";

// Lazy load heavy components
const SidePanel = lazy(() => import("./components/side-panel/SidePanel"));
const GradingSidebar = lazy(() => import("./components/grading-sidebar/GradingSidebar"));
const ScratchpadCapture = lazy(() => import("./components/scratchpad-capture/ScratchpadCapture"));
const FloatingControlPanel = lazy(() => import("./components/floating-control-panel/FloatingControlPanel"));
const LearningAssetsPanel = lazy(() => import("./components/learning-assets/LearningAssetsPanel"));

function App() {
  // Developer mode hook for Gemini Console visibility
  const { isDeveloperMode, toggleDeveloperMode } = useDeveloperMode();

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
  const [currentQuestionId, setCurrentQuestionId] = useState<string | null>(null);
  const [watchedVideoIds, setWatchedVideoIds] = useState<string[]>([]);

  // Ref to hold mediaMixer instance for use in callbacks
  const mediaMixerRef = useRef<any>(null);

  // Media capture with frame callbacks - must be called before useMediaMixer
  const {
    cameraEnabled,
    screenEnabled,
    toggleCamera,
    toggleScreen,
    cameraVideoRef,
    screenVideoRef,
    privacyMode,
    setPrivacyMode,
    processedEdgesRef
  } = useMediaCapture({});

  // MediaMixer hook for local video mixing - uses state from useMediaCapture
  const mediaMixer = useMediaMixer({
    width: 1280,
    height: 2160,
    fps: 2,  // Reduced from 10 to 2 FPS for better performance
    quality: 0.85,
    cameraEnabled: cameraEnabled,
    screenEnabled: screenEnabled,
    cameraVideoRef: cameraVideoRef,
    screenVideoRef: screenVideoRef
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

  // Keyboard shortcut for developer mode (Ctrl+Shift+D)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        toggleDeveloperMode();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleDeveloperMode]);

  return (
    <ThemeProvider defaultTheme="light" storageKey="ai-tutor-theme">
      <div className="App">
        <AuthGuard>
          <AssessmentGuard subject="math">
            <TutorProvider>
              <HintProvider>
                <Header
                  sidebarOpen={isSidebarOpen}
                  onToggleSidebar={toggleSidebar}
                />

                {/* Single FloatingControlPanel - now safely inside TutorProvider */}
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
                  privacyMode={privacyMode}
                  onTogglePrivacy={setPrivacyMode}
                  processedEdgesRef={processedEdgesRef}
                  assessmentMode={true}
                />

                <div className="streaming-console">
                  <Suspense fallback={<div className="flex items-center justify-center h-full w-full">Loading...</div>}>
                    {isDeveloperMode && (
                      <SidePanel
                        open={isSidebarOpen}
                        onToggle={toggleSidebar}
                      />
                    )}
                    {!isDeveloperMode && (
                      <LearningAssetsPanel
                        questionId={currentQuestionId}
                        open={isSidebarOpen}
                        onToggle={toggleSidebar}
                        onVideosWatched={setWatchedVideoIds}
                        isDeveloperMode={isDeveloperMode}
                      />
                    )}
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
                          <ScratchpadCapture onFrameCaptured={(canvas) => {
                            mediaMixer.updateScratchpadFrame(canvas);
                          }}>
                            <QuestionDisplay 
                              onSkillChange={setCurrentSkill}
                              onQuestionChange={setCurrentQuestionId}
                              watchedVideoIds={watchedVideoIds}
                              onAnswerSubmitted={() => setWatchedVideoIds([])}
                            />
                            {isScratchpadOpen && (
                              <div className="scratchpad-container">
                                <Scratchpad />
                              </div>
                            )}
                          </ScratchpadCapture>
                        </div>
                      </div>
                    </main>
                  </Suspense>
                </div>
                <Toaster richColors closeButton />
              </HintProvider>
            </TutorProvider>
          </AssessmentGuard>
        </AuthGuard>
      </div>
    </ThemeProvider>
  );
}

export default App;

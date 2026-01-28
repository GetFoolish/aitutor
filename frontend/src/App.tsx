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
import { apiUtils } from "./lib/api-utils";
import { homeworkService } from "./services/homework-service";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

// Lazy load heavy components
const SidePanel = lazy(() => import("./components/side-panel/SidePanel"));
const GradingSidebar = lazy(() => import("./components/grading-sidebar/GradingSidebar"));
const ScratchpadCapture = lazy(() => import("./components/scratchpad-capture/ScratchpadCapture"));
const FloatingControlPanel = lazy(() => import("./components/floating-control-panel/FloatingControlPanel"));
const LearningAssetsPanel = lazy(() => import("./components/side-panel/LearningAssetsPanel"));
const HomeworkView = lazy(() => import("./components/homework-view/HomeworkView"));

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
  const [isGradingSidebarOpen, setIsGradingSidebarOpen] = useState(true);
  const [currentSkill, setCurrentSkill] = useState<string | null>(null);
  const [currentQuestionId, setCurrentQuestionId] = useState<string | null>(null);
  const [watchedVideoIds, setWatchedVideoIds] = useState<string[]>([]);
  
  // Homework mode state
  const [homeworkMode, setHomeworkMode] = useState(false);
  const [homeworkRefreshKey, setHomeworkRefreshKey] = useState(0);
  const [homeworkQuestions, setHomeworkQuestions] = useState<Array<{id: string; number: number; text: string; answered: boolean; correct?: boolean; bbox?: {left: number; top: number; right: number; bottom: number; page?: number}}>>([]);
  const [currentHomeworkQuestionIndex, setCurrentHomeworkQuestionIndex] = useState(0);
  const [homeworkImageUrl, setHomeworkImageUrl] = useState<string | null>(null);
  const [homeworkFileType, setHomeworkFileType] = useState<string | null>(null);
  const [currentHomeworkId, setCurrentHomeworkId] = useState<string | null>(null);
  const [homeworkCurrentPage, setHomeworkCurrentPage] = useState(0);
  const [homeworkTotalPages, setHomeworkTotalPages] = useState(1);

  // Assessment mode state
  const [assessmentMode, setAssessmentMode] = useState(false);
  const [assessmentSubject, setAssessmentSubject] = useState<string | null>(null);
  const [assessmentQuestions, setAssessmentQuestions] = useState<any[]>([]);
  const [assessmentCurrentIndex, setAssessmentCurrentIndex] = useState(0);
  const [assessmentAnswers, setAssessmentAnswers] = useState<any[]>([]);

  // Ref to hold mediaMixer instance for use in callbacks
  const mediaMixerRef = useRef<any>(null);

  // Media capture with frame callbacks - must be called before useMediaMixer
  const {
    cameraEnabled,
    screenEnabled,
    toggleCamera,
    toggleScreen,
    cameraVideoRef,
    screenVideoRef
  } = useMediaCapture({});

  const [privacyEnabled, setPrivacyEnabled] = useState(false);

  // MediaMixer hook for local video mixing - uses state from useMediaCapture
  const mediaMixer = useMediaMixer({
    width: 1280,
    height: 2160,
    fps: 2,  // Reduced from 10 to 2 FPS for better performance
    quality: 0.85,
    cameraEnabled: cameraEnabled,
    screenEnabled: screenEnabled,
    privacyEnabled: privacyEnabled,
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

  const toggleHomeworkMode = () => {
    console.log('[App] toggleHomeworkMode called, current:', homeworkMode, '-> new:', !homeworkMode);
    setHomeworkMode(!homeworkMode);
  };

  // Assessment functions
  const startAssessment = async (subject: string) => {
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/assessment/start/${subject}`, {});
      
      if (!response.ok) {
        throw new Error(`Failed to start assessment: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        // Already completed - show results
        alert(`You've already completed this assessment! Score: ${data.score}/${data.total || 0}`);
        return;
      }

      // Enter assessment mode
      setAssessmentMode(true);
      setAssessmentSubject(subject);
      setAssessmentQuestions(data.questions);
      setAssessmentCurrentIndex(0);
      setAssessmentAnswers([]);
      // Hide both sidebars
      setIsSidebarOpen(false);
      setIsGradingSidebarOpen(false);
    } catch (error) {
      console.error('Failed to start assessment:', error);
      alert('Failed to start assessment. Please try again.');
    }
  };

  const submitAssessment = async (finalAnswers: any[]) => {
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/assessment/complete`, {
        subject: assessmentSubject,
        answers: finalAnswers
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to complete assessment: ${response.status}`);
      }

      const data = await response.json();
      
      // Exit assessment mode
      setAssessmentMode(false);
      setAssessmentSubject(null);
      setAssessmentQuestions([]);
      setAssessmentCurrentIndex(0);
      setAssessmentAnswers([]);
      
      // Show results
      alert(`Assessment Complete!\nScore: ${data.score}/${data.total}\nGrade Level: ${data.estimated_grade || 'Calculating...'}`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to complete assessment';
      console.error('Failed to complete assessment:', err);
      alert(errorMessage);
    }
  };

  // Expose startAssessment globally for testing
  useEffect(() => {
    (window as any).startAssessment = startAssessment;
    (window as any).exitAssessmentMode = () => {
      setAssessmentMode(false);
      setAssessmentSubject(null);
      setAssessmentQuestions([]);
      setAssessmentCurrentIndex(0);
      setAssessmentAnswers([]);
    };
  }, []);

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
          <AssessmentGuard subject="math" onStartAssessment={startAssessment}>
            <TutorProvider>
              <HintProvider>
                <Header
                  sidebarOpen={isSidebarOpen}
                  onToggleSidebar={toggleSidebar}
                  homeworkMode={homeworkMode}
                  onHomeworkClick={toggleHomeworkMode}
                />

                <div className="streaming-console">
                  <Suspense fallback={<div className="flex items-center justify-center h-full w-full">Loading...</div>}>
                    {/* Sidebars - Always visible */}
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
                      homeworkMode={homeworkMode}
                      homeworkImageUrl={homeworkImageUrl}
                      homeworkFileType={homeworkFileType}
                      homeworkQuestions={homeworkQuestions}
                      currentHomeworkQuestionIndex={currentHomeworkQuestionIndex}
                      onHomeworkQuestionClick={setCurrentHomeworkQuestionIndex}
                      onHomeworkUpload={async (file) => {
                        console.log('[App] onHomeworkUpload called, activating homework mode');
                        // First enable homework mode BEFORE upload
                        setHomeworkMode(true);
                        // Upload the file
                        await homeworkService.uploadHomework(file);
                        console.log('[App] Upload complete, incrementing refresh key');
                        // Increment refresh key to trigger HomeworkView refresh
                        setHomeworkRefreshKey(prev => prev + 1);
                        // Ensure homework mode stays active
                        setTimeout(() => {
                          console.log('[App] Ensuring homework mode is still active');
                          setHomeworkMode(true);
                        }, 100);
                      }}
                      onHomeworkDelete={async () => {
                        if (currentHomeworkId) {
                          await homeworkService.deleteHomework(currentHomeworkId);
                          // Clear homework state
                          setHomeworkImageUrl(null);
                          setHomeworkFileType(null);
                          setHomeworkQuestions([]);
                          setCurrentHomeworkQuestionIndex(0);
                          setCurrentHomeworkId(null);
                          // Refresh to load next homework if any
                          setHomeworkRefreshKey(prev => prev + 1);
                        }
                      }}
                      currentPage={homeworkCurrentPage}
                      totalPages={homeworkTotalPages}
                    />

                    {/* Main Content Area */}
                    <main style={{
                      marginRight: isSidebarOpen ? "260px" : "0",
                      marginLeft: isGradingSidebarOpen ? "260px" : "40px",
                      transition: "all 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
                    }}>
                      <div className="main-app-area">
                        <div className="question-panel">
                          <BackgroundShapes />
                          {homeworkMode ? (
                            /* Homework Mode - Show document viewer */
                            <HomeworkView
                              key={homeworkRefreshKey}
                              onClose={toggleHomeworkMode}
                              onQuestionsExtracted={(questions) => {
                                console.log('[App] onQuestionsExtracted called with', questions.length, 'questions:', questions);
                                setHomeworkQuestions(questions);
                                setCurrentHomeworkQuestionIndex(0);
                              }}
                              onQuestionIndexChange={(index) => {
                                console.log('[App] onQuestionIndexChange called with index:', index);
                                setCurrentHomeworkQuestionIndex(index);
                              }}
                              currentQuestionIndex={currentHomeworkQuestionIndex}
                              onImageUrlChange={setHomeworkImageUrl}
                              onFileTypeChange={setHomeworkFileType}
                              onHomeworkIdChange={setCurrentHomeworkId}
                              onPageInfoChange={(page, total) => {
                                setHomeworkCurrentPage(page);
                                setHomeworkTotalPages(total);
                              }}
                            />
                          ) : (
                            /* Normal Mode - Show Perseus questions */
                            <ScratchpadCapture onFrameCaptured={(canvas) => {
                              mediaMixer.updateScratchpadFrame(canvas);
                            }}>
                              <QuestionDisplay
                                onSkillChange={setCurrentSkill}
                                onQuestionChange={setCurrentQuestionId}
                                watchedVideoIds={watchedVideoIds}
                                onAnswerSubmitted={() => setWatchedVideoIds([])}
                                assessmentMode={assessmentMode}
                                assessmentQuestions={assessmentQuestions}
                                currentQuestionIndex={assessmentCurrentIndex}
                                onAssessmentAnswer={(questionId, isCorrect) => {
                                  const currentQuestion = assessmentQuestions[assessmentCurrentIndex];
                                  const newAnswer = {
                                    question_id: questionId,
                                    skill_id: currentQuestion.dash_metadata.skill_ids[0],
                                    is_correct: isCorrect
                                  };
                                  const newAnswers = [...assessmentAnswers, newAnswer];
                                  setAssessmentAnswers(newAnswers);
                                  setWatchedVideoIds([]);

                                  if (assessmentCurrentIndex < assessmentQuestions.length - 1) {
                                    setTimeout(() => {
                                      setAssessmentCurrentIndex(assessmentCurrentIndex + 1);
                                    }, 2000);
                                  } else {
                                    setTimeout(() => {
                                      submitAssessment(newAnswers);
                                    }, 2000);
                                  }
                                }}
                              />
                              {isScratchpadOpen && (
                                <div className="scratchpad-container">
                                  <Scratchpad />
                                </div>
                              )}
                            </ScratchpadCapture>
                          )}
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
                          privacyMode={privacyEnabled}
                          onTogglePrivacy={setPrivacyEnabled}
                          mediaMixerCanvasRef={mediaMixer.canvasRef}
                          processedEdgesRef={mediaMixer.processedEdgesRef}
                          assessmentMode={assessmentMode}
                        />
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

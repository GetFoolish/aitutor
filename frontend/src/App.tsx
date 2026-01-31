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
import { useAuth } from "./contexts/AuthContext";
import { MemoryDebugInitializer } from "./components/memory-debug/MemoryDebugInitializer";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const CONTENT_API_URL = import.meta.env.VITE_CONTENT_API_URL || 'http://localhost:8001';
const USE_GENERATED_QUESTIONS = import.meta.env.VITE_USE_GENERATED_QUESTIONS === 'true';

// Lazy load heavy components
const SidePanel = lazy(() => import("./components/side-panel/SidePanel"));
const GradingSidebar = lazy(() => import("./components/grading-sidebar/GradingSidebar"));
const ScratchpadCapture = lazy(() => import("./components/scratchpad-capture/ScratchpadCapture"));
const FloatingControlPanel = lazy(() => import("./components/floating-control-panel/FloatingControlPanel"));
const LearningAssetsPanel = lazy(() => import("./components/side-panel/LearningAssetsPanel"));
const QuestionConfig = lazy(() => import("./components/question-config/QuestionConfig"));
const BiographyPanel = lazy(() => import("./components/biography-panel/BiographyPanel"));

function App() {
  const { user } = useAuth();
  // Developer mode hook for Gemini Console visibility
  const { isDeveloperMode, toggleDeveloperMode } = useDeveloperMode();

  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  const processedEdgesRef = useRef<ImageData | null>(null);
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
  
  // Assessment mode state
  const [assessmentMode, setAssessmentMode] = useState(false);
  const [assessmentSubject, setAssessmentSubject] = useState<string | null>(null);
  const [assessmentQuestions, setAssessmentQuestions] = useState<any[]>([]);
  const [assessmentCurrentIndex, setAssessmentCurrentIndex] = useState(0);
  const [assessmentAnswers, setAssessmentAnswers] = useState<any[]>([]);
  
  // Question configuration state (subject/grade/language picker)
  const [showQuestionConfig, setShowQuestionConfig] = useState(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);

  // Biography panel state (Living Biography / Memory panel)
  const [isBiographyPanelOpen, setIsBiographyPanelOpen] = useState(false);

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

  // Assessment functions
  const startAssessment = async (subject: string, config?: { grade?: string; language?: string; count?: number; topic?: string }) => {
    try {
      let questions = [];
      const grade = config?.grade || '3-5';
      const language = config?.language || 'en';
      const count = config?.count || 10;
      const topic = config?.topic || subject;

      // Use Generated Questions API (Innocent Drinks style) if enabled
      if (USE_GENERATED_QUESTIONS) {
        console.log(`🍪 Using Generated Questions: topic="${topic}", subject=${subject}, ${grade}, ${language}, ${count} questions`);
        
        const userId = user?.user_id;
        const genUrl = userId
          ? `${CONTENT_API_URL}/api/generate/personalized?student_id=${encodeURIComponent(userId)}`
          : `${CONTENT_API_URL}/api/generate/live`;

        // Try live generation with language support
        const genResponse = await fetch(genUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: topic,
            grade: grade,
            subject: subject,
            language: language,
            count: count
          })
        });
        
        if (genResponse.ok) {
          questions = await genResponse.json();
          console.log(`✅ Loaded ${questions.length} generated questions`);
        } else {
          // Fallback to static generated questions
          const fallbackResponse = await fetch(`${CONTENT_API_URL}/api/generated/questions/${count}?grade=${grade}&subject=${subject}`);
          if (fallbackResponse.ok) {
            questions = await fallbackResponse.json();
            console.log(`✅ Loaded ${questions.length} questions from static pool`);
          } else {
            console.warn('Generated questions not available, falling back to DASH API');
          }
        }
      }

      // Fallback to DASH API if no generated questions
      if (questions.length === 0) {
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
        questions = data.questions;
      }

      // Enter assessment mode
      setAssessmentMode(true);
      setAssessmentSubject(subject);
      setAssessmentQuestions(questions);
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

  // Handler for question config submission
  const handleQuestionConfigStart = async (config: { subject: string; grade: string; language: string; count: number; topic: string }) => {
    setIsLoadingQuestions(true);
    try {
      localStorage.setItem('learning_pref_topic', config.topic);
      localStorage.setItem('learning_pref_grade', config.grade);
      localStorage.setItem('learning_pref_subject', config.subject);
      localStorage.setItem('learning_pref_language', config.language);
      await startAssessment(config.subject, {
        grade: config.grade,
        language: config.language,
        count: config.count,
        topic: config.topic
      });
      setShowQuestionConfig(false);
    } catch (error) {
      console.error('Failed to start with config:', error);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Expose startAssessment globally for testing
  useEffect(() => {
    (window as any).startAssessment = startAssessment;
    (window as any).showQuestionConfig = () => setShowQuestionConfig(true);
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
          {/* Initialize memory debug functions for console testing (window.memoryDebug) */}
          <MemoryDebugInitializer />
<AssessmentGuard subject="math" onStartAssessment={startAssessment}>
            <TutorProvider>
              <HintProvider>
                <Header
                  sidebarOpen={isSidebarOpen}
                  onToggleSidebar={toggleSidebar}
                />

                {/* Question Config Modal */}
                {showQuestionConfig && (
                  <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    zIndex: 1000,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <div style={{
                      backgroundColor: 'var(--neo-bg, #FFF8E7)',
                      border: '4px solid var(--neo-black, #000)',
                      boxShadow: '8px 8px 0 var(--neo-black, #000)',
                      maxWidth: '650px',
                      maxHeight: '90vh',
                      overflow: 'auto',
                      position: 'relative',
                    }}>
                      <button
                        onClick={() => setShowQuestionConfig(false)}
                        style={{
                          position: 'absolute',
                          top: '12px',
                          right: '12px',
                          background: 'none',
                          border: 'none',
                          fontSize: '24px',
                          cursor: 'pointer',
                        }}
                      >
                        ✕
                      </button>
                      <Suspense fallback={<div>Loading...</div>}>
                        <QuestionConfig 
                          onStart={handleQuestionConfigStart}
                          isLoading={isLoadingQuestions}
                        />
                      </Suspense>
                    </div>
                  </div>
                )}

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
                        open={isSidebarOpen}
                        onToggle={toggleSidebar}
                      />
                    )}
                    <GradingSidebar
                      open={isGradingSidebarOpen}
                      onToggle={toggleGradingSidebar}
                      currentSkill={currentSkill}
                      onShowQuestionConfig={() => setShowQuestionConfig(true)}
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
                          processedEdgesRef={processedEdgesRef}
                          assessmentMode={assessmentMode}
                          onBiographyClick={() => setIsBiographyPanelOpen(!isBiographyPanelOpen)}
                          isBiographyActive={isBiographyPanelOpen}
                        />
                        <BiographyPanel
                          isOpen={isBiographyPanelOpen}
                          onClose={() => setIsBiographyPanelOpen(false)}
                          position="right"
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

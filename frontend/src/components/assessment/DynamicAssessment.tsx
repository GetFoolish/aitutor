/**
 * Dynamic Assessment Flow
 *
 * Uses on-the-fly generated questions based on user's age and selected topics.
 * Shows progress, difficulty indicators, and creates learning path on completion.
 */
import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { useHistory, useLocation, Redirect } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import Header from '../header/Header';
import RendererComponent from '../question-widget-renderer/RendererComponent';
import { HintProvider } from '../../contexts/HintContext';
import { TutorProvider } from '../../features/tutor';
import { Button } from '@/components/ui/button';
import { useMediaCapture } from '../../hooks/useMediaCapture';
import { useMediaMixer } from '../../hooks/useMediaMixer';
import '../auth/auth.scss';

// Lazy load heavy components
const FloatingControlPanel = lazy(() => import('../floating-control-panel/FloatingControlPanel'));
const BiographyPanel = lazy(() => import('../biography-panel/BiographyPanel'));

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
// EXTREME NEO-BRUTALISM: Hide all debug info by default
const SHOW_DEBUG_BANNER = false;
const SHOW_DEBUG_FORCE_ERROR = false;
type LoadSource = 'nav' | 'cache' | 'api' | 'unknown';

/**
 * Fixes malformed widget options before rendering.
 * The AI sometimes generates radio widgets in wrong format.
 */
function fixMalformedWidgets(item: any): any {
  if (!item?.question?.widgets) return item;

  const fixedItem = JSON.parse(JSON.stringify(item)); // Deep clone
  const widgets = fixedItem.question.widgets;

  for (const [widgetId, widget] of Object.entries(widgets)) {
    const w = widget as any;
    if (w?.type === 'radio' && w?.options) {
      // Check if choices already exists
      if (!Array.isArray(w.options.choices)) {
        // Look for wrong format: options like {"3": false, "4": true}
        const wrongFormatChoices: { text: string; correct: boolean }[] = [];
        const keysToRemove: string[] = [];

        for (const [key, value] of Object.entries(w.options)) {
          // Skip known Perseus option keys
          if (['choices', 'randomize', 'multipleSelect', 'countChoices',
               'deselectEnabled', 'displayCount', 'noneOfTheAbove', 'hasNoneOfTheAbove'].includes(key)) {
            continue;
          }
          // If value is boolean, this is likely wrong format
          if (typeof value === 'boolean') {
            wrongFormatChoices.push({ text: String(key), correct: value });
            keysToRemove.push(key);
          }
        }

        // Convert wrong format to correct format
        if (wrongFormatChoices.length >= 2) {
          console.warn(`[DynamicAssessment] Fixing malformed radio widget ${widgetId}:`, wrongFormatChoices);

          // Remove wrong keys
          for (const key of keysToRemove) {
            delete w.options[key];
          }

          // Add proper choices array
          w.options.choices = wrongFormatChoices.map(c => ({
            content: c.text,
            correct: c.correct
          }));
          w.options.randomize = w.options.randomize ?? true;
        }
      }
    }
  }

  return fixedItem;
}

interface Question {
  question: any;
  answerArea: any;
  hints: any[];
  dash_metadata: {
    dash_question_id: string;
    assessment_id: string;
    difficulty: string;
    topic: string;
    subject?: string;
    [key: string]: any;
  };
}

interface LocationState {
  assessmentId?: string;
  subject?: string;
  questions?: Question[];
  totalQuestions?: number;
  onboardingData?: {
    ageRange: string;
    grade: string;
    selectedTopics: string[];
    customTopic: string;
  };
}

interface Answer {
  question_id: string;
  is_correct: boolean;
  difficulty: string;
  topic: string;
  time_taken_ms: number;
}

const DynamicAssessment: React.FC = () => {
  const history = useHistory();
  const location = useLocation<LocationState>();

  // Check if user JUST came from onboarding with freshly generated questions
  // Use a function to compute initial value ONCE (not on every render)
  // Apply widget fixes to questions from onboarding
  const questionsFromOnboarding = (location.state?.questions || []).map((q: any) => fixMalformedWidgets(q));
  const onboardingDataFromNav = location.state?.onboardingData || null;

  // Track valid session in state so it persists across re-renders
  // Computed once on mount based on sessionStorage flag + questions
  const [hasValidSession] = useState(() => {
    const justCompletedOnboarding = sessionStorage.getItem('learner_onboarding_complete') === 'true';
    const hasQuestions = questionsFromOnboarding.length > 0;
    return justCompletedOnboarding && hasQuestions;
  });

  // Initialize state with questions from onboarding (or empty if redirecting)
  const [questions, setQuestions] = useState<Question[]>(questionsFromOnboarding);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [assessmentId, setAssessmentId] = useState<string>('');
  const [subject, setSubject] = useState<string>('math');
  const [showIntro, setShowIntro] = useState(true);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [onboardingData, setOnboardingData] = useState<LocationState["onboardingData"] | null>(null);
  const [loadSource, setLoadSource] = useState<LoadSource>('unknown');
  const [forceRenderError, setForceRenderError] = useState(false);

  // Answer feedback state
  const [showAnswerFeedback, setShowAnswerFeedback] = useState(false);
  const [lastAnswerCorrect, setLastAnswerCorrect] = useState<boolean | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string>('');

  // FloatingControlPanel state
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);
  const [isBiographyPanelOpen, setIsBiographyPanelOpen] = useState(false);
  const [privacyEnabled, setPrivacyEnabled] = useState(false);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);

  // Refs for FloatingControlPanel
  const videoRef = useRef<HTMLVideoElement>(null);
  const processedEdgesRef = useRef<ImageData | null>(null);

  // Media capture hooks
  const {
    cameraEnabled,
    screenEnabled,
    toggleCamera,
    toggleScreen,
    cameraVideoRef,
    screenVideoRef
  } = useMediaCapture({});

  // MediaMixer hook
  const mediaMixer = useMediaMixer({
    width: 1280,
    height: 2160,
    fps: 2,
    quality: 0.85,
    cameraEnabled: cameraEnabled,
    screenEnabled: screenEnabled,
    privacyEnabled: privacyEnabled,
    cameraVideoRef: cameraVideoRef,
    screenVideoRef: screenVideoRef
  });

  // Start mixer when component mounts
  useEffect(() => {
    if (mediaMixer.canvasRef.current) {
      mediaMixer.setIsRunning(true);
      return () => {
        mediaMixer.setIsRunning(false);
      };
    }
  }, [mediaMixer]);

  // Initialize from onboarding data - NO cache, only fresh questions from user flow
  useEffect(() => {
    // Clear ALL stale cache - questions must come fresh from onboarding
    sessionStorage.removeItem('dynamic_assessment_payload');
    sessionStorage.removeItem('dynamic_assessment_id');
    sessionStorage.removeItem('dynamic_assessment_last_source');
    sessionStorage.removeItem('dynamic_assessment_was_unloaded');

    // Set state from navigation (questions already in useState from initialization)
    if (hasValidSession && location.state) {
      // Clear the onboarding flag NOW - so page refresh sends back to onboarding
      // This is safe because hasValidSession is already captured in state
      sessionStorage.removeItem('learner_onboarding_complete');

      setAssessmentId(location.state.assessmentId || '');
      const inferredSubject = location.state.subject || questionsFromOnboarding[0]?.dash_metadata?.subject || 'math';
      setSubject(inferredSubject);
      setTotalQuestions(location.state.totalQuestions ?? questionsFromOnboarding.length);
      setOnboardingData(onboardingDataFromNav);
      setLoadSource('nav');
      setLoading(false);
      console.log('[DynamicAssessment] Ready with fresh questions from onboarding:', questionsFromOnboarding.length);
    }
  }, []);

  useEffect(() => {
    if (loadSource !== 'unknown') {
      sessionStorage.setItem('dynamic_assessment_last_source', loadSource);
    }
  }, [loadSource]);

  const startNewAssessment = async (chosenSubject: string) => {
    setLoading(true);
    setLoadError(null);

    try {
      // Lightweight defaults for dev / out-of-the-box local use.
      const response = await apiUtils.post(`${DASH_API_URL}/api/assessment/dynamic/start`, {
        age_range: '8-10',
        subject: chosenSubject,
        grade: '3-5',
        topics: chosenSubject === 'science' ? ['science'] : chosenSubject === 'reading' ? ['reading'] : ['math-basics'],
        question_count: 10,
      });

      if (!response.ok) {
        throw new Error('Failed to start assessment');
      }

      const assessmentData = await response.json();
      const payload = {
        assessmentId: assessmentData.assessment_id,
        subject: assessmentData.subject,
        questions: assessmentData.questions || [],
        totalQuestions: assessmentData.total_questions ?? assessmentData.questions?.length ?? 0,
      };

      sessionStorage.setItem('dynamic_assessment_payload', JSON.stringify(payload));
      sessionStorage.setItem('dynamic_assessment_id', assessmentData.assessment_id);

      setCurrentIndex(0);
      setAnswers([]);
      setCompleted(false);
      setResults(null);
      setQuestionStartTime(Date.now());

      // Reuse the existing payload loader path - apply widget fixes
      setQuestions(payload.questions.map((q: any) => fixMalformedWidgets(q)));
      setAssessmentId(payload.assessmentId);
      setSubject(payload.subject || chosenSubject);
      setTotalQuestions(payload.totalQuestions);
      setLoading(false);
      setLoadSource('api');
    } catch (err) {
      console.error('Failed to start assessment:', err);
      setLoading(false);
      setLoadError('could not start the assessment. try again?');
    }
  };

  const fetchMoreQuestions = async (minToFetch: number = 3) => {
    if (!assessmentId) return;
    if (questions.length >= totalQuestions) return;

    const start = questions.length;
    const limit = Math.max(1, Math.min(4, minToFetch));

    try {
      const response = await apiUtils.get(`${DASH_API_URL}/api/assessment/dynamic/${assessmentId}/batch?start=${start}&limit=${limit}`);
      if (!response.ok) return;
      const data = await response.json();
      const rawQuestions: Question[] = data.questions || [];
      // Apply widget fixes to new questions
      const newQuestions = rawQuestions.map((q: any) => fixMalformedWidgets(q));
      if (newQuestions.length) {
        const merged = [...questions, ...newQuestions];
        setQuestions(merged);
        sessionStorage.setItem('dynamic_assessment_payload', JSON.stringify({
          assessmentId,
          subject,
          questions: merged,
          totalQuestions,
          onboardingData,
        }));
      }
    } catch (err) {
      console.warn('[DynamicAssessment] Failed to fetch more questions', err);
    }
  };

  // Background prefetch: when we show question N, ask the backend to ensure N+1..N+3 exist.
  useEffect(() => {
    if (!assessmentId) return;
    apiUtils.get(`${DASH_API_URL}/api/assessment/dynamic/${assessmentId}/prefetch?index=${currentIndex}&prefetch_ahead=3`).catch(() => {});

    // If we're close to running out of local questions, pull a new batch.
    if (totalQuestions > 0 && questions.length < totalQuestions && currentIndex >= questions.length - 2) {
      fetchMoreQuestions(3);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, currentIndex]);

  // REDIRECT: If no valid session from onboarding, send to onboarding
  // This MUST be after all hooks
  if (!hasValidSession) {
    return <Redirect to="/app/onboarding" />;
  }

  const currentQuestion = questions[currentIndex];
  const progress = questions.length ? ((currentIndex + 1) / questions.length) * 100 : 0;

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '#4CAF50';
      case 'medium': return '#FF9800';
      case 'hard': return '#f44336';
      default: return '#666';
    }
  };

  const getDifficultyEmoji = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '🟢';
      case 'medium': return '🟡';
      case 'hard': return '🔴';
      default: return '⚪';
    }
  };

  const handleAnswerSubmit = async (isCorrect: boolean) => {
    const timeTaken = Date.now() - questionStartTime;

    const answer: Answer = {
      question_id: currentQuestion.dash_metadata.dash_question_id,
      is_correct: isCorrect,
      difficulty: currentQuestion.dash_metadata.difficulty,
      topic: currentQuestion.dash_metadata.topic,
      time_taken_ms: timeTaken,
    };

    const newAnswers = [...answers, answer];
    setAnswers(newAnswers);

    // Show feedback immediately
    setLastAnswerCorrect(isCorrect);
    setFeedbackMessage(isCorrect
      ? getCorrectFeedback()
      : getIncorrectFeedback()
    );
    setShowAnswerFeedback(true);

    // Move to next question or complete after showing feedback
    const hasNextLoaded = currentIndex < questions.length - 1;
    const hasMoreTotal = totalQuestions > 0 && questions.length < totalQuestions;

    const advanceDelay = 2000; // Show feedback for 2 seconds

    if (hasNextLoaded) {
      setTimeout(() => {
        setShowAnswerFeedback(false);
        setCurrentIndex(currentIndex + 1);
        setQuestionStartTime(Date.now());
      }, advanceDelay);
      return;
    }

    if (hasMoreTotal) {
      // Pull more questions while showing feedback
      await fetchMoreQuestions(3);
      setTimeout(() => {
        setShowAnswerFeedback(false);
        setCurrentIndex((idx) => idx + 1);
        setQuestionStartTime(Date.now());
      }, advanceDelay);
      return;
    }

    // Complete assessment after feedback
    setTimeout(async () => {
      setShowAnswerFeedback(false);
      await completeAssessment(newAnswers);
    }, advanceDelay);
  };

  // Innocent Drinks tone feedback messages
  const getCorrectFeedback = () => {
    const messages = [
      "nailed it! 🎯",
      "yes! you absolute legend! ✨",
      "boom! correct! 💥",
      "look at you go! 🚀",
      "that's the one! 🌟",
      "brilliant! (we knew you had it in you) 💪",
    ];
    return messages[Math.floor(Math.random() * messages.length)];
  };

  const getIncorrectFeedback = () => {
    const messages = [
      "not quite! (but hey, that's how we learn) 📚",
      "oops! close though! 💭",
      "hmm, not this time (we believe in you!) 🌱",
      "nearly! let's keep going 💪",
      "that's ok! mistakes help us grow 🌟",
      "whoops! (happens to the best of us) ✨",
    ];
    return messages[Math.floor(Math.random() * messages.length)];
  };

  const completeAssessment = async (finalAnswers: Answer[]) => {
    setLoading(true);

    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/assessment/dynamic/complete`, {
        assessment_id: assessmentId,
        answers: finalAnswers,
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data);
        setCompleted(true);

        // Set sessionStorage flag so AssessmentGuard knows assessment is complete
        sessionStorage.setItem('assessment_completed_dynamic', 'true');
      } else {
        console.error('Failed to complete assessment');
      }
    } catch (error) {
      console.error('Error completing assessment:', error);
    } finally {
      setLoading(false);
    }
  };

  const startLearning = () => {
    // Navigate to Learning Plan Dashboard
    history.push('/app/learning-plan', {
      skillLevel: results?.learning_path?.skill_level || 'Beginner',
      focusTopics: results?.learning_path?.focus_topics || [],
      strongTopics: results?.learning_path?.strong_topics || [],
      grade: onboardingData?.grade || location.state?.onboardingData?.grade || 'K-2',
      subject: subject || 'math',
      fromAssessment: true,
    });
  };

  if (loadError && !loading) {
    return (
      <div className="login-container" style={{ minHeight: '100vh', background: '#FFFFFF' }}>
        <BackgroundShapes />
        <div className="login-card" style={{
          maxWidth: '600px',
          padding: '48px',
          textAlign: 'center',
          border: '5px solid #000',
          borderRadius: '0',
          boxShadow: '8px 8px 0 #000',
          background: '#FCD34D'
        }}>
          <div style={{ fontSize: '80px', marginBottom: '24px' }}>⚠️</div>
          <h2 style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '36px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '-0.02em',
            marginBottom: '16px'
          }}>
            {loadError}
          </h2>

          <div style={{
            marginTop: '24px',
            marginBottom: '24px',
            fontSize: '18px',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            PICK A SUBJECT AND LET'S GO
          </div>

          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '24px' }}>
            {['MATH', 'SCIENCE', 'READING'].map(subj => (
              <button
                key={subj}
                onClick={() => startNewAssessment(subj.toLowerCase())}
                style={{
                  padding: '16px 32px',
                  fontSize: '20px',
                  fontWeight: 900,
                  fontFamily: 'Space Mono, monospace',
                  background: '#FFFFFF',
                  border: '4px solid #000',
                  borderRadius: '0',
                  boxShadow: '6px 6px 0 #000',
                  cursor: 'pointer',
                  textTransform: 'uppercase'
                }}
              >
                {subj}
              </button>
            ))}
          </div>

          <button
            onClick={() => history.push('/app/onboarding')}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: 700,
              fontFamily: 'Space Mono, monospace',
              background: 'transparent',
              border: '3px solid #000',
              borderRadius: '0',
              cursor: 'pointer',
              textTransform: 'uppercase'
            }}
          >
            ← BACK TO ONBOARDING
          </button>
        </div>
      </div>
    );
  }

  // Pre-Assessment Intro Screen
  // Note: If we reach here, hasValidQuestions is true (redirect guard passed)
  if (showIntro && !loading && !completed) {
    return (
      <TutorProvider>
        <div className="login-container" style={{ minHeight: '100vh' }}>
          <BackgroundShapes />
        <div className="login-card" style={{ maxWidth: '600px', padding: '48px' }}>
          {SHOW_DEBUG_BANNER && (
            <div style={{
              background: '#FFF4CC',
              border: '2px dashed #000',
              borderRadius: '12px',
              padding: '12px 16px',
              marginBottom: '24px',
              fontSize: '12px',
              textTransform: 'uppercase',
              fontWeight: 700,
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  background: '#D32F2F',
                  color: '#fff',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  fontSize: '10px',
                  letterSpacing: '0.12em'
                }}>
                  DEBUG
                </span>
                <span>
                  assessment {assessmentId || 'unknown'} · {totalQuestions || questions.length} questions · source {loadSource}
                </span>
              </div>
              {SHOW_DEBUG_FORCE_ERROR && (
                <button
                  type="button"
                  onClick={() => setForceRenderError(!forceRenderError)}
                  style={{
                    background: forceRenderError ? '#FF6B6B' : '#000',
                    color: '#fff',
                    border: '2px solid #000',
                    borderRadius: '999px',
                    padding: '2px 10px',
                    fontSize: '10px',
                    letterSpacing: '0.12em',
                    cursor: 'pointer'
                  }}
                >
                  {forceRenderError ? 'clear error' : 'force error'}
                </button>
              )}
            </div>
          )}

          {/* Questions loaded from onboarding - show ready screen */}
          <>
              <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                <div style={{ fontSize: '100px', marginBottom: '24px' }}>🎯</div>
                <h2 style={{
                  fontFamily: 'Space Mono, monospace',
                  fontSize: '48px',
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  letterSpacing: '-0.02em',
                  marginBottom: '16px'
                }}>
                  READY?
                </h2>
                <p style={{
                  fontSize: '20px',
                  fontWeight: 700,
                  textTransform: 'uppercase'
                }}>
                  LET'S SEE WHAT YOU KNOW!
                </p>
              </div>

              <div style={{
                background: '#FCD34D',
                border: '5px solid #000',
                borderRadius: '0',
                padding: '32px',
                marginBottom: '32px',
                boxShadow: '6px 6px 0 #000'
              }}>
                <h3 style={{
                  fontSize: '24px',
                  fontWeight: 900,
                  marginBottom: '24px',
                  textTransform: 'uppercase',
                  fontFamily: 'Space Mono, monospace'
                }}>WHAT TO EXPECT:</h3>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  <li style={{ marginBottom: '16px', display: 'flex', alignItems: 'start', gap: '16px' }}>
                    <span style={{ fontSize: '32px' }}>📝</span>
                    <div style={{ fontSize: '18px', fontWeight: 700, textTransform: 'uppercase' }}>
                      {totalQuestions || questions.length} QUESTIONS ABOUT {(
                        onboardingData?.customTopic ||
                        onboardingData?.selectedTopics?.join(', ') ||
                        location.state?.onboardingData?.customTopic ||
                        location.state?.onboardingData?.selectedTopics?.join(', ') ||
                        'YOUR TOPICS'
                      ).toUpperCase()}
                    </div>
                  </li>
                  <li style={{ marginBottom: '16px', display: 'flex', alignItems: 'start', gap: '16px' }}>
                    <span style={{ fontSize: '32px' }}>⏱️</span>
                    <div style={{ fontSize: '18px', fontWeight: 700, textTransform: 'uppercase' }}>
                      ABOUT 5 MINUTES - NO RUSH!
                    </div>
                  </li>
                  <li style={{ marginBottom: '16px', display: 'flex', alignItems: 'start', gap: '16px' }}>
                    <span style={{ fontSize: '32px' }}>📊</span>
                    <div style={{ fontSize: '18px', fontWeight: 700, textTransform: 'uppercase' }}>
                      PERSONALIZED PLAN CREATED FOR YOU
                    </div>
                  </li>
                  <li style={{ display: 'flex', alignItems: 'start', gap: '16px' }}>
                    <span style={{ fontSize: '32px' }}>🎯</span>
                    <div style={{ fontSize: '18px', fontWeight: 700, textTransform: 'uppercase' }}>
                      FOCUS TOPICS IDENTIFIED
                    </div>
                  </li>
                </ul>
              </div>

              <button
                onClick={() => setShowIntro(false)}
                style={{
                  width: '100%',
                  padding: '20px',
                  fontSize: '24px',
                  fontWeight: 900,
                  fontFamily: 'Space Mono, monospace',
                  background: '#22C55E',
                  color: '#000',
                  border: '5px solid #000',
                  borderRadius: '0',
                  cursor: 'pointer',
                  boxShadow: '6px 6px 0 #000',
                  transition: 'all 0.1s',
                  textTransform: 'uppercase'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translate(3px, 3px)';
                  e.currentTarget.style.boxShadow = '3px 3px 0 #000';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translate(0, 0)';
                  e.currentTarget.style.boxShadow = '6px 6px 0 #000';
                }}
              >
                LET'S GO! 🚀
              </button>
            </>
        </div>

        {/* Floating Control Panel with AI Tutor */}
        <Suspense fallback={null}>
          <FloatingControlPanel
            renderCanvasRef={mediaMixer.canvasRef}
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={setVideoStream}
            onMixerStreamChange={setMixerStream}
            enableEditingSettings={false}
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
            assessmentMode={true}
            onBiographyClick={() => setIsBiographyPanelOpen(!isBiographyPanelOpen)}
            isBiographyActive={isBiographyPanelOpen}
          />
        </Suspense>
      </div>
      </TutorProvider>
    );
  }

  if (loading) {
    return (
      <TutorProvider>
        <div className="login-container" style={{ minHeight: '100vh', background: '#FFFFFF' }}>
          <BackgroundShapes />
        <div className="login-card" style={{
          textAlign: 'center',
          padding: '64px',
          border: '5px solid #000',
          borderRadius: '0',
          boxShadow: '8px 8px 0 #000',
          background: '#FCD34D'
        }}>
          <div style={{ fontSize: '80px', marginBottom: '32px' }}>🎯</div>
          <h2 style={{
            fontFamily: 'Space Mono, monospace',
            fontSize: '36px',
            fontWeight: 900,
            textTransform: 'uppercase',
            marginBottom: '24px'
          }}>
            {completed ? 'ANALYZING RESULTS...' : 'LOADING...'}
          </h2>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '0',
              border: '5px solid #000',
              borderTopColor: '#22C55E',
              animation: 'spin 0.8s linear infinite'
            }} />
          </div>
          <p style={{
            fontSize: '18px',
            fontWeight: 700,
            textTransform: 'uppercase',
            marginBottom: '8px'
          }}>BUILDING YOUR QUESTIONS</p>
          <p style={{
            fontSize: '14px',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>~10-20 SECONDS</p>
        </div>

        {/* Floating Control Panel */}
        <Suspense fallback={null}>
          <FloatingControlPanel
            renderCanvasRef={mediaMixer.canvasRef}
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={setVideoStream}
            onMixerStreamChange={setMixerStream}
            enableEditingSettings={false}
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
            assessmentMode={true}
            onBiographyClick={() => setIsBiographyPanelOpen(!isBiographyPanelOpen)}
            isBiographyActive={isBiographyPanelOpen}
          />
        </Suspense>
      </div>
      </TutorProvider>
    );
  }

  // Results Screen - EXTREME NEO-BRUTALISM
  if (completed && results) {
    const scorePercent = Math.round(results.overall_score * 100);

    return (
      <div className="login-container" style={{ minHeight: '100vh', background: '#FFFFFF' }}>
        <BackgroundShapes />
        <div className="login-card" style={{
          maxWidth: '650px',
          padding: '48px',
          border: '5px solid #000',
          borderRadius: '0',
          boxShadow: '8px 8px 0 #000',
          background: '#FFFFFF'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <div style={{ fontSize: '100px', marginBottom: '24px' }}>
              {scorePercent >= 80 ? '🌟' : scorePercent >= 60 ? '👍' : '💪'}
            </div>
            <h1 style={{
              fontFamily: 'Space Mono, monospace',
              fontSize: '48px',
              fontWeight: 900,
              textTransform: 'uppercase',
              marginBottom: '16px'
            }}>
              {scorePercent >= 80 ? 'AMAZING!' : scorePercent >= 60 ? 'NICE JOB!' : 'GOOD EFFORT!'}
            </h1>
            <p style={{
              fontSize: '28px',
              fontWeight: 900,
              textTransform: 'uppercase'
            }}>
              {results.total_correct}/{results.total_questions} CORRECT
            </p>
          </div>

          {/* Score Breakdown */}
          <div style={{
            background: '#FCD34D',
            border: '5px solid #000',
            borderRadius: '0',
            padding: '24px',
            marginBottom: '24px',
            boxShadow: '6px 6px 0 #000'
          }}>
            <h3 style={{
              marginBottom: '20px',
              fontSize: '20px',
              fontWeight: 900,
              textTransform: 'uppercase',
              fontFamily: 'Space Mono, monospace'
            }}>BY DIFFICULTY:</h3>
            <div style={{ display: 'grid', gap: '16px' }}>
              {Object.entries(results.difficulty_scores || {}).map(([diff, scores]: [string, any]) => (
                <div key={diff} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  fontSize: '18px',
                  fontWeight: 700,
                  textTransform: 'uppercase'
                }}>
                  <span style={{ fontSize: '28px' }}>{getDifficultyEmoji(diff)}</span>
                  <span style={{ flex: 1 }}>{diff}</span>
                  <span style={{
                    background: '#000',
                    color: '#FCD34D',
                    padding: '4px 12px',
                    fontWeight: 900
                  }}>
                    {scores.correct}/{scores.total}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Learning Path Preview */}
          <div style={{
            background: '#22C55E',
            border: '5px solid #000',
            borderRadius: '0',
            padding: '24px',
            marginBottom: '32px',
            boxShadow: '6px 6px 0 #000'
          }}>
            <h3 style={{
              marginBottom: '16px',
              fontSize: '20px',
              fontWeight: 900,
              textTransform: 'uppercase',
              fontFamily: 'Space Mono, monospace'
            }}>YOUR PLAN:</h3>
            <p style={{
              marginBottom: '12px',
              fontSize: '18px',
              fontWeight: 700,
              textTransform: 'uppercase'
            }}>
              LEVEL: {(results.learning_path?.skill_level || 'intermediate').toUpperCase()}
            </p>
            {results.learning_path?.focus_topics?.length > 0 && (
              <p style={{
                marginBottom: '12px',
                fontSize: '18px',
                fontWeight: 700,
                textTransform: 'uppercase'
              }}>
                FOCUS: {results.learning_path.focus_topics.join(', ').toUpperCase()}
              </p>
            )}
            {results.learning_path?.strong_topics?.length > 0 && (
              <p style={{
                fontSize: '18px',
                fontWeight: 700,
                textTransform: 'uppercase'
              }}>
                STRENGTHS: {results.learning_path.strong_topics.join(', ').toUpperCase()}
              </p>
            )}
          </div>

          <button
            onClick={startLearning}
            style={{
              width: '100%',
              padding: '20px',
              fontSize: '24px',
              fontWeight: 900,
              fontFamily: 'Space Mono, monospace',
              background: '#FF6B6B',
              color: '#000',
              border: '5px solid #000',
              borderRadius: '0',
              cursor: 'pointer',
              boxShadow: '6px 6px 0 #000',
              transition: 'all 0.1s',
              textTransform: 'uppercase'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translate(3px, 3px)';
              e.currentTarget.style.boxShadow = '3px 3px 0 #000';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translate(0, 0)';
              e.currentTarget.style.boxShadow = '6px 6px 0 #000';
            }}
          >
            START LEARNING! 🚀
          </button>
        </div>
      </div>
    );
  }

  // Question Screen - EXTREME NEO-BRUTALISM
  return (
    <TutorProvider assessmentMode={true}>
      <div style={{ minHeight: '100vh', background: '#FFFFFF' }}>
        <Header />

        <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
          {/* Progress Bar - EXTREME */}
          <div style={{
            marginBottom: '32px',
            background: '#FCD34D',
            border: '5px solid #000',
            borderRadius: '0',
            padding: '16px 24px',
            boxShadow: '6px 6px 0 #000'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '12px'
            }}>
              <span style={{
                fontSize: '20px',
                fontWeight: 900,
                fontFamily: 'Space Mono, monospace',
                textTransform: 'uppercase'
              }}>
                QUESTION {currentIndex + 1}/{questions.length}
              </span>
              <span style={{
                fontSize: '20px',
                fontWeight: 900,
                fontFamily: 'Space Mono, monospace',
                textTransform: 'uppercase',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                {getDifficultyEmoji(currentQuestion?.dash_metadata?.difficulty)} {currentQuestion?.dash_metadata?.difficulty?.toUpperCase()}
              </span>
            </div>
            <div style={{
              height: '16px',
              background: '#FFFFFF',
              border: '4px solid #000',
              borderRadius: '0',
              overflow: 'hidden'
            }}>
              <div style={{
                height: '100%',
                width: `${progress}%`,
                background: '#22C55E',
                transition: 'width 0.3s ease'
              }} />
            </div>
          </div>

          {/* Answer Feedback Banner - Fixed position for visibility */}
          {showAnswerFeedback && (
            <div
              style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                zIndex: 9999,
                background: lastAnswerCorrect ? '#ADFF2F' : '#FF6B6B',
                border: '5px solid #000',
                borderRadius: '0',
                padding: '32px 48px',
                boxShadow: '8px 8px 0 #000',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '16px',
                minWidth: '300px',
              }}
            >
              <span style={{
                fontSize: '64px',
                lineHeight: 1,
              }}>
                {lastAnswerCorrect ? '✓' : '✗'}
              </span>
              <span style={{
                fontSize: '24px',
                fontWeight: 900,
                fontFamily: 'Space Mono, monospace',
                textTransform: 'lowercase',
                color: '#000',
                textAlign: 'center',
              }}>
                {feedbackMessage}
              </span>
            </div>
          )}

          {/* Overlay when feedback showing */}
          {showAnswerFeedback && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.3)',
                zIndex: 9998,
              }}
            />
          )}

          {/* Question - EXTREME */}
          <div style={{
            background: '#FFFFFF',
            borderRadius: '0',
            border: '5px solid #000',
            padding: '32px',
            boxShadow: '8px 8px 0 #000',
            opacity: showAnswerFeedback ? 0.6 : 1,
            transition: 'opacity 0.3s ease',
            pointerEvents: showAnswerFeedback ? 'none' : 'auto',
          }}>
            <HintProvider>
              {currentQuestion && (
                <RendererComponent
                  assessmentMode={true}
                  assessmentQuestions={[currentQuestion]}
                  currentQuestionIndex={0}
                  onAssessmentAnswer={(questionId, isCorrect) => {
                    handleAnswerSubmit(isCorrect);
                  }}
                  debugForceRenderError={forceRenderError}
                />
              )}
            </HintProvider>
          </div>
        </div>

        {/* Floating Control Panel with AI Tutor */}
        <Suspense fallback={null}>
          <FloatingControlPanel
            renderCanvasRef={mediaMixer.canvasRef}
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={setVideoStream}
            onMixerStreamChange={setMixerStream}
            enableEditingSettings={false}
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
            assessmentMode={true}
            onBiographyClick={() => setIsBiographyPanelOpen(!isBiographyPanelOpen)}
            isBiographyActive={isBiographyPanelOpen}
          />
          <BiographyPanel
            isOpen={isBiographyPanelOpen}
            onClose={() => setIsBiographyPanelOpen(false)}
            position="right"
          />
        </Suspense>
      </div>
    </TutorProvider>
  );
};

export default DynamicAssessment;

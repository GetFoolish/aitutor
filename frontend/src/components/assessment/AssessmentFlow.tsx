import React, { useState, useEffect, useRef, useCallback, Suspense, lazy } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';
import Header from '../../components/header/Header';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { TutorProvider } from '../../features/tutor';
import { ThemeProvider } from '../theme/theme-provier';

const FloatingControlPanel = lazy(() => import('../floating-control-panel/FloatingControlPanel'));

/* 🔥 COPY LOGIN BG STYLES */
import '../auth/auth.scss';

const DASH_API_URL =
  import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface Question {
  question: any;
  answerArea: any;
  hints: any[];
  dash_metadata: any;
  [key: string]: any;
}

interface Params {
  subject: string;
}

/* ----------------------------------------------------
   Main component
---------------------------------------------------- */
const AssessmentFlow: React.FC = () => {
  const history = useHistory();
  const { subject } = useParams<Params>();

  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [currentDifficulty, setCurrentDifficulty] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadPhase, setLoadPhase] = useState<'fast' | 'generating' | 'slow'>('fast');

  // Ref to track latest assessmentId for prefetch (avoids stale closures)
  const assessmentIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Client-side content fingerprint tracker to detect duplicate questions
  const seenContentRef = useRef<Set<string>>(new Set());

  // Dummy refs for FloatingControlPanel (media features not used in assessment)
  const dummyVideoRef = useRef<HTMLVideoElement>(null);
  const dummyCanvasRef = useRef<HTMLCanvasElement>(null);
  const dummyEdgesRef = useRef<ImageData | null>(null);

  // Simple content fingerprint for client-side duplicate detection
  const contentFingerprint = useCallback((q: Question): string => {
    const content = q?.question?.content || '';
    const widgets = JSON.stringify(q?.question?.widgets || {});
    return content + '|' + widgets;
  }, []);

  // Fire-and-forget prefetch for next question at both difficulty branches
  const firePrefetch = useCallback((aId: string | null, difficulty: number) => {
    if (!aId) return;
    apiUtils.post(`${DASH_API_URL}/assessment/prefetch`, {
      assessment_id: aId,
      current_difficulty: difficulty,
    }).catch(() => {}); // Silently ignore — prefetch is best-effort
  }, []);

  // Warn before closing tab during active assessment
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (assessmentIdRef.current && !completed) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [completed]);

  useEffect(() => {
    startAssessment();
  }, [subject]);

  const startAssessment = async () => {
    setLoadPhase('fast');
    try {
      const controller = new AbortController();
      abortRef.current = controller;

      // Progressive phase timers: 10s→generating, 30s→slow (with cancel option)
      const phase2Timer = setTimeout(() => setLoadPhase('generating'), 10000);
      const phase3Timer = setTimeout(() => setLoadPhase('slow'), 30000);
      const hardTimeout = setTimeout(() => controller.abort(), 60000); // 60s hard timeout (was 90)

      const response = await apiUtils.post(
        `${DASH_API_URL}/assessment/start-adaptive/${subject}`,
        {},
        { signal: controller.signal }
      );
      clearTimeout(phase2Timer);
      clearTimeout(phase3Timer);
      clearTimeout(hardTimeout);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      if (data.error) {
        // "Already completed" — show results regardless of score (even 0/10)
        if (data.error === 'Assessment already completed' && data.total > 0) {
          sessionStorage.setItem('selected_subject', subject);
          sessionStorage.setItem('assessmentSubject', subject);
          setCompleted(true);
          setScore(data.score ?? 0);
          setTotal(data.total);
        } else {
          // No questions available or other error → show retry UI
          setError(data.error);
        }
        setLoading(false);
        return;
      }

      setAssessmentId(data.assessment_id);
      assessmentIdRef.current = data.assessment_id;
      setCurrentQuestion(data.question);
      setQuestionNumber(data.question_number);
      setTotalQuestions(data.total_questions);
      setCurrentDifficulty(data.current_difficulty);
      setLoading(false);

      // Track first question content fingerprint
      seenContentRef.current.clear();
      seenContentRef.current.add(contentFingerprint(data.question));

      // Pre-fetch the next question while user reads question 1
      firePrefetch(data.assessment_id, data.current_difficulty);
    } catch (err: any) {
      console.error('Assessment start failed:', err);
      const msg = err?.name === 'AbortError'
        ? 'Assessment is taking longer than expected. Please try again.'
        : 'Failed to load assessment. Please try again.';
      setError(msg);
      setLoading(false);
    }
  };

  const handleAnswer = (isCorrect: boolean) => {
    if (!currentQuestion || !assessmentId || submitting) return;

    const q = currentQuestion;
    setSubmitting(true);

    // Fire the API call immediately (don't wait for feedback delay)
    const fetchNext = apiUtils.post(
      `${DASH_API_URL}/assessment/next`,
      {
        assessment_id: assessmentId,
        question_id: q?.dash_metadata?.dash_question_id || `q_${questionNumber}`,
        skill_id: (q?.dash_metadata?.skill_ids || [])[0] || '',
        is_correct: isCorrect,
      }
    );

    // Brief feedback flash, then show next question as soon as API responds
    const minDelay = new Promise(resolve => setTimeout(resolve, 200));

    Promise.all([fetchNext, minDelay]).then(async ([response]) => {
      try {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.completed) {
          setScore(data.score);
          setTotal(data.total);
          setCompleted(true);
          setSubmitting(false);
          return;
        }

        // Client-side duplicate check: log if backend served identical content
        const fp = contentFingerprint(data.question);
        if (seenContentRef.current.has(fp)) {
          console.warn('[AssessmentFlow] Duplicate content detected client-side — skipping');
        }
        seenContentRef.current.add(fp);

        setCurrentQuestion(data.question);
        setQuestionNumber(data.question_number);
        setTotalQuestions(data.total_questions);
        setCurrentDifficulty(data.current_difficulty);
        setSubmitting(false);

        // Pre-fetch the NEXT question while user works on this one
        if (assessmentIdRef.current) {
          firePrefetch(assessmentIdRef.current, data.current_difficulty);
        }
      } catch (err) {
        console.error('Assessment next failed:', err);
        setError('Failed to load next question');
        setSubmitting(false);
      }
    }).catch((err) => {
      console.error('Assessment fetch rejected:', err);
      setError('Network error — please try again');
      setSubmitting(false);
    });
  };

  /* ----------------------------------------------------
     Render
  ---------------------------------------------------- */
  return (
    <ThemeProvider defaultTheme="light" storageKey="ai-tutor-theme">
    <TutorProvider>
    <div className="auth-container">
      <BackgroundShapes />

      <Header
        sidebarOpen={false}
        onToggleSidebar={() => {}}
        assessmentMode={true}
      />

      {loading && (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '20px',
          padding: '20px'
        }}>
          {/* Animated progress bar */}
          <div style={{
            width: '200px',
            height: '8px',
            border: '3px solid #000',
            backgroundColor: '#fff',
            overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              width: '40%',
              backgroundColor: loadPhase === 'slow' ? '#FF6B6B' : '#FFD93D',
              animation: 'loading-bar 1.5s ease-in-out infinite'
            }} />
          </div>
          <div style={{
            fontWeight: 900,
            fontSize: '18px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em'
          }}>
            {loadPhase === 'fast' && `Preparing your ${subject} assessment`}
            {loadPhase === 'generating' && `Generating ${subject} questions`}
            {loadPhase === 'slow' && `Still working on it...`}
          </div>
          <div style={{
            fontSize: '14px',
            color: '#666',
            maxWidth: '400px',
            textAlign: 'center',
            lineHeight: '1.5'
          }}>
            {loadPhase === 'fast' && 'Creating personalized questions at your level. This should only take a few seconds.'}
            {loadPhase === 'generating' && 'Building new questions with AI. Almost there...'}
            {loadPhase === 'slow' && 'This is taking longer than usual. You can keep waiting or try again.'}
          </div>
          {loadPhase === 'slow' && (
            <button
              onClick={() => {
                abortRef.current?.abort();
                setError(null);
                setLoading(true);
                startAssessment();
              }}
              style={{
                padding: '10px 28px',
                border: '3px solid #000',
                background: '#FFD93D',
                boxShadow: '3px 3px 0 #000',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '13px',
                textTransform: 'uppercase'
              }}
            >
              Try Again
            </button>
          )}
          <style>{`
            @keyframes loading-bar {
              0% { transform: translateX(-100%); }
              100% { transform: translateX(350%); }
            }
          `}</style>
        </div>
      )}

      {error && (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '16px',
          padding: 40
        }}>
          <div style={{
            padding: '12px 24px',
            border: '3px solid #000',
            background: '#FF6B6B',
            color: '#fff',
            fontWeight: 700,
            fontSize: '14px',
            textTransform: 'uppercase'
          }}>
            {error}
          </div>
          <button
            onClick={() => { setError(null); setLoading(true); startAssessment(); }}
            style={{
              padding: '12px 32px',
              border: '3px solid #000',
              background: '#FFD93D',
              boxShadow: '3px 3px 0 #000',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              textTransform: 'uppercase'
            }}
          >
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          {completed && (
            <AssessmentResults
              score={score}
              total={total}
              subject={subject}
              onContinue={() => {
                // Persist subject so practice mode loads the right subject
                sessionStorage.setItem('selected_subject', subject);
                sessionStorage.setItem('assessmentSubject', subject);
                history.replace(`/app?subject=${encodeURIComponent(subject)}`);
              }}
            />
          )}

          {!completed && (
            <div style={{ position: 'relative', minHeight: '100vh', paddingTop: '60px' }}>
              {/* Assessment Mode Banner */}
              <div style={{
                position: 'sticky',
                top: '48px',
                zIndex: 30,
                width: '100%',
                marginBottom: '24px'
              }}>
                <div style={{
                  border: '5px solid #000000',
                  backgroundColor: '#FF6B6B',
                  padding: '12px 24px',
                  boxShadow: '0 4px 0px 0px #000000',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  margin: '0 20px'
                }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    backgroundColor: '#FFFFFF',
                    border: '2px solid #000000',
                    borderRadius: '50%',
                    animation: 'pulse-dot 1.5s ease-in-out infinite'
                  }}></div>
                  <span style={{
                    fontSize: '16px',
                    fontWeight: 900,
                    color: '#FFFFFF',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    fontFamily: 'system-ui, -apple-system, sans-serif'
                  }}>
                    ASSESSMENT MODE
                  </span>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    backgroundColor: '#FFFFFF',
                    border: '2px solid #000000',
                    borderRadius: '50%',
                    animation: 'pulse-dot 1.5s ease-in-out infinite'
                  }}></div>
                </div>
              </div>

              <div style={{ padding: '0 20px 40px', maxWidth: 900, margin: '0 auto' }}>
                {submitting && (
                  <div style={{
                    textAlign: 'center',
                    padding: '20px',
                    border: '5px solid #000000',
                    backgroundColor: '#FFD93D',
                    marginBottom: '24px',
                    boxShadow: '3px 3px 0 #000000'
                  }}>
                    <span style={{
                      fontSize: '18px',
                      fontWeight: 700,
                      color: '#000000',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em'
                    }}>
                      Loading next question...
                    </span>
                  </div>
                )}

                {currentQuestion && (
                  <AssessmentQuestion
                    question={currentQuestion}
                    questionNumber={questionNumber}
                    totalQuestions={totalQuestions}
                    onAnswer={handleAnswer}
                  />
                )}
              </div>
            </div>
          )}
        </>
      )}
      <Suspense fallback={null}>
        <FloatingControlPanel
          videoRef={dummyVideoRef}
          renderCanvasRef={dummyCanvasRef}
          supportsVideo={true}
          onPaintClick={() => {}}
          isPaintActive={false}
          cameraEnabled={false}
          screenEnabled={false}
          onToggleCamera={() => {}}
          onToggleScreen={() => {}}
          mediaMixerCanvasRef={dummyCanvasRef}
          privacyMode={false}
          onTogglePrivacy={() => {}}
          processedEdgesRef={dummyEdgesRef}
          assessmentMode={true}
        />
      </Suspense>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(0.8);
          }
        }
      `}</style>
    </div>
    </TutorProvider>
    </ThemeProvider>
  );
};

export default AssessmentFlow;

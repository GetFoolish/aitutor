import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';
import Header from '../../components/header/Header';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import FloatingControlPanel from '../floating-control-panel/FloatingControlPanel';
import { TutorProvider } from '../../features/tutor';

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
  const rootHeight = '100dvh';

  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [currentDifficulty, setCurrentDifficulty] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [startError, setStartError] = useState<string | null>(null);
  const [nextQuestionError, setNextQuestionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSubmittingOverlay, setShowSubmittingOverlay] = useState(false);
  const [loadPhase, setLoadPhase] = useState<'fast' | 'generating' | 'slow'>('fast');
  const [isScratchpadOpen, setIsScratchpadOpen] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [screenEnabled, setScreenEnabled] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(false);

  // Ref to track latest assessmentId for prefetch (avoids stale closures)
  const assessmentIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const submitOverlayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Generation counter — prevents stale abort errors from overwriting new state
  const generationRef = useRef(0);
  // Store unblock function to call it explicitly before exit (Bug #2 fix)
  const unblockRef = useRef<(() => void) | null>(null);

  // Client-side content fingerprint tracker to detect duplicate questions
  const seenContentRef = useRef<Set<string>>(new Set());
  const pendingAnswerRef = useRef<{
    assessment_id: string;
    question_id: string;
    skill_id: string;
    is_correct: boolean;
  } | null>(null);
  const floatingVideoRef = useRef<HTMLVideoElement>(null);
  const floatingRenderCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const floatingMixerCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const floatingProcessedEdgesRef = useRef<ImageData | null>(null);


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

  // Block in-app navigation during active assessment (Bug #62)
  useEffect(() => {
    if (!assessmentId || completed) {
      unblockRef.current = null;
      return;
    }
    const unblock = history.block(
      'You have an active assessment in progress. Are you sure you want to leave? Your progress will be lost.'
    );
    unblockRef.current = unblock; // Store for explicit unlock on exit
    return () => {
      unblock();
      unblockRef.current = null;
    };
  }, [assessmentId, completed, history]);

  useEffect(() => {
    startAssessment();
    return () => {
      // Cleanup: abort in-flight request + clear timers on unmount
      abortRef.current?.abort();
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
      if (submitOverlayTimerRef.current) {
        clearTimeout(submitOverlayTimerRef.current);
        submitOverlayTimerRef.current = null;
      }
    };
  }, [subject]);

  useEffect(() => {
    const prevBodyOverflow = document.body.style.overflow;
    const prevHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevBodyOverflow;
      document.documentElement.style.overflow = prevHtmlOverflow;
    };
  }, []);

  const startAssessment = async () => {
    const gen = ++generationRef.current;
    setLoadPhase('fast');
    setStartError(null);
    setNextQuestionError(null);
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const MAX_START_RETRIES = 2;
      const START_HARD_TIMEOUT_MS = 25000;

      // Progressive phase timers: keep UX honest and fail fast on stalls.
      const phase2Timer = setTimeout(() => setLoadPhase('generating'), 3000);
      const phase3Timer = setTimeout(() => setLoadPhase('slow'), 9000);
      const hardTimeout = setTimeout(() => controller.abort(), START_HARD_TIMEOUT_MS);
      timersRef.current = [phase2Timer, phase3Timer, hardTimeout];

      // Kick warm-up immediately (best-effort) so adaptive start can hit warm cache faster.
      apiUtils
        .post(
          `${DASH_API_URL}/api/start-subject`,
          { subject, region: 'US' },
          { signal: controller.signal }
        )
        .catch(() => null);

      let response: Response | null = null;
      for (let attempt = 0; attempt < MAX_START_RETRIES; attempt += 1) {
        response = await apiUtils.post(
          `${DASH_API_URL}/assessment/start-adaptive/${subject}`,
          {},
          { signal: controller.signal }
        );

        if (response.ok) break;

        const status = response.status;
        let detail = '';
        try {
          const errJson = await response.clone().json();
          detail = String(errJson?.detail || errJson?.error || '').toLowerCase();
        } catch {
          detail = '';
        }

        const transientStartFailure =
          status === 503 ||
          (status === 400 &&
            (detail.includes('no questions') ||
              detail.includes('no supported questions') ||
              detail.includes('prepared')));

        if (!transientStartFailure || attempt >= MAX_START_RETRIES - 1) {
          break;
        }

        // Short backoff; avoid long frozen loading screens.
        await new Promise((resolve) => {
          const timer = setTimeout(resolve, 500 * (attempt + 1));
          timersRef.current.push(timer);
        });
      }

      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];

      if (!response) throw new Error('No response from assessment start');
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
          setStartError(data.error);
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
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
      // Stale request (user clicked Try Again) — ignore the error
      if (gen !== generationRef.current) return;
      console.error('Assessment start failed:', err);
      const msg = err?.name === 'AbortError'
        ? 'Assessment setup timed out. Please try again.'
        : 'Failed to load assessment. Please try again.';
      setStartError(msg);
      setLoading(false);
    }
  };

  const applyNextResponse = useCallback((data: any) => {
    if (data.completed) {
      setScore(data.score ?? 0);
      setTotal(data.total ?? totalQuestions);
      setCompleted(true);
      return;
    }

    if (!data.question) {
      throw new Error('Missing question payload');
    }

    // Client-side duplicate check: keep flowing even if backend reused content.
    const fp = contentFingerprint(data.question);
    if (seenContentRef.current.has(fp)) {
      console.warn('[AssessmentFlow] Duplicate content detected client-side');
    }
    seenContentRef.current.add(fp);

    setCurrentQuestion(data.question);
    setQuestionNumber(data.question_number);
    setTotalQuestions(data.total_questions);
    setCurrentDifficulty(data.current_difficulty);

    if (assessmentIdRef.current) {
      firePrefetch(assessmentIdRef.current, data.current_difficulty);
    }
  }, [contentFingerprint, firePrefetch, totalQuestions]);

  const requestNextQuestion = useCallback(async (
    payload: { assessment_id: string; question_id: string; skill_id: string; is_correct: boolean },
  ): Promise<Response> => {
    // Fast-settle policy: avoid long blocking spinner loops on next-question fetch.
    const NEXT_REQUEST_TIMEOUTS_MS = [1200, 1500];

    for (let attempt = 0; attempt < NEXT_REQUEST_TIMEOUTS_MS.length; attempt += 1) {
      const timeoutMs = NEXT_REQUEST_TIMEOUTS_MS[attempt];
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      let response: Response;
      try {
        response = await apiUtils.post(
          `${DASH_API_URL}/assessment/next`,
          payload,
          { signal: controller.signal },
        );
      } catch (err: any) {
        clearTimeout(timeoutId);
        const aborted = err?.name === 'AbortError';
        if (aborted && attempt < NEXT_REQUEST_TIMEOUTS_MS.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, 120 * (attempt + 1)));
          continue;
        }
        if (aborted) throw new Error('TIMEOUT');
        throw err;
      }
      clearTimeout(timeoutId);

      if (response.ok) {
        return response;
      }

      if (response.status === 503 && attempt < NEXT_REQUEST_TIMEOUTS_MS.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 120 * (attempt + 1)));
        continue;
      }

      throw new Error(`HTTP ${response.status}`);
    }

    throw new Error('HTTP 503');
  }, []);

  const retryPendingNextQuestion = useCallback(async () => {
    const payload = pendingAnswerRef.current;
    if (!payload || submitting) return;

    setSubmitting(true);
    setShowSubmittingOverlay(false);
    if (submitOverlayTimerRef.current) {
      clearTimeout(submitOverlayTimerRef.current);
    }
    submitOverlayTimerRef.current = setTimeout(() => setShowSubmittingOverlay(true), 350);
    setNextQuestionError(null);

    try {
      const response = await requestNextQuestion(payload);
      const data = await response.json();
      applyNextResponse(data);
      pendingAnswerRef.current = null;
    } catch (err: any) {
      console.error('Assessment next retry failed:', err);
      if (err?.message === 'TIMEOUT' || String(err?.message || '').includes('HTTP 503')) {
        setNextQuestionError('Still preparing your next question. Please retry in a moment.');
      } else {
        setNextQuestionError('Network issue while fetching next question. Please retry.');
      }
    } finally {
      setSubmitting(false);
      setShowSubmittingOverlay(false);
      if (submitOverlayTimerRef.current) {
        clearTimeout(submitOverlayTimerRef.current);
        submitOverlayTimerRef.current = null;
      }
    }
  }, [applyNextResponse, requestNextQuestion, submitting]);

  const handleAnswer = async (isCorrect: boolean) => {
    if (!currentQuestion || !assessmentId || submitting) return;

    const payload = {
      assessment_id: assessmentId,
      question_id: currentQuestion?.dash_metadata?.dash_question_id || `q_${questionNumber}`,
      skill_id: (currentQuestion?.dash_metadata?.skill_ids || [])[0] || '',
      is_correct: isCorrect,
    };
    pendingAnswerRef.current = payload;
    setSubmitting(true);
    setShowSubmittingOverlay(false);
    if (submitOverlayTimerRef.current) {
      clearTimeout(submitOverlayTimerRef.current);
    }
    submitOverlayTimerRef.current = setTimeout(() => setShowSubmittingOverlay(true), 350);
    setNextQuestionError(null);

    try {
      const response = await requestNextQuestion(payload);
      const data = await response.json();
      applyNextResponse(data);
      pendingAnswerRef.current = null;
    } catch (err: any) {
      console.error('Assessment next failed:', err);
      if (err?.message === 'TIMEOUT' || String(err?.message || '').includes('HTTP 503')) {
        setNextQuestionError('Still preparing your next question. Please retry in a moment.');
      } else {
        setNextQuestionError('Failed to load next question. Please retry.');
      }
    } finally {
      setSubmitting(false);
      setShowSubmittingOverlay(false);
      if (submitOverlayTimerRef.current) {
        clearTimeout(submitOverlayTimerRef.current);
        submitOverlayTimerRef.current = null;
      }
    }
  };

  /* ----------------------------------------------------
     Render
  ---------------------------------------------------- */
  return (
    <div
      className="assessment-container"
      style={{
        position: 'fixed',
        inset: 0,
        overflowX: 'hidden',
        overflowY: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        height: rootHeight,
        maxHeight: rootHeight,
        width: '100vw',
        padding: 0,
        alignItems: 'stretch',
        justifyContent: 'flex-start',
      }}
    >
      <BackgroundShapes />

      <Header
        sidebarOpen={false}
        onToggleSidebar={() => {}}
        assessmentMode={true}
      />

      {loading && (
        <div style={{
          flex: 1,
          minHeight: 0,
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
          {/* Cancel button — always visible during loading (Bug #54) */}
          <button
            onClick={() => {
              abortRef.current?.abort();
              assessmentIdRef.current = null;
              sessionStorage.removeItem('selected_subject');
              sessionStorage.removeItem('onboarding_complete');
              window.location.replace('/app/dev-login');
            }}
            style={{
              padding: '10px 24px',
              border: '2px solid #000',
              background: '#fff',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '12px',
              textTransform: 'uppercase',
            }}
          >
            Cancel
          </button>
          {loadPhase === 'slow' && (
            <button
              onClick={() => {
                abortRef.current?.abort();
                setStartError(null);
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

      {startError && (
        <div style={{
          flex: 1,
          minHeight: 0,
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
            {startError}
          </div>
          <button
            onClick={() => { setStartError(null); setLoading(true); startAssessment(); }}
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
          <button
            onClick={() => {
              assessmentIdRef.current = null;
              sessionStorage.removeItem('selected_subject');
              sessionStorage.removeItem('onboarding_complete');
              history.replace('/app/dev-login');
            }}
            style={{
              padding: '10px 24px',
              border: '2px solid #000',
              background: '#fff',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '12px',
              textTransform: 'uppercase',
              marginTop: '8px',
            }}
          >
            Back to Dev Login
          </button>
        </div>
      )}

      {!loading && !startError && (
        <>
          {completed && (
            <AssessmentResults
              score={score}
              total={total}
              subject={subject}
              onContinue={() => {
                // Persist subject and deep-link into learning mode route.
                const normalizedSubject = String(subject || '').trim() || 'math';
                const encodedSubject = encodeURIComponent(normalizedSubject);
                sessionStorage.setItem('selected_subject', normalizedSubject);
                sessionStorage.setItem('assessmentSubject', normalizedSubject);
                sessionStorage.setItem('assessment_completed_subject', normalizedSubject);

                // Warm the subject switch before routing so first learning question appears reliably.
                void apiUtils
                  .post(`${DASH_API_URL}/api/start-subject`, { subject: normalizedSubject, region: 'US' })
                  .catch(() => null)
                  .finally(() => {
                    history.replace(`/app/learn/${encodedSubject}?subject=${encodedSubject}&fromAssessment=1`);
                  });
              }}
            />
          )}

          {!completed && (
            <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {/* Assessment Mode Banner */}
              <div style={{
                width: '100%',
                marginBottom: '10px'
              }}>
                <div style={{
                  border: '5px solid #000000',
                  backgroundColor: '#FF6B6B',
                  padding: '10px 16px',
                  boxShadow: '0 4px 0px 0px #000000',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '0 10px',
                }}>
                  {/* Exit assessment — regular flex child, no absolute positioning */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      // CRITICAL: Unblock navigation BEFORE clearing state (Bug #2 fix)
                      if (unblockRef.current) {
                        unblockRef.current();
                        unblockRef.current = null;
                      }
                      // Clear assessmentId so beforeunload handler won't fire
                      assessmentIdRef.current = null;
                      setAssessmentId(null);
                      setCurrentQuestion(null);
                      setCompleted(false);
                      // Keep selected_subject in sessionStorage so learning page can load it
                      // Navigate to learning page with subject param
                      const encodedSubject = encodeURIComponent(subject);
                      history.replace(`/app?subject=${encodedSubject}`);
                    }}
                    style={{
                      flexShrink: 0,
                      background: '#FFFFFF',
                      border: '3px solid #000000',
                      color: '#000000',
                      fontSize: '13px',
                      fontWeight: 900,
                      padding: '6px 14px',
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      boxShadow: '2px 2px 0 #000',
                    }}
                  >
                    ✕ Exit
                  </button>
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
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
                  {/* Right spacer to balance the Exit button */}
                  <div style={{ width: '70px', flexShrink: 0 }}></div>
                </div>
              </div>

              <div className="assessment-content-wrapper" style={{
                padding: '0 12px 10px 12px',
                maxWidth: 1180,
                margin: '0 auto',
                width: '100%',
                flex: '1 1 auto',
                display: 'flex',
                flexDirection: 'column',
                overflowY: 'auto',
                overflowX: 'hidden',
              }}>
                {nextQuestionError && (
                  <div style={{
                    border: '4px solid #000000',
                    backgroundColor: '#FF6B6B',
                    color: '#fff',
                    padding: '14px 16px',
                    marginBottom: '20px',
                    boxShadow: '3px 3px 0 #000',
                    textAlign: 'center'
                  }}>
                    <div style={{
                      fontSize: '14px',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      marginBottom: '10px',
                    }}>
                      {nextQuestionError}
                    </div>
                    <button
                      onClick={retryPendingNextQuestion}
                      disabled={submitting}
                      style={{
                        padding: '10px 24px',
                        border: '3px solid #000',
                        background: '#FFD93D',
                        color: '#000',
                        cursor: submitting ? 'not-allowed' : 'pointer',
                        fontWeight: 800,
                        fontSize: '13px',
                        textTransform: 'uppercase',
                        opacity: submitting ? 0.7 : 1,
                      }}
                    >
                      {submitting ? 'Retrying...' : 'Retry Next Question'}
                    </button>
                  </div>
                )}
                {currentQuestion && (
                  <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', position: 'relative' }}>
                    <AssessmentQuestion
                      question={currentQuestion}
                      questionNumber={questionNumber}
                      totalQuestions={totalQuestions}
                      onAnswer={handleAnswer}
                    />
                    {submitting && showSubmittingOverlay && (
                      <div
                        style={{
                          position: 'absolute',
                          inset: 0,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          pointerEvents: 'none',
                          background: 'rgba(255, 253, 245, 0.62)',
                          backdropFilter: 'blur(1px)',
                          zIndex: 40,
                        }}
                      >
                        <div
                          style={{
                            textAlign: 'center',
                            padding: '12px 18px',
                            border: '4px solid #000000',
                            backgroundColor: '#FFD93D',
                            boxShadow: '3px 3px 0 #000000'
                          }}
                        >
                          <span
                            style={{
                              fontSize: '16px',
                              fontWeight: 800,
                              color: '#000000',
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em'
                            }}
                          >
                            Loading next question...
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !startError && !completed && (
        <TutorProvider assessmentMode={true}>
          <FloatingControlPanel
            renderCanvasRef={floatingRenderCanvasRef}
            videoRef={floatingVideoRef}
            supportsVideo={true}
            onPaintClick={() => setIsScratchpadOpen((prev) => !prev)}
            isPaintActive={isScratchpadOpen}
            cameraEnabled={cameraEnabled}
            screenEnabled={screenEnabled}
            onToggleCamera={setCameraEnabled}
            onToggleScreen={setScreenEnabled}
            privacyMode={privacyMode}
            onTogglePrivacy={setPrivacyMode}
            mediaMixerCanvasRef={floatingMixerCanvasRef}
            processedEdgesRef={floatingProcessedEdgesRef}
            assessmentMode={true}
          />
        </TutorProvider>
      )}

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
  );
};

export default AssessmentFlow;

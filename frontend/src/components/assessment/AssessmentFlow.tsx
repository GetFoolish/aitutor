import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';
import Header from '../../components/header/Header';
import '../question-display/mcq-fix.css';

// Responsive helper: true when viewport ≤ 768px
const useIsMobile = () => {
  const [isMobile, setIsMobile] = React.useState(
    typeof window !== 'undefined' ? window.innerWidth <= 768 : false
  );
  React.useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return isMobile;
};

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
  const isMobile = useIsMobile();

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
  const [showExitDialog, setShowExitDialog] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);

  // Inject alignment-fix CSS at runtime (CSS files may be cached by browser)
  useEffect(() => {
    const id = 'alignment-fix-runtime';
    if (!document.getElementById(id)) {
      const s = document.createElement('style');
      s.id = id;
      s.textContent = [
        '.assessment-content-wrapper { padding-left: 0 !important; }',
        'div:has(> #question-content-container) { transform-origin: top left !important; }',
      ].join('\n');
      document.head.appendChild(s);
    }
    return () => { document.getElementById(id)?.remove(); };
  }, []);

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
    const attemptRecovery = async () => {
      // Check if there's an active session to resume
      let savedSession: string | null = null;
      try { savedSession = localStorage.getItem('active_assessment'); } catch { /* private browsing */ }
      console.log('[AssessmentFlow] Recovery check:', { savedSession, assessmentId, subject });

      if (savedSession && !assessmentId) {
        try {
          const session = JSON.parse(savedSession);
          // Only resume if session is recent (< 1 hour old) and matches current subject
          const isRecent = Date.now() - session.started_at < 3600000;
          const matchesSubject = session.subject === subject;

          console.log('[AssessmentFlow] Session validation:', {
            session_id: session.assessment_id,
            isRecent,
            matchesSubject,
            age: Math.round((Date.now() - session.started_at) / 1000) + 's',
          });

          if (isRecent && matchesSubject) {
            console.log('[AssessmentFlow] Attempting to resume session:', session.assessment_id);
            const response = await apiUtils.get(`${DASH_API_URL}/assessment/resume/${session.assessment_id}`);

            console.log('[AssessmentFlow] Resume response:', response.status, response.ok);

            if (response.ok) {
              const data = await response.json();
              console.log('[AssessmentFlow] Session resumed successfully:', data);

              // Restore state from resumed session
              setAssessmentId(data.assessment_id);
              assessmentIdRef.current = data.assessment_id;
              setCurrentQuestion(data.question);
              setQuestionNumber(data.question_number);
              setTotalQuestions(data.total_questions);
              setCurrentDifficulty(data.current_difficulty);
              setLoading(false);
              return; // Successfully resumed
            } else {
              const errorText = await response.text();
              console.warn('[AssessmentFlow] Resume failed with status', response.status, errorText);
            }
          } else {
            console.log('[AssessmentFlow] Session not valid for resume:', { isRecent, matchesSubject });
          }

          // If resume failed or session too old, clear it
          try { localStorage.removeItem('active_assessment'); } catch { /* private browsing */ }
        } catch (error) {
          console.error('[AssessmentFlow] Resume failed, starting fresh:', error);
          try { localStorage.removeItem('active_assessment'); } catch { /* private browsing */ }
        }
      } else {
        console.log('[AssessmentFlow] No session to resume or assessmentId already set');
      }

      // No session to resume or resume failed - start fresh
      startAssessment();
    };

    attemptRecovery();

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

  const confirmExit = () => {
    setShowExitDialog(false);
    // CRITICAL: Unblock navigation BEFORE clearing state (Bug #2 fix)
    if (unblockRef.current) {
      unblockRef.current();
      unblockRef.current = null;
    }
    // Clear assessmentId so beforeunload handler won't fire
    assessmentIdRef.current = null;
    const currentAssessmentId = assessmentId; // Capture before clearing
    setAssessmentId(null);
    setCurrentQuestion(null);
    setCompleted(false);
    // Clear ALL assessment state from storage to prevent stale resume
    sessionStorage.removeItem('assessmentSubject');
    try { localStorage.removeItem('active_assessment'); } catch { /* private browsing */ }
    // Navigate to exit page with context
    const encodedSubject = encodeURIComponent(subject);
    const exitUrl = currentAssessmentId
      ? `/app/assessment-exit?subject=${encodedSubject}&assessment_id=${currentAssessmentId}`
      : `/app/assessment-exit?subject=${encodedSubject}`;
    history.replace(exitUrl);
  };

  const startAssessment = async () => {
    const gen = ++generationRef.current;
    setLoadPhase('fast');
    setStartError(null);
    setNextQuestionError(null);
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const MAX_START_RETRIES = 2;
      const START_HARD_TIMEOUT_MS = 50000; // Increased from 25s to 50s while backend optimizes

      // Progressive phase timers: keep UX honest and fail fast on stalls.
      const phase2Timer = setTimeout(() => setLoadPhase('generating'), 3000);
      const phase3Timer = setTimeout(() => setLoadPhase('slow'), 9000);
      const hardTimeout = setTimeout(() => controller.abort(), START_HARD_TIMEOUT_MS);
      // Clear any existing timers before setting new ones
      timersRef.current.forEach(clearTimeout);
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
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errorData = await response.clone().json();
          errorDetail = errorData.detail || errorData.error || errorData.message || '';
        } catch {
          errorDetail = await response.text().catch(() => '');
        }
        const errorMsg = `HTTP ${response.status}${errorDetail ? `: ${errorDetail}` : ''}`;
        console.error('[AssessmentFlow] Start failed:', errorMsg);
        throw new Error(errorMsg);
      }
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

      // Validate required fields in response
      if (!data.assessment_id || !data.question) {
        throw new Error('Server returned incomplete assessment data (missing assessment_id or question)');
      }

      setAssessmentId(data.assessment_id);
      assessmentIdRef.current = data.assessment_id;

      // Save session to localStorage for recovery on page refresh
      try {
        localStorage.setItem('active_assessment', JSON.stringify({
          assessment_id: data.assessment_id,
          subject,
          started_at: Date.now(),
          question_count: data.question_number || 1,
        }));
      } catch { /* private browsing — localStorage unavailable */ }

      setCurrentQuestion(data.question);
      setQuestionNumber(data.question_number);
      setTotalQuestions(data.total_questions);
      setCurrentDifficulty(data.current_difficulty);
      setCorrectCount(0);
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
      // Clear saved session on completion
      try { localStorage.removeItem('active_assessment'); } catch { /* private browsing */ }
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

    // Update session in localStorage for recovery on refresh
    if (assessmentIdRef.current) {
      try {
        localStorage.setItem('active_assessment', JSON.stringify({
          assessment_id: assessmentIdRef.current,
          subject,
          started_at: Date.now(),
          question_count: data.question_number || 1,
        }));
      } catch { /* private browsing */ }

      firePrefetch(assessmentIdRef.current, data.current_difficulty);
    }
  }, [contentFingerprint, firePrefetch, totalQuestions, subject]);

  const requestNextQuestion = useCallback(async (
    payload: { assessment_id: string; question_id: string; skill_id: string; is_correct: boolean },
  ): Promise<Response> => {
    // Fast-settle policy: avoid long blocking spinner loops on next-question fetch.
    const NEXT_REQUEST_TIMEOUTS_MS = [4000, 8000];

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
    // Use ref so we never fail due to stale-closure assessmentId state
    const currentAssessmentId = assessmentIdRef.current;
    if (!currentQuestion || !currentAssessmentId || submitting) return;

    const payload = {
      assessment_id: currentAssessmentId,
      question_id: currentQuestion?.dash_metadata?.dash_question_id || `q_${questionNumber}`,
      skill_id: (currentQuestion?.dash_metadata?.skill_ids || [])[0] || '',
      is_correct: isCorrect,
    };
    pendingAnswerRef.current = payload;
    if (isCorrect) setCorrectCount(prev => prev + 1);
    setSubmitting(true);
    setQuestionNumber(prev => prev + 1);
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
        backgroundColor: '#fff',
      }}
    >
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
            border: '1px solid #e0e0e0',
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
            {loadPhase === 'fast' && `Warming up ${subject}`}
            {loadPhase === 'generating' && `Generating questions`}
            {loadPhase === 'slow' && `Quality check in progress`}
          </div>
          <div style={{
            fontSize: '14px',
            color: '#666',
            maxWidth: '420px',
            textAlign: 'center',
            lineHeight: '1.5'
          }}>
            {loadPhase === 'fast' && 'Checking question bank for cached content...'}
            {loadPhase === 'generating' && 'Creating AI-generated questions tailored to your level...'}
            {loadPhase === 'slow' && 'Verifying answer accuracy and hint quality. This ensures you get the best learning experience.'}
          </div>
          {/* Cancel button — always visible during loading (Bug #54) */}
          <button
            onClick={() => {
              abortRef.current?.abort();
              assessmentIdRef.current = null;
              sessionStorage.removeItem('selected_subject');
              // Don't clear onboarding_complete — user already filled in their info,
              // clearing it forces them to redo the entire onboarding flow
              window.location.replace('/app/dev-login');
            }}
            style={{
              padding: '10px 24px',
              border: '1px solid #e0e0e0',
              background: '#fff',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              textTransform: 'uppercase',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              minHeight: '48px',
            }}
          >
            Cancel
          </button>
          {loadPhase === 'slow' && !startError && (
            <button
              onClick={() => {
                abortRef.current?.abort();
                setStartError(null);
                setLoading(true);
                startAssessment();
              }}
              style={{
                padding: '10px 28px',
                border: '1px solid #e0e0e0',
                background: '#FFD93D',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '14px',
                textTransform: 'uppercase',
                minHeight: '48px'
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
            border: '1px solid rgba(255,255,255,0.3)',
            background: '#FF6B6B',
            color: '#fff',
            fontWeight: 700,
            fontSize: '14px',
            textTransform: 'uppercase',
            boxShadow: '0 2px 8px rgba(0,0,0,0.12)'
          }}>
            {startError}
          </div>
          <button
            onClick={() => { if (loading) return; setStartError(null); setLoading(true); startAssessment(); }}
            disabled={loading}
            style={{
              padding: '12px 32px',
              border: '1px solid #e0e0e0',
              background: loading ? '#ddd' : '#FFD93D',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              cursor: loading ? 'wait' : 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              textTransform: 'uppercase',
              minHeight: '48px'
            }}
          >
            {loading ? 'Starting...' : 'Try Again'}
          </button>
          <button
            onClick={() => {
              assessmentIdRef.current = null;
              sessionStorage.removeItem('selected_subject');
              // Don't clear onboarding_complete — preserve user's onboarding data
              history.replace('/app/dev-login');
            }}
            style={{
              padding: '10px 24px',
              border: '1px solid #e0e0e0',
              background: '#fff',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              textTransform: 'uppercase',
              marginTop: '8px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              minHeight: '48px',
            }}
          >
            Try Different Subject
          </button>
          <button
            onClick={() => { history.replace('/app'); }}
            style={{
              padding: '10px 24px',
              border: '1px solid #e0e0e0',
              background: '#E0E0E0',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              textTransform: 'uppercase',
              marginTop: '4px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              minHeight: '48px',
            }}
          >
            Back to Home
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
            <div style={{ position: 'relative', flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', backgroundColor: '#fff' }}>
              {/* Assessment Mode Banner */}
              <div style={{
                width: '100%',
                marginTop: isMobile ? '44px' : '56px',
                marginBottom: '10px'
              }}>
                <div style={{
                  border: '1px solid rgba(255,255,255,0.15)',
                  backgroundColor: '#4f46e5',
                  padding: isMobile ? '8px 10px' : '10px 16px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: isMobile ? '6px' : '12px',
                  margin: isMobile ? '0 0' : '0 10px',
                }}>
                  {/* Exit assessment — regular flex child, no absolute positioning */}
                  <button
                    type="button"
                    className="assessment-exit-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowExitDialog(true);
                    }}
                    style={{
                      flexShrink: 0,
                      fontSize: isMobile ? '12px' : '14px',
                      fontWeight: 900,
                      padding: isMobile ? '6px 12px' : '8px 16px',
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      minHeight: isMobile ? '40px' : '48px',
                      transition: 'transform 100ms ease, box-shadow 100ms ease',
                    }}
                    onMouseDown={(e) => {
                      e.currentTarget.style.transform = 'translate(2px, 2px)';
                    }}
                    onMouseUp={(e) => {
                      e.currentTarget.style.transform = 'translate(0, 0)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translate(0, 0)';
                    }}
                  >
                    Exit
                  </button>
                  {/* Running score badge */}
                  <div style={{
                    flexShrink: 0,
                    background: 'rgba(255,255,255,0.15)',
                    border: '2px solid rgba(255,255,255,0.5)',
                    color: '#fff',
                    fontSize: isMobile ? '11px' : '13px',
                    fontWeight: 900,
                    padding: isMobile ? '4px 8px' : '6px 12px',
                    letterSpacing: '0.05em',
                    minWidth: isMobile ? '52px' : '72px',
                    textAlign: 'center' as const,
                  }}>
                    ✓ {correctCount}
                  </div>
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{
                      fontSize: isMobile ? '12px' : '16px',
                      fontWeight: 900,
                      color: '#FFFFFF',
                      textTransform: 'uppercase',
                      letterSpacing: isMobile ? '0.05em' : '0.1em',
                      fontFamily: 'system-ui, -apple-system, sans-serif'
                    }}>
                      {isMobile
                        ? `GRADE ${currentDifficulty < 0.3 ? '3-4' : currentDifficulty < 0.5 ? '5-6' : currentDifficulty < 0.7 ? '7-8' : '9-10'} ${subject.toUpperCase()}`
                        : `GRADE ${currentDifficulty < 0.3 ? '3-4' : currentDifficulty < 0.5 ? '5-6' : currentDifficulty < 0.7 ? '7-8' : '9-10'} ${subject.toUpperCase()} ASSESSMENT`}
                    </span>
                  </div>
                  {/* Right spacer to balance the Exit button — hidden on mobile */}
                  {!isMobile && <div style={{ width: '70px', flexShrink: 0 }}></div>}
                </div>
              </div>


              <div className="assessment-content-wrapper" style={{
                paddingRight: '0',
                paddingBottom: '0',
                maxWidth: '100%',
                marginLeft: 0,
                marginRight: 0,
                width: '100%',
                flex: '1 1 auto',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                minHeight: 0,
              }}>
                {nextQuestionError && (
                  <div style={{
                    border: '1px solid rgba(255,255,255,0.3)',
                    backgroundColor: '#FF6B6B',
                    color: '#fff',
                    padding: '14px 16px',
                    marginBottom: '20px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
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
                        border: '1px solid #e0e0e0',
                        background: '#FFD93D',
                        color: '#000',
                        cursor: submitting ? 'not-allowed' : 'pointer',
                        fontWeight: 800,
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        opacity: submitting ? 0.7 : 1,
                        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                        minHeight: '48px',
                      }}
                    >
                      {submitting ? 'Retrying...' : 'Retry Next Question'}
                    </button>
                  </div>
                )}
                {!currentQuestion && !nextQuestionError && (
                  <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                    <div style={{
                      border: '1px solid #e0e0e0',
                      backgroundColor: '#FFD93D',
                      padding: '20px',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                      fontWeight: 800,
                      fontSize: '14px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                    }}>
                      Loading question...
                    </div>
                  </div>
                )}
                {currentQuestion && (
                  <div style={{ flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column', position: 'relative', overflowY: 'auto', overflowX: 'hidden' }}>
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
                            border: '1px solid #e0e0e0',
                            backgroundColor: '#FFD93D',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.12)'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ display: 'inline-block', width: '18px', height: '18px', border: '3px solid #4f46e5', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0 }} />
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
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Exit confirmation dialog */}
      {showExitDialog && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1100]"
          onClick={() => setShowExitDialog(false)}
        >
          <div
            role="dialog"
            className="bg-white dark:bg-neutral-800 border border-gray-200 dark:border-gray-700 shadow-xl p-8 max-w-md mx-4 rounded-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-2xl font-black uppercase tracking-tight text-black dark:text-white mb-4">
              Exit Assessment?
            </h3>
            <p className="text-base text-gray-700 dark:text-gray-300 mb-6">
              Your progress will be saved, but you'll need to start a new assessment to continue practicing. You can always try another subject from the home screen.
            </p>
            <div className="flex gap-4">
              <button
                onClick={confirmExit}
                className="flex-1 py-3 px-6 font-black uppercase tracking-wide text-base bg-red-500 dark:bg-red-600 text-white border border-red-400 dark:border-red-700 shadow-md hover:bg-red-600 dark:hover:bg-red-700 hover:shadow-sm active:shadow-none transition-all duration-100 rounded"
              >
                Yes, Exit
              </button>
              <button
                onClick={() => setShowExitDialog(false)}
                className="flex-1 py-3 px-6 font-black uppercase tracking-wide text-base bg-gray-200 dark:bg-neutral-700 text-black dark:text-white border border-gray-300 dark:border-neutral-600 shadow-md hover:bg-gray-300 dark:hover:bg-neutral-600 hover:shadow-sm active:shadow-none transition-all duration-100 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
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

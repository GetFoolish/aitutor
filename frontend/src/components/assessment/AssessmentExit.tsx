import React, { useEffect, useState } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { CheckCircle2, BookOpen, Home } from 'lucide-react';
import { apiUtils } from '../../lib/api-utils';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface SessionStats {
  questionsAnswered: number;
  correct: number;
}

/**
 * AssessmentExit - Clean exit page shown when a user leaves mid-assessment.
 * Displays partial progress stats and provides navigation options.
 */
const AssessmentExit: React.FC = () => {
  const history = useHistory();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);

  const subject = searchParams.get('subject') || 'Assessment';
  const assessmentId = searchParams.get('assessment_id');

  // Stats from URL params (set by AssessmentFlow on exit)
  const urlQuestionsAnswered = parseInt(searchParams.get('questions_answered') || '0', 10);
  const urlCorrect = parseInt(searchParams.get('correct') || '0', 10);

  const [stats, setStats] = useState<SessionStats>({
    questionsAnswered: urlQuestionsAnswered,
    correct: urlCorrect,
  });
  const [statsLoaded, setStatsLoaded] = useState(urlQuestionsAnswered > 0);

  // Try to enrich stats from backend if URL params are zero (e.g. direct navigation)
  useEffect(() => {
    if (!assessmentId || urlQuestionsAnswered > 0) return;

    apiUtils.get(`${DASH_API_URL}/assessment/resume/${assessmentId}`)
      .then(async (res) => {
        if (!res.ok) return;
        const data = await res.json();
        // resume endpoint returns session context — extract questions_asked if available
        const asked = data.questions_asked ?? data.session?.questions_asked;
        const correct = data.correct_count ?? data.session?.correct_count;
        if (typeof asked === 'number') {
          setStats({
            questionsAnswered: asked,
            correct: typeof correct === 'number' ? correct : 0,
          });
          setStatsLoaded(true);
        }
      })
      .catch(() => {
        // Backend unavailable — URL params are the source of truth, keep them
      });
  }, [assessmentId, urlQuestionsAnswered]);

  const accuracy =
    stats.questionsAnswered > 0
      ? Math.round((stats.correct / stats.questionsAnswered) * 100)
      : null;

  const handleTryAnother = () => {
    sessionStorage.removeItem('selected_subject');
    sessionStorage.removeItem('assessmentSubject');
    sessionStorage.removeItem('active_assessment');
    history.push('/app/dev-login?v=4');
  };

  const handleBackHome = () => {
    sessionStorage.removeItem('selected_subject');
    sessionStorage.removeItem('assessmentSubject');
    sessionStorage.removeItem('active_assessment');
    sessionStorage.removeItem('onboarding_complete');
    history.push('/app/dev-login?v=4');
  };

  return (
    <div className="min-h-screen bg-white dark:bg-[#121212] p-4 md:p-8">
      <div className="max-w-2xl mx-auto">
        {/* Exit confirmation card */}
        <div className="bg-white dark:bg-neutral-800 border-[4px] border-black dark:border-white shadow-[8px_8px_0_0_#000] dark:shadow-[8px_8px_0_0_rgba(255,255,255,0.3)] p-8">

          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div className="bg-yellow-400 dark:bg-yellow-500 p-4 border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]">
              <CheckCircle2 className="w-12 h-12 text-black" />
            </div>
            <div>
              <h1 className="text-3xl font-black uppercase tracking-tight text-black dark:text-white">
                Good effort!
              </h1>
              <p className="text-lg text-gray-700 dark:text-gray-300 mt-1">
                {subject}
              </p>
            </div>
          </div>

          {/* Message */}
          <div className="mb-6 p-6 bg-yellow-50 dark:bg-yellow-900/20 border-[4px] border-black dark:border-yellow-500">
            <p className="text-base text-gray-800 dark:text-gray-200">
              You've made a start — every question counts. Come back whenever you're ready to continue.
            </p>
          </div>

          {/* Progress summary */}
          <div className="mb-8">
            <h2 className="text-sm font-black uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-3">
              Your progress so far
            </h2>
            <div className="grid grid-cols-3 gap-3">
              <div className="p-4 bg-gray-50 dark:bg-neutral-700 border-[3px] border-black dark:border-white text-center">
                <p className="text-3xl font-black text-black dark:text-white">
                  {stats.questionsAnswered}
                </p>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mt-1">
                  Answered
                </p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-neutral-700 border-[3px] border-black dark:border-white text-center">
                <p className="text-3xl font-black text-black dark:text-white">
                  {stats.correct}
                </p>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mt-1">
                  Correct
                </p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-neutral-700 border-[3px] border-black dark:border-white text-center">
                <p className="text-3xl font-black text-black dark:text-white">
                  {accuracy !== null ? `${accuracy}%` : '—'}
                </p>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mt-1">
                  Accuracy
                </p>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-4">
            <button
              onClick={handleTryAnother}
              className="w-full py-4 px-6 font-black uppercase tracking-widest text-lg bg-[#FFD93D] text-black border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_#000] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all duration-100 flex items-center justify-center gap-3"
            >
              <BookOpen className="w-5 h-5" />
              Try Another Subject
            </button>

            <button
              onClick={handleBackHome}
              className="w-full py-4 px-6 font-bold uppercase tracking-widest text-base bg-white dark:bg-neutral-700 text-black dark:text-white border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_#000] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all duration-100 flex items-center justify-center gap-3"
            >
              <Home className="w-5 h-5" />
              Back to Home
            </button>
          </div>
        </div>

        {/* Footer note */}
        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          You can start a fresh assessment anytime from the subject selector
        </p>
      </div>
    </div>
  );
};

export default AssessmentExit;

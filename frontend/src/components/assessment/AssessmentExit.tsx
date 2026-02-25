import React from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { CheckCircle2, BookOpen, Home } from 'lucide-react';

/**
 * AssessmentExit - Clean exit page after assessment
 * Shows summary and provides navigation options
 */
const AssessmentExit: React.FC = () => {
  const history = useHistory();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);

  const subject = searchParams.get('subject') || 'Assessment';
  const assessmentId = searchParams.get('assessment_id');

  const handleTryAnother = () => {
    // Clear ALL session storage and force navigate to subject selector
    sessionStorage.clear();
    window.location.href = '/app';
  };

  const handleBackHome = () => {
    // Clear ALL session data and go to subject picker
    sessionStorage.removeItem('selected_subject');
    sessionStorage.removeItem('assessmentSubject');
    sessionStorage.removeItem('active_assessment');
    sessionStorage.removeItem('onboarding_complete');
    sessionStorage.removeItem('assessment_completed_subject');
    // Force page reload to ensure clean state
    window.location.href = '/app';
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
                Assessment Exited
              </h1>
              <p className="text-lg text-gray-700 dark:text-gray-300 mt-1">
                {subject}
              </p>
            </div>
          </div>

          {/* Message */}
          <div className="mb-8 p-6 bg-yellow-50 dark:bg-yellow-900/20 border-[4px] border-black dark:border-yellow-500">
            <p className="text-base text-gray-800 dark:text-gray-200">
              You've exited the assessment. Your progress has been saved.
            </p>
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
          You can start a new assessment anytime from the subject selector
        </p>
      </div>
    </div>
  );
};

export default AssessmentExit;

import React, { useState, useEffect } from 'react';
import { useLocation, useHistory } from 'react-router-dom';
import RendererComponent from '../question-widget-renderer/RendererComponent';
import { MasteryCelebration } from '../celebration/MasteryCelebration';
import { HintProvider } from '../../contexts/HintContext';
import { useAuth } from '../../contexts/AuthContext';

const CONTENT_API_URL = import.meta.env.VITE_CONTENT_API_URL || 'http://localhost:8001';

interface PracticeSessionProps {
  focusTopic?: string;
  grade?: string;
  subject?: string;
}

interface QuestionResult {
  questionId: string;
  correct: boolean;
  timeSpent: number;
}

export const PracticeSession: React.FC<PracticeSessionProps> = () => {
  const location = useLocation();
  const history = useHistory();
  const { user } = useAuth();

  const {
    focusTopic = location.state?.focusTopic,
    grade = location.state?.grade,
    subject = location.state?.subject,
    learningPlan = location.state?.learningPlan
  } = location.state || {};

  const [questions, setQuestions] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [results, setResults] = useState<QuestionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCompletion, setShowCompletion] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const [startTime, setStartTime] = useState(Date.now());
  const [showFeedback, setShowFeedback] = useState(false);
  const [lastAnswerCorrect, setLastAnswerCorrect] = useState(false);

  useEffect(() => {
    loadQuestions();
  }, [focusTopic, grade, subject]);

  const loadQuestions = async () => {
    setLoading(true);
    try {
      const userId = user?.user_id;
      const genUrl = userId
        ? `${CONTENT_API_URL}/api/generate/personalized?student_id=${encodeURIComponent(userId)}`
        : `${CONTENT_API_URL}/api/generate/live`;

      const response = await fetch(genUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: focusTopic || 'general practice',
          grade: grade || 'K-2',
          subject: subject || 'math',
          count: 10,
          language: 'en',
          force_new: false  // Reuse content library when relevant
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('[PracticeSession] Loaded questions for topic:', focusTopic, 'Count:', data.length);
        setQuestions(data);
      } else {
        console.error('[PracticeSession] Failed to load questions:', response.statusText);
      }
    } catch (error) {
      console.error('[PracticeSession] Error loading questions:', error);
    }
    setLoading(false);
  };

  const handleAnswer = (questionId: string, correct: boolean) => {
    const timeSpent = Date.now() - startTime;
    const result: QuestionResult = {
      questionId,
      correct,
      timeSpent
    };

    const newResults = [...results, result];
    setResults(newResults);

    // Save progress to localStorage
    saveProgress(newResults);

    // Show feedback
    setLastAnswerCorrect(correct);
    setShowFeedback(true);

    // Wait 2.5 seconds before advancing
    setTimeout(() => {
      setShowFeedback(false);

      // Check if mastered (8/10 correct)
      if (newResults.length >= 10) {
        const correctCount = newResults.filter(r => r.correct).length;
        const mastered = correctCount >= 8;

        console.log('[PracticeSession] Session complete:', {
          topic: focusTopic,
          correct: correctCount,
          total: newResults.length,
          mastered
        });

        if (mastered) {
          // Show celebration first!
          setShowCelebration(true);
        } else {
          setShowCompletion(true);
        }
        return;
      }

      // Move to next question
      if (currentIndex < questions.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setStartTime(Date.now());
      } else {
        // Ran out of questions, show completion
        setShowCompletion(true);
      }
    }, 2500);
  };

  const saveProgress = (sessionResults: QuestionResult[]) => {
    try {
      const savedProgress = localStorage.getItem('learning_plan_progress');
      let progressData: any = {
        subject,
        grade,
        topics: []
      };

      if (savedProgress) {
        progressData = JSON.parse(savedProgress);
      }

      // Find or create topic progress
      let topicProgress = progressData.topics.find((t: any) => t.topic === focusTopic);
      if (!topicProgress) {
        topicProgress = {
          topic: focusTopic,
          questionsAnswered: 0,
          questionsCorrect: 0,
          totalNeeded: 10,
          mastered: false
        };
        progressData.topics.push(topicProgress);
      }

      // Update progress
      topicProgress.questionsAnswered = sessionResults.length;
      topicProgress.questionsCorrect = sessionResults.filter(r => r.correct).length;
      topicProgress.mastered = topicProgress.questionsCorrect >= 8;

      localStorage.setItem('learning_plan_progress', JSON.stringify(progressData));
      console.log('[PracticeSession] Saved progress:', topicProgress);
    } catch (error) {
      console.error('[PracticeSession] Failed to save progress:', error);
    }
  };

  const getProgressPercent = () => {
    // Show completion progress (questions answered out of 10), not accuracy
    return Math.round((results.length / 10) * 100);
  };

  const handleBackToDashboard = () => {
    history.push('/app/learning-plan', {
      skillLevel: learningPlan?.skillLevel || 'Beginner',
      focusTopics: learningPlan?.focusTopics || [focusTopic],
      strongTopics: learningPlan?.strongTopics || [],
      grade,
      subject
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-2xl">loading practice questions... ✨</div>
      </div>
    );
  }

  if (showCompletion) {
    const correctCount = results.filter(r => r.correct).length;
    const totalCount = results.length;
    const mastered = correctCount >= 8;
    const progressPercent = getProgressPercent();

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-2xl w-full">
          <div
            className={`bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-12 rounded-xl text-center space-y-6`}
          >
            <div className="text-6xl mb-4">
              {mastered ? '🎉' : '🌟'}
            </div>

            <h2 className="text-4xl font-black">
              {mastered ? `you've mastered ${focusTopic}!` : 'great practice session!'}
            </h2>

            <div className="text-2xl text-gray-600">
              you got <span className="font-black text-purple-600">{correctCount}</span> out of{' '}
              <span className="font-black">{totalCount}</span> questions correct!
            </div>

            <div className="w-full h-12 bg-gray-200 border-4 border-black rounded-lg overflow-hidden">
              <div
                className="h-full transition-all duration-1000 ease-out flex items-center justify-center text-lg font-black"
                style={{
                  width: `${progressPercent}%`,
                  backgroundColor: mastered ? '#4ADE80' : '#A78BFA'
                }}
              >
                {progressPercent}%
              </div>
            </div>

            {mastered && (
              <div className="bg-green-100 border-4 border-black p-6 rounded-lg">
                <p className="text-lg font-bold">
                  ✨ amazing work! you've shown mastery of {focusTopic}. ready to tackle the next topic?
                </p>
              </div>
            )}

            {!mastered && totalCount >= 10 && (
              <div className="bg-purple-100 border-4 border-black p-6 rounded-lg">
                <p className="text-lg font-bold">
                  keep practicing! you need {8 - correctCount} more correct answers to master this topic. you got this! 💪
                </p>
              </div>
            )}

            <div className="flex gap-4 pt-4">
              <button
                onClick={() => {
                  setResults([]);
                  setCurrentIndex(0);
                  setShowCompletion(false);
                  setStartTime(Date.now());
                  loadQuestions();
                }}
                className="flex-1 bg-purple-400 hover:bg-purple-500 border-4 border-black font-black py-4 px-6 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all"
              >
                practice more 🚀
              </button>

              <button
                onClick={handleBackToDashboard}
                className="flex-1 bg-white hover:bg-gray-100 border-4 border-black font-black py-4 px-6 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all"
              >
                back to plan 📚
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center space-y-4">
          <div className="text-2xl">no questions available for this topic</div>
          <button
            onClick={handleBackToDashboard}
            className="bg-purple-400 hover:bg-purple-500 border-4 border-black font-black py-3 px-6 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all"
          >
            back to plan
          </button>
        </div>
      </div>
    );
  }

  const correctCount = results.filter(r => r.correct).length;
  const progressPercent = results.length > 0 ? Math.round((correctCount / results.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress Header */}
      <div className="bg-white border-b-4 border-black p-4">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <div className="space-y-1">
              <div className="text-sm font-bold text-gray-600">working on</div>
              <div className="text-2xl font-black capitalize">{focusTopic} 🎯</div>
            </div>
            <div className="text-right space-y-1">
              <div className="text-sm font-bold text-gray-600">progress</div>
              <div className="text-2xl font-black" style={{ color: progressPercent >= 80 ? '#4ADE80' : '#A78BFA' }}>
                {correctCount}/{results.length} correct
              </div>
            </div>
          </div>

          <div className="w-full h-3 bg-gray-200 border-2 border-black rounded-full overflow-hidden">
            <div
              className="h-full transition-all duration-300"
              style={{
                width: `${(results.length / 10) * 100}%`,
                backgroundColor: '#A78BFA'
              }}
            />
          </div>
          <div className="text-xs text-gray-600 mt-1">
            question {results.length + 1} of 10
          </div>
        </div>
      </div>

      {/* Question Display */}
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] rounded-xl p-8">
          <HintProvider>
            <RendererComponent
              assessmentMode={true}
              assessmentQuestions={[questions[currentIndex]]}
              currentQuestionIndex={0}
              onAssessmentAnswer={handleAnswer}
            />
          </HintProvider>
        </div>

        {/* Feedback Banner */}
        {showFeedback && (
          <div
            className="mt-6 p-6 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] rounded-xl text-center"
            style={{
              backgroundColor: lastAnswerCorrect ? '#E8F5E9' : '#FFEBEE',
              animation: 'slideIn 0.3s ease-out'
            }}
          >
            <div className="text-4xl mb-2">
              {lastAnswerCorrect ? '✓' : '✗'}
            </div>
            <div
              className="text-2xl font-black uppercase"
              style={{
                color: lastAnswerCorrect ? '#2E7D32' : '#C62828',
                letterSpacing: '0.05em'
              }}
            >
              {lastAnswerCorrect ? 'Correct!' : 'Incorrect'}
            </div>
            <div className="text-sm text-gray-600 mt-2">
              moving to next question...
            </div>
          </div>
        )}

        <div className="mt-6 text-center">
          <button
            onClick={handleBackToDashboard}
            className="text-sm font-bold text-gray-600 hover:text-gray-900 underline"
          >
            back to learning plan
          </button>
        </div>
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      {/* Mastery Celebration Modal */}
      <MasteryCelebration
        show={showCelebration}
        topic={focusTopic || ''}
        onClose={() => {
          setShowCelebration(false);
          setShowCompletion(true);
        }}
      />
    </div>
  );
};

export default PracticeSession;

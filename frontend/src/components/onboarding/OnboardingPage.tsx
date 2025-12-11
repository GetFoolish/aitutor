/**
 * Onboarding Page - Duolingo/Kahoot-style onboarding for Math
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiUtils } from '../../lib/api-utils';
import './onboarding.scss';
import { CheckCircle2, XCircle, Trophy, Star, Zap, ArrowRight, Sparkles } from 'lucide-react';

const ONBOARDING_API_URL = import.meta.env.VITE_ONBOARDING_API_URL || 'http://localhost:8004';

interface OnboardingQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  skill_level: string;
  points: number;
}

interface OnboardingProgress {
  current_question_index: number;
  total_questions: number;
  correct_answers: number;
  total_points: number;
  completed: boolean;
  achievements: string[];
}

const ACHIEVEMENTS = {
  perfect_score: { icon: Trophy, label: 'Perfect Score!', color: '#FFD700' },
  math_master: { icon: Star, label: 'Math Master', color: '#FF6B6B' },
  speed_demon: { icon: Zap, label: 'Speed Demon', color: '#4ECDC4' },
  level_up: { icon: Sparkles, label: 'Level Up!', color: '#9B59B6' }
};

const OnboardingPage: React.FC = () => {
  const { user } = useAuth();
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [isAnswered, setIsAnswered] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [explanation, setExplanation] = useState('');
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [submittingAnswer, setSubmittingAnswer] = useState(false);
  const [timeStarted, setTimeStarted] = useState<number>(Date.now());
  const [showAchievement, setShowAchievement] = useState<string | null>(null);
  const [pointsEarned, setPointsEarned] = useState(0);
  const [streak, setStreak] = useState(0);
  const [combo, setCombo] = useState(1);
  const [level, setLevel] = useState(1);
  const [xp, setXp] = useState(0);

  useEffect(() => {
    loadQuestions();
    loadProgress();
  }, []);

  const loadQuestions = async () => {
    try {
      const response = await apiUtils.get(`${ONBOARDING_API_URL}/api/onboarding/questions`);
      if (!response.ok) {
        throw new Error(`Failed to load questions: ${response.status}`);
      }
      const data = await response.json();
      setQuestions(data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading questions:', error);
      // If service is unavailable, show error message
      setLoading(false);
      // You could set an error state here to show a user-friendly message
    }
  };

  const loadProgress = async () => {
    try {
      const response = await apiUtils.get(`${ONBOARDING_API_URL}/api/onboarding/progress`);
      if (!response.ok) {
        throw new Error(`Failed to load progress: ${response.status}`);
      }
      const progressData = await response.json();
      setProgress(progressData);
      if (progressData.current_question_index < questions.length) {
        setCurrentQuestionIndex(progressData.current_question_index);
      }
      // Initialize streak from correct answers
      setStreak(progressData.correct_answers || 0);
      // Initialize XP from total points
      setXp(progressData.total_points || 0);
      // Calculate level from XP
      setLevel(Math.floor((progressData.total_points || 0) / 100) + 1);
    } catch (error) {
      console.error('Error loading progress:', error);
    }
  };

  const handleAnswer = async (answer: string) => {
    if (isAnswered || submittingAnswer) return;

    setSelectedAnswer(answer);
    setSubmittingAnswer(true);
    const timeTaken = (Date.now() - timeStarted) / 1000;

    try {
      const currentQuestion = questions[currentQuestionIndex];
      const response = await apiUtils.post(`${ONBOARDING_API_URL}/api/onboarding/answer`, {
        question_id: currentQuestion.question_id,
        answer: answer,
        time_taken_seconds: timeTaken
      });

      if (!response.ok) {
        throw new Error(`Failed to submit answer: ${response.status}`);
      }
      const result = await response.json();
      setIsAnswered(true);
      setIsCorrect(result.is_correct);
      setExplanation(result.explanation);
      setSubmittingAnswer(false);
      
      // Calculate combo multiplier (increases with streak)
      const newCombo = result.is_correct ? Math.min(combo + 0.2, 3) : 1;
      setCombo(newCombo);
      
      // Update streak
      if (result.is_correct) {
        setStreak(prev => prev + 1);
      } else {
        setStreak(0);
      }
      
      // Calculate points with combo
      const basePoints = result.points_earned || 0;
      const comboPoints = Math.floor(basePoints * newCombo);
      setPointsEarned(comboPoints);
      
      // Update XP and level
      const newXp = xp + comboPoints;
      setXp(newXp);
      const newLevel = Math.floor(newXp / 100) + 1;
      if (newLevel > level) {
        setLevel(newLevel);
        // Show level up animation
        setShowAchievement('level_up');
        setTimeout(() => setShowAchievement(null), 3000);
      }
      
      setProgress(result.progress);

      // Show achievement if earned
      if (result.achievements && result.achievements.length > 0) {
        const newAchievements = result.achievements.filter(
          (a: string) => !progress?.achievements.includes(a)
        );
        if (newAchievements.length > 0) {
          setShowAchievement(newAchievements[0]);
          setTimeout(() => setShowAchievement(null), 3000);
        }
      }

      // Auto-advance after 2 seconds
      if (!result.progress.completed) {
        setTimeout(() => {
          nextQuestion();
        }, 2000);
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      setIsAnswered(false);
      setSubmittingAnswer(false);
      setIsCorrect(null);
    }
  };

  const nextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setSelectedAnswer('');
      setIsAnswered(false);
      setIsCorrect(null);
      setExplanation('');
      setTimeStarted(Date.now());
      setPointsEarned(0);
      // Reset combo if wrong answer
      if (!isCorrect) {
        setCombo(1);
      }
    }
  };

  const handleComplete = async () => {
    try {
      const response = await apiUtils.post(`${ONBOARDING_API_URL}/api/onboarding/complete`);
      if (!response.ok) {
        throw new Error(`Failed to complete onboarding: ${response.status}`);
      }
      // Redirect to main app
      window.location.href = '/';
    } catch (error) {
      console.error('Error completing onboarding:', error);
    }
  };

  if (loading) {
    return (
      <div className="onboarding-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading your math adventure...</p>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="onboarding-container">
        <div className="error-message">
          <p>Unable to load questions. Please try again later.</p>
        </div>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const progressPercent = ((currentQuestionIndex + 1) / questions.length) * 100;
  const isLastQuestion = currentQuestionIndex === questions.length - 1;
  const isCompleted = progress?.completed || false;

  if (isCompleted) {
    return (
      <div className="onboarding-container">
        <div className="completion-screen">
          <div className="completion-content">
            <div className="celebration-icon">
              <Sparkles size={80} color="#FFD700" />
            </div>
            <h1>Congratulations! 🎉</h1>
            <p className="completion-message">
              You've completed the Math onboarding!
            </p>
            <div className="final-stats">
              <div className="stat-item">
                <div className="stat-value">{progress?.correct_answers || 0}</div>
                <div className="stat-label">Correct Answers</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{progress?.total_points || 0}</div>
                <div className="stat-label">Total Points</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">
                  {progress && progress.total_questions > 0
                    ? Math.round((progress.correct_answers / progress.total_questions) * 100)
                    : 0}%
                </div>
                <div className="stat-label">Accuracy</div>
              </div>
            </div>
            {progress?.achievements && progress.achievements.length > 0 && (
              <div className="achievements-list">
                <h3>Achievements Unlocked:</h3>
                <div className="achievements-grid">
                  {progress.achievements.map((achievement) => {
                    const achievementData = ACHIEVEMENTS[achievement as keyof typeof ACHIEVEMENTS];
                    if (!achievementData) return null;
                    const Icon = achievementData.icon;
                    return (
                      <div key={achievement} className="achievement-badge">
                        <Icon size={32} color={achievementData.color} />
                        <span>{achievementData.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            <button className="continue-button" onClick={handleComplete}>
              Start Learning! <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="onboarding-container">
      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progressPercent}%` }}></div>
        <div className="progress-text">
          Question {currentQuestionIndex + 1} of {questions.length}
        </div>
      </div>

      {/* Stats Display */}
      <div className="stats-display">
        {progress && (
          <div className="stat-item points">
            <Star size={18} color="#FFD700" />
            <span>{progress.total_points}</span>
          </div>
        )}
        {streak > 0 && (
          <div className="stat-item streak">
            <span className="fire-emoji">🔥</span>
            <span>{streak}x</span>
          </div>
        )}
        {combo > 1 && (
          <div className="stat-item combo">
            <Zap size={18} color="#4ECDC4" />
            <span>{combo.toFixed(1)}x</span>
          </div>
        )}
        <div className="stat-item level">
          <span className="level-badge">Lv {level}</span>
        </div>
      </div>

      {/* Achievement Popup */}
      {showAchievement && (
        <div className="achievement-popup">
          {(() => {
            const achievementData = ACHIEVEMENTS[showAchievement as keyof typeof ACHIEVEMENTS];
            if (!achievementData) return null;
            const Icon = achievementData.icon;
            return (
              <>
                <Icon size={48} color={achievementData.color} />
                <h3>{achievementData.label}</h3>
              </>
            );
          })()}
        </div>
      )}

      {/* Question Card */}
      <div className="question-card">
        <div className="question-header">
          <div className="question-number">Question {currentQuestionIndex + 1}</div>
          <div className="question-points">+{currentQuestion.points} points</div>
        </div>

        <div className="question-content">
          <h2 className="question-text">{currentQuestion.question_text}</h2>

          {currentQuestion.question_type === 'multiple_choice' && (
            <div className="options-grid">
              {currentQuestion.options?.map((option, index) => {
                let optionClass = 'option-button';
                // Only show feedback styling after we know if the answer is correct (isCorrect is not null)
                if (isAnswered && isCorrect !== null) {
                  if (option === currentQuestion.correct_answer) {
                    optionClass += ' correct';
                  } else if (option === selectedAnswer && isCorrect === false) {
                    optionClass += ' incorrect';
                  }
                }

                return (
                  <button
                    key={index}
                    className={optionClass}
                    onClick={() => handleAnswer(option)}
                    disabled={isAnswered || submittingAnswer}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          )}

          {isAnswered && isCorrect !== null && (
            <div className={`feedback ${isCorrect ? 'correct' : 'incorrect'}`}>
              {isCorrect ? (
                <CheckCircle2 size={32} color="#4CAF50" />
              ) : (
                <XCircle size={32} color="#F44336" />
              )}
              <p className="explanation">{explanation}</p>
              {isCorrect && pointsEarned > 0 && (
                <div className="points-earned">
                  +{pointsEarned} points!
                  {combo > 1 && (
                    <span className="combo-badge">x{combo.toFixed(1)} combo!</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {isAnswered && isLastQuestion && (
          <button className="complete-button" onClick={handleComplete}>
            Complete Onboarding <ArrowRight size={20} />
          </button>
        )}
      </div>

    </div>
  );
};

export default OnboardingPage;


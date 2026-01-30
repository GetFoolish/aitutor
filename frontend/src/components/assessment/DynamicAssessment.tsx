/**
 * Dynamic Assessment Flow
 * 
 * Uses on-the-fly generated questions based on user's age and selected topics.
 * Shows progress, difficulty indicators, and creates learning path on completion.
 */
import React, { useState, useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import Header from '../header/Header';
import RendererComponent from '../question-widget-renderer/RendererComponent';
import { HintProvider } from '../../contexts/HintContext';
import { Button } from '@/components/ui/button';
import '../auth/auth.scss';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const SHOW_DEBUG_BANNER = import.meta.env.VITE_SHOW_DEBUG_BANNER === 'true';

interface Question {
  question: any;
  answerArea: any;
  hints: any[];
  dash_metadata: {
    dash_question_id: string;
    assessment_id: string;
    difficulty: string;
    topic: string;
    [key: string]: any;
  };
}

interface LocationState {
  assessmentId: string;
  questions: Question[];
  totalQuestions?: number;
  onboardingData: {
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
  
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [assessmentId, setAssessmentId] = useState<string>('');
  const [showIntro, setShowIntro] = useState(true);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [onboardingData, setOnboardingData] = useState<LocationState["onboardingData"] | null>(null);

  useEffect(() => {
    const applyPayload = (payload: {
      assessmentId: string;
      questions: Question[];
      onboardingData?: LocationState["onboardingData"];
      totalQuestions?: number;
    }) => {
      const incomingQuestions = payload.questions || [];
      if (!incomingQuestions.length) {
        console.warn('[DynamicAssessment] Empty questions payload');
        setLoading(false);
        setLoadError('No questions were generated. Please try again.');
        return;
      }

      console.log('[DynamicAssessment] Loaded assessment payload', {
        assessmentId: payload.assessmentId,
        questions: incomingQuestions.length,
        totalQuestions: payload.totalQuestions,
        source: 'applyPayload'
      });

      setQuestions(incomingQuestions);
      setAssessmentId(payload.assessmentId || '');
      setTotalQuestions(payload.totalQuestions ?? incomingQuestions.length ?? 0);
      setOnboardingData(payload.onboardingData ?? null);
      setLoading(false);
    };

    const loadAssessment = async () => {
      setLoading(true);
      setLoadError(null);

      const statePayload = location.state;
      if (statePayload?.questions?.length) {
        console.log('[DynamicAssessment] Using navigation state payload');
        applyPayload(statePayload);
        return;
      }

      const cached = sessionStorage.getItem('dynamic_assessment_payload');
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (parsed?.questions?.length) {
            console.log('[DynamicAssessment] Using cached assessment payload');
            applyPayload(parsed);
            return;
          }
        } catch (error) {
          console.warn('Failed to parse cached assessment payload', error);
        }
      }

      const cachedId = statePayload?.assessmentId || sessionStorage.getItem('dynamic_assessment_id');
      if (cachedId) {
        try {
          console.log('[DynamicAssessment] Reloading assessment from API', { assessmentId: cachedId });
          const response = await apiUtils.get(`${DASH_API_URL}/api/assessment/dynamic/${cachedId}`);
          if (response.ok) {
            const data = await response.json();
            const payload = {
              assessmentId: data.assessment_id || cachedId,
              questions: data.questions || [],
              totalQuestions: data.total_questions ?? data.questions?.length ?? 0,
              onboardingData: statePayload?.onboardingData,
            };
            sessionStorage.setItem('dynamic_assessment_payload', JSON.stringify(payload));
            applyPayload(payload);
            return;
          }
        } catch (error) {
          console.error('Failed to reload assessment from API:', error);
        }
      }

      setLoading(false);
      setLoadError('We could not load your assessment. Please start again.');
    };

    loadAssessment();
  }, [location.state, history]);

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

    // Move to next question or complete
    if (currentIndex < questions.length - 1) {
      setTimeout(() => {
        setCurrentIndex(currentIndex + 1);
        setQuestionStartTime(Date.now());
      }, 1500);
    } else {
      // Complete assessment
      await completeAssessment(newAnswers);
    }
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
      subject: 'math',
      fromAssessment: true,
    });
  };

  if (loadError && !loading) {
    return (
      <div className="login-container" style={{ minHeight: '100vh' }}>
        <BackgroundShapes />
        <div className="login-card" style={{ maxWidth: '600px', padding: '40px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{ fontFamily: 'var(--neo-heading)', marginBottom: '12px' }}>
            {loadError}
          </h2>
          <Button onClick={() => history.push('/app/onboarding')}>
            back to onboarding
          </Button>
        </div>
      </div>
    );
  }

  // Pre-Assessment Intro Screen
  if (showIntro && !loading && !completed) {
    return (
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
              letterSpacing: '0.08em'
            }}>
              debug: {assessmentId ? `assessment ${assessmentId}` : 'no assessment id'} · {totalQuestions || questions.length} questions · source {location.state?.questions?.length ? 'nav' : sessionStorage.getItem('dynamic_assessment_payload') ? 'cache' : 'api'}
            </div>
          )}
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>🎯</div>
            <h2 style={{ fontFamily: 'var(--neo-heading)', fontSize: '32px', marginBottom: '12px' }}>
              ready to start your assessment?
            </h2>
            <p style={{ fontSize: '16px', color: '#666' }}>
              let's see what you know! no pressure, just do your best ✨
            </p>
          </div>

          <div style={{ backgroundColor: '#f5f5f5', borderRadius: '12px', padding: '24px', marginBottom: '32px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '16px' }}>what to expect:</h3>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              <li style={{ marginBottom: '12px', display: 'flex', alignItems: 'start', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📝</span>
                <div>
                  <strong>{totalQuestions || questions.length} questions</strong> about {onboardingData?.selectedTopics?.join(', ') || location.state?.onboardingData?.selectedTopics?.join(', ') || 'your chosen subjects'}
                </div>
              </li>
              <li style={{ marginBottom: '12px', display: 'flex', alignItems: 'start', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>⏱️</span>
                <div>
                  <strong>about 5 minutes</strong> - take your time, no rush!
                </div>
              </li>
              <li style={{ marginBottom: '12px', display: 'flex', alignItems: 'start', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📊</span>
                <div>
                  <strong>personalized plan</strong> created based on your answers
                </div>
              </li>
              <li style={{ display: 'flex', alignItems: 'start', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>🎯</span>
                <div>
                  <strong>focus topics</strong> identified to help you improve
                </div>
              </li>
            </ul>
          </div>

          <button
            onClick={() => setShowIntro(false)}
            style={{
              width: '100%',
              padding: '16px',
              fontSize: '18px',
              fontWeight: 700,
              background: '#6C63FF',
              color: 'white',
              border: '3px solid #000',
              borderRadius: '12px',
              cursor: 'pointer',
              boxShadow: '4px 4px 0 #000',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translate(2px, 2px)';
              e.currentTarget.style.boxShadow = '2px 2px 0 #000';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translate(0, 0)';
              e.currentTarget.style.boxShadow = '4px 4px 0 #000';
            }}
          >
            let's go! 🚀
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="login-container" style={{ minHeight: '100vh' }}>
        <BackgroundShapes />
        <div className="login-card" style={{ textAlign: 'center', padding: '60px' }}>
          <div style={{ fontSize: '48px', marginBottom: '24px' }}>🎯</div>
          <h2 style={{ fontFamily: 'var(--neo-heading)', marginBottom: '16px' }}>
            {completed ? 'analyzing your results...' : 'loading your assessment...'}
          </h2>
          <p style={{ color: '#666' }}>hang tight, this won't take long</p>
        </div>
      </div>
    );
  }

  // Results Screen
  if (completed && results) {
    const scorePercent = Math.round(results.overall_score * 100);
    
    return (
      <div className="login-container" style={{ minHeight: '100vh' }}>
        <BackgroundShapes />
        <div className="login-card" style={{ maxWidth: '600px', padding: '40px' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>
              {scorePercent >= 80 ? '🌟' : scorePercent >= 60 ? '👍' : '💪'}
            </div>
            <h1 style={{ fontFamily: 'var(--neo-heading)', fontSize: '32px', marginBottom: '8px' }}>
              {scorePercent >= 80 ? 'amazing work!' : scorePercent >= 60 ? 'nice job!' : 'good effort!'}
            </h1>
            <p style={{ fontSize: '24px', color: '#666' }}>
              you got <strong>{results.total_correct}</strong> out of <strong>{results.total_questions}</strong> right
            </p>
          </div>

          {/* Score Breakdown */}
          <div style={{ 
            background: '#f5f5f5', 
            borderRadius: '12px', 
            padding: '20px',
            marginBottom: '24px'
          }}>
            <h3 style={{ marginBottom: '16px', fontSize: '16px' }}>how you did by difficulty:</h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              {Object.entries(results.difficulty_scores || {}).map(([diff, scores]: [string, any]) => (
                <div key={diff} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '20px' }}>{getDifficultyEmoji(diff)}</span>
                  <span style={{ flex: 1, textTransform: 'capitalize' }}>{diff}</span>
                  <span style={{ fontWeight: 600 }}>
                    {scores.correct}/{scores.total}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Learning Path Preview */}
          <div style={{ 
            background: '#E3F2FD', 
            borderRadius: '12px', 
            padding: '20px',
            marginBottom: '24px'
          }}>
            <h3 style={{ marginBottom: '12px', fontSize: '16px' }}>your personalized plan:</h3>
            <p style={{ marginBottom: '8px' }}>
              <strong>skill level:</strong> {results.learning_path?.skill_level || 'intermediate'}
            </p>
            {results.learning_path?.focus_topics?.length > 0 && (
              <p style={{ marginBottom: '8px' }}>
                <strong>we'll focus on:</strong> {results.learning_path.focus_topics.join(', ')}
              </p>
            )}
            {results.learning_path?.strong_topics?.length > 0 && (
              <p>
                <strong>you're great at:</strong> {results.learning_path.strong_topics.join(', ')}
              </p>
            )}
          </div>

          <Button
            onClick={startLearning}
            style={{
              width: '100%',
              padding: '16px',
              fontSize: '18px',
              fontWeight: 700,
              background: '#6C63FF',
              border: '3px solid #000',
              borderRadius: '12px',
              boxShadow: '4px 4px 0 #000',
            }}
          >
            let's start learning! 🚀
          </Button>
        </div>
      </div>
    );
  }

  // Question Screen
  return (
    <div style={{ minHeight: '100vh', background: 'var(--neo-bg, #FFFDF5)' }}>
      <Header />
      
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
        {SHOW_DEBUG_BANNER && (
          <div style={{
            background: '#FFF4CC',
            border: '2px dashed #000',
            borderRadius: '12px',
            padding: '10px 14px',
            marginBottom: '16px',
            fontSize: '12px',
            textTransform: 'uppercase',
            fontWeight: 700,
            letterSpacing: '0.08em'
          }}>
            debug: {assessmentId ? `assessment ${assessmentId}` : 'no assessment id'} · {totalQuestions || questions.length} questions · source {location.state?.questions?.length ? 'nav' : sessionStorage.getItem('dynamic_assessment_payload') ? 'cache' : 'api'} · index {currentIndex + 1}
          </div>
        )}
        {/* Progress Bar */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '8px'
          }}>
            <span style={{ fontSize: '14px', color: '#666' }}>
              question {currentIndex + 1} of {questions.length}
            </span>
            <span style={{ 
              fontSize: '14px', 
              color: getDifficultyColor(currentQuestion?.dash_metadata?.difficulty),
              fontWeight: 600
            }}>
              {getDifficultyEmoji(currentQuestion?.dash_metadata?.difficulty)} {currentQuestion?.dash_metadata?.difficulty}
            </span>
          </div>
          <div style={{
            height: '8px',
            background: '#e0e0e0',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              width: `${progress}%`,
              background: '#6C63FF',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>

        {/* Question */}
        <div style={{
          background: '#fff',
          borderRadius: '16px',
          border: '3px solid #000',
          padding: '24px',
          boxShadow: '6px 6px 0 #000'
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
              />
            )}
          </HintProvider>
        </div>

        {/* Topic indicator */}
        <div style={{ 
          marginTop: '16px', 
          textAlign: 'center',
          fontSize: '13px',
          color: '#888'
        }}>
          topic: {currentQuestion?.dash_metadata?.topic}
        </div>
      </div>
    </div>
  );
};

export default DynamicAssessment;

import React, { useState, useEffect, useRef, Suspense, lazy } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import QuestionDisplay from '../question-display/QuestionDisplay';
import AssessmentResults from './AssessmentResults';
import { HintProvider } from '../../contexts/HintContext';
import LearningAssetsPanel from '../learning-assets/LearningAssetsPanel';
import { TutorProvider } from '../../features/tutor';

const FloatingControlPanel = lazy(() => import('../floating-control-panel/FloatingControlPanel'));

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

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

const AssessmentFlow: React.FC = () => {
  const history = useHistory();
  const { subject } = useParams<Params>();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [awaitingNext, setAwaitingNext] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentQuestionId, setCurrentQuestionId] = useState<string | null>(null);
  const [watchedVideoIds, setWatchedVideoIds] = useState<string[]>([]);
  
  // Floating control panel state
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const processedEdgesRef = useRef<ImageData | null>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [mixerStream, setMixerStream] = useState<MediaStream | null>(null);
  const [isScratchpadOpen, setScratchpadOpen] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [screenEnabled, setScreenEnabled] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(false);

  useEffect(() => {
    startAssessment();
  }, [subject]);

  const startAssessment = async () => {
    try {
      const response = await apiUtils.post(`${DASH_API_URL}/assessment/start/${subject}`, {});
      
      if (!response.ok) {
        throw new Error(`Failed to start assessment: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        // Already completed
        setCompleted(true);
        setScore(data.score);
        setTotal(data.total || 0);
        setLoading(false);
        return;
      }

      setQuestions(data.questions);
      setTotal(data.total);
      setLoading(false);
    } catch (error) {
      console.error('Failed to start assessment:', error);
      history.push('/app');
    }
  };

  const handleAnswer = (questionId: string, isCorrect: boolean) => {
    const currentQuestion = questions[currentIndex];
    const newAnswer = {
      question_id: questionId,
      skill_id: currentQuestion.dash_metadata.skill_ids[0],
      is_correct: isCorrect
    };

    const newAnswers = [...answers, newAnswer];
    setAnswers(newAnswers);
    setAwaitingNext(true);
    
    // Reset watched videos
    setWatchedVideoIds([]);

    if (currentIndex < questions.length - 1) {
      // Wait 2 seconds to show feedback before moving to next question
      setTimeout(() => {
        setCurrentIndex(currentIndex + 1);
        setAwaitingNext(false);
      }, 2000);
    } else {
      // Assessment complete - submit all answers after showing final feedback
      setTimeout(() => {
        submitAssessment(newAnswers);
      }, 2000);
    }
  };
  
  // Update currentQuestionId when question changes
  useEffect(() => {
    if (questions[currentIndex]?.dash_metadata?.dash_question_id) {
      setCurrentQuestionId(questions[currentIndex].dash_metadata.dash_question_id);
    }
  }, [currentIndex, questions]);

  const submitAssessment = async (finalAnswers: any[]) => {
    try {
      setSubmitting(true);
      setError(null);

      const response = await apiUtils.post(`${DASH_API_URL}/assessment/complete`, {
        subject,
        answers: finalAnswers
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to complete assessment: ${response.status}`);
      }

      const data = await response.json();
      setScore(data.score);
      setTotal(data.total);
      setCompleted(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to complete assessment';
      console.error('Failed to complete assessment:', err);
      setError(errorMessage);
      setSubmitting(false);
      // Don't redirect immediately - show error to user
    }
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        fontSize: '18px',
        backgroundColor: 'var(--neo-bg)',
        color: 'var(--neo-black)',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em'
      }}>
        <div style={{
          padding: '24px 32px',
          border: '5px solid var(--neo-black)',
          backgroundColor: 'var(--neo-yellow)',
          boxShadow: '3px 3px 0 var(--neo-black)'
        }}>
          Loading Assessment...
        </div>
      </div>
    );
  }

  if (completed) {
    return (
      <AssessmentResults
        score={score}
        total={total}
        subject={subject}
        onContinue={() => history.replace('/app')}
      />
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '40px 20px',
        backgroundColor: 'var(--neo-bg)',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          maxWidth: '600px',
          border: '5px solid var(--neo-black)',
          backgroundColor: '#FFEBEE',
          padding: '32px',
          boxShadow: '3px 3px 0 var(--neo-black)'
        }}>
          <h2 style={{
            color: '#C62828',
            fontSize: '24px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '16px',
            marginTop: 0
          }}>
            Assessment Error
          </h2>
          <p style={{
            color: '#C62828',
            fontSize: '16px',
            fontWeight: 600,
            marginBottom: '24px'
          }}>
            {error}
          </p>
          <button
            onClick={() => history.replace('/app')}
            style={{
              width: '100%',
              padding: '16px 32px',
              fontSize: '16px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              backgroundColor: 'var(--neo-yellow)',
              color: 'var(--neo-black)',
              border: '5px solid var(--neo-black)',
              cursor: 'pointer',
              boxShadow: '2px 2px 0 var(--neo-black)',
              transition: 'all 0.2s ease',
            }}
            onMouseDown={(e) => {
              (e.target as HTMLElement).style.boxShadow = '1px 1px 0 var(--neo-black)';
              (e.target as HTMLElement).style.transform = 'translateY(2px) translateX(2px)';
            }}
            onMouseUp={(e) => {
              (e.target as HTMLElement).style.boxShadow = '2px 2px 0 var(--neo-black)';
              (e.target as HTMLElement).style.transform = 'translateY(0) translateX(0)';
            }}
          >
            Return to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <TutorProvider>
      <div style={{
        backgroundColor: 'var(--neo-bg)',
        minHeight: '100vh',
        paddingTop: '20px'
      }}>
        {submitting && (
          <div style={{
            position: 'fixed',
            top: '80px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            padding: '16px 24px',
            border: '5px solid var(--neo-black)',
            backgroundColor: 'var(--neo-yellow)',
            boxShadow: '3px 3px 0 var(--neo-black)',
            textAlign: 'center',
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--neo-black)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            Submitting Assessment...
          </div>
        )}
        
        <LearningAssetsPanel
          questionId={currentQuestionId}
          open={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onVideosWatched={setWatchedVideoIds}
        />
        
        <div style={{
          maxWidth: '900px',
          margin: '0 auto',
          padding: '0 20px',
          marginRight: isSidebarOpen ? '260px' : '0',
          transition: 'margin-right 0.5s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>
          <div style={{
            marginBottom: '20px',
            textAlign: 'center',
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--neo-black)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            border: '5px solid var(--neo-black)',
            padding: '16px',
            backgroundColor: 'var(--neo-yellow)',
            boxShadow: '3px 3px 0 var(--neo-black)'
          }}>
            {subject} Assessment - Question {currentIndex + 1} of {questions.length}
          </div>

          <HintProvider>
            {questions.length > 0 && (
              <QuestionDisplay
                assessmentMode={true}
                assessmentQuestions={questions}
                currentQuestionIndex={currentIndex}
                onAssessmentAnswer={handleAnswer}
                watchedVideoIds={watchedVideoIds}
                onAnswerSubmitted={() => setWatchedVideoIds([])}
              />
            )}
          </HintProvider>
        </div>
        
        <Suspense fallback={null}>
          <FloatingControlPanel
            renderCanvasRef={canvasRef}
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={setVideoStream}
            onMixerStreamChange={setMixerStream}
            enableEditingSettings={true}
            onPaintClick={() => setScratchpadOpen(!isScratchpadOpen)}
            isPaintActive={isScratchpadOpen}
            cameraEnabled={cameraEnabled}
            screenEnabled={screenEnabled}
            onToggleCamera={setCameraEnabled}
            onToggleScreen={setScreenEnabled}
            mediaMixerCanvasRef={canvasRef}
            privacyMode={privacyMode}
            onTogglePrivacy={setPrivacyMode}
            processedEdgesRef={processedEdgesRef}
          />
        </Suspense>
      </div>
    </TutorProvider>
  );
};

export default AssessmentFlow;

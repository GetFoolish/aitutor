import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import { TutorProvider, useTutorContext } from '../../features/tutor';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';

const FloatingControlPanel = lazy(() => import('../../components/floating-control-panel/FloatingControlPanel'));

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

// Helper component to access tutor client and send the question
const QuestionSender: React.FC<{ question: Question }> = ({ question }) => {
  const { client, connected } = useTutorContext();

  useEffect(() => {
    if (!connected || !client) return;

    // Extract visible text from the Perseus question content
    // This safely handles widgets, markdown, images, etc.
    const questionContent = question.question?.content || '';
    const widgets = question.question?.widgets || {};

    // Simple fallback: use raw content (Perseus markdown)
    let questionText = questionContent.trim();

    // If content is empty or very short, try to build a readable version
    if (!questionText || questionText.length < 10) {
      // Some questions store text in widgets (e.g., radio, dropdown)
      const widgetTexts: string[] = [];
      Object.values(widgets).forEach((widget: any) => {
        if (widget?.options?.choices) {
          widget.options.choices.forEach((choice: any) => {
            if (choice?.content) widgetTexts.push(choice.content);
          });
        } else if (widget?.options?.content) {
          widgetTexts.push(widget.options.content);
        }
      });
      if (widgetTexts.length > 0) {
        questionText = widgetTexts.join(' ');
      }
    }

    if (questionText) {
      const message = `New assessment question:\n\n${questionText}`;
      try {
        client.send({ text: message });
      } catch (err) {
        console.warn('Failed to send question to tutor:', err);
      }
    }
  }, [question, client, connected]);

  return null;
};

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

  const mediaMixerCanvasRef = React.useRef<HTMLCanvasElement>(null);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const processedEdgesRef = React.useRef<ImageData | null>(null);

  const [isScratchpadOpen, setIsScratchpadOpen] = useState(false);
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

  const handleAnswer = async (isCorrect: boolean) => {
    const currentQuestion = questions[currentIndex];
    const newAnswer = {
      question_id: currentQuestion.dash_metadata.dash_question_id,
      skill_id: currentQuestion.dash_metadata.skill_ids[0],
      is_correct: isCorrect
    };

    const newAnswers = [...answers, newAnswer];
    setAnswers(newAnswers);

    if (currentIndex < questions.length - 1) {
      setTimeout(() => {
        setCurrentIndex(currentIndex + 1);
      }, 2000);
    } else {
      setTimeout(() => {
        submitAssessment(newAnswers);
      }, 2000);
    }
  };

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

  const currentQuestion = questions[currentIndex];

  return (
    <div style={{ position: 'relative', minHeight: '100vh', backgroundColor: 'var(--neo-bg)' }}>
      <div style={{ padding: '40px 20px' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          {submitting && (
            <div style={{
              marginBottom: '24px',
              padding: '16px',
              border: '5px solid var(--neo-black)',
              backgroundColor: 'var(--neo-yellow)',
              boxShadow: '2px 2px 0 var(--neo-black)',
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
          {currentQuestion && (
            <AssessmentQuestion
              question={currentQuestion}
              questionNumber={currentIndex + 1}
              totalQuestions={questions.length}
              onAnswer={handleAnswer}
            />
          )}
        </div>
      </div>

      <TutorProvider>
        {/* Send current question to tutor when it changes */}
        {currentQuestion && <QuestionSender question={currentQuestion} />}

        <Suspense fallback={null}>
          <FloatingControlPanel
            renderCanvasRef={mediaMixerCanvasRef}
            videoRef={videoRef}
            supportsVideo={true}
            onVideoStreamChange={() => {}}
            onMixerStreamChange={() => {}}
            enableEditingSettings={true}
            onPaintClick={() => setIsScratchpadOpen(!isScratchpadOpen)}
            isPaintActive={isScratchpadOpen}
            cameraEnabled={cameraEnabled}
            screenEnabled={screenEnabled}
            onToggleCamera={setCameraEnabled}
            onToggleScreen={setScreenEnabled}
            mediaMixerCanvasRef={mediaMixerCanvasRef}
            privacyMode={privacyMode}
            onTogglePrivacy={setPrivacyMode}
            processedEdgesRef={processedEdgesRef}
            assessmentMode={true}
          />
        </Suspense>
      </TutorProvider>
    </div>
  );
};

export default AssessmentFlow;

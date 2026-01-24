import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import { TutorProvider, useTutorContext } from '../../features/tutor';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';
import Header from '../../components/header/Header';
import BackgroundShapes from '../background-shapes/BackgroundShapes';

/* 🔥 COPY LOGIN BG STYLES */
import '../auth/auth.scss';

const FloatingControlPanel = lazy(() =>
  import('../../components/floating-control-panel/FloatingControlPanel')
);

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
   Tutor question sender
---------------------------------------------------- */
const QuestionSender: React.FC<{ question: Question }> = ({ question }) => {
  const { client, connected } = useTutorContext();

  useEffect(() => {
    if (!connected || !client) return;

    const questionContent = question.question?.content || '';
    const widgets = question.question?.widgets || {};

    let questionText = questionContent.trim();

    if (!questionText || questionText.length < 10) {
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
      try {
        client.send({ text: `New assessment question:\n\n${questionText}` });
      } catch (err) {
        console.warn('Failed to send question to tutor:', err);
      }
    }
  }, [question, client, connected]);

  return null;
};

/* ----------------------------------------------------
   Main component
---------------------------------------------------- */
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
      const response = await apiUtils.post(
        `${DASH_API_URL}/assessment/start/${subject}`,
        {}
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

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
    } catch (err) {
      console.error(err);
      history.replace('/');
    }
  };

  const handleAnswer = (isCorrect: boolean) => {
    const q = questions[currentIndex];

    const updated = [
      ...answers,
      {
        question_id: q.dash_metadata.dash_question_id,
        skill_id: q.dash_metadata.skill_ids[0],
        is_correct: isCorrect,
      },
    ];

    setAnswers(updated);

    setTimeout(() => {
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((i) => i + 1);
      } else {
        submitAssessment(updated);
      }
    }, 1500);
  };

  const submitAssessment = async (finalAnswers: any[]) => {
    try {
      setSubmitting(true);

      const response = await apiUtils.post(
        `${DASH_API_URL}/assessment/complete`,
        { subject, answers: finalAnswers }
      );

      if (!response.ok) throw new Error('Submit failed');

      const data = await response.json();
      setScore(data.score);
      setTotal(data.total);
      setCompleted(true);
      
      // Note: Tutor disconnect will be handled by AssessmentResults component
    } catch (err) {
      setError('Failed to submit assessment');
      setSubmitting(false);
    }
  };

  /* ----------------------------------------------------
     Render
  ---------------------------------------------------- */
  return (
    <div className="auth-container">
      <BackgroundShapes />

      <Header
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      {loading && (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
          Loading…
        </div>
      )}

      {error && (
        <div style={{ padding: 40, color: 'red' }}>{error}</div>
      )}

      {!loading && !error && (
        <TutorProvider assessmentMode={true}>
          {completed && (
            <AssessmentResults
              score={score}
              total={total}
              subject={subject}
              onContinue={() => history.replace('/')}
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
                      Submitting Assessment...
                    </span>
                  </div>
                )}

                {questions[currentIndex] && (
                  <AssessmentQuestion
                    question={questions[currentIndex]}
                    questionNumber={currentIndex + 1}
                    totalQuestions={questions.length}
                    onAnswer={handleAnswer}
                  />
                )}
              </div>

              {questions[currentIndex] && (
                <QuestionSender question={questions[currentIndex]} />
              )}

              <Suspense fallback={null}>
                <FloatingControlPanel
                  renderCanvasRef={mediaMixerCanvasRef}
                  videoRef={videoRef}
                  supportsVideo
                  onVideoStreamChange={() => {}}
                  onMixerStreamChange={() => {}}
                  enableEditingSettings
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
            </div>
          )}
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

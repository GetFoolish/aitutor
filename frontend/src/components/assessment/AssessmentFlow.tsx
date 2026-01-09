import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';
import { TutorProvider, useTutorContext } from '../../features/tutor';
import AssessmentQuestion from './AssessmentQuestion';
import AssessmentResults from './AssessmentResults';
import Header from '../../components/header/Header';

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
      history.replace('/app');
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
    } catch (err) {
      setError('Failed to submit assessment');
      setSubmitting(false);
    }
  };

  /* ----------------------------------------------------
     Render states
  ---------------------------------------------------- */

  if (loading) {
    return (
      <>
        <Header />
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
          Loading…
        </div>
      </>
    );
  }

  if (completed) {
    return (
      <>
        <Header />
        <AssessmentResults
          score={score}
          total={total}
          subject={subject}
          onContinue={() => history.replace('/app')}
        />
      </>
    );
  }

  if (error) {
    return (
      <>
        <Header />
        <div style={{ padding: 40, color: 'red' }}>{error}</div>
      </>
    );
  }

  const currentQuestion = questions[currentIndex];

  /* ----------------------------------------------------
     Correct layout
  ---------------------------------------------------- */
  return (
    <>
      <Header />

      <div style={{ position: 'relative', minHeight: '100vh' }}>
        <div style={{ padding: '40px 20px', maxWidth: 800, margin: '0 auto' }}>
          {submitting && <div>Submitting…</div>}

          {currentQuestion && (
            <AssessmentQuestion
              question={currentQuestion}
              questionNumber={currentIndex + 1}
              totalQuestions={questions.length}
              onAnswer={handleAnswer}
            />
          )}
        </div>

        <TutorProvider>
          {currentQuestion && <QuestionSender question={currentQuestion} />}

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
              assessmentMode
            />
          </Suspense>
        </TutorProvider>
      </div>
    </>
  );
};

export default AssessmentFlow;

import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import { TutorProvider } from '../../features/tutor';
import AssessmentQuestion from './AssessmentQuestion';
import Header from '../../components/header/Header';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { Button } from '@/components/ui/button';
import '../auth/auth.scss';

const CONTENT_API_URL = import.meta.env.VITE_CONTENT_API_URL || 'http://localhost:8001';

// Age options
const AGES = [
  { label: '5-7 years', grade: 'K-2', emoji: '🧒' },
  { label: '8-10 years', grade: '3-5', emoji: '👧' },
  { label: '11-13 years', grade: '6-8', emoji: '🧑' },
  { label: '14-17 years', grade: '9-12', emoji: '👨‍🎓' },
];

// Subjects
const SUBJECTS = [
  { id: 'math', label: 'Math', icon: '🔢', color: '#FFD93D' },
  { id: 'english', label: 'English', icon: '📚', color: '#A8E6CF' },
  { id: 'science', label: 'Science', icon: '🔬', color: '#88D8FF' },
  { id: 'coding', label: 'Coding', icon: '💻', color: '#C9B1FF' },
];

// ========== STEP 1: Age Selection ==========
const StepAge: React.FC<{ onSelect: (grade: string) => void }> = ({ onSelect }) => (
  <div className="auth-container">
    <BackgroundShapes />
    <Header sidebarOpen={false} onToggleSidebar={() => {}} />
    
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 60px)', padding: '20px' }}>
      <div className="auth-card" style={{ maxWidth: '500px', width: '100%' }}>
        <h1 style={{ fontSize: '28px', marginBottom: '8px', textTransform: 'lowercase', fontWeight: 900 }}>
          hey there! 👋
        </h1>
        <p style={{ color: '#666', marginBottom: '32px' }}>
          how old are you?
        </p>

        <div style={{ display: 'grid', gap: '12px' }}>
          {AGES.map((age) => (
            <button
              key={age.grade}
              onClick={() => onSelect(age.grade)}
              style={{
                padding: '20px 24px',
                border: '4px solid #000',
                background: '#fff',
                cursor: 'pointer',
                textAlign: 'left',
                fontSize: '18px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                boxShadow: '4px 4px 0px 0px #000',
              }}
            >
              <span style={{ fontSize: '32px' }}>{age.emoji}</span>
              <span>{age.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  </div>
);

// ========== STEP 2: Topic Input ==========
const StepTopic: React.FC<{
  subject: string;
  topic: string;
  loading: boolean;
  error: string;
  onSubjectChange: (s: string) => void;
  onTopicChange: (t: string) => void;
  onBack: () => void;
  onGenerate: () => void;
}> = ({ subject, topic, loading, error, onSubjectChange, onTopicChange, onBack, onGenerate }) => (
  <div className="auth-container">
    <BackgroundShapes />
    <Header sidebarOpen={false} onToggleSidebar={() => {}} />
    
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 60px)', padding: '20px' }}>
      <div className="auth-card" style={{ maxWidth: '600px', width: '100%' }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', marginBottom: '16px', color: '#666' }}>
          ← back
        </button>

        <h1 style={{ fontSize: '28px', marginBottom: '8px', textTransform: 'lowercase', fontWeight: 900 }}>
          what do you want to learn? ✨
        </h1>
        <p style={{ color: '#666', marginBottom: '24px' }}>
          type anything you want - we'll create questions just for you!
        </p>

        {/* Subject pills (optional) */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
          {SUBJECTS.map((s) => (
            <button
              key={s.id}
              onClick={() => onSubjectChange(subject === s.id ? '' : s.id)}
              style={{
                padding: '8px 14px',
                border: subject === s.id ? '3px solid #000' : '2px solid #ccc',
                background: subject === s.id ? s.color : '#fff',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>{s.icon}</span> {s.label}
            </button>
          ))}
        </div>

        {/* Free text input */}
        <textarea
          value={topic}
          onChange={(e) => {
            console.log('TYPING:', e.target.value);
            onTopicChange(e.target.value);
          }}
          placeholder="e.g., teach me addition with dinosaurs, spelling words about space, how plants grow..."
          style={{
            width: '100%',
            minHeight: '120px',
            padding: '16px',
            fontSize: '18px',
            border: '4px solid #000',
            boxShadow: '4px 4px 0px 0px #000',
            fontFamily: 'inherit',
            marginBottom: '20px',
            resize: 'vertical',
          }}
        />

        {error && (
          <div style={{ padding: '12px', background: '#FF6B6B', color: '#fff', border: '3px solid #000', marginBottom: '16px', fontWeight: 600 }}>
            {error}
          </div>
        )}

        <button
          onClick={onGenerate}
          disabled={loading || (!topic.trim() && !subject)}
          style={{
            width: '100%',
            height: '56px',
            fontSize: '18px',
            textTransform: 'uppercase',
            fontWeight: 900,
            backgroundColor: loading || (!topic.trim() && !subject) ? '#ccc' : '#FFD93D',
            color: '#000',
            border: '4px solid #000',
            cursor: loading || (!topic.trim() && !subject) ? 'not-allowed' : 'pointer',
            borderRadius: '8px',
          }}
        >
          {loading ? 'generating...' : 'generate my questions! 🚀'}
        </button>
      </div>
    </div>
  </div>
);

// ========== STEP 3: Questions (no FloatingControlPanel to simplify) ==========
const StepQuestions: React.FC<{
  questions: any[];
  currentIndex: number;
  onAnswer: (isCorrect: boolean) => void;
}> = ({ questions, currentIndex, onAnswer }) => {
  return (
    <div className="auth-container">
      <BackgroundShapes />
      <Header sidebarOpen={false} onToggleSidebar={() => {}} />

      <TutorProvider assessmentMode={true}>
        <div style={{ paddingTop: '60px', minHeight: '100vh' }}>
          {/* Banner */}
          <div style={{ margin: '0 20px 24px', padding: '12px 24px', background: '#FF6B6B', border: '4px solid #000', textAlign: 'center' }}>
            <span style={{ color: '#fff', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              📝 Assessment Mode
            </span>
          </div>

          <div style={{ padding: '0 20px 40px', maxWidth: 900, margin: '0 auto' }}>
            {questions[currentIndex] && (
              <AssessmentQuestion
                question={questions[currentIndex]}
                questionNumber={currentIndex + 1}
                totalQuestions={questions.length}
                onAnswer={onAnswer}
              />
            )}
          </div>
        </div>
      </TutorProvider>
    </div>
  );
};

// ========== STEP 4: Simple Results (no TutorProvider needed) ==========
const StepResults: React.FC<{
  score: number;
  total: number;
  subject: string;
  onContinue: () => void;
}> = ({ score, total, subject, onContinue }) => {
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const passed = percentage >= 70;
  
  return (
    <div className="auth-container">
      <BackgroundShapes />
      <Header sidebarOpen={false} onToggleSidebar={() => {}} />
      
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 60px)', padding: '20px' }}>
        <div className="auth-card" style={{ maxWidth: '500px', width: '100%', textAlign: 'center' }}>
          <div style={{ fontSize: '64px', marginBottom: '16px' }}>
            {passed ? '🎉' : '💪'}
          </div>
          <h1 style={{ fontSize: '28px', marginBottom: '8px', textTransform: 'lowercase', fontWeight: 900 }}>
            {passed ? 'awesome job!' : 'good effort!'}
          </h1>
          <p style={{ color: '#666', marginBottom: '24px', fontSize: '18px' }}>
            you got <strong>{score}</strong> out of <strong>{total}</strong> correct ({percentage}%)
          </p>
          
          <div style={{ 
            padding: '20px', 
            background: passed ? '#A8E6CF' : '#FFD93D', 
            border: '4px solid #000',
            marginBottom: '24px'
          }}>
            <span style={{ fontWeight: 700, fontSize: '18px' }}>
              {passed ? "you're ready for more challenges!" : "let's practice some more and you'll nail it!"}
            </span>
          </div>
          
          <Button onClick={onContinue} className="w-full h-14 text-lg" style={{ fontWeight: 900 }}>
            continue learning →
          </Button>
        </div>
      </div>
    </div>
  );
};

// ========== MAIN FLOW COMPONENT ==========
const AssessmentFlow: React.FC = () => {
  const history = useHistory();

  // All state at top level
  const [step, setStep] = useState(1);
  const [grade, setGrade] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [questions, setQuestions] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [score, setScore] = useState(0);

  const handleAgeSelect = (selectedGrade: string) => {
    setGrade(selectedGrade);
    setStep(2);
  };

  const handleGenerate = async () => {
    // Use topic if provided, otherwise use subject name
    const prompt = topic.trim() || subject || 'math';
    console.log('[GENERATE] Starting...', { prompt, grade, subject });
    
    if (!prompt) {
      setError('please select a subject or tell us what you want to learn!');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${CONTENT_API_URL}/api/generate/live`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          grade: grade || 'K-2',
          subject: subject || 'math',
          count: 5,
        }),
      });
      
      console.log('[GENERATE] Response status:', res.status);
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Generation failed');
      }
      
      const data = await res.json();
      console.log('[GENERATE] Got questions:', data.length);
      
      if (data && data.length > 0) {
        setQuestions(data);
        setStep(3);
      } else {
        throw new Error('No questions generated');
      }
    } catch (e) {
      console.error('[GENERATE] Error:', e);
      setError('oops! failed to generate questions. try again?');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = (isCorrect: boolean) => {
    console.log('[FLOW] handleAnswer called with isCorrect:', isCorrect);
    console.log('[FLOW] Current score before update:', score);
    if (isCorrect) {
      setScore(s => {
        console.log('[FLOW] Updating score from', s, 'to', s + 1);
        return s + 1;
      });
    }
    
    setTimeout(() => {
      console.log('[FLOW] Timeout fired. currentIndex:', currentIndex, 'questions.length:', questions.length);
      if (currentIndex < questions.length - 1) {
        setCurrentIndex(i => i + 1);
      } else {
        console.log('[FLOW] Setting completed to true. Final score:', score);
        setCompleted(true);
      }
    }, 1500);
  };

  // Render based on state - each step is its own component with isolated hooks
  if (step === 1) {
    return <StepAge onSelect={handleAgeSelect} />;
  }

  if (step === 2) {
    return (
      <StepTopic
        subject={subject}
        topic={topic}
        loading={loading}
        error={error}
        onSubjectChange={setSubject}
        onTopicChange={(t) => { console.log('SET TOPIC:', t); setTopic(t); }}
        onBack={() => setStep(1)}
        onGenerate={handleGenerate}
      />
    );
  }

  if (step === 3 && !completed) {
    return (
      <StepQuestions
        questions={questions}
        currentIndex={currentIndex}
        onAnswer={handleAnswer}
      />
    );
  }

  if (completed) {
    return (
      <StepResults
        score={score}
        total={questions.length}
        subject={subject || 'general'}
        onContinue={() => {
          // Set session storage flag for assessment completion
          sessionStorage.setItem('assessment_completed_math', 'true');

          // Determine skill level based on score
          const percentage = questions.length > 0 ? (score / questions.length) * 100 : 0;
          const skillLevel = percentage >= 80 ? 'Advanced' : percentage >= 60 ? 'Intermediate' : 'Beginner';

          // Navigate to Learning Plan Dashboard
          history.push('/app/learning-plan', {
            skillLevel,
            focusTopics: [topic || subject || 'general'],
            strongTopics: percentage >= 80 ? [topic || subject] : [],
            grade,
            subject: subject || 'general',
            fromAssessment: true,
          });
        }}
      />
    );
  }

  return null;
};

export default AssessmentFlow;

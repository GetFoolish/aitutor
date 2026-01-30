/**
 * Learner Onboarding - Post-Login
 * 
 * Collects:
 * 1. Age/Grade level
 * 2. What they want to learn (predefined options + custom input)
 * 
 * Then triggers dynamic assessment generation
 */
import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { jwtUtils } from '../../lib/jwt-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import '../auth/auth.scss';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

// Predefined learning topics
const LEARNING_TOPICS = [
  { id: 'math-basics', label: 'Basic Math', icon: '🔢', category: 'math' },
  { id: 'algebra', label: 'Algebra', icon: '📐', category: 'math' },
  { id: 'geometry', label: 'Geometry', icon: '📏', category: 'math' },
  { id: 'fractions', label: 'Fractions & Decimals', icon: '🥧', category: 'math' },
  { id: 'word-problems', label: 'Word Problems', icon: '📝', category: 'math' },
  { id: 'statistics', label: 'Statistics & Probability', icon: '📊', category: 'math' },
  { id: 'reading', label: 'Reading Comprehension', icon: '📚', category: 'english' },
  { id: 'writing', label: 'Writing & Grammar', icon: '✍️', category: 'english' },
  { id: 'science', label: 'Science', icon: '🔬', category: 'science' },
  { id: 'coding', label: 'Coding Basics', icon: '💻', category: 'tech' },
];

const AGE_OPTIONS = [
  { value: '5-7', label: '5-7 years (K-2)', grade: 'K-2' },
  { value: '8-10', label: '8-10 years (3-5)', grade: '3-5' },
  { value: '11-13', label: '11-13 years (6-8)', grade: '6-8' },
  { value: '14-17', label: '14-17 years (9-12)', grade: '9-12' },
  { value: '18+', label: '18+ (Adult)', grade: 'adult' },
];

interface OnboardingData {
  ageRange: string;
  grade: string;
  selectedTopics: string[];
  customTopic: string;
}

const LearnerOnboarding: React.FC = () => {
  const history = useHistory();
  const { user } = useAuth();
  
  const [step, setStep] = useState<'age' | 'topics' | 'loading'>('age');
  const [data, setData] = useState<OnboardingData>({
    ageRange: '',
    grade: '',
    selectedTopics: [],
    customTopic: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAgeSelect = (ageOption: typeof AGE_OPTIONS[0]) => {
    setData(prev => ({
      ...prev,
      ageRange: ageOption.value,
      grade: ageOption.grade,
    }));
    setStep('topics');
  };

  const handleTopicToggle = (topicId: string) => {
    setData(prev => ({
      ...prev,
      selectedTopics: prev.selectedTopics.includes(topicId)
        ? prev.selectedTopics.filter(t => t !== topicId)
        : [...prev.selectedTopics, topicId],
    }));
  };

  const handleStartAssessment = async () => {
    if (data.selectedTopics.length === 0 && !data.customTopic.trim()) {
      setError('please select at least one topic or tell us what you want to learn');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Save onboarding data to user profile
      const token = jwtUtils.getToken();
      
      // Prepare topics list
      const allTopics = [
        ...data.selectedTopics,
        ...(data.customTopic.trim() ? [data.customTopic.trim()] : []),
      ];

      // Persist preferences for later practice sessions
      const primaryTopicId = data.selectedTopics[0];
      const primaryTopic = LEARNING_TOPICS.find(t => t.id === primaryTopicId);
      const inferredSubject = primaryTopic?.category || 'math';
      localStorage.setItem('learning_pref_topic', allTopics.join(', '));
      localStorage.setItem('learning_pref_grade', data.grade);
      localStorage.setItem('learning_pref_subject', inferredSubject);

      // Create assessment session with dynamic question generation
      const response = await fetch(`${DASH_API_URL}/api/assessment/dynamic/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          age_range: data.ageRange,
          grade: data.grade,
          topics: allTopics,
          question_count: 10, // Mix of easy/medium/hard
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start assessment');
      }

      const assessmentData = await response.json();
      if (!assessmentData.questions || assessmentData.questions.length === 0) {
        throw new Error('No questions were generated');
      }

      // Mark learner onboarding complete for this session
      sessionStorage.setItem('learner_onboarding_complete', 'true');
      window.dispatchEvent(new CustomEvent('learner-onboarding-complete'));
      
      const totalQuestions = assessmentData.total_questions ?? assessmentData.questions?.length ?? 0;
      const assessmentPayload = {
        assessmentId: assessmentData.assessment_id,
        questions: assessmentData.questions,
        onboardingData: data,
        totalQuestions,
      };

      // Cache for refresh/resume flows
      sessionStorage.setItem('dynamic_assessment_payload', JSON.stringify(assessmentPayload));
      sessionStorage.setItem('dynamic_assessment_id', assessmentData.assessment_id);

      // Navigate to dynamic assessment
      history.push('/app/assessment/dynamic', assessmentPayload);

    } catch (err) {
      console.error('Failed to start assessment:', err);
      setError('oops! something went wrong. try again?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container" style={{ minHeight: '100vh' }}>
      <BackgroundShapes />
      
      <div className="login-card" style={{ maxWidth: '600px', padding: '40px' }}>
        {/* Step 1: Age Selection */}
        {step === 'age' && (
          <>
            <h1 style={{ 
              fontFamily: 'var(--neo-heading)', 
              fontSize: '28px', 
              marginBottom: '8px',
              textTransform: 'lowercase'
            }}>
              hey there! 👋
            </h1>
            <p style={{ 
              color: '#666', 
              marginBottom: '32px',
              fontSize: '16px'
            }}>
              first things first - how old are you?
            </p>

            <div style={{ display: 'grid', gap: '12px' }}>
              {AGE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleAgeSelect(option)}
                  style={{
                    padding: '16px 20px',
                    border: '3px solid #000',
                    borderRadius: '12px',
                    background: '#fff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '16px',
                    fontFamily: 'var(--neo-body)',
                    transition: 'all 0.2s',
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = '#FFD93D';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = '#fff';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Step 2: Topic Selection */}
        {step === 'topics' && (
          <>
            <button
              onClick={() => setStep('age')}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '14px',
                marginBottom: '16px',
                color: '#666',
              }}
            >
              ← back
            </button>

            <h1 style={{ 
              fontFamily: 'var(--neo-heading)', 
              fontSize: '28px', 
              marginBottom: '8px',
              textTransform: 'lowercase'
            }}>
              what do you want to learn? 📚
            </h1>
            <p style={{ 
              color: '#666', 
              marginBottom: '24px',
              fontSize: '16px'
            }}>
              pick as many as you like (or type your own below)
            </p>

            {/* Topic Grid */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(2, 1fr)', 
              gap: '12px',
              marginBottom: '24px'
            }}>
              {LEARNING_TOPICS.map((topic) => {
                const isSelected = data.selectedTopics.includes(topic.id);
                return (
                  <button
                    key={topic.id}
                    onClick={() => handleTopicToggle(topic.id)}
                    style={{
                      padding: '14px 16px',
                      border: `3px solid ${isSelected ? '#4CAF50' : '#000'}`,
                      borderRadius: '12px',
                      background: isSelected ? '#E8F5E9' : '#fff',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '14px',
                      fontFamily: 'var(--neo-body)',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontSize: '20px' }}>{topic.icon}</span>
                    <span>{topic.label}</span>
                    {isSelected && <span style={{ marginLeft: 'auto' }}>✓</span>}
                  </button>
                );
              })}
            </div>

            {/* Custom Topic Input */}
            <div style={{ marginBottom: '24px' }}>
              <Label style={{ marginBottom: '8px', display: 'block', fontSize: '14px' }}>
                or tell us something specific you want to learn:
              </Label>
              <Input
                placeholder="e.g., minecraft math, dinosaur facts, chess strategies..."
                value={data.customTopic}
                onChange={(e) => setData(prev => ({ ...prev, customTopic: e.target.value }))}
                style={{
                  border: '3px solid #000',
                  borderRadius: '8px',
                  padding: '12px',
                  fontSize: '14px',
                }}
              />
            </div>

            {error && (
              <p style={{ color: '#f44336', marginBottom: '16px', fontSize: '14px' }}>
                {error}
              </p>
            )}

            {/* Start Assessment Button */}
            <Button
              onClick={handleStartAssessment}
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '18px',
                fontWeight: 700,
                background: '#6C63FF',
                border: '3px solid #000',
                borderRadius: '12px',
                boxShadow: '4px 4px 0 #000',
                cursor: isLoading ? 'wait' : 'pointer',
              }}
            >
              {isLoading ? 'setting things up...' : "let's see where you're at 🚀"}
            </Button>

            <p style={{ 
              textAlign: 'center', 
              marginTop: '16px', 
              fontSize: '13px', 
              color: '#888' 
            }}>
              we'll ask you a few questions to figure out the best starting point
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default LearnerOnboarding;

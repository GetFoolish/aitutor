/**
 * SubjectAwareContent - Routes content based on user's selected subjects
 * Math -> Perseus questions (existing QuestionDisplay)
 * Other subjects -> AI-generated content
 */
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import QuestionDisplay from '../question-display/QuestionDisplay';
import GeneratedContent from './GeneratedContent';

interface SubjectAwareContentProps {
  onSkillChange?: (skill: string | null) => void;
  onQuestionChange?: (questionId: string | null) => void;
  watchedVideoIds?: string[];
  onAnswerSubmitted?: () => void;
  assessmentMode?: boolean;
  assessmentQuestions?: any[];
  currentQuestionIndex?: number;
  onAssessmentAnswer?: (questionId: string, isCorrect: boolean) => void;
  onSubjectChange?: (subject: string) => void;
}

const SubjectAwareContent: React.FC<SubjectAwareContentProps> = (props) => {
  const { user } = useAuth();
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);

  // Get user's subjects, default to Math if none selected
  const userSubjects = user?.subjects || ['Math'];

  // Handle subject selection
  const handleSubjectSelect = (subject: string) => {
    setSelectedSubject(subject);
    props.onSubjectChange?.(subject);
  };

  // Determine which subject to show
  const activeSubject = selectedSubject || userSubjects[0] || 'Math';

  // Check if we should show Math (Perseus) content
  const isMathSubject = activeSubject.toLowerCase() === 'math';

  return (
    <div className="subject-aware-content">
      {/* Subject selector if user has multiple subjects */}
      {userSubjects.length > 1 && (
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '16px',
          padding: '12px',
          background: '#FFFDF5',
          border: '3px solid #000',
          boxShadow: '4px 4px 0 #000'
        }}>
          {userSubjects.map((subject) => (
            <button
              key={subject}
              onClick={() => handleSubjectSelect(subject)}
              style={{
                padding: '8px 16px',
                border: '3px solid #000',
                background: activeSubject === subject ? '#FFD93D' : '#fff',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: activeSubject === subject ? '2px 2px 0 #000' : 'none',
                transform: activeSubject === subject ? 'translate(-1px, -1px)' : 'none'
              }}
            >
              {subject}
            </button>
          ))}
        </div>
      )}

      {/* Content based on subject */}
      {isMathSubject ? (
        <QuestionDisplay
          onSkillChange={props.onSkillChange}
          onQuestionChange={props.onQuestionChange}
          watchedVideoIds={props.watchedVideoIds}
          onAnswerSubmitted={props.onAnswerSubmitted}
          assessmentMode={props.assessmentMode}
          assessmentQuestions={props.assessmentQuestions}
          currentQuestionIndex={props.currentQuestionIndex}
          onAssessmentAnswer={props.onAssessmentAnswer}
        />
      ) : (
        <GeneratedContent
          subject={activeSubject}
          grade={user?.current_grade || 'GRADE_5'}
          userName={user?.name || 'Student'}
        />
      )}
    </div>
  );
};

export default SubjectAwareContent;

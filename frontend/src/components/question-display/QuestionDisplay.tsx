import React from 'react';
import RendererComponent from "../question-widget-renderer/RendererComponent";
import './mcq-fix.css'; // Fix for MCQ highlighting bug


interface QuestionDisplayProps {
  onSkillChange?: (skill: string) => void;
  onQuestionChange?: (questionId: string | null) => void;
  watchedVideoIds?: string[];
  onAnswerSubmitted?: () => void;
  // Assessment mode props
  assessmentMode?: boolean;
  assessmentQuestions?: any[];
  onAssessmentAnswer?: (questionId: string, isCorrect: boolean) => void;
  currentQuestionIndex?: number;
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({ 
  onSkillChange, 
  onQuestionChange,
  watchedVideoIds,
  onAnswerSubmitted,
  assessmentMode = false,
  assessmentQuestions = [],
  onAssessmentAnswer,
  currentQuestionIndex = 0
}) => {
  return (
    <div className="w-full flex flex-col items-center bg-transparent">
      <div className="w-full" id="perseus-capture-area">
        <RendererComponent 
          onSkillChange={onSkillChange} 
          onQuestionChange={onQuestionChange}
          watchedVideoIds={watchedVideoIds}
          onAnswerSubmitted={onAnswerSubmitted}
          assessmentMode={assessmentMode}
          assessmentQuestions={assessmentQuestions}
          onAssessmentAnswer={onAssessmentAnswer}
          currentQuestionIndex={currentQuestionIndex}
        />
      </div>
    </div>
  );
};

export default QuestionDisplay;

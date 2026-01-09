import React from 'react';
import RendererComponent from "../question-widget-renderer/RendererComponent";
import './mcq-fix.css'; // Fix for MCQ highlighting bug


interface QuestionDisplayProps {
  onSkillChange?: (skill: string) => void;
  onLearningAssetChange?: (asset: any) => void;
  onQuestionChange?: (text: string) => void;
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({ onSkillChange, onLearningAssetChange, onQuestionChange }) => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-transparent">
      <div className="w-full h-full" id="perseus-capture-area">
        <RendererComponent
          onSkillChange={onSkillChange}
          onLearningAssetChange={onLearningAssetChange}
          onQuestionChange={onQuestionChange}
        />
      </div>
    </div>
  );
};

export default QuestionDisplay;

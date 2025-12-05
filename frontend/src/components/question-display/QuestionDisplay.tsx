import React from 'react';
import RendererComponent from "../question-widget-renderer/RendererComponent";

interface QuestionDisplayProps {
  onSkillChange?: (skill: string) => void;
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({ onSkillChange }) => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-transparent">
      <div className="w-full h-full" id="perseus-capture-area">
        <RendererComponent onSkillChange={onSkillChange} />
      </div>
    </div>
  );
};

export default QuestionDisplay;

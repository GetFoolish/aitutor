import React from 'react';
import RendererComponent from "../question-widget-renderer/RendererComponent";

const QuestionDisplay: React.FC = () => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-transparent">
      <div className="w-full h-full" id="perseus-capture-area">
        <RendererComponent />
      </div>
    </div>
  );
};

export default QuestionDisplay;

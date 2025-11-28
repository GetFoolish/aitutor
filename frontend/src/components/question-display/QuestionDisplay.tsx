import React, { useState, useEffect } from 'react';
import './question-display.scss';
import RendererComponent from "../question-widget-renderer/RendererComponent";

const QuestionDisplay: React.FC = () => {
  
  return (
    <div className="question-display" style={{width: '100%', height: '100%'}}>
      <h2 className="question-title">Here's your next question:</h2>
      <div className="perseus-content" id="perseus-capture-area">
        <RendererComponent />
      </div>
    </div>
  );
};

export default QuestionDisplay;

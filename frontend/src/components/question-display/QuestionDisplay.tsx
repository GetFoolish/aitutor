import React, { useState, useEffect } from 'react';
import './question-display.scss';
import RendererComponent from "../question-widget-renderer/RendererComponent";
import { Scratchpad } from "../scratchpad/Scratchpad";

const QuestionDisplay: React.FC = () => {
  return (
    <div className="question-display-wrapper">
      <h2 style={{
        color: 'white',
        marginBottom: '20px',
        fontSize: '24px',
        fontWeight: 'bold'
      }}>
        Here's your next question:
      </h2>

      <div className="perseus-question-box">
        <RendererComponent />
      </div>

      <div style={{ marginTop: '30px' }}>
        <Scratchpad height={300} />
      </div>
    </div>
  );
};

export default QuestionDisplay;

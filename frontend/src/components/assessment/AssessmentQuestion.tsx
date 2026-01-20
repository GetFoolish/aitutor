import React, { useRef, useState, useEffect } from 'react';
import { ServerItemRenderer } from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { RenderStateRoot } from "@khanacademy/wonder-blocks-core";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { scorePerseusItem } from "@khanacademy/perseus-score";
import { keScoreFromPerseusScore } from "../../package/perseus/src/util/scoring";
import { CheckCircle2, XCircle } from "lucide-react";
import { KEScore } from "@khanacademy/perseus-core";

interface Props {
  question: any;
  questionNumber: number;
  totalQuestions: number;
  onAnswer: (isCorrect: boolean) => void;
}

const AssessmentQuestion: React.FC<Props> = ({
  question,
  questionNumber,
  totalQuestions,
  onAnswer
}) => {
  const rendererRef = useRef<ServerItemRenderer>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [keScore, setKeScore] = useState<KEScore | null>(null);

  // Reset answer state when question changes
  useEffect(() => {
    setIsAnswered(false);
    setShowFeedback(false);
    setKeScore(null);
  }, [question]);

  const handleSubmit = () => {
    if (!rendererRef.current) return;

    const userInput = rendererRef.current.getUserInput();
    const questionData = question.question;
    const scoreResult = scorePerseusItem(questionData, userInput, "en");

    const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
    const score = keScoreFromPerseusScore(
      scoreResult,
      maxCompatGuess,
      rendererRef.current.getSerializedState().question,
    );

    setIsAnswered(true);
    setShowFeedback(true);
    setKeScore(score);
    onAnswer(score.correct);
  };

  const progressPercentage = (questionNumber / totalQuestions) * 100;

  return (
    <div className="framework-perseus" style={{ marginTop: '0' }}>
      {/* Enhanced Question Header with Progress */}
      <div style={{
        marginBottom: '32px',
        border: '5px solid #000000',
        backgroundColor: '#FFD93D',
        boxShadow: '4px 4px 0px 0px #000000',
        overflow: 'hidden'
      }}>
        <div style={{
          padding: '20px 24px',
          textAlign: 'center',
          borderBottom: '3px solid #000000'
        }}>
          <div style={{
            fontSize: '20px',
            fontWeight: 900,
            color: '#000000',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '8px',
            fontFamily: 'system-ui, -apple-system, sans-serif'
          }}>
            QUESTION {questionNumber} OF {totalQuestions}
          </div>
          <div style={{
            fontSize: '14px',
            fontWeight: 700,
            color: '#000000',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            opacity: 0.8
          }}>
            Assessment in Progress
          </div>
        </div>
        
        {/* Progress Bar */}
        <div style={{
          height: '12px',
          backgroundColor: '#FFFFFF',
          borderTop: '3px solid #000000',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${progressPercentage}%`,
            backgroundColor: '#FF6B6B',
            borderRight: '3px solid #000000',
            transition: 'width 0.3s ease-out',
            boxShadow: 'inset 0 0 0 2px #000000'
          }}></div>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '10px',
            fontWeight: 900,
            color: '#000000',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            zIndex: 1,
            textShadow: '0 0 4px #FFFFFF'
          }}>
            {Math.round(progressPercentage)}%
          </div>
        </div>
      </div>

      <div 
        id="question-content-container"
        className="border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 text-black dark:text-white p-4 md:p-5 lg:p-6 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] mb-6"
      >
        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
          <RenderStateRoot>
            <ServerItemRenderer
              ref={rendererRef}
              problemNum={0}
              item={question}
              dependencies={storybookDependenciesV2}
              apiOptions={{}}
              linterContext={{
                contentType: "",
                highlightLint: true,
                paths: [],
                stack: [],
              }}
              showSolutions="none"
              hintsVisible={0}
              reviewMode={false}
            />
          </RenderStateRoot>
        </PerseusI18nContextProvider>
      </div>

      {!isAnswered && (
        <div style={{ marginBottom: '24px' }}>
          <button
            onClick={handleSubmit}
            style={{
              width: '100%',
              padding: '20px 32px',
              fontSize: '18px',
              fontWeight: 900,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              backgroundColor: '#FFD93D',
              color: '#000000',
              border: '5px solid #000000',
              cursor: 'pointer',
              boxShadow: '4px 4px 0px 0px #000000',
              transition: 'all 0.1s ease-out',
              fontFamily: 'system-ui, -apple-system, sans-serif'
            }}
            onMouseDown={(e) => {
              (e.target as HTMLElement).style.boxShadow = '2px 2px 0px 0px #000000';
              (e.target as HTMLElement).style.transform = 'translate(2px, 2px)';
            }}
            onMouseUp={(e) => {
              (e.target as HTMLElement).style.boxShadow = '4px 4px 0px 0px #000000';
              (e.target as HTMLElement).style.transform = 'translate(0, 0)';
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.boxShadow = '4px 4px 0px 0px #000000';
              (e.target as HTMLElement).style.transform = 'translate(0, 0)';
            }}
          >
            Submit Answer
          </button>
        </div>
      )}

      {showFeedback && keScore && (
        <div style={{
          marginBottom: '24px',
          padding: '20px',
          border: '5px solid #000000',
          backgroundColor: keScore.correct ? '#E8F5E9' : '#FFEBEE',
          boxShadow: '4px 4px 0px 0px #000000',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px'
        }}>
          {keScore.correct ? (
            <>
              <CheckCircle2 size={32} style={{ color: '#2E7D32', flexShrink: 0 }} />
              <span style={{
                color: '#2E7D32',
                fontWeight: 700,
                fontSize: '18px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Correct!
              </span>
            </>
          ) : (
            <>
              <XCircle size={32} style={{ color: '#C62828', flexShrink: 0 }} />
              <span style={{
                color: '#C62828',
                fontWeight: 700,
                fontSize: '18px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Incorrect
              </span>
            </>
          )}
        </div>
      )}

      {showFeedback && !isAnswered && (
        <div style={{
          padding: '20px',
          border: '5px solid #000000',
          backgroundColor: '#FFD93D',
          boxShadow: '4px 4px 0px 0px #000000',
          textAlign: 'center',
          fontSize: '16px',
          fontWeight: 900,
          color: '#000000',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          animation: 'pulse 1.5s ease-in-out infinite'
        }}>
          Moving to next question...
        </div>
      )}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.7;
          }
        }
      `}</style>
    </div>
  );
};

export default AssessmentQuestion;

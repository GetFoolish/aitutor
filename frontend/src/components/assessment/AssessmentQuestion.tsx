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

  return (
    <div style={{ marginTop: '32px' }}>
      <div style={{
        marginBottom: '24px',
        fontSize: '16px',
        fontWeight: 700,
        color: 'var(--neo-black)',
        textAlign: 'center',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        border: '5px solid var(--neo-black)',
        padding: '16px',
        backgroundColor: 'var(--neo-yellow)',
        boxShadow: '2px 2px 0 var(--neo-black)'
      }}>
        Question {questionNumber} of {totalQuestions}
      </div>

      <div style={{
        border: '5px solid var(--neo-black)',
        backgroundColor: 'var(--neo-bg)',
        color: 'var(--neo-black)',
        padding: '24px',
        boxShadow: '3px 3px 0 var(--neo-black)',
        marginBottom: '24px'
      }}>
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
              padding: '16px 32px',
              fontSize: '16px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              backgroundColor: 'var(--neo-yellow)',
              color: 'var(--neo-black)',
              border: '5px solid var(--neo-black)',
              cursor: 'pointer',
              boxShadow: '2px 2px 0 var(--neo-black)',
              transition: 'all 0.2s ease',
            }}
            onMouseDown={(e) => {
              (e.target as HTMLElement).style.boxShadow = '1px 1px 0 var(--neo-black)';
              (e.target as HTMLElement).style.transform = 'translateY(2px) translateX(2px)';
            }}
            onMouseUp={(e) => {
              (e.target as HTMLElement).style.boxShadow = '2px 2px 0 var(--neo-black)';
              (e.target as HTMLElement).style.transform = 'translateY(0) translateX(0)';
            }}
          >
            Submit Answer
          </button>
        </div>
      )}

      {showFeedback && keScore && (
        <div style={{
          marginBottom: '24px',
          padding: '16px',
          border: '5px solid var(--neo-black)',
          backgroundColor: keScore.correct ? '#E8F5E9' : '#FFEBEE',
          boxShadow: '2px 2px 0 var(--neo-black)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px'
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
          padding: '16px',
          border: '5px solid var(--neo-black)',
          backgroundColor: 'var(--neo-yellow)',
          boxShadow: '2px 2px 0 var(--neo-black)',
          textAlign: 'center',
          fontSize: '14px',
          fontWeight: 700,
          color: 'var(--neo-black)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Moving to next question...
        </div>
      )}
    </div>
  );
};

export default AssessmentQuestion;

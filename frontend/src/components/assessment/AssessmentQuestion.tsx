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

// Innocent Drinks style formatting
import './assessment-questions.css';

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
    console.log('[QUESTION] New question loaded:', JSON.stringify(question, null, 2));
    console.log('[QUESTION] Question structure check:', {
      hasQuestion: !!question,
      hasQuestionProperty: !!question?.question,
      hasContent: !!question?.question?.content,
      hasWidgets: !!question?.question?.widgets,
      questionKeys: question ? Object.keys(question) : [],
      questionQuestionKeys: question?.question ? Object.keys(question.question) : []
    });
    setIsAnswered(false);
    setShowFeedback(false);
    setKeScore(null);
  }, [question]);

  const handleSubmit = () => {
    console.log('[SUBMIT] Button clicked');

    if (!rendererRef.current) {
      console.error('[SUBMIT] ERROR: rendererRef.current is null!');
      return;
    }

    try {
      console.log('[SUBMIT] Getting user input...');
      const userInput = rendererRef.current.getUserInput();
      console.log('[SUBMIT] Got user input:', userInput);

      // Use original question data for widgets, but get current state for validation
      const questionData = question.question;
      console.log('[SCORING] User input:', JSON.stringify(userInput));
      console.log('[SCORING] Question widgets:', JSON.stringify(questionData?.widgets));

      if (!questionData || !questionData.widgets) {
        console.error('[SUBMIT] ERROR: Question data or widgets are undefined!');
        alert('Error: Question data is missing. Please refresh and try again.');
        return;
      }

      console.log('[SUBMIT] Scoring answer...');
      const scoreResult = scorePerseusItem(questionData, userInput, "en");
      console.log('[SCORING] Perseus score result:', JSON.stringify(scoreResult));
      console.log('[SCORING] Score type:', scoreResult.type);

      if (scoreResult.type === 'points') {
        console.log('[SCORING] Earned:', scoreResult.earned, 'Total:', scoreResult.total);
      }

      const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
      const serializedState = rendererRef.current.getSerializedState();

      const score = keScoreFromPerseusScore(
        scoreResult,
        maxCompatGuess,
        serializedState.question,
      );

      console.log('[SCORING] Final KE score:', JSON.stringify(score));
      console.log('[SCORING] Is correct (raw):', score.correct, 'type:', typeof score.correct);

      const fallbackIsCorrect = () => {
        let fallbackCorrect = false;
        const widgets = questionData?.widgets || {};

        for (const [widgetId, widgetInput] of Object.entries(userInput)) {
          const widgetDef = (widgets as Record<string, any>)?.[widgetId];
          if (!widgetDef) continue;

          if (widgetDef.type === 'radio') {
            const choices = widgetDef.options?.choices || [];
            const selectedIds = (widgetInput as any).selectedChoiceIds || [];
            const isMultiSelect = widgetDef.options?.multipleSelect || false;

            if (isMultiSelect) {
              const correctIndices = choices
                .map((c: any, i: number) => c.correct ? i : -1)
                .filter((i: number) => i >= 0);
              const selectedIndices = selectedIds.map((id: string) => {
                const match = id.match(/choice-(\d+)-/);
                return match ? parseInt(match[1]) : -1;
              }).filter((i: number) => i >= 0);

              fallbackCorrect = correctIndices.length === selectedIndices.length &&
                correctIndices.every((idx: number) => selectedIndices.includes(idx));
            } else {
              if (selectedIds.length === 1) {
                const selectedId = selectedIds[0];
                const match = selectedId.match(/choice-(\d+)-/);
                if (match) {
                  const selectedIndex = parseInt(match[1]);
                  fallbackCorrect = choices[selectedIndex]?.correct === true;
                }
              }
            }
          } else if (widgetDef.type === 'orderer') {
            const correctOptions = widgetDef.options?.correctOptions || [];
            const userOrder = (widgetInput as any).current || [];

            if (correctOptions.length === userOrder.length) {
              fallbackCorrect = correctOptions.every((correctOpt: any, index: number) => {
                return correctOpt.content === userOrder[index];
              });
            }
          }
        }

        return fallbackCorrect;
      };

      // Handle different score types
      let isCorrectBoolean = false;

      if (scoreResult.type === 'points') {
        // For points-based scoring, check if earned equals total
        isCorrectBoolean = scoreResult.earned === scoreResult.total && scoreResult.total > 0;
      } else if (scoreResult.type === 'invalid') {
        // Fall back to lightweight widget checks
        isCorrectBoolean = fallbackIsCorrect();
      } else {
        // Default to score.correct with boolean conversion
        isCorrectBoolean = Boolean(score.correct === true || score.correct === 'true' ||
          (typeof score.correct === 'object' && score.correct?.correct === true));
      }

      const sanitizedScore = {
        ...score,
        correct: isCorrectBoolean
      };

      console.log('[SCORING] Sanitized correct value:', sanitizedScore.correct, 'type:', typeof sanitizedScore.correct);
      console.log('[SUBMIT] Setting answered state and calling onAnswer callback...');

      setIsAnswered(true);
      setShowFeedback(true);
      setKeScore(sanitizedScore);
      onAnswer(sanitizedScore.correct);

      console.log('[SUBMIT] Complete!');
    } catch (error) {
      console.error('[SUBMIT] ERROR during scoring:', error);
      alert('Error scoring answer: ' + (error instanceof Error ? error.message : String(error)));
    }
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
        style={{
          fontSize: '22px',
          lineHeight: '1.6',
          fontWeight: 500,
          color: '#000000',
        }}
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

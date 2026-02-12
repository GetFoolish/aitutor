import React, { useRef, useState, useEffect, useMemo } from 'react';
import { ServerItemRenderer } from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { RenderStateRoot } from "@khanacademy/wonder-blocks-core";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { keScoreFromPerseusScore } from "../../package/perseus/src/util/scoring";
import { CheckCircle2, XCircle } from "lucide-react";
import { KEScore } from "@khanacademy/perseus-core";
import AudioPlayButton, { extractAudioWord } from "../AudioPlayButton";
import { reportQuestionAnalytics } from "../../lib/api-utils";
import { scorePerseusQuestion, hasUserInput } from "../../lib/scoring-utils";

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
  const [hintsShown, setHintsShown] = useState(0);
  const [pendingCorrect, setPendingCorrect] = useState<boolean | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Reset answer state when question changes
  useEffect(() => {
    setIsAnswered(false);
    setShowFeedback(false);
    setHintsShown(0);
    setKeScore(null);
    setPendingCorrect(null);
    startTimeRef.current = Date.now();
  }, [question]);

  // Handle "Next Question" — deferred until student clicks the button
  const handleNext = () => {
    if (pendingCorrect !== null) {
      onAnswer(pendingCorrect);
      setPendingCorrect(null);
    }
  };

  // Sanitize question — patch missing widget fields + strip phantom picture references
  const sanitizedQuestion = useMemo(() => {
    if (!question?.question) return question;
    try {
    const q = { ...question, question: { ...question.question } };
    // Strip picture/image references with no actual images
    if (typeof q.question.content === 'string') {
      q.question.content = q.question.content
        .replace(/\b(?:look at|examine|see|observe|study|check out)\s+(?:the\s+)?(?:picture|image|diagram|illustration|photo|figure)s?\b[^.!?\n]*[.!?]?\s*/gi, '')
        .replace(/\b(?:in the (?:picture|image|diagram|illustration) (?:below|above|shown))[^.!?\n]*[.!?]?\s*/gi, '')
        .replace(/\b(?:the (?:picture|image|diagram|illustration) (?:below|above|shows?))[^.!?\n]*[.!?]?\s*/gi, '')
        .trim();
    }
    // Ensure every widget has a placeholder in content (definition+radio combo fix)
    if (q.question.widgets && typeof q.question.content === 'string') {
      for (const wname of Object.keys(q.question.widgets)) {
        const wtype = (q.question.widgets[wname] as any)?.type;
        if (wtype === 'image') continue;
        if (!q.question.content.includes(`[[☃ ${wname}]]`)) {
          q.question.content = q.question.content.trimEnd() + `\n\n[[☃ ${wname}]]`;
        }
      }
    }
    // Patch missing required widget fields
    if (q.question.widgets) {
      q.question.widgets = { ...q.question.widgets };
      for (const [key, widget] of Object.entries(q.question.widgets)) {
        const w = widget as any;
        // Radio: options is an array instead of {choices: [...]}
        if (w?.type === 'radio' && Array.isArray(w.options)) {
          const multipleSelect = w.multipleSelect || false;
          const randomize = w.randomize || false;
          const { multipleSelect: _ms, randomize: _rz, ...rest } = w;
          q.question.widgets[key] = {
            ...rest,
            options: { choices: w.options, multipleSelect, randomize },
          };
        }
        if (w?.type === 'numeric-input' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: { coefficient: false, static: false, labelText: '', size: 'normal', ...w.options },
          };
        }
        // Orderer: normalize string options to {content: string} objects
        if (w?.type === 'orderer' && w.options) {
          const fixArr = (arr: any[]) => arr?.map((item: any) =>
            typeof item === 'string' ? { content: item } : item
          );
          q.question.widgets[key] = {
            ...w,
            options: {
              ...w.options,
              options: fixArr(w.options.options || []),
              correctOptions: fixArr(w.options.correctOptions || []),
            },
          };
        }
        // Expression: ensure buttonSets and other required fields
        if (w?.type === 'expression' && w.options) {
          const exprOpts = { ...w.options };
          if (!exprOpts.buttonSets || !Array.isArray(exprOpts.buttonSets) || exprOpts.buttonSets.length === 0) {
            exprOpts.buttonSets = ['basic'];
          }
          if (!exprOpts.functions || !Array.isArray(exprOpts.functions) || exprOpts.functions.length === 0) {
            exprOpts.functions = ['f', 'g', 'h'];
          }
          if (exprOpts.times === undefined) exprOpts.times = false;
          if (!exprOpts.buttonsVisible) exprOpts.buttonsVisible = 'never';
          q.question.widgets[key] = { ...w, options: exprOpts };
        }
        // Definition: ensure togglePrompt, definition, and static fields
        if (w?.type === 'definition' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              togglePrompt: 'Definition',
              definition: '',
              static: false,
              ...w.options,
            },
          };
        }
        // Dropdown: ensure placeholder and static fields
        if (w?.type === 'dropdown' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              placeholder: 'Select an answer',
              static: false,
              ...w.options,
            },
          };
        }
        // Matcher: ensure labels and padding
        if (w?.type === 'matcher' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              labels: ['Left', 'Right'],
              orderMatters: false,
              padding: true,
              ...w.options,
            },
          };
        }
        // Sorter: ensure layout
        if (w?.type === 'sorter' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              layout: 'horizontal',
              padding: true,
              ...w.options,
            },
          };
        }
        // Categorizer: ensure required fields
        if (w?.type === 'categorizer' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              randomizeItems: false,
              static: false,
              highlightLint: false,
              ...w.options,
            },
          };
        }
        // Number-line: ensure required fields
        if (w?.type === 'number-line' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              labelRange: '',
              initialX: w.options.correctX ?? 0,
              tickStep: 1,
              labelStyle: 'decimal',
              labelTicks: true,
              isInequality: false,
              snapDivisions: 2,
              correctRel: 'eq',
              numDivisions: 10,
              divisionRange: w.options.range || [0, 10],
              isTickCtrl: false,
              static: false,
              ...w.options,
            },
          };
        }
        // Table: ensure required fields
        if (w?.type === 'table' && w.options) {
          q.question.widgets[key] = {
            ...w,
            options: {
              headers: [],
              rows: 4,
              columns: 2,
              ...w.options,
            },
          };
        }
      }
    }
    return q;
    } catch (err) {
      console.error('[AssessmentQuestion] Sanitization failed:', err);
      return question;
    }
  }, [question]);

  // Detect if question needs audio (phonics/listening questions)
  const audioWord = useMemo(() => {
    const content = question?.question?.content || '';
    return extractAudioWord(content);
  }, [question]);

  const [emptyWarning, setEmptyWarning] = useState(false);

  const handleSubmit = () => {
    if (isAnswered) return; // Prevent double-submit
    if (!rendererRef.current) {
      console.error('[AssessmentQuestion] rendererRef is null — widget failed to render, skipping as incorrect');
      // Widget failed to render — mark as incorrect and move on
      setIsAnswered(true);
      setShowFeedback(true);
      setKeScore({ correct: false, empty: false, message: null, guess: null, state: null });
      onAnswer(false);
      return;
    }

    try {

    const userInput = rendererRef.current.getUserInput();
    const questionData = sanitizedQuestion.question;

    // Empty submission guard
    if (!hasUserInput(questionData.widgets || {}, userInput)) {
      setEmptyWarning(true);
      setTimeout(() => setEmptyWarning(false), 2500);
      return;
    }

    // Custom scoring via shared utility (Perseus doesn't handle our AI answer format)
    const scoringResult = scorePerseusQuestion(questionData.widgets || {}, userInput);

    const isCorrect = scoringResult.correct;
    console.log('[AssessmentQuestion] Custom score:', isCorrect, `(${scoringResult.correctCount}/${scoringResult.scoreableCount})`);

    const scoreResult = {
      type: 'points' as const,
      earned: isCorrect ? 1 : 0,
      total: 1,
      message: null
    };

    const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
    const score = keScoreFromPerseusScore(
      scoreResult,
      maxCompatGuess,
      rendererRef.current.getSerializedState().question,
    );

    setIsAnswered(true);
    setShowFeedback(true);
    setKeScore(score);
    setPendingCorrect(score.correct);

    // Fire-and-forget analytics reporting
    const questionId = question?.dash_metadata?.dash_question_id || `assessment_q_${questionNumber}`;
    const skillId = (question?.dash_metadata?.skill_ids || [])[0];
    reportQuestionAnalytics({
      question_id: questionId,
      correct: score.correct,
      hints_used: hintsShown,
      time_seconds: (Date.now() - startTimeRef.current) / 1000,
      skipped: false,
      skill_id: skillId,
    });

    } catch (err) {
      console.error('[AssessmentQuestion] Scoring error:', err);
      // Don't penalize — allow retry
      setIsAnswered(false);
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

      {/* Audio play button for phonics/listening questions */}
      {audioWord && (
        <div style={{ marginBottom: '16px' }}>
          <AudioPlayButton word={audioWord} autoPlay={true} />
        </div>
      )}

      <div
        id="question-content-container"
        className="border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 text-black dark:text-white p-4 md:p-5 lg:p-6 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] mb-6"
      >
        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
          <RenderStateRoot>
            <ServerItemRenderer
              ref={rendererRef}
              problemNum={0}
              item={sanitizedQuestion}
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

      {/* Progressive Hints */}
      {!isAnswered && question?.hints?.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          {hintsShown > 0 && (
            <div style={{ marginBottom: '12px' }}>
              {(question.hints || []).slice(0, hintsShown).map((hint: any, idx: number) => (
                <div key={idx} style={{
                  padding: '12px 16px',
                  marginBottom: '8px',
                  border: '3px solid #000',
                  backgroundColor: '#FFF9C4',
                  boxShadow: '2px 2px 0 #000',
                  fontSize: '14px',
                  lineHeight: '1.5'
                }}>
                  <strong style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Hint {idx + 1}:
                  </strong>{' '}
                  {hint.content}
                </div>
              ))}
            </div>
          )}
          {hintsShown < (question.hints || []).length && (
            <button
              onClick={() => setHintsShown(h => h + 1)}
              style={{
                padding: '10px 20px',
                fontSize: '13px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                backgroundColor: '#E3F2FD',
                color: '#1565C0',
                border: '3px solid #000',
                cursor: 'pointer',
                boxShadow: '2px 2px 0 #000',
                marginBottom: '8px'
              }}
            >
              Show Hint ({hintsShown + 1}/{(question.hints || []).length})
            </button>
          )}
        </div>
      )}

      {/* Empty submission warning */}
      {emptyWarning && (
        <div style={{
          marginBottom: '12px',
          padding: '12px 16px',
          border: '3px solid #000',
          backgroundColor: '#FFF3E0',
          boxShadow: '2px 2px 0 #000',
          fontSize: '14px',
          fontWeight: 700,
          color: '#E65100',
          textTransform: 'uppercase',
          letterSpacing: '0.03em',
          textAlign: 'center'
        }}>
          Please select or enter an answer first
        </div>
      )}

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
          border: '5px solid #000000',
          backgroundColor: keScore.correct ? '#E8F5E9' : '#FFEBEE',
          boxShadow: '4px 4px 0px 0px #000000',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            borderBottom: !keScore.correct && question?.hints?.length ? '3px solid #000' : 'none'
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
          {/* Show explanation hint when incorrect */}
          {!keScore.correct && question?.hints?.length > 0 && (
            <div style={{
              padding: '14px 20px',
              fontSize: '14px',
              lineHeight: '1.5',
              color: '#333',
              backgroundColor: '#FFF3E0'
            }}>
              <strong style={{ textTransform: 'uppercase', fontSize: '12px', letterSpacing: '0.05em' }}>
                Explanation:
              </strong>{' '}
              {question.hints[question.hints.length - 1]?.content || question.hints[0]?.content || ''}
            </div>
          )}
        </div>
      )}

      {/* Next Question button — shown after submit, student advances when ready */}
      {isAnswered && pendingCorrect !== null && (
        <div style={{ marginBottom: '24px' }}>
          <button
            onClick={handleNext}
            style={{
              width: '100%',
              padding: '20px 32px',
              fontSize: '18px',
              fontWeight: 900,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              backgroundColor: '#4FC3F7',
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
            Next Question
          </button>
        </div>
      )}
    </div>
  );
};

export default AssessmentQuestion;

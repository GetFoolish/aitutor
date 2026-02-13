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
// @ts-ignore — katex types require 'bundler' moduleResolution
import katex from 'katex';
import 'katex/dist/katex.min.css';

/** Render text with inline LaTeX ($...$) as rendered math via KaTeX */
function renderTextWithLatex(text: string): React.ReactNode {
  if (!text) return '';
  // Split on $...$ patterns (inline math)
  const parts = text.split(/(\$[^$]+\$)/g);
  return parts.map((part, i) => {
    if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
      const tex = part.slice(1, -1);
      try {
        const html = katex.renderToString(tex, { throwOnError: false, displayMode: false });
        return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
      } catch {
        return <code key={i}>{tex}</code>;
      }
    }
    return <span key={i}>{part}</span>;
  });
}

// Widget types that use deprecated string refs and are broken in React 18
const BROKEN_WIDGET_TYPES = new Set(['orderer', 'matcher']);

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
    // Strip STANDALONE image-reference sentences (not mid-sentence references)
    // Only strip when the reference is the entire sentence to avoid breaking question text
    if (typeof q.question.content === 'string') {
      q.question.content = q.question.content
        .replace(/^(?:look at|examine|see|observe|study|check out)\s+(?:the\s+)?(?:picture|image|diagram|illustration|photo|figure)s?\b[^.!?\n]*[.!?]\s*/gim, '')
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
        // Expression: convert to numeric-input to avoid MathInput crash (string ref issue in React 18)
        if (w?.type === 'expression' && w.options) {
          const answerForms = w.options.answerForms || [];
          const firstAnswer = answerForms[0]?.value || '0';
          // Replace placeholder in content
          if (typeof q.question.content === 'string') {
            q.question.content = q.question.content.replace(`[[☃ ${key}]]`, `[[☃ ${key}]]`);
          }
          q.question.widgets[key] = {
            type: 'numeric-input',
            graded: true,
            options: {
              coefficient: false,
              static: false,
              labelText: '',
              size: 'normal',
              answers: [{
                status: 'correct',
                value: parseFloat(firstAnswer) || 0,
                maxError: 0.01,
                simplify: 'optional',
                strict: false,
                message: '',
              }],
            },
          };
        }
        // Definition: inline the definition text to avoid popover dismiss bugs
        // The definition widget's Wonder Blocks Popover has dismiss issues,
        // so we render definition text directly in content and remove the widget.
        if (w?.type === 'definition' && w.options) {
          const defText = (w.options.definition || '').trim();
          const prompt = (w.options.togglePrompt || 'Definition').trim();
          const placeholder = `[[☃ ${key}]]`;
          if (defText && typeof q.question.content === 'string' && q.question.content.includes(placeholder)) {
            q.question.content = q.question.content.replace(
              placeholder,
              ` (*${prompt}:* ${defText}) `
            );
            delete q.question.widgets[key];
            continue; // Skip further processing for this widget
          }
          // Fallback: if no definition text, keep widget but add required fields
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
        // Matcher: leave as-is — BROKEN_WIDGET_TYPES will trigger "Skip" UX
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

  // Detect if question has only widget types broken in React 18
  const brokenWidgetOnly = useMemo(() => {
    const widgets = sanitizedQuestion?.question?.widgets || {};
    const scoreable = Object.values(widgets).filter((w: any) => {
      const t = w?.type;
      return t && t !== 'image' && t !== 'definition';
    });
    if (scoreable.length === 0) return false;
    return scoreable.every((w: any) => BROKEN_WIDGET_TYPES.has(w.type));
  }, [sanitizedQuestion]);

  // Detect if question needs audio (phonics/listening questions)
  const audioWord = useMemo(() => {
    const content = question?.question?.content || '';
    return extractAudioWord(content);
  }, [question]);

  const [emptyWarning, setEmptyWarning] = useState(false);

  const handleSubmit = () => {
    if (isAnswered) return; // Prevent double-submit
    if (!rendererRef.current) {
      console.error('[AssessmentQuestion] rendererRef is null — widget still loading, please wait');
      // Widget still loading — show a warning instead of force-marking incorrect
      setEmptyWarning(true);
      setTimeout(() => setEmptyWarning(false), 2000);
      return;
    }

    try {

    const userInput = rendererRef.current.getUserInput();
    const questionData = sanitizedQuestion.question;

    // Empty submission guard
    if (!hasUserInput(questionData.widgets || {}, userInput)) {
      setEmptyWarning(true);
      setTimeout(() => {
        document.getElementById('empty-submit-warning')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
      setTimeout(() => setEmptyWarning(false), 3500);
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
      // Show visible error to user instead of silent failure
      setEmptyWarning(true);
      setTimeout(() => {
        document.getElementById('empty-submit-warning')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
      setTimeout(() => setEmptyWarning(false), 4000);
      setIsAnswered(false);
    }
  };

  const progressPercentage = (questionNumber / totalQuestions) * 100;

  return (
    <div className="framework-perseus mt-0">
      {/* Enhanced Question Header with Progress */}
      <div className="mb-8 border-[5px] border-black dark:border-white bg-[#FFD93D] shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] overflow-hidden">
        <div className="px-6 py-5 text-center border-b-[3px] border-black dark:border-white">
          <div className="text-xl font-black text-black uppercase tracking-widest mb-2 font-sans">
            QUESTION {questionNumber || 1} OF {totalQuestions || '?'}
          </div>
          <div className="text-sm font-bold text-black uppercase tracking-wide opacity-80">
            Assessment in Progress
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-3 bg-white dark:bg-neutral-800 border-t-[3px] border-black dark:border-white relative overflow-hidden">
          <div
            className="h-full bg-[#FF6B6B] border-r-[3px] border-black dark:border-white transition-all duration-300 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] font-black text-black dark:text-white uppercase tracking-wide z-10">
            {Math.round(progressPercentage)}%
          </div>
        </div>
      </div>

      {/* Audio play button for phonics/listening questions */}
      {audioWord && (
        <div className="mb-4">
          <AudioPlayButton word={audioWord} autoPlay={true} />
        </div>
      )}

      <div
        id="question-content-container"
        className="border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 text-black dark:text-white p-4 md:p-5 lg:p-6 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] mb-6"
        style={{ overflow: 'visible' }}
      >
        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
          <RenderStateRoot>
            <ServerItemRenderer
              key={question?.dash_metadata?.dash_question_id || `q-${questionNumber}`}
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
        <div className="mb-4">
          {hintsShown > 0 && (
            <div className="mb-3">
              {(question.hints || []).slice(0, hintsShown).map((hint: any, idx: number) => (
                <div key={idx} className="py-3 px-4 mb-2 border-[3px] border-black dark:border-white bg-[#FFF9C4] dark:bg-amber-900/40 shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] text-sm leading-relaxed break-words text-black dark:text-white">
                  <strong className="text-[11px] uppercase tracking-wide">
                    Hint {idx + 1}:
                  </strong>{' '}
                  {renderTextWithLatex(hint.content)}
                </div>
              ))}
            </div>
          )}
          {hintsShown < (question.hints || []).length && (
            <button
              onClick={() => setHintsShown(h => h + 1)}
              className="py-2.5 px-5 text-[13px] font-bold uppercase tracking-wide bg-[#E3F2FD] dark:bg-blue-900/40 text-[#1565C0] dark:text-blue-300 border-[3px] border-black dark:border-white cursor-pointer shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] mb-2 hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all duration-100"
            >
              Show Hint ({hintsShown + 1}/{(question.hints || []).length})
            </button>
          )}
        </div>
      )}

      {!isAnswered && brokenWidgetOnly && (
        <div className="mb-6 relative z-10">
          <div className="mb-3 py-3 px-5 border-[3px] border-black dark:border-white bg-[#FFF3E0] dark:bg-orange-900/30 text-sm font-bold text-center text-black dark:text-orange-200 uppercase tracking-wide">
            Drag-and-drop questions are not supported yet
          </div>
          <button
            onClick={() => onAnswer(false)}
            className="w-full py-4 px-6 text-base font-black uppercase tracking-widest bg-[#E0E0E0] text-black border-[4px] border-black cursor-pointer shadow-[3px_3px_0_0_rgba(0,0,0,1)] transition-all duration-100 font-sans hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]"
          >
            Skip Question
          </button>
        </div>
      )}

      {!isAnswered && !brokenWidgetOnly && (
        <div className="mb-6" style={{ position: 'relative', zIndex: 20, isolation: 'isolate' }}>
          <button
            onClick={handleSubmit}
            disabled={isAnswered}
            className="w-full py-5 px-8 text-lg font-black uppercase tracking-widest bg-[#FFD93D] text-black border-[5px] border-black dark:border-white cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 font-sans hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
          >
            Submit Answer
          </button>
          {emptyWarning && (
            <div
              id="empty-submit-warning"
              className="mt-3 py-4 px-5 border-[4px] border-black dark:border-white bg-[#FFF3E0] dark:bg-orange-900/40 shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] text-base font-black text-[#E65100] dark:text-orange-300 uppercase tracking-wide text-center animate-bounce"
              style={{ animationDuration: '0.4s', animationIterationCount: '2' }}
            >
              Please select or enter an answer first
            </div>
          )}
        </div>
      )}

      {showFeedback && keScore && (
        <div
          className={`mb-6 border-[5px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] overflow-hidden ${keScore.correct ? 'bg-[#E8F5E9]' : 'bg-[#FFEBEE]'}`}
          style={{ position: 'relative', zIndex: 20, isolation: 'isolate', backgroundColor: keScore.correct ? '#E8F5E9' : '#FFEBEE' }}
        >
          <div className={`px-5 py-4 flex items-center justify-center gap-4 ${!keScore.correct && question?.hints?.length ? 'border-b-[3px] border-black dark:border-white' : ''}`}>
            {keScore.correct ? (
              <>
                <CheckCircle2 size={32} className="text-[#2E7D32] dark:text-green-400 flex-shrink-0" />
                <span className="text-[#2E7D32] dark:text-green-400 font-bold text-lg uppercase tracking-wide">
                  Correct!
                </span>
              </>
            ) : (
              <>
                <XCircle size={32} className="text-[#C62828] dark:text-red-400 flex-shrink-0" />
                <span className="text-[#C62828] dark:text-red-400 font-bold text-lg uppercase tracking-wide">
                  Incorrect
                </span>
              </>
            )}
          </div>
          {/* Show explanation hint when incorrect */}
          {!keScore.correct && question?.hints?.length > 0 && (
            <div className="px-5 py-3.5 text-sm leading-relaxed text-[#333] dark:text-neutral-200 bg-[#FFF3E0] dark:bg-amber-900/30">
              <strong className="uppercase text-xs tracking-wide">
                Explanation:
              </strong>{' '}
              {renderTextWithLatex(question.hints[question.hints.length - 1]?.content || question.hints[0]?.content || '')}
            </div>
          )}
        </div>
      )}

      {/* Next Question button — shown after submit, student advances when ready */}
      {isAnswered && pendingCorrect !== null && (
        <div className="mb-6" style={{ position: 'relative', zIndex: 20, isolation: 'isolate' }}>
          <button
            onClick={handleNext}
            className="w-full py-5 px-8 text-lg font-black uppercase tracking-widest bg-[#4FC3F7] text-black border-[5px] border-black dark:border-white cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 font-sans hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none"
          >
            Next Question
          </button>
        </div>
      )}
    </div>
  );
};

export default AssessmentQuestion;

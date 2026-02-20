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
import '../question-display/mcq-fix.css';

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

const stripWrappingQuotes = (value: unknown): string => {
  const text = typeof value === 'string' ? value.trim() : String(value ?? '').trim();
  if (text.length >= 2) {
    const first = text[0];
    const last = text[text.length - 1];
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return text.slice(1, -1).trim();
    }
  }
  return text;
};

const sanitizeChoicesArray = (choices: any[]): any[] => {
  return (choices || []).map((choice: any, index: number) => {
    if (typeof choice === 'string') {
      return { id: `choice-${index}`, content: stripWrappingQuotes(choice), correct: false };
    }
    if (!choice || typeof choice !== 'object') {
      return { id: `choice-${index}`, content: stripWrappingQuotes(choice), correct: false };
    }
    return {
      ...choice,
      id: typeof choice.id === 'string' && choice.id.trim() ? choice.id : `choice-${index}`,
      content: stripWrappingQuotes(choice.content),
      correct: Boolean(choice.correct),
    };
  });
};

const normalizeInlineWidgetLayout = (container: HTMLElement) => {
  const inlineContainers = container.querySelectorAll<HTMLElement>('.perseus-widget-container.widget-inline-block');
  inlineContainers.forEach((el) => {
    el.style.setProperty('display', 'inline-flex', 'important');
    el.style.setProperty('vertical-align', 'baseline', 'important');
    el.style.setProperty('align-items', 'baseline', 'important');
    el.style.setProperty('width', 'auto', 'important');
    el.style.setProperty('max-width', 'min(80vw, 500px)', 'important');
  });

  const inlineDropdowns = container.querySelectorAll<HTMLElement>('.perseus-widget-container.widget-inline-block .perseus-dropdown');
  inlineDropdowns.forEach((el) => {
    el.style.setProperty('display', 'inline-flex', 'important');
    el.style.setProperty('max-width', 'min(80vw, 500px)', 'important');
    el.style.setProperty('width', 'auto', 'important');
  });

  const inlineComboboxButtons = container.querySelectorAll<HTMLElement>(
    '.perseus-widget-container.widget-inline-block .perseus-dropdown > button[role="combobox"]'
  );
  inlineComboboxButtons.forEach((btn) => {
    btn.style.setProperty('min-width', 'clamp(120px, 20vw, 280px)', 'important');
    btn.style.setProperty('max-width', 'min(80vw, 500px)', 'important');
    btn.style.setProperty('width', 'auto', 'important');
    btn.style.setProperty('min-height', '38px', 'important');
    btn.style.setProperty('height', 'auto', 'important');
    btn.style.setProperty('padding', '6px 10px', 'important');
    btn.style.setProperty('line-height', '1.2', 'important');
    btn.style.setProperty('font-size', '14px', 'important');
    btn.style.setProperty('align-items', 'flex-start', 'important');
  });

  const inlineValueSpans = container.querySelectorAll<HTMLElement>(
    '.perseus-widget-container.widget-inline-block .perseus-dropdown > button[role="combobox"] > span:first-child'
  );
  inlineValueSpans.forEach((span) => {
    span.style.setProperty('white-space', 'normal', 'important');
    span.style.setProperty('overflow', 'visible', 'important');
    span.style.setProperty('text-overflow', 'clip', 'important');
    span.style.setProperty('word-break', 'break-word', 'important');
  });

  const inlineTextInputs = container.querySelectorAll<HTMLInputElement>(
    '.perseus-widget-container.widget-inline-block input[type="text"]'
  );
  inlineTextInputs.forEach((input) => {
    input.style.setProperty('min-width', 'clamp(120px, 20vw, 280px)', 'important');
    input.style.setProperty('max-width', 'min(80vw, 500px)', 'important');
    input.style.setProperty('width', 'auto', 'important');
    input.style.setProperty('font-size', '14px', 'important');
  });
};

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
  const questionCardRef = useRef<HTMLDivElement>(null);
  const headerBlockRef = useRef<HTMLDivElement>(null);
  const contentBlockRef = useRef<HTMLDivElement>(null);
  const actionDockRef = useRef<HTMLDivElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [keScore, setKeScore] = useState<KEScore | null>(null);
  const [hintsShown, setHintsShown] = useState(0);
  const [pendingCorrect, setPendingCorrect] = useState<boolean | null>(null);
  const [autoFitZoom, setAutoFitZoom] = useState(1);
  const startTimeRef = useRef<number>(Date.now());
  const [viewportHeight, setViewportHeight] = useState<number>(() =>
    typeof window !== 'undefined' ? window.innerHeight : 1024
  );
  const compactViewport = viewportHeight <= 920;
  const ultraCompactViewport = viewportHeight <= 800;
  const contentZoom =
    viewportHeight <= 700 ? 0.9 :
    viewportHeight <= 760 ? 0.94 :
    viewportHeight <= 840 ? 0.96 :
    viewportHeight <= 920 ? 0.98 :
    1;
  const actionDockStyle: React.CSSProperties = {
    position: 'relative',
    left: 0,
    width: '100%',
    zIndex: 60,
    marginTop: compactViewport ? '4px' : '8px',
    padding: ultraCompactViewport ? '1px' : compactViewport ? '3px' : '6px',
    border: ultraCompactViewport ? '2px solid #000' : '3px solid #000',
    background: 'rgba(255,255,255,0.96)',
    boxShadow: '2px 2px 0 #000',
    pointerEvents: 'auto',
  };
  const postAnswerActionDockStyle: React.CSSProperties = {
    position: 'relative',
    left: 0,
    width: '100%',
    zIndex: 70,
    marginTop: compactViewport ? '4px' : '8px',
    padding: ultraCompactViewport ? '1px' : compactViewport ? '3px' : '6px',
    border: ultraCompactViewport ? '2px solid #000' : '3px solid #000',
    background: 'rgba(255,255,255,0.96)',
    boxShadow: '2px 2px 0 #000',
    pointerEvents: 'auto',
  };

  // Reset answer state when question changes
  useEffect(() => {
    setIsAnswered(false);
    setShowFeedback(false);
    setHintsShown(0);
    setKeScore(null);
    setPendingCorrect(null);
    setAutoFitZoom(1);
    startTimeRef.current = Date.now();
  }, [question]);

  useEffect(() => {
    const onResize = () => setViewportHeight(window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Enforce compact inline widget geometry for sentence-embedded dropdown/text widgets.
  // This runs after each question render to override widget-internal style drift.
  useEffect(() => {
    const container = document.getElementById("question-content-container");
    if (!container) return;

    let cancelled = false;
    const applyLayout = () => {
      if (cancelled) return;
      normalizeInlineWidgetLayout(container);
    };

    const raf1 = requestAnimationFrame(applyLayout);
    const raf2 = requestAnimationFrame(applyLayout);
    const timeoutId = window.setTimeout(applyLayout, 40);
    const observer = new MutationObserver(() => applyLayout());
    observer.observe(container, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'aria-expanded'],
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      window.clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, [question, questionNumber, isAnswered, compactViewport, contentZoom]);

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
    const hasRadioWidget = Object.values(q.question.widgets || {}).some((w: any) => w?.type === 'radio');
    if (hasRadioWidget && typeof q.question.content === 'string') {
      q.question.content = q.question.content
        .replace(/^\s*choose\s+\d+\s+answers?:\s*$/gim, '')
        .replace(/^\s*choose\s+one\s+answer:\s*$/gim, '')
        .replace(/\n{3,}/g, '\n\n')
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
            options: { choices: sanitizeChoicesArray(w.options), multipleSelect, randomize },
          };
        } else if (w?.type === 'radio' && w.options && Array.isArray(w.options.choices)) {
          q.question.widgets[key] = {
            ...w,
            options: {
              ...w.options,
              choices: sanitizeChoicesArray(w.options.choices),
              noneOfTheAbove: false,
              // Ensure no pre-selected state from AI generation
              selectedChoiceIds: undefined,
              deselectEnabled: false,
            },
          };
        }
        if (w?.type === 'numeric-input' && w.options) {
          // Ensure answers is always an array (prevents Perseus linter "answers is not iterable" crash)
          const answers = Array.isArray(w.options.answers) ? w.options.answers : [];
          q.question.widgets[key] = {
            ...w,
            options: { coefficient: false, static: false, labelText: '', size: 'normal', ...w.options, answers },
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
            options: { placeholder: 'Select an answer', static: false, ...w.options, choices: sanitizeChoicesArray(w.options.choices || []) },
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
  const hasOverlaySensitiveWidget = useMemo(() => {
    const widgets = (sanitizedQuestion?.question?.widgets || {}) as Record<string, any>;
    return Object.values(widgets).some(
      (w: any) => w?.type === 'dropdown' || w?.type === 'definition'
    );
  }, [sanitizedQuestion]);

  useEffect(() => {
    const contentEl = contentBlockRef.current;
    if (!contentEl) return;

    let raf = 0;
    let timeoutId: number | null = null;
    const minFitZoom = hasOverlaySensitiveWidget ? 0.9 : 0.78;

    const recompute = () => {
      const clientHeight = contentEl.clientHeight;
      const scrollHeight = contentEl.scrollHeight;
      if (!clientHeight || !scrollHeight) return;

      const fitRatio = clientHeight / scrollHeight;
      const nextZoom = fitRatio >= 0.995 ? 1 : Math.max(minFitZoom, Math.min(1, fitRatio));
      setAutoFitZoom((prev) => (Math.abs(prev - nextZoom) > 0.01 ? nextZoom : prev));
    };

    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(recompute);
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(recompute, 45);
    };

    schedule();
    const observer = new ResizeObserver(() => schedule());
    observer.observe(contentEl);
    if (questionCardRef.current) observer.observe(questionCardRef.current);
    if (headerBlockRef.current) observer.observe(headerBlockRef.current);
    if (actionDockRef.current) observer.observe(actionDockRef.current);
    if (feedbackRef.current) observer.observe(feedbackRef.current);
    window.addEventListener('resize', schedule);

    return () => {
      cancelAnimationFrame(raf);
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      observer.disconnect();
      window.removeEventListener('resize', schedule);
    };
  }, [
    question,
    questionNumber,
    totalQuestions,
    hintsShown,
    isAnswered,
    showFeedback,
    hasOverlaySensitiveWidget,
  ]);
  const baseContentZoom = hasOverlaySensitiveWidget ? 1 : contentZoom;
  const resolvedContentZoom = Math.min(baseContentZoom, autoFitZoom);
  const contentZoomWrapperStyle: React.CSSProperties | undefined =
    resolvedContentZoom < 1
      ? ({
          zoom: resolvedContentZoom,
          width: '100%',
          maxWidth: '100%',
          boxSizing: 'border-box',
        } as React.CSSProperties)
      : undefined;
  const contentBlockStyle: React.CSSProperties = {
    ...(contentZoomWrapperStyle || {}),
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    overflowX: 'hidden',
    paddingRight: compactViewport ? '2px' : '4px',
  };
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
      setTimeout(() => setEmptyWarning(false), 4000);
      setIsAnswered(false);
    }
  };

  const progressPercentage = (questionNumber / totalQuestions) * 100;
  const isFinalQuestion = totalQuestions > 0 && questionNumber >= totalQuestions;

  return (
    <div
      ref={questionCardRef}
      className="framework-perseus mt-0"
      style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', height: '100%', overflow: 'hidden' }}
    >
      {/* Enhanced Question Header with Progress */}
      <div
        ref={headerBlockRef}
        className={`${ultraCompactViewport ? 'mb-1' : compactViewport ? 'mb-2' : 'mb-3'} border-[5px] border-black dark:border-white bg-[#FFD93D] shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] overflow-hidden`}
      >
        <div className={`${ultraCompactViewport ? 'px-3 py-2' : compactViewport ? 'px-4 py-3' : 'px-6 py-5'} text-center border-b-[4px] border-black dark:border-white`}>
          <div className={`${ultraCompactViewport ? 'text-lg mb-0.5' : compactViewport ? 'text-xl mb-1' : 'text-2xl mb-2'} font-black text-black uppercase tracking-widest font-sans`}>
            QUESTION {questionNumber || 1} OF {totalQuestions || '?'}
          </div>
          <div className={`${ultraCompactViewport ? 'text-sm' : compactViewport ? 'text-base' : 'text-lg'} font-bold text-black uppercase tracking-wide opacity-80`}>
            Assessment in Progress
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-4 bg-white dark:bg-neutral-800 border-t-[4px] border-black dark:border-white relative overflow-hidden">
          <div
            className="h-full bg-[#FF6B6B] border-r-[4px] border-black dark:border-white transition-all duration-300 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-xs font-black text-black dark:text-white uppercase tracking-wide z-10">
            {Math.round(progressPercentage)}%
          </div>
        </div>
      </div>

      {/* Audio play button for phonics/listening questions */}
      {audioWord && (
        <div className={`${compactViewport ? 'mb-2' : 'mb-3'}`}>
          <AudioPlayButton word={audioWord} autoPlay={true} />
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div ref={contentBlockRef} style={contentBlockStyle}>
          <div
            id="question-content-container"
            className={`border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 text-black dark:text-white ${ultraCompactViewport ? 'p-3 mb-2' : compactViewport ? 'p-4 mb-3' : 'p-5 md:p-6 lg:p-7 mb-4'} shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.4)]`}
            style={{
              overflowX: 'clip',
              overflowY: 'visible',
              maxHeight: 'none',
              flexShrink: 0,
            }}
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
                    highlightLint: false,
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
            <div className={`${ultraCompactViewport ? 'mb-1' : compactViewport ? 'mb-2' : 'mb-3'}`}>
              {hintsShown > 0 && (
                <div className={ultraCompactViewport ? 'mb-1' : 'mb-2'}>
                  {(question.hints || []).slice(0, hintsShown).map((hint: any, idx: number) => (
                    <div
                      key={idx}
                      data-testid="assessment-inline-hint"
                      className={`${ultraCompactViewport ? 'py-2 px-3 text-sm' : compactViewport ? 'py-3 px-4 text-base' : 'py-4 px-5 text-lg'} mb-3 border-[4px] border-black dark:border-white bg-[#FFF9C4] dark:bg-amber-900/40 shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] leading-relaxed break-words text-[#111827] dark:text-[#F9FAFB]`}
                    >
                      <strong className="text-sm font-black uppercase tracking-wide">
                        Hint {idx + 1}:
                      </strong>{' '}
                      <span>{renderTextWithLatex(hint.content)}</span>
                    </div>
                  ))}
                </div>
              )}
              {hintsShown < (question.hints || []).length && (
                <button
                  data-testid="assessment-show-hint-button"
                  onClick={() => setHintsShown(h => h + 1)}
                  className={`${ultraCompactViewport ? 'py-3 px-5 text-sm' : 'py-4 px-6 text-base'} font-black uppercase tracking-wide bg-[#FFD93D] dark:bg-[#FFD93D] text-black dark:text-black border-[4px] border-black dark:border-white cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] mb-3 hover:bg-[#FFE066] dark:hover:bg-[#FFE066] hover:translate-x-1 hover:translate-y-1 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] transition-all duration-100 active:translate-x-2 active:translate-y-2 active:shadow-none`}
                >
                  Show Hint ({hintsShown + 1}/{(question.hints || []).length})
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {!isAnswered && brokenWidgetOnly && (
        <div className={`${compactViewport ? 'mb-3' : 'mb-5'} relative z-10`}>
          <div className="mb-4 py-4 px-6 border-[4px] border-black dark:border-white bg-[#FFF3E0] dark:bg-orange-900/30 text-base font-black text-center text-black dark:text-orange-200 uppercase tracking-wide shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
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
        <div
          ref={actionDockRef}
          data-testid="assessment-action-dock"
          className={ultraCompactViewport ? 'mb-1' : compactViewport ? 'mb-2' : 'mb-4'}
          style={actionDockStyle}
        >
          <button
            data-testid="assessment-submit-button"
            onClick={handleSubmit}
            disabled={isAnswered}
            className={`${ultraCompactViewport ? 'py-2.5 px-4 text-sm' : compactViewport ? 'py-3 px-5 text-base' : 'py-5 px-8 text-lg'} w-full font-black uppercase tracking-widest bg-[#FFD93D] text-black border-[5px] border-black dark:border-white cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 font-sans hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)]`}
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

      {/* Next Question button — shown immediately after submit, kept sticky so it can't drop below fold */}
      {isAnswered && pendingCorrect !== null && (
        <div
          ref={actionDockRef}
          data-testid="assessment-action-dock"
          className={ultraCompactViewport ? 'mb-1' : compactViewport ? 'mb-2' : 'mb-4'}
          style={postAnswerActionDockStyle}
        >
          <button
            data-testid="assessment-next-button"
            onClick={handleNext}
            className={`${ultraCompactViewport ? 'py-2.5 px-4 text-sm' : compactViewport ? 'py-3 px-5 text-base' : 'py-5 px-8 text-lg'} w-full font-black uppercase tracking-widest bg-[#4FC3F7] text-black border-[5px] border-black dark:border-white cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 font-sans hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none`}
          >
            {isFinalQuestion ? 'Finish Assessment' : 'Next Question'}
          </button>
        </div>
      )}

      {showFeedback && keScore && (
        <div
          ref={feedbackRef}
          className={`${compactViewport ? 'mb-2' : 'mb-4'} border-[5px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] overflow-hidden ${keScore.correct ? 'bg-[#E8F5E9]' : 'bg-[#FFEBEE]'}`}
          style={{ position: 'relative', zIndex: 20, isolation: 'isolate', backgroundColor: keScore.correct ? '#E8F5E9' : '#FFEBEE', flexShrink: 0 }}
        >
          <div className={`px-5 py-4 flex items-center justify-center gap-4 ${!keScore.correct && question?.hints?.length ? 'border-b-[4px] border-black dark:border-white' : ''}`}>
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
            <div
              data-testid="assessment-explanation"
              className="px-6 py-4 text-base leading-relaxed text-[#1F2937] dark:text-[#F9FAFB] bg-[#FFF3E0] dark:bg-[#3B2A14]"
              style={{
                minHeight: ultraCompactViewport ? 56 : 72,
                maxHeight: ultraCompactViewport ? 160 : compactViewport ? 200 : 260,
                overflowY: 'auto',
                overflowX: 'hidden',
                lineHeight: 1.5,
                whiteSpace: 'normal',
                wordBreak: 'break-word',
                flexShrink: 0,
              }}
            >
              <strong className="uppercase text-sm font-black tracking-wide">
                Explanation:
              </strong>{' '}
              <span>{renderTextWithLatex(question.hints[question.hints.length - 1]?.content || question.hints[0]?.content || '')}</span>
            </div>
          )}
        </div>
      )}

    </div>
  );
};

export default AssessmentQuestion;

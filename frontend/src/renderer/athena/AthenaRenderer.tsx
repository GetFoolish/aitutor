/**
 * Athena Renderer - Main Entry Point
 *
 * A modern, performant content renderer for educational content.
 * Supports Perseus JSON format for backward compatibility while
 * providing improved performance and multi-subject notation support.
 */

import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useCallback,
  useMemo,
  useEffect,
  Suspense,
} from 'react';
import { AthenaProvider, useAthena } from './AthenaContext';
import { HtmlWithInlineWidgets } from './components/HtmlWithInlineWidgets';
import {
  processImageMarkdown,
  processContent,
} from './utils/ContentRendererUtils';
import './athena.css';
import type {
  AthenaRendererProps,
  AthenaRendererRef,
  PerseusItem,
  AthenaItem,
  SerializedState,
  ScoringResult,
  WidgetScoreDetail,
  NotationType,
} from './core/types';

// ============================================================================
// CONTENT RENDERER (Internal Component)
// ============================================================================

interface ContentRendererProps {
  item: PerseusItem | AthenaItem;
  problemNum: number;
}

const ContentRenderer = forwardRef<AthenaRendererRef, ContentRendererProps>(
  function ContentRenderer({ item, problemNum }, ref) {
    const { state, setAnswer, dispatchEvent } = useAthena();
    const containerRef = useRef<HTMLDivElement>(null);

    // Process content and widgets
    const { processedContent, processedWidgets } = useMemo(() => {
      const content = item?.question?.content || '';
      const widgets = item?.question?.widgets || {};

      // Process main content
      const processedHtml = processContent(content);

      // Process widget options (images in options)
      const newWidgets = { ...widgets };
      Object.keys(newWidgets).forEach(widgetId => {
        const widget = newWidgets[widgetId];
        if (widget?.options) {
          const newOptions = { ...(widget.options as any) };
          let changed = false;

          // Process passageText
          if (newOptions.passageText && typeof newOptions.passageText === 'string') {
            newOptions.passageText = processImageMarkdown(newOptions.passageText);
            changed = true;
          }

          // Process passageTitle
          if (newOptions.passageTitle && typeof newOptions.passageTitle === 'string') {
            newOptions.passageTitle = processImageMarkdown(newOptions.passageTitle);
            changed = true;
          }

          if (changed) {
            newWidgets[widgetId] = {
              ...widget,
              options: newOptions,
            };
          }
        }
      });

      return { processedContent: processedHtml, processedWidgets: newWidgets };
    }, [item.question?.content, item.question?.widgets]);

    // Get user input for all widgets
    const getUserInput = useCallback((): Record<string, unknown> => {
      return { ...state.answers };
    }, [state.answers]);

    // Get legacy user input format
    const getUserInputLegacy = useCallback((): unknown[] => {
      return Object.values(state.answers);
    }, [state.answers]);

    // Get serialized state
    const getSerializedState = useCallback((): SerializedState => {
      return {
        question: state.answers,
      };
    }, [state.answers]);

    // Restore state
    const restoreState = useCallback(
      (serializedState: SerializedState) => {
        if (serializedState.question) {
          Object.entries(serializedState.question).forEach(([widgetId, value]) => {
            setAnswer(widgetId, value);
          });
        }
      },
      [setAnswer]
    );

    // Focus management
    const focus = useCallback(() => {
      containerRef.current?.focus();
    }, []);

    const blur = useCallback(() => {
      containerRef.current?.blur();
    }, []);

    // Scoring (basic implementation - will be enhanced in Phase 4)
    const score = useCallback((): ScoringResult => {
      const widgets = item.question?.widgets || {};
      const details: WidgetScoreDetail[] = [];
      let totalEarned = 0;
      let totalPossible = 0;
      let allCorrect = true;
      let isEmpty = true;

      Object.entries(widgets).forEach(([widgetId, widget]) => {
        const userAnswer = state.answers[widgetId];
        const widgetType = widget.type as any;

        // Skip ungraded widgets
        if (!widget.graded) {
          return;
        }

        totalPossible += 1;

        if (userAnswer !== undefined && userAnswer !== null && userAnswer !== '') {
          isEmpty = false;
        }

        // Basic scoring logic (to be expanded in Phase 4)
        let correct = false;

        if (widgetType === 'radio' && widget.options) {
          const options = widget.options as any;
          const choices = Array.isArray(options?.choices) ? options.choices : [];
          const selectedIndex = userAnswer as number;
          correct = choices[selectedIndex]?.correct === true;
        } else if (widgetType === 'numeric-input' && widget.options) {
          const options = widget.options as any;
          const answers = Array.isArray(options?.answers) ? options.answers : [];
          
          // Handle fractions in user answer
          let numericAnswer = parseFloat(String(userAnswer));
          const strAnswer = String(userAnswer);
          if (strAnswer.includes('/')) {
            const [num, den] = strAnswer.split('/');
            if (num && den && !isNaN(Number(num)) && !isNaN(Number(den)) && Number(den) !== 0) {
              numericAnswer = Number(num) / Number(den);
            }
          }

          correct = answers.some((ans: any) => {
            if (!ans) return false;
            const tolerance = ans.maxError || 0;
            return (
              ans.status === 'correct' &&
              Math.abs(numericAnswer - ans.value) <= tolerance
            );
          });
        }

        if (correct) {
          totalEarned += 1;
        } else {
          allCorrect = false;
        }

        details.push({
          widgetId,
          widgetType,
          correct,
          earned: correct ? 1 : 0,
          total: 1,
        });
      });

      return {
        correct: allCorrect && !isEmpty,
        empty: isEmpty,
        earned: totalEarned,
        total: totalPossible,
        details,
      };
    }, [item.question?.widgets, state.answers]);

    // Expose ref methods
    useImperativeHandle(
      ref,
      () => ({
        getUserInput,
        getUserInputLegacy,
        getSerializedState,
        restoreState,
        focus,
        blur,
        score,
      }),
      [getUserInput, getUserInputLegacy, getSerializedState, restoreState, focus, blur, score]
    );

    // Dispatch render events
    useEffect(() => {
      dispatchEvent({
        type: 'render-start',
        timestamp: Date.now(),
        data: { problemNum },
      });

      return () => {
        dispatchEvent({
          type: 'render-complete',
          timestamp: Date.now(),
          data: { problemNum },
        });
      };
    }, [problemNum, dispatchEvent]);

    return (
      <div
        ref={containerRef}
        className={`athena-content athena-theme-${state.theme}`}
        tabIndex={-1}
        role="region"
        aria-label="Question content"
      >
        <div className="athena-question">
          <HtmlWithInlineWidgets
            html={processedContent}
            widgets={processedWidgets}
            keyPrefix={`question-${problemNum}`}
            state={state}
            setAnswer={setAnswer}
          />
        </div>

        {/* Hints section */}
        {state.hintsVisible > 0 && Array.isArray(item.hints) && item.hints.length > 0 && (
          <div className="athena-hints">
            <h4 className="athena-hints-title">Hints</h4>
            {item.hints.slice(0, state.hintsVisible).map((hint, idx) => {
              // Process hint content using centralized processor
              const hintContent = processContent(hint?.content || '');

              return (
                <div key={`hint-${idx}`} className="athena-hint-item expanded">
                  <div className="athena-hint-header">
                    <span className="athena-hint-label">Hint {idx + 1} of {item.hints?.length || 0}</span>
                  </div>
                  <HtmlWithInlineWidgets
                    html={hintContent}
                    widgets={processedWidgets}
                    keyPrefix={`hint-${problemNum}-${idx}`}
                    state={state}
                    setAnswer={setAnswer}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
);

// ============================================================================
// LOADING FALLBACK
// ============================================================================

function LoadingFallback() {
  return (
    <div className="athena-loading">
      <div className="athena-loading-spinner" />
      <span className="athena-loading-text">Loading content...</span>
    </div>
  );
}

// ============================================================================
// ERROR BOUNDARY
// ============================================================================

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class AthenaErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Athena render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="athena-error">
            <h4>Unable to render content</h4>
            <p>{this.state.error?.message || 'An unexpected error occurred'}</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

// ============================================================================
// MAIN RENDERER COMPONENT
// ============================================================================

export const AthenaRenderer = forwardRef<AthenaRendererRef, AthenaRendererProps>(
  function AthenaRenderer(
    {
      item,
      problemNum = 0,
      hintsVisible = 0,
      reviewMode = false,
      showSolutions = 'none',
      initialState,
      onStateChange,
      onAnswerChange,
      readOnly = false,
      theme = 'light',
      ariaLabel,
      apiOptions = {},
      dependencies = {},
    },
    ref
  ) {
    const contentRef = useRef<AthenaRendererRef>(null);

    // Forward ref to content renderer
    useImperativeHandle(ref, () => ({
      getUserInput: () => contentRef.current?.getUserInput() || {},
      getUserInputLegacy: () => contentRef.current?.getUserInputLegacy() || [],
      getSerializedState: () =>
        contentRef.current?.getSerializedState() || { question: {} },
      restoreState: (state) => contentRef.current?.restoreState(state),
      focus: () => contentRef.current?.focus(),
      blur: () => contentRef.current?.blur(),
      score: () =>
        contentRef.current?.score() || {
          correct: false,
          empty: true,
          earned: 0,
          total: 0,
          details: [],
        },
    }));

    // Handle state changes
    const handleEvent = useCallback(
      (event: any) => {
        if (event.type === 'answer-change' && onAnswerChange) {
          onAnswerChange(event.data.widgetId, event.data.value);
        }
        dependencies.onEvent?.(event);
      },
      [onAnswerChange, dependencies]
    );

    return (
      <AthenaErrorBoundary>
        <AthenaProvider
          theme={theme}
          dependencies={{ ...dependencies, onEvent: handleEvent }}
          apiOptions={apiOptions}
          initialAnswers={initialState?.question || {}}
          hintsVisible={hintsVisible}
          reviewMode={reviewMode}
          showSolutions={showSolutions}
          readOnly={readOnly}
        >
          <div
            className="athena-renderer"
            role="application"
            aria-label={ariaLabel || `Question ${problemNum + 1}`}
          >
            <Suspense fallback={<LoadingFallback />}>
              <ContentRenderer ref={contentRef} item={item} problemNum={problemNum} />
            </Suspense>
          </div>
        </AthenaProvider>
      </AthenaErrorBoundary>
    );
  }
);

export default AthenaRenderer;

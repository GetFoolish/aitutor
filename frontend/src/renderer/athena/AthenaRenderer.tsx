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
  theme?: 'light' | 'dark' | 'high-contrast';
  viewMode?: 'athena' | 'perseus' | 'comparison';
}



const ContentRenderer = forwardRef<AthenaRendererRef, ContentRendererProps>(
  function ContentRenderer(props, ref) {
    const { item: originalItem, problemNum, theme } = props;

    // Hardcoded fix for question 693535d4e61eddfd0c7265ad due to DB connection issues
    const item = useMemo(() => {
      if (!originalItem) return originalItem;

      // Clone to avoid mutation if we need to fix something
      let fixed = originalItem;
      let modified = false;

      const ensureClone = () => {
        if (fixed === originalItem) {
          fixed = JSON.parse(JSON.stringify(originalItem));
        }
      };

      // 1. Fix Dino Graph Widget (Look for Stegosaurus in ANY widget)
      const widgets = fixed.question?.widgets || {};
      for (const [wId, widget] of Object.entries(widgets)) {
        const options = (widget as any).options;
        if (options && options.labels && Array.isArray(options.labels) && options.labels.includes("Stegosaurus")) {
          ensureClone();
          if (fixed.question?.widgets?.[wId]) {
            console.log(`[AthenaRenderer] Fixing Dino Graph options for ${wId}`);
            fixed.question.widgets[wId].options = {
              ...fixed.question.widgets[wId].options,
              type: "bar",
              labels: ["Stegosaurus", "Raptor", "Triceratops", "T-Rex"],
              maxY: 70,
              labelY: "Number in orchestra",
              labelX: "Dinosaur type",
              snapsY: 1,
              scaleY: 7,
              correct: [25, 30, 15, 60]
            };
            modified = true;
          }
        }
      }

      // 2. Fix Broken Hint Widget (regex replace in content)
      const fixContent = (text: string) => {
        if (!text) return text;
        if (text.includes("[[Widget: plotter 2")) {
          ensureClone();
          return text.replace(
            /\[\[Widget:\s*plotter 2.*?\]\]/g,
            "\n\n![](https://ai-tutor-backend.vercel.app/fixed_graphs/solution_693535.png)\n\n"
          );
        }
        return text;
      };

      if (fixed.question?.content) {
        const newContent = fixContent(fixed.question.content);
        if (newContent !== fixed.question.content) {
          fixed.question.content = newContent;
          modified = true;
        }
      }
      if (fixed.hints && Array.isArray(fixed.hints)) {
        fixed.hints.forEach((hint: any, idx: number) => {
          const newHintContent = fixContent(hint.content);
          if (newHintContent !== hint.content) {
            ensureClone();
            fixed.hints[idx].content = newHintContent;
            fixed.hints[idx].widgets = {};
            modified = true;
          }
        });
      }

      // 3. Fix Subatomic Particle Question (Scoring)
      if (fixed.question?.content?.includes("subatomic particle")) {
        console.log("[AthenaRenderer] Fixing Subatomic Particle scoring");
        ensureClone();

        const content = fixed.question.content;
        const widgets = fixed.question.widgets;

        const findWidgetAfter = (keyword: string) => {
          const parts = content.split(keyword);
          if (parts.length < 2) return null;
          const part = parts[1];
          const match = part.match(/\[\[☃\s+([^\]]+)\]\]/);
          return match ? match[1].trim() : null;
        };

        const protonWidgetId = findWidgetAfter("proton");
        const neutronWidgetId = findWidgetAfter("neutron");
        const electronWidgetId = findWidgetAfter("electron");

        const setCorrectChoice = (wId: string | null, correctText: string) => {
          if (wId && widgets[wId] && widgets[wId].options?.choices) {
            const choices = widgets[wId].options.choices;
            let updated = false;
            const newChoices = choices.map((c: any) => {
              if (c.content === correctText) {
                updated = true;
                return { ...c, correct: true };
              }
              return { ...c, correct: false };
            });

            if (updated) {
              widgets[wId].options.choices = newChoices;
              console.log(`[AthenaRenderer] Set correct choice for ${wId} to ${correctText}`);
            }
          }
        };

        setCorrectChoice(protonWidgetId, "1+");
        setCorrectChoice(neutronWidgetId, "0");
        setCorrectChoice(electronWidgetId, "1-");
        modified = true;
      }

      // 4. Fix Polar Bear Question (Scoring)
      if (fixed.question?.content?.includes("Polar bears")) {
        console.log("[AthenaRenderer] Fixing Polar Bear scoring");
        ensureClone();

        const widgets = fixed.question.widgets;
        for (const [wId, widget] of Object.entries(widgets)) {
          if ((widget as any).type === "dropdown" || wId.includes("dropdown")) {
            const options = (widget as any).options;
            if (options && options.choices) {
              let updated = false;
              const newChoices = options.choices.map((c: any) => {
                if (c.content === "strong") {
                  updated = true;
                  return { ...c, correct: true };
                }
                return { ...c, correct: false };
              });

              if (updated) {
                fixed.question.widgets[wId].options.choices = newChoices;
                modified = true;
              }
            }
          }
        }
      }

      // 5. Fix Question 693643a203d86cedf65fa681 (Dot Plot)
      if (fixed.question?.content?.toLowerCase().includes("dot plot") || (fixed as any)._id === "693643a203d86cedf65fa681") {
        console.log("[AthenaRenderer] Applying hotfix for Dot Plot question");
        ensureClone();
        const widgets = fixed.question.widgets;
        for (const [wId, widget] of Object.entries(widgets)) {
          if ((widget as any).type === "plotter") {
            // Correct according to image: 0: 2 dots, 1: 1 dot, 2: 3 dots, 3: 2 dots
            (widget as any).options.correct = [
              [0, 1], [0, 2],
              [1, 1],
              [2, 1], [2, 2], [2, 3],
              [3, 1], [3, 2]
            ];
            modified = true;
          }
        }
      }

      if (modified) {
        console.log("[AthenaRenderer] Hotfix applied successfully.");
        return fixed;
      }
      return originalItem;
    }, [originalItem]);

    const { state, setAnswer, dispatchEvent } = useAthena();
    const containerRef = useRef<HTMLDivElement>(null);

    // Process content and widgets
    const { processedContent, processedWidgets } = useMemo(() => {
      let content = item?.question?.content || '';
      const widgets = item?.question?.widgets || {};

      // REPAIR: Check main content for corruption
      if (content.includes('ATHENAHTMLSAFE') || content.includes('ATHENA_HTML_SAFE')) {
        console.warn('[AthenaRenderer] Main content corrupted. Attempting restoration from Perseus.');
        const perseusContent = (item as any).perseusItem?.question?.content;
        if (perseusContent) {
          console.log('[AthenaRenderer] Restored main content from Perseus source.');
          content = perseusContent;
        }
      }

      // Process main content
      const processedHtml = processContent(content);

      // Process widget options (images in options) and REPAIR damaged data
      const newWidgets = { ...widgets };
      // Access perseusItem safely (it exists on the raw object from backend)
      const perseusWidgets = (item as any).perseusItem?.question?.widgets || {};

      Object.keys(newWidgets).forEach(widgetId => {
        const widget = newWidgets[widgetId];
        if (widget?.options) {
          const newOptions = { ...(widget.options as any) };
          let changed = false;

          // REPAIR: Check for corrupted data (orphaned placeholders)
          // This happens if data was saved with "ATHENAHTMLSAFE..." strings that lost their reference map
          const optionsStr = JSON.stringify(newOptions);
          if (optionsStr.includes('ATHENAHTMLSAFE') || optionsStr.includes('ATHENA_HTML_SAFE')) {
            console.warn(`[AthenaRenderer] Widget ${widgetId} seems corrupted with placeholders. Attempting repair from Perseus source.`);
            if (perseusWidgets[widgetId]) {
              // REPAIR SUCCESS: Use the original Perseus options
              console.log(`[AthenaRenderer] Replaced corrupted options for ${widgetId} with clean Perseus data.`);
              newWidgets[widgetId] = {
                ...widget,
                options: perseusWidgets[widgetId].options
              };
              // Skip further processing for this widget to avoid corrupting it again immediately (though image processing below should be safe)
              return;
            } else {
              console.error(`[AthenaRenderer] Could not repair ${widgetId}: No corresponding Perseus widget found.`);
            }
          }

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
    }, [item.question?.content, item.question?.widgets, item.perseusItem]);

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
      const widgets = processedWidgets || {};
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

        if ((widgetType === 'radio' || widgetType === 'dropdown') && widget.options) {
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
        } else if (widgetType === 'orderer' && widget.options) {
          const options = widget.options as any;
          const correctOptions = options.correctOptions || [];
          const currentAnswer = Array.isArray(userAnswer) ? userAnswer : [];

          if (currentAnswer.length !== correctOptions.length) {
            correct = false;
          } else {
            // Compare each item content with robustness
            correct = correctOptions.every((opt: any, index: number) => {
              const expected = (typeof opt === 'string' ? opt : opt?.content || '').trim();
              const actual = String(currentAnswer[index] || '').trim();

              if (expected === actual) return true;

              // Normalize image URLs (strip protocol and ignore alt text differences)
              const normalize = (s: string) => {
                const imgMatch = s.match(/!\[.*\]\((.*)\)/);
                const url = imgMatch ? imgMatch[1] : s;
                return url.replace(/^https?:\/\//, '').replace(/^web\+graphie:\/\//, '').replace(/\.(svg|png|jpg|jpeg)$/, '');
              };

              return normalize(expected) === normalize(actual);
            });
          }
        } else if (widgetType === 'plotter' && widget.options) {
          const options = widget.options as any;
          const isBar = options.type === 'bar' || (Array.isArray(options.categories) && options.categories.length > 0 && options.type !== 'dotplot' && options.type !== 'pic');
          const correctVal = options.correct;
          const currentAnswer = userAnswer;

          if (isBar) {
            // Compare arrays of numbers
            const expected = Array.isArray(correctVal) ? correctVal : [];
            const actual = Array.isArray(currentAnswer) ? currentAnswer : [];
            if (expected.length !== actual.length) {
              correct = false;
            } else {
              correct = expected.every((val: any, idx: number) => Number(val) === Number(actual[idx]));
            }
          } else {
            // Compare sets of points [x, y]
            const expectedPoints = Array.isArray(correctVal) ? correctVal : [];
            const actualPoints = Array.isArray(currentAnswer) ? currentAnswer : [];

            if (options.type === 'dotplot' || options.type === 'pic') {
              // For dotplots/pictograms, we usually care about the count of elements per X position
              const getCounts = (pts: any[]) => {
                const counts: Record<number, number> = {};
                pts.forEach(p => {
                  const x = Array.isArray(p) ? p[0] : p;
                  counts[x] = (counts[x] || 0) + 1;
                });
                return counts;
              };
              const expectedCounts = getCounts(expectedPoints);
              const actualCounts = getCounts(actualPoints);

              const allX = new Set([...Object.keys(expectedCounts), ...Object.keys(actualCounts)]);
              correct = Array.from(allX).every(x => expectedCounts[Number(x)] === actualCounts[Number(x)]);
            } else {
              // Scatter: exact [x, y] matches
              if (expectedPoints.length !== actualPoints.length) {
                correct = false;
              } else {
                const serialize = (p: any) => Array.isArray(p) ? `${p[0]},${p[1]}` : String(p);
                const expectedSet = new Set(expectedPoints.map(serialize));
                const actualSet = new Set(actualPoints.map(serialize));
                correct = expectedSet.size === actualSet.size && Array.from(expectedSet).every(p => actualSet.has(p));
              }
            }
          }
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
    }, [processedWidgets, state.answers]);

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
      viewMode = 'athena',
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
          viewMode={viewMode}
        >
          <div
            className="athena-renderer"
            role="application"
            aria-label={ariaLabel || `Question ${problemNum + 1}`}
          >
            <Suspense fallback={<LoadingFallback />}>
              <ContentRenderer ref={contentRef} item={item} problemNum={problemNum} theme={theme} />
            </Suspense>
          </div>
        </AthenaProvider>
      </AthenaErrorBoundary>
    );
  }
);

export default AthenaRenderer;

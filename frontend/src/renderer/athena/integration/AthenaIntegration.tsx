/**
 * Athena Integration
 *
 * Drop-in replacement for Perseus renderer.
 * Use this component to gradually migrate from Perseus to Athena.
 */

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import {
  AthenaProvider,
  AthenaRenderer,
  PerseusAdapter,
  ScoringEngine,
  useAnswerState,
  ScreenReaderAnnouncerProvider,
} from '../index';
import type {
  AthenaItem,
  PerseusItem,
  AthenaRendererRef,
  ScoringResult,
  AthenaAPIOptions,
} from '../index';

export interface AthenaQuestionRendererProps {
  /** Perseus-format question data */
  question: PerseusItem;
  /** Called when user answers change */
  onAnswerChange?: (answers: Record<string, unknown>) => void;
  /** Called when user submits answer */
  onSubmit?: (result: ScoringResult) => void;
  /** Whether to show hints */
  showHints?: boolean;
  /** Number of hints to show initially */
  initialHints?: number;
  /** Review mode (show correct answers) */
  reviewMode?: boolean;
  /** Read-only mode */
  readOnly?: boolean;
  /** Custom API options */
  apiOptions?: AthenaAPIOptions;
  /** Custom class name */
  className?: string;
  /** Locale for internationalization */
  locale?: string;
}

/**
 * Drop-in replacement for Perseus ServerItemRenderer
 */
export function AthenaQuestionRenderer({
  question,
  onAnswerChange,
  onSubmit,
  showHints = true,
  initialHints = 0,
  reviewMode = false,
  readOnly = false,
  apiOptions,
  className = '',
  locale = 'en',
}: AthenaQuestionRendererProps) {
  const rendererRef = useRef<AthenaRendererRef>(null);
  const [visibleHints, setVisibleHints] = useState(initialHints);
  const [lastResult, setLastResult] = useState<ScoringResult | null>(null);

  // Convert Perseus to Athena format
  const athenaItem = useMemo(() => {
    const adapter = new PerseusAdapter();
    const result = adapter.convertItem(question);
    if (!result.success) {
      console.error('Failed to convert Perseus item:', result.errors);
      return null;
    }
    return result.data;
  }, [question]);

  // Handle answer changes
  const handleChange = useCallback((answers: Record<string, unknown>) => {
    onAnswerChange?.(answers);
    setLastResult(null);
  }, [onAnswerChange]);

  // Handle submission
  const handleSubmit = useCallback(() => {
    if (!rendererRef.current || !athenaItem) return;

    const answers = rendererRef.current.getUserInput();
    const engine = new ScoringEngine();
    const result = engine.scoreItem(athenaItem, answers);

    setLastResult(result);
    onSubmit?.(result);
  }, [athenaItem, onSubmit]);

  // Handle hint reveal
  const handleRevealHint = useCallback(() => {
    if (athenaItem && visibleHints < athenaItem.hints.length) {
      setVisibleHints(prev => prev + 1);
    }
  }, [athenaItem, visibleHints]);

  // Reset on question change
  useEffect(() => {
    setVisibleHints(initialHints);
    setLastResult(null);
  }, [question, initialHints]);

  if (!athenaItem) {
    return (
      <div className={`athena-integration-error ${className}`}>
        <p>Failed to load question. Please try again.</p>
      </div>
    );
  }

  return (
    <AthenaProvider
      theme="light"
      apiOptions={apiOptions}
    >
      <ScreenReaderAnnouncerProvider>
        <div className={`athena-integration ${className}`}>
          <AthenaRenderer
            ref={rendererRef}
            item={athenaItem}
            reviewMode={reviewMode}
            readOnly={readOnly}
            onAnswerChange={(widgetId, value) => handleChange({ [widgetId]: value })}
          />

          {/* Hints section */}
          {showHints && athenaItem.hints.length > 0 && (
            <div className="athena-integration-hints">
              {visibleHints > 0 && (
                <div className="athena-integration-hints-list">
                  {athenaItem.hints.slice(0, visibleHints).map((hint, index) => (
                    <div key={index} className="athena-integration-hint">
                      <strong>Hint {index + 1}:</strong>
                      <div className="athena-integration-hint-content">
                        {hint.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {visibleHints < athenaItem.hints.length && !reviewMode && (
                <button
                  type="button"
                  className="athena-integration-hint-btn"
                  onClick={handleRevealHint}
                >
                  Get a hint ({athenaItem.hints.length - visibleHints} remaining)
                </button>
              )}
            </div>
          )}

          {/* Actions */}
          {!readOnly && !reviewMode && (
            <div className="athena-integration-actions">
              <button
                type="button"
                className="athena-integration-submit-btn"
                onClick={handleSubmit}
              >
                Check Answer
              </button>
            </div>
          )}

          {/* Result feedback */}
          {lastResult && (
            <div className={`athena-integration-result ${lastResult.correct ? 'correct' : 'incorrect'}`}>
              {lastResult.correct ? (
                <span>Correct! You earned {lastResult.earned}/{lastResult.total} points.</span>
              ) : (
                <span>Not quite right. You earned {lastResult.earned}/{lastResult.total} points.</span>
              )}
            </div>
          )}
        </div>
      </ScreenReaderAnnouncerProvider>
    </AthenaProvider>
  );
}

/**
 * Hook for using Athena with existing Perseus data
 */
export function useAthenaQuestion(perseusItem: PerseusItem) {
  const [athenaItem, setAthenaItem] = useState<AthenaItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});

  // Convert on mount/change
  useEffect(() => {
    const adapter = new PerseusAdapter();
    const result = adapter.convertItem(perseusItem);

    if (result.success && result.data) {
      setAthenaItem(result.data);
      setError(null);
    } else {
      setAthenaItem(null);
      setError(result.errors?.[0]?.message || 'Failed to convert question');
    }
  }, [perseusItem]);

  // Score answers
  const score = useCallback(() => {
    if (!athenaItem) return null;

    const engine = new ScoringEngine();
    return engine.scoreItem(athenaItem, answers);
  }, [athenaItem, answers]);

  // Reset answers
  const reset = useCallback(() => {
    setAnswers({});
  }, []);

  return {
    athenaItem,
    error,
    answers,
    setAnswers,
    score,
    reset,
    isReady: !!athenaItem,
  };
}

/**
 * Batch convert Perseus questions to Athena format
 */
export async function migratePerseusQuestions(
  questions: PerseusItem[]
): Promise<{
  successful: AthenaItem[];
  failed: Array<{ index: number; error: string }>;
  stats: { total: number; success: number; failed: number };
}> {
  const adapter = new PerseusAdapter();
  const successful: AthenaItem[] = [];
  const failed: Array<{ index: number; error: string }> = [];

  for (let i = 0; i < questions.length; i++) {
    const result = adapter.convertItem(questions[i]);
    if (result.success && result.data) {
      successful.push(result.data);
    } else {
      failed.push({
        index: i,
        error: result.errors?.[0]?.message || 'Unknown error',
      });
    }
  }

  return {
    successful,
    failed,
    stats: {
      total: questions.length,
      success: successful.length,
      failed: failed.length,
    },
  };
}

export default AthenaQuestionRenderer;

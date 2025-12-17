/**
 * Hints Renderer
 *
 * Renders hints with support for:
 * - Progressive reveal
 * - Widgets within hints
 * - Math/notation rendering
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import type { AthenaHint, AthenaWidget, NotationType } from '../core/types';
import { ContentParser } from '../core/ContentParser';
import { MarkdownProcessor } from '../core/MarkdownProcessor';
import { NotationEngineManager } from '../notation/NotationEngineManager';
import { HintsStateManager, type HintsState } from './HintsStateManager';

export interface HintsRendererProps {
  /** Array of hint objects */
  hints: AthenaHint[];
  /** Number of hints to show (controlled) */
  visibleCount?: number;
  /** Callback when user requests next hint */
  onRequestHint?: () => void;
  /** Whether in review mode (show all hints) */
  reviewMode?: boolean;
  /** Custom class name */
  className?: string;
  /** Theme */
  theme?: 'light' | 'dark' | 'high-contrast';
  /** Whether to allow expanding/collapsing */
  collapsible?: boolean;
  /** Widget renderer function */
  renderWidget?: (widgetId: string, widget: AthenaWidget) => React.ReactNode;
}

/**
 * Renders a list of hints with progressive reveal
 */
export function HintsRenderer({
  hints,
  visibleCount: controlledVisibleCount,
  onRequestHint,
  reviewMode = false,
  className = '',
  theme = 'light',
  collapsible = true,
  renderWidget,
}: HintsRendererProps) {
  // Internal state manager for uncontrolled mode
  const [manager] = useState(
    () =>
      new HintsStateManager(hints, {
        initialVisibleCount: reviewMode ? hints.length : 0,
        allowReveal: !reviewMode,
      })
  );

  const [state, setState] = useState<HintsState>(manager.getState());
  const [expandedHints, setExpandedHints] = useState<Set<number>>(new Set());

  // Use controlled or internal state
  const visibleCount = controlledVisibleCount ?? state.visibleCount;

  // Subscribe to manager state changes
  useEffect(() => {
    return manager.subscribe(setState);
  }, [manager]);

  // Update manager when review mode changes
  useEffect(() => {
    if (reviewMode) {
      manager.revealAll();
    }
  }, [reviewMode, manager]);

  // Handle request hint
  const handleRequestHint = useCallback(() => {
    if (onRequestHint) {
      onRequestHint();
    } else {
      manager.revealNext();
    }
  }, [onRequestHint, manager]);

  // Toggle hint expansion
  const toggleHint = useCallback((index: number) => {
    setExpandedHints((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  // Mark hint as viewed when it becomes visible
  const handleHintVisible = useCallback(
    (index: number) => {
      manager.markViewed(index);
    },
    [manager]
  );

  // Visible hints
  const visibleHints = useMemo(
    () => hints.slice(0, visibleCount),
    [hints, visibleCount]
  );

  // Remaining hints count
  const remainingCount = hints.length - visibleCount;

  if (hints.length === 0) {
    return null;
  }

  return (
    <div
      className={`athena-hints athena-hints-${theme} ${className}`}
      role="complementary"
      aria-label="Hints"
    >
      {/* Hints list */}
      <div className="athena-hints-list">
        {visibleHints.map((hint, index) => (
          <HintItem
            key={index}
            hint={hint}
            index={index}
            total={hints.length}
            expanded={!collapsible || expandedHints.has(index)}
            collapsible={collapsible}
            onToggle={() => toggleHint(index)}
            onVisible={() => handleHintVisible(index)}
            theme={theme}
            renderWidget={renderWidget}
          />
        ))}
      </div>

      {/* Request hint button */}
      {!reviewMode && remainingCount > 0 && (
        <div className="athena-hints-actions">
          <button
            type="button"
            className="athena-hint-request-button"
            onClick={handleRequestHint}
            aria-label={`Show next hint (${remainingCount} remaining)`}
          >
            <HintIcon />
            <span>
              Get a hint
              <span className="athena-hint-count">
                ({remainingCount} remaining)
              </span>
            </span>
          </button>
        </div>
      )}

      {/* All hints revealed message */}
      {visibleCount > 0 && remainingCount === 0 && (
        <div className="athena-hints-complete" aria-live="polite">
          All hints revealed
        </div>
      )}
    </div>
  );
}

/**
 * Individual hint item
 */
interface HintItemProps {
  hint: AthenaHint;
  index: number;
  total: number;
  expanded: boolean;
  collapsible: boolean;
  onToggle: () => void;
  onVisible: () => void;
  theme: 'light' | 'dark' | 'high-contrast';
  renderWidget?: (widgetId: string, widget: AthenaWidget) => React.ReactNode;
}

function HintItem({
  hint,
  index,
  total,
  expanded,
  collapsible,
  onToggle,
  onVisible,
  theme,
  renderWidget,
}: HintItemProps) {
  const contentRef = React.useRef<HTMLDivElement>(null);
  const [renderedContent, setRenderedContent] = useState<string>('');

  // Mark as visible on mount
  useEffect(() => {
    onVisible();
  }, [onVisible]);

  // Process hint content
  useEffect(() => {
    const processContent = async () => {
      // Parse the content
      const parseResult = ContentParser.parse(hint.content, hint.widgets);

      // Process markdown
      const processed = MarkdownProcessor.full(hint.content);

      // Render notation
      if (processed.hasMath && contentRef.current) {
        // Will be handled by useEffect on mount
      }

      setRenderedContent(processed.html);
    };

    processContent();
  }, [hint.content, hint.widgets]);

  // Render math notation after content is set
  useEffect(() => {
    if (!contentRef.current) return;

    const mathElements = contentRef.current.querySelectorAll('.athena-math');
    mathElements.forEach(async (element) => {
      const latex = element.getAttribute('data-math');
      const displayMode = element.getAttribute('data-display') === 'true';

      if (latex) {
        try {
          await NotationEngineManager.render(
            'math',
            latex,
            element as HTMLElement,
            { displayMode, theme }
          );
        } catch (error) {
          console.warn('Failed to render math in hint:', error);
        }
      }
    });
  }, [renderedContent, theme]);

  // Render widgets in content
  const renderContent = () => {
    // Replace widget placeholders with rendered widgets
    let content = renderedContent;

    if (renderWidget && hint.widgets) {
      for (const [widgetId, widget] of Object.entries(hint.widgets)) {
        const placeholder = `<span class="athena-widget-placeholder" data-widget-id="${widgetId}"></span>`;
        // Widget rendering would go here
      }
    }

    return { __html: content };
  };

  return (
    <div
      className={`athena-hint-item ${expanded ? 'expanded' : 'collapsed'}`}
      aria-expanded={expanded}
    >
      {/* Hint header */}
      {collapsible ? (
        <button
          type="button"
          className="athena-hint-header"
          onClick={onToggle}
          aria-controls={`hint-content-${index}`}
        >
          <span className="athena-hint-label">
            Hint {index + 1} of {total}
          </span>
          <ChevronIcon expanded={expanded} />
        </button>
      ) : (
        <div className="athena-hint-header">
          <span className="athena-hint-label">
            Hint {index + 1} of {total}
          </span>
        </div>
      )}

      {/* Hint content */}
      {expanded && (
        <div
          id={`hint-content-${index}`}
          ref={contentRef}
          className="athena-hint-content"
          dangerouslySetInnerHTML={renderContent()}
        />
      )}
    </div>
  );
}

/**
 * Progressive hints component with automatic reveal
 */
export function ProgressiveHints({
  hints,
  initialCount = 0,
  onHintReveal,
  ...props
}: Omit<HintsRendererProps, 'visibleCount'> & {
  initialCount?: number;
  onHintReveal?: (index: number, totalRevealed: number) => void;
}) {
  const [visibleCount, setVisibleCount] = useState(initialCount);

  const handleRequestHint = useCallback(() => {
    if (visibleCount < hints.length) {
      const newCount = visibleCount + 1;
      setVisibleCount(newCount);
      onHintReveal?.(newCount - 1, newCount);
    }
  }, [visibleCount, hints.length, onHintReveal]);

  return (
    <HintsRenderer
      {...props}
      hints={hints}
      visibleCount={visibleCount}
      onRequestHint={handleRequestHint}
    />
  );
}

/**
 * Hook for using hints with state management
 */
export function useHints(
  hints: AthenaHint[],
  options?: {
    initialCount?: number;
    reviewMode?: boolean;
  }
) {
  const [manager] = useState(
    () =>
      new HintsStateManager(hints, {
        initialVisibleCount: options?.initialCount ?? 0,
        allowReveal: !options?.reviewMode,
      })
  );

  const [state, setState] = useState<HintsState>(manager.getState());

  useEffect(() => {
    return manager.subscribe(setState);
  }, [manager]);

  return {
    state,
    visibleHints: manager.getVisibleHints(),
    revealNext: () => manager.revealNext(),
    revealAll: () => manager.revealAll(),
    reset: () => manager.reset(),
    hasMore: manager.hasMoreHints(),
    stats: manager.getStats(),
  };
}

// Icons
function HintIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M10 2a6 6 0 00-6 6c0 2.22 1.21 4.16 3 5.19V15a1 1 0 001 1h4a1 1 0 001-1v-1.81c1.79-1.03 3-2.97 3-5.19a6 6 0 00-6-6zM8 17v1a2 2 0 104 0v-1H8z" />
    </svg>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
      style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
    >
      <path
        fillRule="evenodd"
        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default HintsRenderer;

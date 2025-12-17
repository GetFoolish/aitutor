/**
 * Preview Pane
 *
 * Live preview of Athena content.
 */

import React, { useState, useCallback, useMemo, Suspense } from 'react';
import { useEditorContext } from './EditorFrame';
import type { AthenaItem, AthenaWidget } from '../core/types';

export interface PreviewPaneProps {
  /** Item to preview (optional if within EditorFrame) */
  item?: AthenaItem;
  /** Preview mode */
  mode?: 'desktop' | 'tablet' | 'mobile';
  /** Whether to show answers */
  showAnswers?: boolean;
  /** Whether in review mode */
  reviewMode?: boolean;
  /** Custom class name */
  className?: string;
  /** Custom renderer component */
  renderContent?: (item: AthenaItem) => React.ReactNode;
  /** Called when answer changes in preview */
  onAnswerChange?: (widgetId: string, answer: unknown) => void;
}

interface PreviewDevice {
  id: string;
  label: string;
  width: number;
  icon: string;
}

const PREVIEW_DEVICES: PreviewDevice[] = [
  { id: 'desktop', label: 'Desktop', width: 0, icon: 'desktop' },
  { id: 'tablet', label: 'Tablet', width: 768, icon: 'tablet' },
  { id: 'mobile', label: 'Mobile', width: 375, icon: 'mobile' },
];

/**
 * Preview pane component
 */
export function PreviewPane({
  item: propItem,
  mode = 'desktop',
  showAnswers = false,
  reviewMode = false,
  className = '',
  renderContent,
  onAnswerChange,
}: PreviewPaneProps) {
  // Try to use editor context if available
  let editorContext: ReturnType<typeof useEditorContext> | null = null;
  try {
    editorContext = useEditorContext();
  } catch {
    // Not within EditorFrame
  }

  const item = propItem ?? editorContext?.item;
  const [deviceMode, setDeviceMode] = useState<string>(mode);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [visibleHints, setVisibleHints] = useState(0);

  if (!item) {
    return (
      <div className={`athena-preview-pane athena-preview-pane--empty ${className}`}>
        <p>No content to preview</p>
      </div>
    );
  }

  const selectedDevice = PREVIEW_DEVICES.find(d => d.id === deviceMode) || PREVIEW_DEVICES[0];

  // Handle answer change
  const handleAnswerChange = useCallback((widgetId: string, answer: unknown) => {
    setAnswers(prev => ({ ...prev, [widgetId]: answer }));
    onAnswerChange?.(widgetId, answer);
  }, [onAnswerChange]);

  // Handle hint reveal
  const handleRevealHint = useCallback(() => {
    if (visibleHints < item.hints.length) {
      setVisibleHints(prev => prev + 1);
    }
  }, [item.hints.length, visibleHints]);

  // Reset preview
  const handleReset = useCallback(() => {
    setAnswers({});
    setVisibleHints(0);
  }, []);

  // Preview frame style
  const frameStyle: React.CSSProperties = selectedDevice.width > 0
    ? {
        maxWidth: selectedDevice.width,
        margin: '0 auto',
        border: '1px solid var(--athena-border-color, #e0e0e0)',
        borderRadius: '8px',
        overflow: 'hidden',
      }
    : {};

  return (
    <div className={`athena-preview-pane ${className}`}>
      {/* Preview toolbar */}
      <div className="athena-preview-toolbar">
        <div className="athena-preview-devices">
          {PREVIEW_DEVICES.map(device => (
            <button
              key={device.id}
              type="button"
              className={`athena-preview-device-btn ${deviceMode === device.id ? 'athena-preview-device-btn--active' : ''}`}
              onClick={() => setDeviceMode(device.id)}
              title={device.label}
              aria-pressed={deviceMode === device.id}
            >
              <span className={`athena-icon athena-icon--${device.icon}`} />
            </button>
          ))}
        </div>

        <div className="athena-preview-toolbar-spacer" />

        <div className="athena-preview-actions">
          <button
            type="button"
            className="athena-preview-btn"
            onClick={handleReset}
            title="Reset preview"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Preview content */}
      <div className="athena-preview-content" style={frameStyle}>
        <Suspense fallback={<PreviewLoading />}>
          {renderContent ? (
            renderContent(item)
          ) : (
            <DefaultPreviewContent
              item={item}
              answers={answers}
              onAnswerChange={handleAnswerChange}
              visibleHints={visibleHints}
              onRevealHint={handleRevealHint}
              reviewMode={reviewMode}
              showAnswers={showAnswers}
            />
          )}
        </Suspense>
      </div>

      {/* Preview info */}
      <div className="athena-preview-info">
        <span>
          {deviceMode === 'desktop' ? 'Full width' : `${selectedDevice.width}px`}
        </span>
        {Object.keys(answers).length > 0 && (
          <span>{Object.keys(answers).length} answered</span>
        )}
        {visibleHints > 0 && (
          <span>{visibleHints}/{item.hints.length} hints</span>
        )}
      </div>
    </div>
  );
}

/**
 * Loading placeholder
 */
function PreviewLoading() {
  return (
    <div className="athena-preview-loading">
      <div className="athena-preview-loading-spinner" />
      <span>Loading preview...</span>
    </div>
  );
}

/**
 * Default preview content renderer
 */
interface DefaultPreviewContentProps {
  item: AthenaItem;
  answers: Record<string, unknown>;
  onAnswerChange: (widgetId: string, answer: unknown) => void;
  visibleHints: number;
  onRevealHint: () => void;
  reviewMode: boolean;
  showAnswers: boolean;
}

function DefaultPreviewContent({
  item,
  answers,
  onAnswerChange,
  visibleHints,
  onRevealHint,
  reviewMode,
  showAnswers,
}: DefaultPreviewContentProps) {
  // Parse content and render widgets
  const renderedContent = useMemo(() => {
    return renderContentWithWidgets(
      item.question.content,
      item.question.widgets,
      answers,
      onAnswerChange,
      reviewMode,
      showAnswers
    );
  }, [item.question.content, item.question.widgets, answers, onAnswerChange, reviewMode, showAnswers]);

  return (
    <div className="athena-preview-item">
      {/* Question content */}
      <div className="athena-preview-question">
        {renderedContent}
      </div>

      {/* Hints section */}
      {item.hints.length > 0 && (
        <div className="athena-preview-hints">
          <div className="athena-preview-hints-header">
            <span>Hints ({visibleHints}/{item.hints.length})</span>
            {visibleHints < item.hints.length && (
              <button
                type="button"
                className="athena-preview-hint-btn"
                onClick={onRevealHint}
              >
                Show Hint
              </button>
            )}
          </div>

          {visibleHints > 0 && (
            <div className="athena-preview-hints-list">
              {item.hints.slice(0, visibleHints).map((hint, index) => (
                <div key={index} className="athena-preview-hint">
                  <div className="athena-preview-hint-number">Hint {index + 1}</div>
                  <div className="athena-preview-hint-content">
                    {hint.content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Render content with widget placeholders replaced
 */
function renderContentWithWidgets(
  content: string,
  widgets: Record<string, AthenaWidget>,
  answers: Record<string, unknown>,
  onAnswerChange: (widgetId: string, answer: unknown) => void,
  reviewMode: boolean,
  showAnswers: boolean
): React.ReactNode {
  if (!content) {
    return <p className="athena-preview-empty">No content</p>;
  }

  // Split content by widget placeholders
  const parts = content.split(/(\[\[☃\s*[^\]]+\]\])/g);

  return (
    <div className="athena-preview-rendered">
      {parts.map((part, index) => {
        // Check if this is a widget placeholder
        const widgetMatch = part.match(/\[\[☃\s*([^\]]+)\]\]/);
        if (widgetMatch) {
          const widgetId = widgetMatch[1].trim();
          const widget = widgets[widgetId];

          if (!widget) {
            return (
              <span key={index} className="athena-preview-widget-missing">
                [Missing widget: {widgetId}]
              </span>
            );
          }

          return (
            <PreviewWidget
              key={index}
              widgetId={widgetId}
              widget={widget}
              value={answers[widgetId]}
              onChange={(value) => onAnswerChange(widgetId, value)}
              reviewMode={reviewMode}
              showAnswer={showAnswers}
            />
          );
        }

        // Regular text content
        if (part.trim()) {
          return <PreviewText key={index} content={part} />;
        }

        return null;
      })}
    </div>
  );
}

/**
 * Preview text with basic formatting
 */
function PreviewText({ content }: { content: string }) {
  // Simple rendering - in production, use proper markdown/notation rendering
  const html = content
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\$\$([^$]+)\$\$/g, '<div class="athena-math-display">$1</div>')
    .replace(/\$([^$]+)\$/g, '<span class="athena-math-inline">$1</span>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />');

  return (
    <div
      className="athena-preview-text"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
    />
  );
}

/**
 * Preview widget placeholder
 */
interface PreviewWidgetProps {
  widgetId: string;
  widget: AthenaWidget;
  value: unknown;
  onChange: (value: unknown) => void;
  reviewMode: boolean;
  showAnswer: boolean;
}

function PreviewWidget({
  widgetId,
  widget,
  value,
  onChange,
  reviewMode,
  showAnswer,
}: PreviewWidgetProps) {
  // Cast options to any for flexible property access
  const options = widget.options as any;

  // Simple widget preview based on type
  switch (widget.type) {
    case 'numeric-input':
    case 'input-number':
      return (
        <span className="athena-preview-widget athena-preview-widget--input">
          <input
            type="text"
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter answer"
            disabled={reviewMode}
            className="athena-preview-input"
          />
          {showAnswer && options?.answers && (
            <span className="athena-preview-answer">
              Answer: {JSON.stringify(options.answers)}
            </span>
          )}
        </span>
      );

    case 'radio':
      const choices = (options?.choices || []) as Array<{ content: string; correct?: boolean }>;
      return (
        <div className="athena-preview-widget athena-preview-widget--radio">
          {choices.map((choice, i) => (
            <label key={i} className="athena-preview-radio-option">
              <input
                type={options?.multipleSelect ? 'checkbox' : 'radio'}
                name={widgetId}
                checked={Array.isArray(value) ? value.includes(i) : value === i}
                onChange={() => {
                  if (options?.multipleSelect) {
                    const current = (value as number[]) || [];
                    const newValue = current.includes(i)
                      ? current.filter(v => v !== i)
                      : [...current, i];
                    onChange(newValue);
                  } else {
                    onChange(i);
                  }
                }}
                disabled={reviewMode}
              />
              <span className={showAnswer && choice.correct ? 'athena-preview-correct' : ''}>
                {choice.content}
              </span>
            </label>
          ))}
        </div>
      );

    case 'dropdown':
      const dropdownOptions = (options?.choices || []) as string[];
      return (
        <span className="athena-preview-widget athena-preview-widget--dropdown">
          <select
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={reviewMode}
            className="athena-preview-select"
          >
            <option value="">Select...</option>
            {dropdownOptions.map((opt, i) => (
              <option key={i} value={opt}>{opt}</option>
            ))}
          </select>
        </span>
      );

    case 'expression':
      return (
        <span className="athena-preview-widget athena-preview-widget--expression">
          <input
            type="text"
            value={(value as string) || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter expression"
            disabled={reviewMode}
            className="athena-preview-input athena-preview-input--math"
          />
          {showAnswer && options?.answerForms && (
            <span className="athena-preview-answer">
              Answer: {JSON.stringify(options.answerForms)}
            </span>
          )}
        </span>
      );

    case 'image':
      const imageUrl = options?.backgroundImage?.url;
      return (
        <div className="athena-preview-widget athena-preview-widget--image">
          {imageUrl ? (
            <img src={imageUrl} alt={options?.alt || 'Image'} />
          ) : (
            <span className="athena-preview-placeholder">[Image]</span>
          )}
        </div>
      );

    case 'passage':
      return (
        <div className="athena-preview-widget athena-preview-widget--passage">
          <div className="athena-preview-passage-content">
            {options?.passageText || '[Passage content]'}
          </div>
        </div>
      );

    default:
      return (
        <span className="athena-preview-widget athena-preview-widget--unknown">
          [{widget.type}: {widgetId}]
        </span>
      );
  }
}

export default PreviewPane;

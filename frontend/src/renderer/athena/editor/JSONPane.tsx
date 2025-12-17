/**
 * JSON Pane
 *
 * Raw JSON view and editor for Athena content.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useEditorContext } from './EditorFrame';
import type { AthenaItem } from '../core/types';

export interface JSONPaneProps {
  /** Item to display (optional if within EditorFrame) */
  item?: AthenaItem;
  /** Called when JSON is edited */
  onChange?: (item: AthenaItem) => void;
  /** Whether editing is allowed */
  editable?: boolean;
  /** Custom class name */
  className?: string;
  /** Indent size for JSON formatting */
  indentSize?: number;
  /** Whether to show line numbers */
  showLineNumbers?: boolean;
  /** Whether to enable syntax highlighting */
  syntaxHighlight?: boolean;
}

/**
 * JSON pane component
 */
export function JSONPane({
  item: propItem,
  onChange,
  editable = true,
  className = '',
  indentSize = 2,
  showLineNumbers = true,
  syntaxHighlight = true,
}: JSONPaneProps) {
  // Try to use editor context if available
  let editorContext: ReturnType<typeof useEditorContext> | null = null;
  try {
    editorContext = useEditorContext();
  } catch {
    // Not within EditorFrame
  }

  const item = propItem ?? editorContext?.item;
  const handleChange = onChange ?? editorContext?.updateItem;

  const [jsonText, setJsonText] = useState('');
  const [parseError, setParseError] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  // Format JSON
  useEffect(() => {
    if (item && !isDirty) {
      try {
        setJsonText(JSON.stringify(item, null, indentSize));
        setParseError(null);
      } catch (err) {
        setParseError('Failed to stringify item');
      }
    }
  }, [item, indentSize, isDirty]);

  // Handle text change
  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setJsonText(text);
    setIsDirty(true);

    // Validate JSON
    try {
      JSON.parse(text);
      setParseError(null);
    } catch (err) {
      setParseError((err as Error).message);
    }
  }, []);

  // Apply changes
  const handleApply = useCallback(() => {
    if (parseError) return;

    try {
      const parsed = JSON.parse(jsonText) as AthenaItem;
      handleChange?.(parsed);
      setIsDirty(false);
    } catch (err) {
      setParseError((err as Error).message);
    }
  }, [jsonText, parseError, handleChange]);

  // Reset changes
  const handleReset = useCallback(() => {
    if (item) {
      setJsonText(JSON.stringify(item, null, indentSize));
      setParseError(null);
      setIsDirty(false);
    }
  }, [item, indentSize]);

  // Format JSON
  const handleFormat = useCallback(() => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, indentSize));
      setParseError(null);
    } catch (err) {
      setParseError((err as Error).message);
    }
  }, [jsonText, indentSize]);

  // Copy to clipboard
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(jsonText);
  }, [jsonText]);

  // Minify JSON
  const handleMinify = useCallback(() => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed));
      setParseError(null);
    } catch (err) {
      setParseError((err as Error).message);
    }
  }, [jsonText]);

  // Sync scroll for line numbers
  const handleScroll = useCallback(() => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }, []);

  // Count lines
  const lineCount = jsonText.split('\n').length;

  // Syntax highlight (simple implementation)
  const highlightedContent = syntaxHighlight
    ? highlightJSON(jsonText)
    : jsonText;

  if (!item) {
    return (
      <div className={`athena-json-pane athena-json-pane--empty ${className}`}>
        <p>No item to display</p>
      </div>
    );
  }

  return (
    <div className={`athena-json-pane ${className}`}>
      {/* Toolbar */}
      <div className="athena-json-toolbar">
        <div className="athena-json-toolbar-left">
          <button
            type="button"
            className="athena-json-btn"
            onClick={handleFormat}
            title="Format JSON"
          >
            Format
          </button>
          <button
            type="button"
            className="athena-json-btn"
            onClick={handleMinify}
            title="Minify JSON"
          >
            Minify
          </button>
          <button
            type="button"
            className="athena-json-btn"
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            Copy
          </button>
        </div>

        <div className="athena-json-toolbar-right">
          {editable && isDirty && (
            <>
              <button
                type="button"
                className="athena-json-btn athena-json-btn--secondary"
                onClick={handleReset}
              >
                Reset
              </button>
              <button
                type="button"
                className="athena-json-btn athena-json-btn--primary"
                onClick={handleApply}
                disabled={!!parseError}
              >
                Apply
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error display */}
      {parseError && (
        <div className="athena-json-error">
          <span className="athena-json-error-icon">⚠️</span>
          <span className="athena-json-error-message">{parseError}</span>
        </div>
      )}

      {/* Editor */}
      <div className="athena-json-editor">
        {showLineNumbers && (
          <div
            ref={lineNumbersRef}
            className="athena-json-line-numbers"
            aria-hidden="true"
          >
            {Array.from({ length: lineCount }, (_, i) => (
              <div key={i} className="athena-json-line-number">
                {i + 1}
              </div>
            ))}
          </div>
        )}

        <div className="athena-json-content">
          <textarea
            ref={textareaRef}
            className="athena-json-textarea"
            value={jsonText}
            onChange={handleTextChange}
            onScroll={handleScroll}
            readOnly={!editable}
            spellCheck={false}
            aria-label="JSON editor"
          />
          {syntaxHighlight && (
            <div
              className="athena-json-highlight"
              dangerouslySetInnerHTML={{ __html: highlightedContent }}
              aria-hidden="true"
            />
          )}
        </div>
      </div>

      {/* Status */}
      <div className="athena-json-status">
        <span>{jsonText.length} characters</span>
        <span>{lineCount} lines</span>
        {isDirty && <span className="athena-json-status-dirty">Modified</span>}
        {!parseError && <span className="athena-json-status-valid">Valid JSON</span>}
      </div>
    </div>
  );
}

/**
 * Simple JSON syntax highlighting
 */
function highlightJSON(json: string): string {
  return json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Strings
    .replace(/"([^"\\]|\\.)*"/g, '<span class="athena-json-string">"$&"</span>')
    // Fix: strings already have quotes, remove duplicate
    .replace(/"<span class="athena-json-string">"([^"]*)"<\/span>"/g, '<span class="athena-json-string">"$1"</span>')
    // Numbers
    .replace(/\b(-?\d+\.?\d*)\b/g, '<span class="athena-json-number">$1</span>')
    // Booleans and null
    .replace(/\b(true|false|null)\b/g, '<span class="athena-json-keyword">$1</span>')
    // Keys (property names)
    .replace(/"([^"]+)":/g, '<span class="athena-json-key">"$1"</span>:');
}

export default JSONPane;

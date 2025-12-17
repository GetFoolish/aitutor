/**
 * Content Editor
 *
 * WYSIWYG content editor with markdown and notation support.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useEditorContext } from './EditorFrame';
import type { AthenaWidget } from '../core/types';

export interface ContentEditorProps {
  /** Initial content */
  content?: string;
  /** Called when content changes */
  onChange?: (content: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether editor is disabled */
  disabled?: boolean;
  /** Minimum height */
  minHeight?: number;
  /** Custom class name */
  className?: string;
  /** Available widgets to insert */
  widgets?: Record<string, AthenaWidget>;
  /** Callback to insert widget */
  onInsertWidget?: (widgetId: string) => void;
}

interface EditorSelection {
  start: number;
  end: number;
  text: string;
}

export interface ContentEditorRef {
  /** Insert text at cursor */
  insertText: (text: string) => void;
  /** Insert widget placeholder at cursor */
  insertWidget: (widgetId: string) => void;
  /** Get current selection */
  getSelection: () => EditorSelection | null;
  /** Set selection */
  setSelection: (start: number, end: number) => void;
  /** Focus editor */
  focus: () => void;
  /** Get content */
  getContent: () => string;
  /** Set content */
  setContent: (content: string) => void;
}

/**
 * Content editor component
 */
export const ContentEditor = React.forwardRef<ContentEditorRef, ContentEditorProps>(
  function ContentEditor(
    {
      content: propContent,
      onChange,
      placeholder = 'Start writing your content here...\n\nUse **bold** and *italic* for formatting.\nUse $math$ for inline equations and $$display math$$ for block equations.',
      disabled = false,
      minHeight = 300,
      className = '',
      widgets = {},
      onInsertWidget,
    },
    ref
  ) {
    // Try to use editor context if available
    let editorContext: ReturnType<typeof useEditorContext> | null = null;
    try {
      editorContext = useEditorContext();
    } catch {
      // Not within EditorFrame, use props
    }

    const content = propContent ?? editorContext?.item.question.content ?? '';
    const handleChange = onChange ?? editorContext?.onContentChange;

    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [isFocused, setIsFocused] = useState(false);
    const [showWidgetMenu, setShowWidgetMenu] = useState(false);
    const [showFormatMenu, setShowFormatMenu] = useState(false);

    // Expose ref methods
    React.useImperativeHandle(ref, () => ({
      insertText: (text: string) => {
        if (!textareaRef.current) return;
        const { selectionStart, selectionEnd } = textareaRef.current;
        const before = content.substring(0, selectionStart);
        const after = content.substring(selectionEnd);
        const newContent = before + text + after;
        handleChange?.(newContent);
        // Set cursor after inserted text
        setTimeout(() => {
          textareaRef.current?.setSelectionRange(
            selectionStart + text.length,
            selectionStart + text.length
          );
          textareaRef.current?.focus();
        }, 0);
      },
      insertWidget: (widgetId: string) => {
        if (!textareaRef.current) return;
        const placeholder = `[[☃ ${widgetId}]]`;
        const { selectionStart, selectionEnd } = textareaRef.current;
        const before = content.substring(0, selectionStart);
        const after = content.substring(selectionEnd);
        const newContent = before + placeholder + after;
        handleChange?.(newContent);
        onInsertWidget?.(widgetId);
      },
      getSelection: () => {
        if (!textareaRef.current) return null;
        const { selectionStart, selectionEnd } = textareaRef.current;
        return {
          start: selectionStart,
          end: selectionEnd,
          text: content.substring(selectionStart, selectionEnd),
        };
      },
      setSelection: (start: number, end: number) => {
        textareaRef.current?.setSelectionRange(start, end);
        textareaRef.current?.focus();
      },
      focus: () => textareaRef.current?.focus(),
      getContent: () => content,
      setContent: (newContent: string) => handleChange?.(newContent),
    }), [content, handleChange, onInsertWidget]);

    // Handle text change
    const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
      handleChange?.(e.target.value);
    }, [handleChange]);

    // Format helpers
    const wrapSelection = useCallback((prefix: string, suffix: string) => {
      if (!textareaRef.current) return;
      const { selectionStart, selectionEnd } = textareaRef.current;
      const selectedText = content.substring(selectionStart, selectionEnd);
      const before = content.substring(0, selectionStart);
      const after = content.substring(selectionEnd);
      const newContent = before + prefix + selectedText + suffix + after;
      handleChange?.(newContent);
      // Select the wrapped text
      setTimeout(() => {
        textareaRef.current?.setSelectionRange(
          selectionStart + prefix.length,
          selectionEnd + prefix.length
        );
        textareaRef.current?.focus();
      }, 0);
    }, [content, handleChange]);

    // Formatting actions
    const formatActions = {
      bold: () => wrapSelection('**', '**'),
      italic: () => wrapSelection('*', '*'),
      code: () => wrapSelection('`', '`'),
      inlineMath: () => wrapSelection('$', '$'),
      displayMath: () => wrapSelection('\n$$\n', '\n$$\n'),
      link: () => wrapSelection('[', '](url)'),
      heading: () => wrapSelection('\n## ', '\n'),
      bullet: () => wrapSelection('\n- ', ''),
      numbered: () => wrapSelection('\n1. ', ''),
    };

    // Handle keyboard shortcuts
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'b':
            e.preventDefault();
            formatActions.bold();
            break;
          case 'i':
            e.preventDefault();
            formatActions.italic();
            break;
          case 'k':
            e.preventDefault();
            formatActions.link();
            break;
          case 'm':
            e.preventDefault();
            formatActions.inlineMath();
            break;
        }
      }
      // Tab handling
      if (e.key === 'Tab') {
        e.preventDefault();
        const { selectionStart, selectionEnd } = textareaRef.current!;
        const before = content.substring(0, selectionStart);
        const after = content.substring(selectionEnd);
        const newContent = before + '  ' + after;
        handleChange?.(newContent);
        setTimeout(() => {
          textareaRef.current?.setSelectionRange(selectionStart + 2, selectionStart + 2);
        }, 0);
      }
    }, [content, handleChange, formatActions]);

    // Auto-resize textarea
    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.max(minHeight, textareaRef.current.scrollHeight)}px`;
      }
    }, [content, minHeight]);

    // Count widgets in content
    const widgetPlaceholders = content.match(/\[\[☃\s*[^\]]+\]\]/g) || [];

    return (
      <div className={`athena-content-editor ${className} ${isFocused ? 'athena-content-editor--focused' : ''}`}>
        {/* Formatting toolbar */}
        <div className="athena-content-editor-toolbar">
          <div className="athena-content-editor-toolbar-group">
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.bold}
              title="Bold (Ctrl+B)"
              aria-label="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.italic}
              title="Italic (Ctrl+I)"
              aria-label="Italic"
            >
              <em>I</em>
            </button>
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.code}
              title="Code"
              aria-label="Code"
            >
              {'</>'}
            </button>
          </div>

          <div className="athena-content-editor-toolbar-divider" />

          <div className="athena-content-editor-toolbar-group">
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.inlineMath}
              title="Inline math (Ctrl+M)"
              aria-label="Inline math"
            >
              $x$
            </button>
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.displayMath}
              title="Display math"
              aria-label="Display math"
            >
              $$
            </button>
          </div>

          <div className="athena-content-editor-toolbar-divider" />

          <div className="athena-content-editor-toolbar-group">
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.heading}
              title="Heading"
              aria-label="Heading"
            >
              H
            </button>
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.bullet}
              title="Bullet list"
              aria-label="Bullet list"
            >
              •
            </button>
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.numbered}
              title="Numbered list"
              aria-label="Numbered list"
            >
              1.
            </button>
          </div>

          <div className="athena-content-editor-toolbar-divider" />

          <div className="athena-content-editor-toolbar-group">
            <button
              type="button"
              className="athena-content-editor-btn"
              onClick={formatActions.link}
              title="Link (Ctrl+K)"
              aria-label="Insert link"
            >
              🔗
            </button>
          </div>

          <div className="athena-content-editor-toolbar-spacer" />

          {/* Widget insertion */}
          <div className="athena-content-editor-toolbar-group">
            <div className="athena-content-editor-dropdown">
              <button
                type="button"
                className="athena-content-editor-btn athena-content-editor-btn--dropdown"
                onClick={() => setShowWidgetMenu(!showWidgetMenu)}
                aria-expanded={showWidgetMenu}
                aria-haspopup="menu"
              >
                + Widget
              </button>
              {showWidgetMenu && (
                <div className="athena-content-editor-dropdown-menu" role="menu">
                  {Object.entries(widgets).length === 0 ? (
                    <div className="athena-content-editor-dropdown-empty">
                      No widgets available
                    </div>
                  ) : (
                    Object.entries(widgets).map(([id, widget]) => (
                      <button
                        key={id}
                        type="button"
                        className="athena-content-editor-dropdown-item"
                        role="menuitem"
                        onClick={() => {
                          const placeholder = `[[☃ ${id}]]`;
                          if (textareaRef.current) {
                            const { selectionStart, selectionEnd } = textareaRef.current;
                            const before = content.substring(0, selectionStart);
                            const after = content.substring(selectionEnd);
                            handleChange?.(before + placeholder + after);
                          }
                          setShowWidgetMenu(false);
                        }}
                      >
                        <span className="athena-content-editor-dropdown-item-label">
                          {id}
                        </span>
                        <span className="athena-content-editor-dropdown-item-type">
                          {widget.type}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main editor */}
        <div className="athena-content-editor-main">
          <textarea
            ref={textareaRef}
            className="athena-content-editor-textarea"
            value={content}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            spellCheck
            style={{ minHeight }}
            aria-label="Content editor"
          />
        </div>

        {/* Status bar */}
        <div className="athena-content-editor-status">
          <span>{content.length} characters</span>
          <span>{content.split(/\s+/).filter(Boolean).length} words</span>
          <span>{widgetPlaceholders.length} widgets</span>
        </div>
      </div>
    );
  }
);

export default ContentEditor;

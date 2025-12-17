/**
 * Hint Editor
 *
 * Component for editing hints with widgets.
 */

import React, { useState, useCallback } from 'react';
import { useEditorContext } from './EditorFrame';
import type { AthenaHint, AthenaWidget } from '../core/types';

export interface HintEditorProps {
  /** Hints to edit (optional if within EditorFrame) */
  hints?: AthenaHint[];
  /** Called when hints change */
  onChange?: (hints: AthenaHint[]) => void;
  /** Maximum number of hints allowed */
  maxHints?: number;
  /** Custom class name */
  className?: string;
}

/**
 * Hint editor component
 */
export function HintEditor({
  hints: propHints,
  onChange,
  maxHints = 10,
  className = '',
}: HintEditorProps) {
  // Try to use editor context
  let editorContext: ReturnType<typeof useEditorContext> | null = null;
  try {
    editorContext = useEditorContext();
  } catch {
    // Not within EditorFrame
  }

  const hints = propHints ?? editorContext?.item.hints ?? [];
  const handleChange = onChange ?? editorContext?.onHintsChange;

  const [expandedIndex, setExpandedIndex] = useState<number | null>(
    hints.length > 0 ? 0 : null
  );
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  // Add new hint
  const handleAddHint = useCallback(() => {
    if (hints.length >= maxHints) return;

    const newHint: AthenaHint = {
      content: '',
      widgets: {},
      images: {},
    };

    const newHints = [...hints, newHint];
    handleChange?.(newHints);
    setExpandedIndex(newHints.length - 1);
  }, [hints, maxHints, handleChange]);

  // Update hint
  const handleUpdateHint = useCallback((index: number, updates: Partial<AthenaHint>) => {
    const newHints = hints.map((hint, i) =>
      i === index ? { ...hint, ...updates } : hint
    );
    handleChange?.(newHints);
  }, [hints, handleChange]);

  // Delete hint
  const handleDeleteHint = useCallback((index: number) => {
    const newHints = hints.filter((_, i) => i !== index);
    handleChange?.(newHints);
    if (expandedIndex === index) {
      setExpandedIndex(null);
    } else if (expandedIndex !== null && expandedIndex > index) {
      setExpandedIndex(expandedIndex - 1);
    }
  }, [hints, expandedIndex, handleChange]);

  // Move hint up
  const handleMoveUp = useCallback((index: number) => {
    if (index === 0) return;
    const newHints = [...hints];
    [newHints[index - 1], newHints[index]] = [newHints[index], newHints[index - 1]];
    handleChange?.(newHints);
    setExpandedIndex(index - 1);
  }, [hints, handleChange]);

  // Move hint down
  const handleMoveDown = useCallback((index: number) => {
    if (index === hints.length - 1) return;
    const newHints = [...hints];
    [newHints[index], newHints[index + 1]] = [newHints[index + 1], newHints[index]];
    handleChange?.(newHints);
    setExpandedIndex(index + 1);
  }, [hints, handleChange]);

  // Duplicate hint
  const handleDuplicate = useCallback((index: number) => {
    if (hints.length >= maxHints) return;

    const newHint: AthenaHint = {
      ...hints[index],
      widgets: { ...hints[index].widgets },
      images: { ...hints[index].images },
    };

    const newHints = [...hints.slice(0, index + 1), newHint, ...hints.slice(index + 1)];
    handleChange?.(newHints);
    setExpandedIndex(index + 1);
  }, [hints, maxHints, handleChange]);

  // Drag and drop handlers
  const handleDragStart = useCallback((index: number) => {
    setDraggedIndex(index);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
  }, [draggedIndex]);

  const handleDrop = useCallback((e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === targetIndex) return;

    const newHints = [...hints];
    const [removed] = newHints.splice(draggedIndex, 1);
    newHints.splice(targetIndex, 0, removed);

    handleChange?.(newHints);
    setExpandedIndex(targetIndex);
    setDraggedIndex(null);
  }, [hints, draggedIndex, handleChange]);

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
  }, []);

  return (
    <div className={`athena-hint-editor ${className}`}>
      {/* Header */}
      <div className="athena-hint-editor-header">
        <h3>Hints ({hints.length}/{maxHints})</h3>
        <button
          type="button"
          className="athena-hint-editor-add-btn"
          onClick={handleAddHint}
          disabled={hints.length >= maxHints}
        >
          + Add Hint
        </button>
      </div>

      {/* Hint list */}
      {hints.length === 0 ? (
        <div className="athena-hint-editor-empty">
          <p>No hints yet. Click "Add Hint" to create one.</p>
          <p className="athena-hint-editor-empty-help">
            Hints are revealed progressively to help students who are stuck.
          </p>
        </div>
      ) : (
        <div className="athena-hint-editor-list">
          {hints.map((hint, index) => (
            <HintEditorItem
              key={index}
              hint={hint}
              index={index}
              isExpanded={expandedIndex === index}
              isDragging={draggedIndex === index}
              onToggle={() => setExpandedIndex(expandedIndex === index ? null : index)}
              onChange={(updates) => handleUpdateHint(index, updates)}
              onDelete={() => handleDeleteHint(index)}
              onMoveUp={() => handleMoveUp(index)}
              onMoveDown={() => handleMoveDown(index)}
              onDuplicate={() => handleDuplicate(index)}
              canMoveUp={index > 0}
              canMoveDown={index < hints.length - 1}
              canDuplicate={hints.length < maxHints}
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
            />
          ))}
        </div>
      )}

      {/* Help text */}
      <div className="athena-hint-editor-help">
        <p>
          <strong>Tips:</strong> Use Markdown for formatting. Add widget placeholders
          like <code>[[☃ widget-id]]</code> to include interactive elements in hints.
        </p>
      </div>
    </div>
  );
}

/**
 * Individual hint editor item
 */
interface HintEditorItemProps {
  hint: AthenaHint;
  index: number;
  isExpanded: boolean;
  isDragging: boolean;
  onToggle: () => void;
  onChange: (updates: Partial<AthenaHint>) => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDuplicate: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
  canDuplicate: boolean;
  onDragStart: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onDragEnd: () => void;
}

function HintEditorItem({
  hint,
  index,
  isExpanded,
  isDragging,
  onToggle,
  onChange,
  onDelete,
  onMoveUp,
  onMoveDown,
  onDuplicate,
  canMoveUp,
  canMoveDown,
  canDuplicate,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: HintEditorItemProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Handle content change
  const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ content: e.target.value });
  }, [onChange]);

  // Handle delete with confirmation
  const handleDelete = useCallback(() => {
    if (hint.content.trim() || Object.keys(hint.widgets).length > 0) {
      setShowDeleteConfirm(true);
    } else {
      onDelete();
    }
  }, [hint.content, hint.widgets, onDelete]);

  // Preview text
  const previewText = hint.content
    ? hint.content.substring(0, 50) + (hint.content.length > 50 ? '...' : '')
    : '(empty hint)';

  return (
    <div
      className={`athena-hint-editor-item ${isExpanded ? 'athena-hint-editor-item--expanded' : ''} ${isDragging ? 'athena-hint-editor-item--dragging' : ''}`}
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
    >
      {/* Header */}
      <div className="athena-hint-editor-item-header">
        <button
          type="button"
          className="athena-hint-editor-item-drag"
          aria-label="Drag to reorder"
        >
          ⋮⋮
        </button>

        <button
          type="button"
          className="athena-hint-editor-item-toggle"
          onClick={onToggle}
          aria-expanded={isExpanded}
        >
          <span className="athena-hint-editor-item-number">Hint {index + 1}</span>
          {!isExpanded && (
            <span className="athena-hint-editor-item-preview">{previewText}</span>
          )}
          <span className={`athena-hint-editor-item-arrow ${isExpanded ? 'athena-hint-editor-item-arrow--open' : ''}`}>
            ▼
          </span>
        </button>

        <div className="athena-hint-editor-item-actions">
          <button
            type="button"
            className="athena-hint-editor-item-btn"
            onClick={onMoveUp}
            disabled={!canMoveUp}
            title="Move up"
            aria-label="Move hint up"
          >
            ↑
          </button>
          <button
            type="button"
            className="athena-hint-editor-item-btn"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            title="Move down"
            aria-label="Move hint down"
          >
            ↓
          </button>
          <button
            type="button"
            className="athena-hint-editor-item-btn"
            onClick={onDuplicate}
            disabled={!canDuplicate}
            title="Duplicate"
            aria-label="Duplicate hint"
          >
            ⧉
          </button>
          <button
            type="button"
            className="athena-hint-editor-item-btn athena-hint-editor-item-btn--danger"
            onClick={handleDelete}
            title="Delete"
            aria-label="Delete hint"
          >
            ×
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="athena-hint-editor-item-content">
          <label className="athena-hint-editor-label">
            Hint Content
            <textarea
              className="athena-hint-editor-textarea"
              value={hint.content}
              onChange={handleContentChange}
              placeholder="Enter hint content... Use Markdown for formatting."
              rows={6}
            />
          </label>

          {/* Widget count */}
          {Object.keys(hint.widgets).length > 0 && (
            <div className="athena-hint-editor-widgets">
              <span>
                {Object.keys(hint.widgets).length} widget(s) in this hint
              </span>
            </div>
          )}
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="athena-hint-editor-confirm">
          <p>Delete this hint?</p>
          <div className="athena-hint-editor-confirm-actions">
            <button
              type="button"
              className="athena-hint-editor-btn athena-hint-editor-btn--secondary"
              onClick={() => setShowDeleteConfirm(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="athena-hint-editor-btn athena-hint-editor-btn--danger"
              onClick={() => {
                setShowDeleteConfirm(false);
                onDelete();
              }}
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default HintEditor;

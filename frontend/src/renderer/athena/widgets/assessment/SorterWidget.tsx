/**
 * Sorter Widget
 *
 * Drag-and-drop reordering widget.
 * Users arrange items in the correct order.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { SorterOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';

// Load KaTeX dynamically
let katexModule: any = null;
async function ensureKaTeX() {
  if (katexModule) return katexModule;
  try {
    const module = await import('katex');
    katexModule = module.default || module;
    return katexModule;
  } catch {
    return null;
  }
}

export interface SorterWidgetProps extends WidgetProps<SorterOptions> {}

interface DragState {
  isDragging: boolean;
  dragIndex: number | null;
  dropIndex: number | null;
}

export function SorterWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: SorterWidgetProps) {
  const options = widget.options || {};

  // Load KaTeX
  const [katex, setKatex] = useState<any>(null);
  useEffect(() => {
    ensureKaTeX().then(k => setKatex(k));
  }, []);

  // Render content with math and image support
  const renderContent = useCallback((content: string): string => {
    if (!content) return '';
    let processed = content;

    // 1. Handle markdown images ![alt](url) - convert to <img> with web+graphie support
    // Use PNG for graphie images because PNG has labels baked in
    processed = processed.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
      let imageUrl = url;
      // Convert web+graphie:// URLs to https:// with PNG extension
      if (imageUrl.startsWith('web+graphie://')) {
        imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
      }
      return `<img src="${imageUrl}" alt="${alt}" style="max-width:100%;height:auto;display:block;margin:0.5rem 0;" onerror="if(this.src.endsWith('.png')){this.src=this.src.replace('.png','.svg')}else if(this.src.endsWith('.svg')){this.src=this.src.replace('.svg','.png')}" />`;
    });

    // 2. Handle display math $$...$$
    processed = processed.replace(/\$\$([^$]+)\$\$/g, (_, math) => {
      try {
        if (katex) {
          return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
        }
        return `<span class="athena-math-display">${math}</span>`;
      } catch {
        return `<span class="athena-math-display">${math}</span>`;
      }
    });

    // 3. Handle inline math $...$
    processed = processed.replace(/\$([^$\n]+)\$/g, (_, math) => {
      try {
        if (katex) {
          return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
        }
        return `<span class="athena-math-inline">${math}</span>`;
      } catch {
        return `<span class="athena-math-inline">${math}</span>`;
      }
    });

    // 4. Handle bold/italic
    processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    return processed;
  }, [katex]);

  // Handle both sorter format (correct, choices) and orderer format (correctOptions, otherOptions)
  const getCorrectOrder = (): string[] => {
    if (Array.isArray(options.correct)) return options.correct;
    if (Array.isArray(options.correctOptions)) {
      // Orderer format: correctOptions is array of {content: string} objects
      return options.correctOptions.map((opt: any) =>
        typeof opt === 'string' ? opt : (opt.content || opt.text || String(opt))
      );
    }
    return [];
  };

  const getInitialItems = (): string[] => {
    if (Array.isArray(options.choices)) return options.choices;

    // Orderer format: combine correctOptions and otherOptions
    const correctOpts = Array.isArray(options.correctOptions)
      ? options.correctOptions.map((opt: any) =>
          typeof opt === 'string' ? opt : (opt.content || opt.text || String(opt))
        )
      : [];
    const otherOpts = Array.isArray(options.otherOptions)
      ? options.otherOptions.map((opt: any) =>
          typeof opt === 'string' ? opt : (opt.content || opt.text || String(opt))
        )
      : [];

    return [...correctOpts, ...otherOpts];
  };

  const correctOrder = getCorrectOrder();
  const initialItems = getInitialItems().length > 0 ? getInitialItems() : correctOrder;

  // Shuffle items for initial state if not already provided
  const getInitialOrder = (): string[] => {
    if (value && Array.isArray(value)) {
      return value as string[];
    }
    // Shuffle the items
    const shuffled = [...initialItems];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  const [items, setItems] = useState<string[]>(getInitialOrder);
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dragIndex: null,
    dropIndex: null,
  });

  const dragItem = useRef<number | null>(null);
  const dragOverItem = useRef<number | null>(null);

  const isDisabled = readOnly || disabled;

  const handleDragStart = useCallback(
    (index: number) => {
      if (isDisabled) return;
      dragItem.current = index;
      setDragState({
        isDragging: true,
        dragIndex: index,
        dropIndex: null,
      });
    },
    [isDisabled]
  );

  const handleDragEnter = useCallback(
    (index: number) => {
      if (isDisabled) return;
      dragOverItem.current = index;
      setDragState((prev) => ({
        ...prev,
        dropIndex: index,
      }));
    },
    [isDisabled]
  );

  const handleDragEnd = useCallback(() => {
    if (isDisabled) return;
    if (dragItem.current !== null && dragOverItem.current !== null) {
      const newItems = [...items];
      const draggedItem = newItems[dragItem.current];

      // Remove from old position
      newItems.splice(dragItem.current, 1);
      // Insert at new position
      newItems.splice(dragOverItem.current, 0, draggedItem);

      setItems(newItems);
      onChange?.(newItems);
    }

    dragItem.current = null;
    dragOverItem.current = null;
    setDragState({
      isDragging: false,
      dragIndex: null,
      dropIndex: null,
    });
  }, [isDisabled, items, onChange]);

  // Keyboard navigation (Left/Right for horizontal layout)
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      if (isDisabled) return;

      if ((e.key === 'ArrowLeft' || e.key === 'ArrowUp') && index > 0) {
        e.preventDefault();
        const newItems = [...items];
        [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];
        setItems(newItems);
        onChange?.(newItems);
      } else if ((e.key === 'ArrowRight' || e.key === 'ArrowDown') && index < items.length - 1) {
        e.preventDefault();
        const newItems = [...items];
        [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];
        setItems(newItems);
        onChange?.(newItems);
      }
    },
    [isDisabled, items, onChange]
  );

  // Check if an item is in the correct position (for review mode)
  const isCorrectPosition = (item: string, index: number): boolean => {
    return correctOrder[index] === item;
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      itemBg: '#f8f9fa',
      border: '#e0e0e0',
      text: '#333',
      dragBg: '#e3f2fd',
      correct: '#e8f5e9',
      incorrect: '#ffebee',
    },
    dark: {
      bg: '#2d2d2d',
      itemBg: '#3d3d3d',
      border: '#4d4d4d',
      text: '#fff',
      dragBg: '#1e3a5f',
      correct: '#1b5e20',
      incorrect: '#b71c1c',
    },
    'high-contrast': {
      bg: '#000',
      itemBg: '#222',
      border: '#fff',
      text: '#fff',
      dragBg: '#333',
      correct: '#0f0',
      incorrect: '#f00',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="sorter">
      <div className="athena-sorter-container">
        {options.title && (
          <div
            className="athena-sorter-title"
            style={{
              marginBottom: '12px',
              fontWeight: 600,
              color: themeStyles.text,
            }}
          >
            {options.title}
          </div>
        )}

        <div
          className="athena-sorter-instructions"
          style={{
            marginBottom: '12px',
            fontSize: '14px',
            color: '#666',
          }}
        >
          {isDisabled
            ? 'Items arranged in order:'
            : 'Drag items to arrange them in the correct order (or use arrow keys)'}
        </div>

        <div
          className="athena-sorter-list"
          role="listbox"
          aria-label="Sortable items"
          style={{
            display: 'flex',
            flexDirection: 'row',
            flexWrap: 'wrap',
            gap: '8px',
            padding: 0,
            margin: 0,
          }}
        >
          {items.map((item, index) => {
            const isDragging = dragState.dragIndex === index;
            const isDropTarget = dragState.dropIndex === index;
            const correct = reviewMode && isCorrectPosition(item, index);
            const incorrect = reviewMode && !isCorrectPosition(item, index);

            let itemBg = themeStyles.itemBg;
            let borderColor = themeStyles.border;
            if (isDragging) {
              itemBg = themeStyles.dragBg;
              borderColor = '#2196f3';
            }
            if (isDropTarget) borderColor = '#2196f3';
            if (correct) {
              itemBg = themeStyles.correct;
              borderColor = '#4caf50';
            }
            if (incorrect) {
              itemBg = themeStyles.incorrect;
              borderColor = '#f44336';
            }

            return (
              <div
                key={`${item}-${index}`}
                role="option"
                aria-selected={isDragging}
                draggable={!isDisabled}
                onDragStart={() => handleDragStart(index)}
                onDragEnter={() => handleDragEnter(index)}
                onDragEnd={handleDragEnd}
                onDragOver={(e) => e.preventDefault()}
                onKeyDown={(e) => handleKeyDown(e, index)}
                tabIndex={isDisabled ? -1 : 0}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '12px 20px',
                  backgroundColor: itemBg,
                  border: `2px solid ${borderColor}`,
                  borderRadius: '4px',
                  cursor: isDisabled ? 'default' : 'ew-resize',
                  opacity: isDragging ? 0.5 : 1,
                  transition: 'all 0.15s ease',
                  color: themeStyles.text,
                  fontSize: '16px',
                  fontWeight: 500,
                  minWidth: '48px',
                  textAlign: 'center',
                  userSelect: 'none',
                  boxShadow: isDragging ? '0 4px 12px rgba(0,0,0,0.15)' : '0 1px 3px rgba(0,0,0,0.08)',
                  transform: isDragging ? 'scale(1.05)' : 'scale(1)',
                }}
              >
                {/* Item content */}
                <span dangerouslySetInnerHTML={{ __html: renderContent(item) }} />

                {/* Review mode indicators */}
                {reviewMode && (
                  <span style={{ marginLeft: '8px', display: 'flex', alignItems: 'center' }}>
                    {correct ? (
                      <CheckIcon style={{ color: '#4caf50', width: 18, height: 18 }} />
                    ) : (
                      <CrossIcon style={{ color: '#f44336', width: 18, height: 18 }} />
                    )}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

function DragHandleIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M11 18c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2zm-2-8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm6 4c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
    </svg>
  );
}

function CheckIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
    </svg>
  );
}

function CrossIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
    </svg>
  );
}

export default SorterWidget;

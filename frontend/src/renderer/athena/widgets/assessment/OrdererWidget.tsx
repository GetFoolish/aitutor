/**
 * Orderer Widget
 *
 * Drag-and-drop widget where users select cards from available options
 * and arrange them in a specific order. Unlike Sorter, not all cards need to be used.
 */

import React, { useState, useCallback, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
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

interface OrdererOptionItem {
  content: string;
  images?: Record<string, unknown>;
  widgets?: Record<string, unknown>;
}

interface OrdererOptions {
  options?: OrdererOptionItem[];
  correctOptions?: OrdererOptionItem[];
  otherOptions?: OrdererOptionItem[];
  layout?: 'horizontal' | 'vertical';
  height?: 'normal' | 'auto';
  infinite?: boolean;
}

export interface OrdererWidgetProps extends WidgetProps<OrdererOptions> { }

export function OrdererWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: OrdererWidgetProps) {
  const options = widget?.options || {};

  // Load KaTeX
  const [katex, setKatex] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    ensureKaTeX().then(k => setKatex(k));
  }, []);

  // Render content with math and image support
  const renderContent = useCallback((content: string): string => {
    if (!content) return '';
    let processed = content;

    try {
      // 1. Handle markdown images ![alt](url)
      processed = processed.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
        let imageUrl = url;
        // Convert web+graphie:// URLs to https:// with PNG extension
        // This ensures compatibility with Perseus assets
        if (imageUrl.startsWith('web+graphie://')) {
          imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
        }

        return `<img src="${imageUrl}" alt="${alt}" style="max-width:100%;max-height:80px;height:auto;display:block;margin:4px auto;" onerror="if(this.src.endsWith('.png')){this.src=this.src.replace('.png','.svg')}else if(this.src.endsWith('.svg')){this.src=this.src.replace('.svg','.png')}" />`;
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
    } catch (e) {
      console.error('Error rendering content:', e);
      return content;
    }
  }, [katex]);

  // Extract content string from option item
  const getContentString = (item: OrdererOptionItem | string): string => {
    if (typeof item === 'string') return item;
    if (item && typeof item === 'object' && 'content' in item) {
      return item.content || '';
    }
    return String(item || '');
  };

  // Get available cards
  const getAvailableCards = (): string[] => {
    try {
      if (Array.isArray(options.options) && options.options.length > 0) {
        return options.options.map(getContentString);
      }
      // Fallback: combine correctOptions and otherOptions
      const correct = (options.correctOptions || []).map(getContentString);
      const other = (options.otherOptions || []).map(getContentString);
      return [...correct, ...other];
    } catch (e) {
      console.error('Error getting available cards:', e);
      return [];
    }
  };

  // Get correct sequence
  const getCorrectSequence = (): string[] => {
    try {
      if (Array.isArray(options.correctOptions)) {
        return options.correctOptions.map(getContentString);
      }
      return [];
    } catch (e) {
      console.error('Error getting correct sequence:', e);
      return [];
    }
  };

  const allCards = getAvailableCards();
  const correctSequence = getCorrectSequence();
  const isHorizontal = options.layout === 'horizontal';
  const isDisabled = readOnly || disabled;

  // State: which cards are in the answer area and which are available
  const [selectedCards, setSelectedCards] = useState<string[]>(() => {
    if (value && Array.isArray(value)) {
      return value as string[];
    }
    return [];
  });

  // Compute available cards (not yet selected)
  // If "infinite" option is enabled, available cards are never removed.
  // Otherwise, remove selected instances from the available pool.
  // AUTO-FIX: If we only have ONE card available but multiple are needed for the correct sequence,
  // we assume it's a "bank" style question and enable infinite mode automatically.
  const isInfinite = !!widget?.options?.infinite || (allCards.length === 1 && correctSequence.length > 1);
  const availableCards = isInfinite ? [...allCards] : [...allCards];

  if (!isInfinite) {
    selectedCards.forEach(selected => {
      const index = availableCards.indexOf(selected);
      if (index !== -1) {
        availableCards.splice(index, 1);
      }
    });
  }

  // Drag state
  const [draggedCard, setDraggedCard] = useState<string | null>(null);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragSource, setDragSource] = useState<'available' | 'selected' | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);

  const handleDragStart = useCallback((card: string, source: 'available' | 'selected', index?: number) => {
    if (isDisabled) return;
    setDraggedCard(card);
    setDraggedIndex(index !== undefined ? index : null);
    setDragSource(source);
  }, [isDisabled]);

  const handleDragEnd = useCallback(() => {
    setDraggedCard(null);
    setDraggedIndex(null);
    setDragSource(null);
    setDropTargetIndex(null);
  }, []);

  const handleDropOnAnswer = useCallback((dropIndex: number) => {
    if (isDisabled || !draggedCard) return;

    let newSelected = [...selectedCards];

    if (dragSource === 'available') {
      // Add card from available pool
      newSelected.splice(dropIndex, 0, draggedCard);
    } else if (dragSource === 'selected' && draggedIndex !== null) {
      // Reorder within selected using index to handle identical items
      newSelected.splice(draggedIndex, 1);
      const adjustedIndex = dropIndex > draggedIndex ? dropIndex - 1 : dropIndex;
      newSelected.splice(adjustedIndex, 0, draggedCard);
    }

    setSelectedCards(newSelected);
    onChange?.(newSelected);
    handleDragEnd();
  }, [isDisabled, draggedCard, dragSource, draggedIndex, selectedCards, onChange, handleDragEnd]);

  const handleDropOnAvailable = useCallback(() => {
    if (isDisabled || !draggedCard || dragSource !== 'selected' || draggedIndex === null) return;

    // Remove only the specific instance being dragged
    const newSelected = [...selectedCards];
    newSelected.splice(draggedIndex, 1);

    setSelectedCards(newSelected);
    onChange?.(newSelected);
    handleDragEnd();
  }, [isDisabled, draggedCard, dragSource, draggedIndex, selectedCards, onChange, handleDragEnd]);

  // Click handlers for touch/mobile support
  const handleCardClick = useCallback((card: string, source: 'available' | 'selected', index?: number) => {
    if (isDisabled) return;

    if (source === 'available') {
      const newSelected = [...selectedCards, card];
      setSelectedCards(newSelected);
      onChange?.(newSelected);
    } else if (index !== undefined) {
      // Remove only the clicked instance
      const newSelected = [...selectedCards];
      newSelected.splice(index, 1);
      setSelectedCards(newSelected);
      onChange?.(newSelected);
    }
  }, [isDisabled, selectedCards, onChange]);

  // Check correctness in review mode
  const isCorrect = reviewMode && JSON.stringify(selectedCards) === JSON.stringify(correctSequence);
  const isIncorrect = reviewMode && !isCorrect && selectedCards.length > 0;

  // Error state
  if (error) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="orderer">
        <div style={{ padding: '16px', backgroundColor: '#fee', border: '1px solid #f00', borderRadius: '8px' }}>
          <strong>Error:</strong> {error}
        </div>
      </BaseWidgetWrapper>
    );
  }

  // No cards available
  if (allCards.length === 0) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="orderer">
        <div style={{ padding: '16px', color: '#666', fontStyle: 'italic' }}>
          No options available for this orderer widget.
        </div>
      </BaseWidgetWrapper>
    );
  }

  const themeStyles = {
    light: {
      cardBg: '#fff',
      cardBorder: '#ddd',
      text: '#333',
      highlight: '#2196f3',
      correct: '#4caf50',
      incorrect: '#f44336',
      dropZoneBg: '#fafafa',
      dropZoneBorder: '#ccc',
      availableBg: '#f5f5f5',
      availableBorder: '#e0e0e0',
      labelColor: '#666',
    },
    dark: {
      cardBg: '#2d2d2d',
      cardBorder: '#444',
      text: '#fff',
      highlight: '#64b5f6',
      correct: '#81c784',
      incorrect: '#e57373',
      dropZoneBg: '#1e1e1e',
      dropZoneBorder: '#444',
      availableBg: '#1e1e1e',
      availableBorder: '#444',
      labelColor: '#ccc',
    },
    'high-contrast': {
      cardBg: '#222',
      cardBorder: '#fff',
      text: '#fff',
      highlight: '#00f',
      correct: '#0f0',
      incorrect: '#f00',
      dropZoneBg: '#111',
      dropZoneBorder: '#fff',
      availableBg: '#000',
      availableBorder: '#fff',
      labelColor: '#fff',
    },
  }[theme];

  const cardStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px 16px',
    margin: '4px',
    backgroundColor: themeStyles.cardBg,
    border: `2px solid ${themeStyles.cardBorder}`,
    borderRadius: '8px',
    cursor: isDisabled ? 'default' : 'grab',
    userSelect: 'none',
    fontSize: '16px',
    fontWeight: 500,
    color: themeStyles.text,
    transition: 'all 0.2s ease',
    minWidth: '60px',
    minHeight: '50px',
    textAlign: 'center',
  };

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="orderer">
      <div className="athena-orderer-container">
        {/* Instructions */}
        <div style={{ marginBottom: '12px', fontSize: '14px', color: themeStyles.labelColor }}>
          {isDisabled
            ? 'Your answer:'
            : 'Drag cards to the answer area, or click to add/remove.'}
        </div>

        {/* Answer Area */}
        <div
          className="athena-orderer-answer-area"
          onDragOver={(e) => {
            e.preventDefault();
            if (!isDisabled) setDropTargetIndex(selectedCards.length);
          }}
          onDrop={() => handleDropOnAnswer(selectedCards.length)}
          onDragLeave={() => setDropTargetIndex(null)}
          style={{
            display: 'flex',
            flexDirection: isHorizontal ? 'row' : 'column',
            flexWrap: 'wrap',
            alignItems: 'center',
            minHeight: '70px',
            padding: '12px',
            marginBottom: '12px',
            backgroundColor: reviewMode
              ? isCorrect ? 'rgba(76, 175, 80, 0.1)' : isIncorrect ? 'rgba(244, 67, 54, 0.1)' : themeStyles.dropZoneBg
              : themeStyles.dropZoneBg,
            border: `2px dashed ${reviewMode
              ? isCorrect ? themeStyles.correct : isIncorrect ? themeStyles.incorrect : themeStyles.dropZoneBorder
              : dropTargetIndex !== null ? themeStyles.highlight : themeStyles.dropZoneBorder
              }`,
            borderRadius: '8px',
            transition: 'all 0.2s ease',
          }}
        >
          {selectedCards.length === 0 ? (
            <span style={{ color: themeStyles.labelColor, fontStyle: 'italic', fontSize: '14px' }}>
              {isDisabled ? 'No cards selected' : 'Drop cards here or click to add'}
            </span>
          ) : (
            selectedCards.map((card, index) => (
              <div
                key={`selected-${index}`}
                draggable={!isDisabled}
                onDragStart={() => handleDragStart(card, 'selected', index)}
                onDragEnd={handleDragEnd}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (!isDisabled) setDropTargetIndex(index);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleDropOnAnswer(index);
                }}
                onClick={() => handleCardClick(card, 'selected', index)}
                style={{
                  ...cardStyle,
                  backgroundColor: draggedCard === card ? themeStyles.highlight : themeStyles.cardBg,
                  color: draggedCard === card ? '#fff' : themeStyles.text,
                  opacity: draggedCard === card ? 0.6 : 1,
                  borderColor: dropTargetIndex === index ? themeStyles.highlight : themeStyles.cardBorder,
                }}
                dangerouslySetInnerHTML={{ __html: renderContent(card) }}
              />
            ))
          )}

          {/* Review mode indicator */}
          {reviewMode && selectedCards.length > 0 && (
            <div style={{ marginLeft: 'auto', paddingLeft: '12px' }}>
              {isCorrect ? (
                <svg width="28" height="28" viewBox="0 0 24 24" fill={themeStyles.correct}>
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                </svg>
              ) : (
                <svg width="28" height="28" viewBox="0 0 24 24" fill={themeStyles.incorrect}>
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                </svg>
              )}
            </div>
          )}
        </div>

        {/* Available Cards */}
        {!isDisabled && availableCards.length > 0 && (
          <div
            className="athena-orderer-available"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDropOnAvailable}
            style={{
              display: 'flex',
              flexDirection: isHorizontal ? 'row' : 'column',
              flexWrap: 'wrap',
              alignItems: 'center',
              padding: '12px',
              backgroundColor: themeStyles.availableBg,
              borderRadius: '8px',
              border: `2px solid ${dragSource === 'selected' ? themeStyles.highlight : themeStyles.availableBorder}`,
            }}
          >
            <span style={{ marginRight: '12px', fontSize: '14px', color: themeStyles.labelColor, fontWeight: 500 }}>
              Available:
            </span>
            {availableCards.map((card, index) => (
              <div
                key={`available-${index}`}
                draggable={!isDisabled}
                onDragStart={() => handleDragStart(card, 'available')}
                onDragEnd={handleDragEnd}
                onClick={() => handleCardClick(card, 'available')}
                style={{
                  ...cardStyle,
                  opacity: draggedCard === card ? 0.6 : 1,
                  backgroundColor: draggedCard === card ? themeStyles.highlight : themeStyles.cardBg,
                  color: draggedCard === card ? '#fff' : themeStyles.text,
                }}
                dangerouslySetInnerHTML={{ __html: renderContent(card) }}
              />
            ))}
          </div>
        )}

        {/* Show correct answer in review mode */}
        {reviewMode && isIncorrect && (
          <div style={{ marginTop: '12px', padding: '10px', backgroundColor: '#fff3e0', borderRadius: '6px', fontSize: '14px' }}>
            <span style={{ fontWeight: 500, color: '#e65100' }}>Correct answer: </span>
            <span style={{ color: '#333' }}>
              {correctSequence.length} items in correct order
            </span>
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default OrdererWidget;

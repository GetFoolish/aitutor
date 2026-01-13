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
}

interface IndexedCard {
  index: number;
  content: string;
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

  // Debug logging
  useEffect(() => {
    console.log('[OrdererWidget] Initialized:', {
      widgetId,
      options,
      value,
      readOnly,
      disabled,
      reviewMode,
    });
  }, []);

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
        return `<img src="${url}" alt="${alt}" style="max-width:100%;max-height:80px;height:auto;display:block;margin:4px auto;" onerror="this.style.display='none'" />`;
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
      // Priority 1: Use correctOptions + otherOptions if correctOptions exists (Perseus format)
      if (Array.isArray(options.correctOptions) && options.correctOptions.length > 0) {
        const correct = options.correctOptions.map(getContentString);
        const other = (options.otherOptions || []).map(getContentString);
        const combined = [...correct, ...other];
        console.log('[OrdererWidget] Available cards from correctOptions + otherOptions:', {
          correct,
          other,
          combined,
        });
        return combined;
      }
      
      // Priority 2: Fallback to options array (legacy/test format)
      if (Array.isArray(options.options) && options.options.length > 0) {
        const cards = options.options.map(getContentString);
        console.log('[OrdererWidget] Available cards from options.options:', cards);
        return cards;
      }
      
      // Priority 3: Try otherOptions alone if correctOptions was empty but exists
      const other = (options.otherOptions || []).map(getContentString);
      if (other.length > 0) {
        console.log('[OrdererWidget] Available cards from otherOptions only:', other);
        return other;
      }
      
      return [];
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

  const allCardsContent = getAvailableCards();
  const correctSequence = getCorrectSequence();
  const isHorizontal = options.layout === 'horizontal';
  const isDisabled = readOnly || disabled;

  // Create indexed cards to handle duplicates
  const allCards: IndexedCard[] = allCardsContent.map((content, index) => ({
    index,
    content,
  }));

  // State: track selected card indices instead of content strings
  const [selectedIndices, setSelectedIndices] = useState<number[]>(() => {
    if (value && Array.isArray(value)) {
      console.log('[OrdererWidget] Initial value:', value);
      // Map initial values to indices based on content matching
      const indices: number[] = [];
      (value as string[]).forEach(selectedContent => {
        const cardIndex = allCards.findIndex(
          card => card.content === selectedContent && !indices.includes(card.index)
        );
        if (cardIndex !== -1) {
          indices.push(cardIndex);
        }
      });
      return indices;
    }
    return [];
  });

  // Compute available cards (not yet selected by index)
  const availableCards = allCards.filter(card => !selectedIndices.includes(card.index));
  
  // Get selected cards in order
  const selectedCards = selectedIndices.map(idx => allCards[idx]);

  // Debug logging for state changes
  useEffect(() => {
    console.log('[OrdererWidget] State update:', {
      allCards: allCards.length,
      selectedIndices: selectedIndices.length,
      availableCards: availableCards.length,
      isDisabled,
      selectedCardsPreview: selectedCards.slice(0, 2).map(c => c.content.substring(0, 50)),
      availableCardsPreview: availableCards.slice(0, 2).map(c => c.content.substring(0, 50)),
    });
  }, [selectedIndices, allCards.length, availableCards.length, isDisabled]);

  // Drag state (now tracking by card index)
  const [draggedCardIndex, setDraggedCardIndex] = useState<number | null>(null);
  const [dragSource, setDragSource] = useState<'available' | 'selected' | null>(null);
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);

  const handleDragStart = useCallback((cardIndex: number, source: 'available' | 'selected') => {
    if (isDisabled) return;
    setDraggedCardIndex(cardIndex);
    setDragSource(source);
  }, [isDisabled]);

  const handleDragEnd = useCallback(() => {
    setDraggedCardIndex(null);
    setDragSource(null);
    setDropTargetIndex(null);
  }, []);

  const handleDropOnAnswer = useCallback((dropIndex: number) => {
    if (isDisabled || draggedCardIndex === null) return;

    console.log('[OrdererWidget] handleDropOnAnswer:', {
      dropIndex,
      draggedCardIndex,
      dragSource,
      currentSelected: selectedIndices.length,
    });

    let newSelectedIndices = [...selectedIndices];

    if (dragSource === 'available') {
      // Add card index from available pool
      newSelectedIndices.splice(dropIndex, 0, draggedCardIndex);
      console.log('[OrdererWidget] Added card from available, new count:', newSelectedIndices.length);
    } else if (dragSource === 'selected') {
      // Reorder within selected
      const currentIndex = newSelectedIndices.indexOf(draggedCardIndex);
      if (currentIndex !== -1) {
        newSelectedIndices.splice(currentIndex, 1);
        const adjustedIndex = dropIndex > currentIndex ? dropIndex - 1 : dropIndex;
        newSelectedIndices.splice(adjustedIndex, 0, draggedCardIndex);
        console.log('[OrdererWidget] Reordered within selected');
      }
    }

    setSelectedIndices(newSelectedIndices);
    // Convert indices back to content strings for onChange callback
    const selectedContent = newSelectedIndices.map(idx => allCards[idx].content);
    onChange?.(selectedContent);
    handleDragEnd();
  }, [isDisabled, draggedCardIndex, dragSource, selectedIndices, onChange, handleDragEnd, allCards]);

  const handleDropOnAvailable = useCallback(() => {
    if (isDisabled || draggedCardIndex === null || dragSource !== 'selected') return;

    const newSelectedIndices = selectedIndices.filter(idx => idx !== draggedCardIndex);
    setSelectedIndices(newSelectedIndices);
    // Convert indices back to content strings for onChange callback
    const selectedContent = newSelectedIndices.map(idx => allCards[idx].content);
    onChange?.(selectedContent);
    handleDragEnd();
  }, [isDisabled, draggedCardIndex, dragSource, selectedIndices, onChange, handleDragEnd, allCards]);

  // Click handlers for touch/mobile support
  const handleCardClick = useCallback((cardIndex: number, source: 'available' | 'selected') => {
    if (isDisabled) return;

    console.log('[OrdererWidget] handleCardClick:', {
      source,
      cardIndex,
      currentSelected: selectedIndices.length,
    });

    if (source === 'available') {
      const newSelectedIndices = [...selectedIndices, cardIndex];
      console.log('[OrdererWidget] Added via click, new count:', newSelectedIndices.length);
      setSelectedIndices(newSelectedIndices);
      // Convert indices back to content strings for onChange callback
      const selectedContent = newSelectedIndices.map(idx => allCards[idx].content);
      onChange?.(selectedContent);
    } else {
      const newSelectedIndices = selectedIndices.filter(idx => idx !== cardIndex);
      console.log('[OrdererWidget] Removed via click, new count:', newSelectedIndices.length);
      setSelectedIndices(newSelectedIndices);
      // Convert indices back to content strings for onChange callback
      const selectedContent = newSelectedIndices.map(idx => allCards[idx].content);
      onChange?.(selectedContent);
    }
  }, [isDisabled, selectedIndices, onChange, allCards]);

  // Check correctness in review mode (compare content strings)
  const selectedContent = selectedIndices.map(idx => allCards[idx].content);
  const isCorrect = reviewMode && JSON.stringify(selectedContent) === JSON.stringify(correctSequence);
  const isIncorrect = reviewMode && !isCorrect && selectedIndices.length > 0;

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
            selectedCards.map((card, displayIndex) => (
              <div
                key={`selected-${card.index}`}
                draggable={!isDisabled}
                onDragStart={() => handleDragStart(card.index, 'selected')}
                onDragEnd={handleDragEnd}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (!isDisabled) setDropTargetIndex(displayIndex);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleDropOnAnswer(displayIndex);
                }}
                onClick={() => handleCardClick(card.index, 'selected')}
                style={{
                  ...cardStyle,
                  backgroundColor: draggedCardIndex === card.index ? themeStyles.highlight : themeStyles.cardBg,
                  color: draggedCardIndex === card.index ? '#fff' : themeStyles.text,
                  opacity: draggedCardIndex === card.index ? 0.6 : 1,
                  borderColor: dropTargetIndex === displayIndex ? themeStyles.highlight : themeStyles.cardBorder,
                }}
                dangerouslySetInnerHTML={{ __html: renderContent(card.content) }}
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
            {availableCards.map((card) => (
              <div
                key={`available-${card.index}`}
                draggable={!isDisabled}
                onDragStart={() => handleDragStart(card.index, 'available')}
                onDragEnd={handleDragEnd}
                onClick={() => handleCardClick(card.index, 'available')}
                style={{
                  ...cardStyle,
                  opacity: draggedCardIndex === card.index ? 0.6 : 1,
                  backgroundColor: draggedCardIndex === card.index ? themeStyles.highlight : themeStyles.cardBg,
                  color: draggedCardIndex === card.index ? '#fff' : themeStyles.text,
                }}
                dangerouslySetInnerHTML={{ __html: renderContent(card.content) }}
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

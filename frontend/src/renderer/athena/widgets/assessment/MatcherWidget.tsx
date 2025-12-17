/**
 * Matcher Widget
 *
 * Match items from two columns.
 * Users connect related items by clicking pairs.
 */

import React, { useState, useCallback, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { MatcherOptions } from '../../core/types';
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

export interface MatcherWidgetProps extends WidgetProps<MatcherOptions> {}

interface MatchPair {
  leftIndex: number;
  rightIndex: number;
}

export function MatcherWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: MatcherWidgetProps) {
  const options = widget.options || {};
  const leftItems = Array.isArray(options.left) ? options.left : [];
  const rightItems = Array.isArray(options.right) ? options.right : [];
  const correctPairs = Array.isArray(options.correctPairs) ? options.correctPairs : [];

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

  // Initialize matches from value prop
  const getInitialMatches = (): MatchPair[] => {
    if (value && Array.isArray(value)) {
      return value as MatchPair[];
    }
    return [];
  };

  const [matches, setMatches] = useState<MatchPair[]>(getInitialMatches);
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);

  const isDisabled = readOnly || disabled;

  const handleLeftClick = useCallback(
    (index: number) => {
      if (isDisabled) return;

      // Check if this left item is already matched
      const existingMatch = matches.find((m) => m.leftIndex === index);
      if (existingMatch) {
        // Remove the match
        const newMatches = matches.filter((m) => m.leftIndex !== index);
        setMatches(newMatches);
        onChange?.(newMatches);
        setSelectedLeft(null);
      } else {
        setSelectedLeft(index);
      }
    },
    [isDisabled, matches, onChange]
  );

  const handleRightClick = useCallback(
    (index: number) => {
      if (isDisabled || selectedLeft === null) return;

      // Remove any existing match for this right item
      const filteredMatches = matches.filter(
        (m) => m.rightIndex !== index && m.leftIndex !== selectedLeft
      );

      // Add new match
      const newMatches = [...filteredMatches, { leftIndex: selectedLeft, rightIndex: index }];
      setMatches(newMatches);
      onChange?.(newMatches);
      setSelectedLeft(null);
    },
    [isDisabled, matches, onChange, selectedLeft]
  );

  // Get match for a left item
  const getMatchForLeft = (leftIndex: number): number | null => {
    const match = matches.find((m) => m.leftIndex === leftIndex);
    return match ? match.rightIndex : null;
  };

  // Get match for a right item
  const getMatchForRight = (rightIndex: number): number | null => {
    const match = matches.find((m) => m.rightIndex === rightIndex);
    return match ? match.leftIndex : null;
  };

  // Check if a match is correct (for review mode)
  const isCorrectMatch = (leftIndex: number, rightIndex: number): boolean => {
    return correctPairs.some(
      (pair) => pair.left === leftIndex && pair.right === rightIndex
    );
  };

  // Generate colors for matched pairs
  const matchColors = [
    '#2196f3',
    '#4caf50',
    '#ff9800',
    '#9c27b0',
    '#e91e63',
    '#00bcd4',
    '#ffeb3b',
    '#795548',
  ];

  const getMatchColor = (matchIndex: number): string => {
    return matchColors[matchIndex % matchColors.length];
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      itemBg: '#f8f9fa',
      border: '#e0e0e0',
      text: '#333',
      selected: '#e3f2fd',
      correct: '#e8f5e9',
      incorrect: '#ffebee',
    },
    dark: {
      bg: '#2d2d2d',
      itemBg: '#3d3d3d',
      border: '#4d4d4d',
      text: '#fff',
      selected: '#1e3a5f',
      correct: '#1b5e20',
      incorrect: '#b71c1c',
    },
    'high-contrast': {
      bg: '#000',
      itemBg: '#222',
      border: '#fff',
      text: '#fff',
      selected: '#333',
      correct: '#0f0',
      incorrect: '#f00',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="matcher">
      <div className="athena-matcher-container">
        {options.title && (
          <div
            className="athena-matcher-title"
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
          className="athena-matcher-instructions"
          style={{
            marginBottom: '16px',
            fontSize: '14px',
            color: '#666',
          }}
        >
          {isDisabled
            ? 'Matched pairs:'
            : 'Click an item on the left, then click its match on the right'}
        </div>

        <div
          className="athena-matcher-columns"
          style={{
            display: 'flex',
            gap: '24px',
            justifyContent: 'center',
          }}
        >
          {/* Left column */}
          <div className="athena-matcher-left" style={{ flex: '0 0 45%' }}>
            <div
              style={{
                marginBottom: '8px',
                fontWeight: 500,
                color: themeStyles.text,
              }}
            >
              {options.leftLabel || 'Items'}
            </div>
            {leftItems.map((item, index) => {
              const matchedRight = getMatchForLeft(index);
              const isSelected = selectedLeft === index;
              const matchIndex = matches.findIndex((m) => m.leftIndex === index);
              const hasMatch = matchedRight !== null;

              let bgColor = themeStyles.itemBg;
              if (isSelected) bgColor = themeStyles.selected;
              if (reviewMode && hasMatch) {
                bgColor = isCorrectMatch(index, matchedRight!)
                  ? themeStyles.correct
                  : themeStyles.incorrect;
              }

              return (
                <button
                  key={index}
                  onClick={() => handleLeftClick(index)}
                  disabled={isDisabled}
                  aria-pressed={isSelected}
                  aria-label={`${item}${hasMatch ? ` - matched with ${rightItems[matchedRight!]}` : ''}`}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    marginBottom: '8px',
                    backgroundColor: bgColor,
                    border: `2px solid ${
                      hasMatch ? getMatchColor(matchIndex) : themeStyles.border
                    }`,
                    borderRadius: '8px',
                    cursor: isDisabled ? 'default' : 'pointer',
                    textAlign: 'left',
                    color: themeStyles.text,
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {hasMatch && (
                    <span
                      style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: getMatchColor(matchIndex),
                        flexShrink: 0,
                      }}
                    />
                  )}
                  <span style={{ flex: 1 }} dangerouslySetInnerHTML={{ __html: renderContent(item) }} />
                  {reviewMode && hasMatch && (
                    <span style={{ flexShrink: 0 }}>
                      {isCorrectMatch(index, matchedRight!) ? (
                        <CheckIcon style={{ color: '#4caf50' }} />
                      ) : (
                        <CrossIcon style={{ color: '#f44336' }} />
                      )}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Right column */}
          <div className="athena-matcher-right" style={{ flex: '0 0 45%' }}>
            <div
              style={{
                marginBottom: '8px',
                fontWeight: 500,
                color: themeStyles.text,
              }}
            >
              {options.rightLabel || 'Matches'}
            </div>
            {rightItems.map((item, index) => {
              const matchedLeft = getMatchForRight(index);
              const matchIndex = matches.findIndex((m) => m.rightIndex === index);
              const hasMatch = matchedLeft !== null;
              const isSelectable = selectedLeft !== null && !hasMatch;

              let bgColor = themeStyles.itemBg;
              if (isSelectable) bgColor = '#fffde7';
              if (reviewMode && hasMatch) {
                bgColor = isCorrectMatch(matchedLeft!, index)
                  ? themeStyles.correct
                  : themeStyles.incorrect;
              }

              return (
                <button
                  key={index}
                  onClick={() => handleRightClick(index)}
                  disabled={isDisabled || (selectedLeft === null && !hasMatch)}
                  aria-label={`${item}${hasMatch ? ` - matched with ${leftItems[matchedLeft!]}` : ''}`}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    marginBottom: '8px',
                    backgroundColor: bgColor,
                    border: `2px solid ${
                      hasMatch ? getMatchColor(matchIndex) : themeStyles.border
                    }`,
                    borderRadius: '8px',
                    cursor:
                      isDisabled || (selectedLeft === null && !hasMatch)
                        ? 'default'
                        : 'pointer',
                    textAlign: 'left',
                    color: themeStyles.text,
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease',
                    opacity: selectedLeft === null && !hasMatch && !isDisabled ? 0.6 : 1,
                  }}
                >
                  {hasMatch && (
                    <span
                      style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: getMatchColor(matchIndex),
                        flexShrink: 0,
                      }}
                    />
                  )}
                  <span style={{ flex: 1 }} dangerouslySetInnerHTML={{ __html: renderContent(item) }} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Match count */}
        <div
          style={{
            marginTop: '16px',
            textAlign: 'center',
            fontSize: '14px',
            color: '#666',
          }}
        >
          {matches.length} of {Math.min(leftItems.length, rightItems.length)} matched
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

function CheckIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
    </svg>
  );
}

function CrossIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
    </svg>
  );
}

export default MatcherWidget;

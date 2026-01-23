/**
 * Matcher Widget
 *
 * Match items from two columns.
 * Users connect related items by clicking pairs.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Reorder, useDragControls } from 'framer-motion';
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

export interface MatcherWidgetProps extends WidgetProps<MatcherOptions> { }

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
  console.log('[MatcherWidget] Rendering with theme:', theme, 'Options:', options);
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
    processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
      try {
        if (katex) {
          return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
        }
        return `<div class="athena-math-display">${math}</div>`;
      } catch {
        return `<div class="athena-math-display">${math}</div>`;
      }
    });

    // 3. Handle inline math: $\begin{env}...\end{env}$ (multiline) | $...$ (single line)
    const inlineMathRegex = /\$\\begin\{([^}]+)\}([\s\S]+?)\\end\{\1\}\$|\$([^$\n]+)\$/g;
    processed = processed.replace(inlineMathRegex, (match, envName, envContent, simpleContent) => {
      const math = envName ? `\\begin{${envName}}${envContent}\\end{${envName}}` : simpleContent;
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

  // Determine initial order of right column based on existing matches (value)
  // Logic: If left[0] is matched with right[x], then right[x] should be at visual index 0.
  const getInitialRightIndices = (): number[] => {
    const indices: number[] = rightItems.map((_, i) => i);

    // If no values, return default order (0, 1, 2...)
    if (!value || !Array.isArray(value) || value.length === 0) {
      return indices;
    }

    const savedMatches = value as MatchPair[];
    const newOrder = [...indices];

    // Attempt to reconstruct order: for each visual row i (corresponding to left[i]), find which right item is matched
    // Note: This logic assumes 1-to-1 matching. Partial matching might be weird but DnD implies strict ordering.
    // We strictly map leftItems indices to positions.
    const usedRightIndices = new Set<number>();

    // Sort array based on matches
    // Create a map of LeftIndex -> RightIndex
    const leftToRightMap = new Map<number, number>();
    savedMatches.forEach(m => leftToRightMap.set(m.leftIndex, m.rightIndex));

    const reordered: number[] = [];

    // 1. Fill slots for left items that have matches
    for (let i = 0; i < leftItems.length; i++) {
      if (leftToRightMap.has(i)) {
        const rIdx = leftToRightMap.get(i)!;
        if (rIdx < rightItems.length) {
          reordered.push(rIdx);
          usedRightIndices.add(rIdx);
        } else {
          // Matched index out of bounds? Should not happen but fallback
          reordered.push(-1); // Placeholder, will fill later
        }
      } else {
        reordered.push(-1);
      }
    }

    // 2. Fill remaining slots with unused right indices
    let nextUnused = 0;
    for (let i = 0; i < reordered.length; i++) {
      if (reordered[i] === -1) {
        while (nextUnused < rightItems.length && usedRightIndices.has(nextUnused)) {
          nextUnused++;
        }
        if (nextUnused < rightItems.length) {
          reordered[i] = nextUnused;
          usedRightIndices.add(nextUnused);
        }
      }
    }

    // If we have more right items than left items, append them to the bottom
    while (nextUnused < rightItems.length) {
      if (!usedRightIndices.has(nextUnused)) {
        reordered.push(nextUnused);
      }
      nextUnused++;
    }

    // Filter out any failed placeholders just in case
    return reordered.filter(idx => idx !== -1);
  };

  const [rightIndices, setRightIndices] = useState<number[]>(getInitialRightIndices);

  // Update matches whenever the order changes
  const updateMatches = (newOrder: number[]) => {
    setRightIndices(newOrder);

    // Generate matches: Visual Row i maps Left[i] to Right[newOrder[i]]
    const newMatches: MatchPair[] = [];
    const minLength = Math.min(leftItems.length, newOrder.length);

    for (let i = 0; i < minLength; i++) {
      newMatches.push({
        leftIndex: i,
        rightIndex: newOrder[i]
      });
    }

    onChange?.(newMatches);
  };

  const isDisabled = readOnly || disabled;

  const themeStyles = {
    light: {
      bg: '#fff',
      itemBg: '#f8f9fa',
      border: '#e0e0e0',
      text: '#333',
      selected: '#e3f2fd',
      correct: '#e8f5e9',
      incorrect: '#ffebee',
      dragging: '#e3f2fd',
    },
    dark: {
      bg: '#000000', // Strict black as requested
      itemBg: '#1e1e1e', // Very dark grey for items
      border: '#333333',
      text: '#ffffff',
      selected: '#263238', // Darker blue-grey
      correct: '#004d40', // Dark teal
      incorrect: '#b71c1c',
      dragging: '#1e3a5f',
    },
    'high-contrast': {
      bg: '#000',
      itemBg: '#222',
      border: '#fff',
      text: '#fff',
      selected: '#333',
      correct: '#0f0',
      incorrect: '#f00',
      dragging: '#333',
    },
  }[theme];

  // Colors for feedback (check correctness)
  // In DnD mode, 'correct' means the right item at index i matches the expected right index for left item i
  const getFeedbackStyle = (idx: number, originalRightIdx: number) => {
    if (!reviewMode) return {};

    // What is the correct right index for left item at visual row 'idx'?
    const correctPair = correctPairs.find(p => p.left === idx);
    const isCorrect = correctPair && correctPair.right === originalRightIdx;

    return {
      backgroundColor: isCorrect ? themeStyles.correct : themeStyles.incorrect,
      borderColor: isCorrect ? '#4caf50' : '#f44336'
    };
  };

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="matcher">
      <div
        className="athena-matcher-container"
        style={{
          backgroundColor: themeStyles.bg,
          color: themeStyles.text,
          padding: '16px',
          borderRadius: '8px',
          transition: 'background-color 0.2s ease, color 0.2s ease'
        }}
      >
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
            color: themeStyles.text,
            opacity: 0.8
          }}
        >
          {isDisabled
            ? 'Matched pairs:'
            : 'Reorder the items on the right to match the left side.'}
        </div>

        <div
          className="athena-matcher-columns"
          style={{
            display: 'flex',
            gap: '24px',
            justifyContent: 'center',
            alignItems: 'flex-start', // Important for potential height mismatches
          }}
        >
          {/* Left column (Fixed) */}
          <div className="athena-matcher-left" style={{ flex: '0 0 45%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ marginBottom: '8px', fontWeight: 500, color: themeStyles.text }}>
              {options.leftLabel || 'Items'}
            </div>
            {leftItems.map((item, index) => (
              <div
                key={`left-${index}`}
                style={{
                  width: '100%',
                  minHeight: '48px', // Ensure consistent height for alignment
                  padding: '12px 16px',
                  backgroundColor: themeStyles.itemBg,
                  border: `1px solid ${themeStyles.border}`,
                  borderRadius: '8px',
                  color: themeStyles.text,
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <div dangerouslySetInnerHTML={{ __html: renderContent(item) }} style={{ color: 'inherit' }} />
              </div>
            ))}
          </div>

          {/* Right column (Sortable) */}
          <div className="athena-matcher-right" style={{ flex: '0 0 45%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ marginBottom: '8px', fontWeight: 500, color: themeStyles.text }}>
              {options.rightLabel || 'Matches'}
            </div>

            <Reorder.Group
              axis="y"
              values={rightIndices}
              onReorder={isDisabled ? () => { } : updateMatches} // Disable reorder if readOnly
              style={{ display: 'flex', flexDirection: 'column', gap: '8px', listStyle: 'none', padding: 0, margin: 0 }}
            >
              {rightIndices.map((originalIndex, visualIndex) => {
                const itemContent = rightItems[originalIndex];
                const feedback = getFeedbackStyle(visualIndex, originalIndex);

                return (
                  <Reorder.Item
                    key={originalIndex} // Use original index as stable key
                    value={originalIndex}
                    drag={!isDisabled}
                    dragConstraints={{ top: 0, bottom: 0 }} // Constrain logic if needed, but Reorder handles list
                    style={{
                      width: '100%',
                      minHeight: '48px',
                      padding: '12px 16px',
                      backgroundColor: themeStyles.itemBg,
                      border: `1px solid ${themeStyles.border}`,
                      borderRadius: '8px',
                      color: themeStyles.text,
                      fontSize: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      cursor: isDisabled ? 'default' : 'grab',
                      userSelect: 'none',
                      ...feedback
                    }}
                    whileDrag={{
                      scale: 1.02,
                      boxShadow: '0 5px 15px rgba(0,0,0,0.1)',
                      cursor: 'grabbing',
                      backgroundColor: themeStyles.dragging,
                      zIndex: 10
                    }}
                  >
                    <div style={{ flex: 1, color: 'inherit' }} dangerouslySetInnerHTML={{ __html: renderContent(itemContent) }} />
                    {/* Handle Icon for affordability */}
                    {!isDisabled && (
                      <div style={{ marginLeft: '10px', color: 'inherit', opacity: 0.5, fontSize: '20px' }} aria-hidden="true">
                        ☰
                      </div>
                    )}
                    {/* Review Mode Icons */}
                    {reviewMode && feedback.borderColor && (
                      <div style={{ marginLeft: '10px' }}>
                        {feedback.borderColor === '#4caf50' ? (
                          <span style={{ color: '#4caf50' }}>✓</span>
                        ) : (
                          <span style={{ color: '#f44336' }}>✗</span>
                        )}
                      </div>
                    )}
                  </Reorder.Item>
                );
              })}
            </Reorder.Group>

            {/* Show extra items non-draggable or handle mismatch? 
                If rightItems > leftItems, the extra ones will be at the bottom.
                Generally Matcher widgets should be balanced or handle extras.
            */}
          </div>
        </div>

        {/* Match count */}
        <div
          style={{
            marginTop: '16px',
            textAlign: 'center',
            fontSize: '14px',
            color: themeStyles.text, // Fix: Use theme text color instead of hardcoded #666
            opacity: 0.7
          }}
        >
          {rightIndices.length} of {Math.min(leftItems.length, rightItems.length)} matched
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}


function CrossIcon({ style }: { style?: React.CSSProperties }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={style} aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
  );
}

export default MatcherWidget;

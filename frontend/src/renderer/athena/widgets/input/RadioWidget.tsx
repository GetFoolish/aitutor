/**
 * Radio Widget
 *
 * Multiple choice widget supporting:
 * - Single selection (radio)
 * - Multiple selection (checkboxes)
 * - Randomization
 * - Rich content in choices
 */

import React, { useCallback, useMemo, useId, useEffect, useRef, useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { RadioOptions } from '../../core/types';
import { BaseWidgetWrapper, useWidgetState } from '../base/BaseWidget';
import { GraphieImage } from '../display/GraphieImage';

// Load KaTeX dynamically
let katexLoaded = false;
let katexModule: any = null;

async function ensureKaTeX() {
  if (katexLoaded && katexModule) return katexModule;
  try {
    // @ts-ignore - KaTeX types not installed
    katexModule = await import('katex');
    // Also ensure CSS is loaded
    if (typeof document !== 'undefined' && !document.querySelector('link[href*="katex"]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
      document.head.appendChild(link);
    }
    katexLoaded = true;
    return katexModule.default || katexModule;
  } catch (e) {
    console.warn('Failed to load KaTeX:', e);
    return null;
  }
}

export interface RadioWidgetProps extends WidgetProps<RadioOptions> { }

export function RadioWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly = false,
  disabled = false,
  reviewMode = false,
  theme = 'light',
}: RadioWidgetProps) {
  const options = widget.options || {};
  const groupId = useId();
  const [katex, setKatex] = React.useState<any>(null);

  // Load KaTeX on mount
  useEffect(() => {
    ensureKaTeX().then(k => {
      if (k) setKatex(k);
    });
  }, []);

  // Handle both single and multiple selection
  const isMultiSelect = options.multipleSelect ?? false;

  const state = useWidgetState<number | number[]>(
    value as number | number[] | undefined,
    onChange as ((value: number | number[]) => void) | undefined
  );

  // Debug: log widget options
  useEffect(() => {
    console.log('[RadioWidget] Options:', {
      widgetId,
      choices: options.choices,
      choicesLength: options.choices?.length,
      multipleSelect: options.multipleSelect,
      fullOptions: options,
    });
  }, [widgetId, options]);

  // Add error handlers to images after rendering (since inline onerror doesn't work with dangerouslySetInnerHTML)
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!containerRef.current) return;

    const images = containerRef.current.querySelectorAll('img.athena-choice-image[data-fallback-base]');
    images.forEach((img) => {
      const imgEl = img as HTMLImageElement;
      const fallbackBase = imgEl.dataset.fallbackBase;

      if (!fallbackBase) return;

      imgEl.onerror = () => {
        console.log('[RadioWidget] Image failed to load:', imgEl.src);
        // Try alternate extension
        if (imgEl.src.endsWith('.png')) {
          console.log('[RadioWidget] Trying SVG fallback');
          imgEl.src = fallbackBase + '.svg';
        } else if (imgEl.src.endsWith('.svg')) {
          console.log('[RadioWidget] Trying PNG fallback');
          imgEl.src = fallbackBase + '.png';
        }
      };
    });
  });

  // Randomize choices if enabled (but keep indices for scoring)
  const displayOrder = useMemo(() => {
    // Safety check for undefined or non-array choices
    if (!options.choices || !Array.isArray(options.choices) || options.choices.length === 0) {
      console.warn('[RadioWidget] No choices found:', { widgetId, choices: options.choices });
      return [];
    }

    const indices = options.choices.map((_, i) => i);

    if (options.randomize) {
      // Simple Fisher-Yates shuffle
      for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [indices[i], indices[j]] = [indices[j], indices[i]];
      }
    }

    return indices;
  }, [options.choices, options.randomize, widgetId]);

  // Handle selection
  const handleSelect = useCallback(
    (index: number) => {
      if (disabled || readOnly) return;

      if (isMultiSelect) {
        const currentValues = Array.isArray(state.value) ? state.value : [];
        const newValues = currentValues.includes(index)
          ? currentValues.filter((i) => i !== index)
          : [...currentValues, index];
        state.setValue(newValues);
      } else {
        // Single select - toggle if deselect enabled
        if (options.deselectEnabled && state.value === index) {
          state.setValue(-1);
        } else {
          state.setValue(index);
        }
      }
    },
    [disabled, readOnly, isMultiSelect, state, options.deselectEnabled]
  );

  // Check if an index is selected
  const isSelected = useCallback(
    (index: number) => {
      if (isMultiSelect) {
        return Array.isArray(state.value) && state.value.includes(index);
      }
      return state.value === index;
    },
    [isMultiSelect, state.value]
  );

  // Get correct indices for review mode
  const correctIndices = useMemo(() => {
    if (!reviewMode || !options.choices || !Array.isArray(options.choices)) return new Set<number>();
    return new Set(
      options.choices
        .map((choice, index) => (choice?.correct ? index : -1))
        .filter((i) => i >= 0)
    );
  }, [reviewMode, options.choices]);

  // Process markdown table in choice content
  const processTable = (text: string): string => {
    const lines = text.split('\n');
    const result: string[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      if (line.includes('|') && line.split('|').length >= 2) {
        const tableLines: string[] = [];
        let j = i;
        while (j < lines.length && lines[j].includes('|')) {
          tableLines.push(lines[j]);
          j++;
        }
        // Look for separator row
        const separatorIndex = tableLines.findIndex(l => /^[\s|:\-]+$/.test(l.trim()) && l.includes('-'));
        if (separatorIndex >= 1 && tableLines.length >= 3) {
          // Parse alignments
          const alignments: string[] = [];
          tableLines[separatorIndex].split('|').filter(c => c.trim()).forEach(cell => {
            const t = cell.trim();
            if (t.startsWith(':') && t.endsWith(':')) alignments.push('center');
            else if (t.endsWith(':')) alignments.push('right');
            else alignments.push('center');
          });
          // Build table
          let html = '<table class="athena-choice-table" style="border-collapse:collapse;margin:0.5rem 0;font-size:0.9rem;width:100%;"><thead><tr>';
          const headerCells = tableLines[0].split('|').filter(c => c.trim());
          headerCells.forEach((cell, idx) => {
            html += `<th style="padding:6px 10px;border:1px solid var(--athena-border, #ddd);background:var(--athena-inline-code-bg, #f5f5f5);color:var(--athena-text);text-align:${alignments[idx] || 'center'}">${cell.trim()}</th>`;
          });
          html += '</tr></thead><tbody>';
          for (let k = separatorIndex + 1; k < tableLines.length; k++) {
            html += '<tr>';
            const cells = tableLines[k].split('|').filter(c => c.trim());
            cells.forEach((cell, idx) => {
              html += `<td style="padding:6px 10px;border:1px solid var(--athena-border, #ddd);color:var(--athena-text);text-align:${alignments[idx] || 'center'}">${cell.trim()}</td>`;
            });
            html += '</tr>';
          }
          html += '</tbody></table>';
          result.push(html);
          i = j;
          continue;
        }
      }
      result.push(line);
      i++;
    }
    return result.join('\n');
  };

  // Render choice content with KaTeX math support and images
  const renderChoiceContent = useCallback(
    (content: string): string => {
      // First process tables
      let processed = processTable(content);

      // 0. FIRST: Protect escaped dollar signs \$ by converting to placeholder
      const DOLLAR_PLACEHOLDER = '\u0000DOLLAR\u0000';
      processed = processed.replace(/\\\$/g, DOLLAR_PLACEHOLDER);

      // 1. Handle markdown images ![alt](url) - convert to placeholder that we'll handle in React
      // Note: We use a data attribute instead of onerror because inline handlers don't work with dangerouslySetInnerHTML
      processed = processed.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
        let imageUrl = url;
        // Convert web+graphie:// URLs to https:// with PNG extension
        if (imageUrl.startsWith('web+graphie://')) {
          imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
        }
        // Add CDN extension if missing
        if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
          !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
          imageUrl = imageUrl + '.png';
        }
        const isFixedGraph = imageUrl.includes('fixed_graphs');
        const isSvg = imageUrl.toLowerCase().includes('.svg');
        const hasGraphKeywords = alt && (
          alt.toLowerCase().includes('graph') ||
          alt.toLowerCase().includes('diagram') ||
          alt.toLowerCase().includes('drawing') ||
          alt.toLowerCase().includes('figure') ||
          alt.toLowerCase().includes('axis') ||
          alt.toLowerCase().includes('axes') ||
          alt.toLowerCase().includes('plot') ||
          alt.toLowerCase().includes('coordinate') ||
          alt.toLowerCase().includes('illustration')
        );

        const extraClass = (isFixedGraph || isSvg || hasGraphKeywords) ? ' target-graph-fix' : '';

        return `<img src="${imageUrl}" alt="${alt}" class="athena-choice-image${extraClass}" data-fallback-base="${url.replace('web+graphie://', 'https://').replace(/\.(png|svg)$/, '')}" style="max-width:100%;height:auto;display:block;margin:0.5rem 0;" referrerpolicy="no-referrer" />`;
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

      // 4. Handle LaTeX commands like \dfrac, \frac without $ delimiters
      processed = processed.replace(/\\(dfrac|frac|sqrt|int|sum|prod|lim)\{([^}]+)\}\{([^}]+)\}/g, (match, cmd, arg1, arg2) => {
        try {
          if (katex) {
            return katex.renderToString(`\\${cmd}{${arg1}}{${arg2}}`, { displayMode: false, throwOnError: false });
          }
          return match;
        } catch {
          return match;
        }
      });

      // 5. Handle bold **...**
      processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

      // 6. Handle italic *...*
      processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');

      // 7. LAST: Restore escaped dollar signs
      processed = processed.replace(new RegExp(DOLLAR_PLACEHOLDER, 'g'), '$');

      return processed;
    },
    [katex]
  );

  // Component to render choice content with proper graphie support
  const ChoiceContent = ({ content }: { content: string }) => {
    // Check if content contains graphie images
    const graphiePattern = /!\[([^\]]*)\]\((web\+graphie:\/\/[^)]+)\)/g;
    const matches = [...content.matchAll(graphiePattern)];

    if (matches.length === 0) {
      // No graphie images - use the existing HTML rendering
      return (
        <span
          className="athena-radio-content"
          dangerouslySetInnerHTML={{ __html: renderChoiceContent(content) }}
        />
      );
    }

    // Split content into parts: text and graphie images
    const parts: Array<{ type: 'text' | 'graphie'; content: string; alt?: string; url?: string }> = [];
    let lastIndex = 0;

    matches.forEach((match) => {
      const fullMatch = match[0];
      const alt = match[1];
      const url = match[2];
      const startIndex = match.index!;

      // Add text before this image
      if (startIndex > lastIndex) {
        const textContent = content.slice(lastIndex, startIndex);
        if (textContent.trim()) {
          parts.push({ type: 'text', content: textContent });
        }
      }

      // Add the graphie image
      parts.push({ type: 'graphie', content: fullMatch, alt, url });

      lastIndex = startIndex + fullMatch.length;
    });

    // Add remaining text after last image
    if (lastIndex < content.length) {
      const textContent = content.slice(lastIndex);
      if (textContent.trim()) {
        parts.push({ type: 'text', content: textContent });
      }
    }

    return (
      <span className="athena-radio-content">
        {parts.map((part, index) => {
          if (part.type === 'graphie' && part.url) {
            return (
              <GraphieImage
                key={index}
                url={part.url}
                alt={part.alt || ''}
                style={{ margin: '0.5rem 0', maxWidth: '100%' }}
              />
            );
          }
          // Regular text - process with existing function (but skip graphie images)
          const processedContent = renderChoiceContent(part.content);
          return (
            <span
              key={index}
              dangerouslySetInnerHTML={{ __html: processedContent }}
            />
          );
        })}
      </span>
    );
  };

  return (
    <BaseWidgetWrapper
      widgetId={widgetId}
      widgetType="radio"
      disabled={disabled}
      readOnly={readOnly}
      reviewMode={reviewMode}
    >
      <div
        ref={containerRef}
        className="athena-radio-group"
        role={isMultiSelect ? 'group' : 'radiogroup'}
        aria-labelledby={`${groupId}-label`}
      >
        <style>{`
          /* Specific fix for fixed graphs in dark mode */
          :root.dark .target-graph-fix,
          .dark .target-graph-fix,
          [data-theme="dark"] .target-graph-fix {
            filter: invert(1) hue-rotate(180deg) !important;
            mix-blend-mode: screen !important;
            background-color: transparent !important;
          }
        `}</style>
        {/* Instruction text */}
        <div
          className="athena-radio-instruction"
          style={{
            marginBottom: '12px',
            fontSize: '15px',
            fontWeight: 500,
            color: 'var(--athena-text, #333)',
          }}
        >
          {isMultiSelect ? 'Choose all answers that apply:' : 'Choose 1 answer:'}
        </div>

        {/* Fallback when no choices */}
        {displayOrder.length === 0 && (
          <div className="athena-radio-empty" style={{ color: '#999', fontStyle: 'italic' }}>
            No answer choices available
          </div>
        )}

        {displayOrder.map((originalIndex, displayIndex) => {
          const choice = options.choices?.[originalIndex];
          if (!choice) return null; // Safety check for undefined choice
          const selected = isSelected(originalIndex);
          const isCorrectChoice = correctIndices.has(originalIndex);

          let choiceClass = 'athena-radio-choice';
          if (selected) choiceClass += ' athena-radio-choice--selected';
          if (reviewMode && selected) {
            choiceClass += isCorrectChoice ? ' athena-radio-choice--correct' : ' athena-radio-choice--incorrect';
          }
          if (reviewMode && isCorrectChoice && !selected) {
            choiceClass += ' athena-radio-choice--missed-correct';
          }

          return (
            <div key={originalIndex} className={choiceClass}>
              <label className="athena-radio-label">
                <input
                  type={isMultiSelect ? 'checkbox' : 'radio'}
                  name={groupId}
                  checked={selected}
                  onChange={() => handleSelect(originalIndex)}
                  disabled={disabled || readOnly}
                  className="athena-radio-input"
                  aria-describedby={
                    reviewMode && choice.clue ? `${groupId}-clue-${originalIndex}` : undefined
                  }
                />

                <span className="athena-radio-indicator">
                  {isMultiSelect ? (
                    <CheckboxIcon checked={selected} />
                  ) : (
                    <RadioIcon checked={selected} />
                  )}
                </span>

                <ChoiceContent content={choice.content} />

                {/* Review mode indicators */}
                {reviewMode && (
                  <span className="athena-radio-status">
                    {selected && isCorrectChoice && <CorrectIcon />}
                    {selected && !isCorrectChoice && <IncorrectIcon />}
                    {!selected && isCorrectChoice && <MissedIcon />}
                  </span>
                )}
              </label>

              {/* Show clue in review mode if incorrect */}
              {reviewMode && selected && !isCorrectChoice && choice.clue && (
                <div
                  id={`${groupId}-clue-${originalIndex}`}
                  className="athena-radio-clue"
                  role="note"
                >
                  {choice.clue}
                </div>
              )}

              {/* None of the above indicator */}
              {choice.isNoneOfTheAbove && (
                <span className="athena-radio-nota-indicator">(None of the above)</span>
              )}
            </div>
          );
        })}
      </div>
    </BaseWidgetWrapper>
  );
}

// Icons
function RadioIcon({ checked }: { checked: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <circle cx="9" cy="9" r="8" fill="none" stroke="currentColor" strokeWidth="2" />
      {checked && <circle cx="9" cy="9" r="4" fill="currentColor" />}
    </svg>
  );
}

function CheckboxIcon({ checked }: { checked: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <rect x="1" y="1" width="16" height="16" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
      {checked && (
        <path d="M4 9l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

function CorrectIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="correct-icon" aria-label="Correct">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  );
}

function IncorrectIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="incorrect-icon" aria-label="Incorrect">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  );
}

function MissedIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="missed-icon" aria-label="Missed correct answer">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" opacity="0.5" />
    </svg>
  );
}

export default RadioWidget;

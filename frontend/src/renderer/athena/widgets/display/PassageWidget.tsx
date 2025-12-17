/**
 * Passage Widget
 *
 * Display reading passages with:
 * - Line numbers
 * - Text highlighting
 * - Footnotes
 */

import React, { useMemo, useCallback, useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { PassageOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { MarkdownProcessor } from '../../core/MarkdownProcessor';

// Base URL for resolving relative asset URLs (from backend API)
const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

export interface PassageWidgetProps extends WidgetProps<PassageOptions> {}

export function PassageWidget({
  widgetId,
  widget,
  theme = 'light',
}: PassageWidgetProps) {
  const options = widget.options || {};
  const [selectedLineRange, setSelectedLineRange] = useState<[number, number] | null>(null);

  // Helper function to process image URLs
  const processImageUrl = (url: string): string => {
    let imageUrl = url.trim().replace(/[)\s]+$/, '');

    // Handle CDN URLs without extension
    if (imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) {
      if (!imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
        imageUrl = imageUrl + '.png';
      }
    }
    // Handle web+graphie:// URLs
    else if (imageUrl.startsWith('web+graphie://')) {
      imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
    }
    // Handle relative URLs
    else if (imageUrl.startsWith('/')) {
      imageUrl = ASSETS_BASE_URL + imageUrl;
    }

    return imageUrl;
  };

  // Convert image markdown to HTML img tag
  const convertImageToHtml = (alt: string, url: string): string => {
    const imageUrl = processImageUrl(url);
    // Note: Using data-fallback pattern instead of onerror (which gets stripped by sanitizer)
    return `<img src="${imageUrl}" alt="${alt}" class="athena-passage-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" data-original-url="${url}" />`;
  };

  // Pre-process the passage: convert ALL image markdown to HTML BEFORE splitting into lines
  const { lines, processedText } = useMemo(() => {
    if (!options.passageText) return { lines: [], processedText: '' };

    let text = options.passageText;

    console.log('[PassageWidget] Raw passageText:', text.substring(0, 500));

    // DEBUG: Check for image markdown
    if (text.includes('![')) {
      const imageMatch = text.match(/!\[[^\]]*\]\([^)]{0,150}/);
      console.log('[PassageWidget] FOUND IMAGE MARKDOWN:', imageMatch?.[0]);
    }

    // First normalize all line breaks to \n
    text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // STEP 1: Convert ALL image markdown to HTML tags BEFORE any line splitting
    // This handles multiline URLs by processing the entire text at once

    // Pattern A: Join multiline URLs first - URL split with hyphen
    text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]*?)-\n\s*([^\s)\n]+)/g, (_, alt, urlPart1, urlPart2) => {
      const fullUrl = urlPart1 + '-' + urlPart2;
      console.log('[PassageWidget] Pre-process: Joined hyphen-split URL:', fullUrl);
      return `![${alt}](${fullUrl})`;
    });

    // Pattern B: Join multiline URLs - general case (iterate to handle multiple)
    let prevText = '';
    let iterations = 0;
    while (prevText !== text && iterations < 10) {
      prevText = text;
      iterations++;
      text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]*?)\s*\n\s*([^\s)\n]+)/g, (_, alt, urlPart1, urlPart2) => {
        const fullUrl = urlPart1 + urlPart2;
        console.log('[PassageWidget] Pre-process: Joined multiline URL:', fullUrl);
        return `![${alt}](${fullUrl})`;
      });
    }

    // Pattern C: Standard image with closing paren - ![alt](url)
    text = text.replace(/!\[([^\]]*)\]\(([^)\s\n]+)\)/g, (_, alt, url) => {
      console.log('[PassageWidget] Pre-process: Standard image:', url);
      return convertImageToHtml(alt, url);
    });

    // Pattern D: Image without closing paren at end of line - ![alt](url
    text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s\n]+)$/gm, (_, alt, url) => {
      console.log('[PassageWidget] Pre-process: Image without closing paren (end of line):', url);
      return convertImageToHtml(alt, url);
    });

    // Pattern E: Image without closing paren followed by newline - ![alt](url\n
    text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s\n]+)\n/g, (_, alt, url) => {
      console.log('[PassageWidget] Pre-process: Image without closing paren (before newline):', url);
      return convertImageToHtml(alt, url) + '\n';
    });

    // Pattern F: Catch remaining ![](url patterns (empty alt)
    text = text.replace(/!\[\]\((https?:\/\/[^\s)\n]+)/g, (_, url) => {
      console.log('[PassageWidget] Pre-process: Empty alt image:', url);
      return convertImageToHtml('', url);
    });

    // Pattern G: Last resort - any remaining ![...]( followed by CDN/Perseus URL
    text = text.replace(/!\[([^\]]*)\]\(([^)\s]*(?:cdn\.kastatic|ka-perseus)[^\s)\n]*)/g, (_, alt, url) => {
      console.log('[PassageWidget] Pre-process: Last resort CDN image:', url);
      return convertImageToHtml(alt, url);
    });

    // NUCLEAR OPTION: Replace ANY remaining ![...](url) patterns
    // This catches everything that slipped through previous patterns
    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
      console.log('[PassageWidget] Nuclear: Standard image pattern:', url.substring(0, 80));
      return convertImageToHtml(alt, url);
    });

    // NUCLEAR FALLBACK: Any remaining ![]( followed by URL characters
    text = text.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s<\n]+)/g, (_, alt, url) => {
      console.log('[PassageWidget] Nuclear fallback: Truncated URL:', url.substring(0, 80));
      return convertImageToHtml(alt, url.replace(/[)\s]+$/, ''));
    });

    // Check for any remaining raw image markdown
    if (text.includes('![') && text.includes('](')) {
      console.log('[PassageWidget] WARNING: Still has raw image markdown after ALL processing');
      // Log the first occurrence for debugging
      const match = text.match(/!\[[^\]]*\]\([^)]{0,100}/);
      if (match) {
        console.log('[PassageWidget] Remaining markdown:', match[0]);
      }
    }

    console.log('[PassageWidget] After pre-processing:', text.substring(0, 500));

    return { lines: text.split('\n'), processedText: text };
  }, [options.passageText]);

  // Process each line - images are already converted to HTML, just process other markdown
  const processedLines = useMemo(() => {
    console.log('[PassageWidget] Processing lines:', lines.length);

    return lines.map((line, index) => {
      let processed = line;

      // Images are already converted to HTML in pre-processing
      // Just process remaining markdown (bold, italic, links, etc.)
      // but skip image processing in MarkdownProcessor since we've already done it

      // Simple inline markdown processing (avoid re-processing images)
      // Bold
      processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      // Italic
      processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');
      // Inline code
      processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
      // Links (but not images - negative lookbehind)
      processed = processed.replace(/(?<!!)\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

      return processed;
    });
  }, [lines]);

  // Process footnotes
  const footnotes = useMemo(() => {
    if (!options.footnotes) return [];

    // Parse footnotes (format: [1] Footnote text)
    const footnotePattern = /\[(\d+)\]\s*(.+)/g;
    const matches: Array<{ num: number; text: string }> = [];
    let match;

    const text = options.footnotes;
    while ((match = footnotePattern.exec(text)) !== null) {
      matches.push({
        num: parseInt(match[1], 10),
        text: match[2],
      });
    }

    return matches;
  }, [options.footnotes]);

  // Handle line click for highlighting
  const handleLineClick = useCallback((lineNum: number, event: React.MouseEvent) => {
    if (event.shiftKey && selectedLineRange) {
      // Extend selection
      const start = Math.min(selectedLineRange[0], lineNum);
      const end = Math.max(selectedLineRange[1], lineNum);
      setSelectedLineRange([start, end]);
    } else {
      // New selection or toggle
      if (selectedLineRange && selectedLineRange[0] === lineNum && selectedLineRange[1] === lineNum) {
        setSelectedLineRange(null);
      } else {
        setSelectedLineRange([lineNum, lineNum]);
      }
    }
  }, [selectedLineRange]);

  // Check if line is in selected range
  const isLineSelected = useCallback((lineNum: number) => {
    if (!selectedLineRange) return false;
    return lineNum >= selectedLineRange[0] && lineNum <= selectedLineRange[1];
  }, [selectedLineRange]);

  // Process passageTitle for images
  const processedTitle = useMemo(() => {
    if (!options.passageTitle) return '';
    let title = options.passageTitle;

    // Process image markdown in title
    if (title.includes('![')) {
      title = title.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
        let imageUrl = url.trim();
        if (imageUrl.startsWith('web+graphie://')) {
          imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
        } else if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
                   !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
          imageUrl = imageUrl + '.png';
        }
        console.log('[PassageWidget] Processing title image:', imageUrl);
        return `<img src="${imageUrl}" alt="${alt}" class="athena-passage-title-image" style="max-width:100%;height:auto;display:block;margin:0.5rem 0;" referrerpolicy="no-referrer" />`;
      });

      // Also handle truncated URLs
      title = title.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s\n<]+)/g, (_, alt, url) => {
        let imageUrl = url.trim().replace(/[)\s]+$/, '');
        if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
            !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
          imageUrl = imageUrl + '.png';
        }
        console.log('[PassageWidget] Processing title image (truncated):', imageUrl);
        return `<img src="${imageUrl}" alt="${alt}" class="athena-passage-title-image" style="max-width:100%;height:auto;display:block;margin:0.5rem 0;" referrerpolicy="no-referrer" />`;
      });
    }

    // Process bold/italic
    title = title.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    title = title.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    return title;
  }, [options.passageTitle]);

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="passage">
      <article className="athena-passage">
        {/* Title */}
        {options.passageTitle && (
          <header className="athena-passage-header">
            <h2
              className="athena-passage-title"
              dangerouslySetInnerHTML={{ __html: processedTitle }}
            />
          </header>
        )}

        {/* Passage content */}
        <div
          className={`athena-passage-content ${
            options.showLineNumbers ? 'with-line-numbers' : ''
          }`}
        >
          {processedLines.map((lineHtml, index) => {
            const lineNum = index + 1;
            const isSelected = isLineSelected(lineNum);
            const isEmpty = lines[index].trim() === '';

            return (
              <div
                key={index}
                className={`athena-passage-line ${isSelected ? 'selected' : ''} ${
                  isEmpty ? 'empty' : ''
                }`}
                onClick={(e) => handleLineClick(lineNum, e)}
              >
                {options.showLineNumbers && (
                  <span
                    className="athena-passage-line-number"
                    aria-hidden="true"
                  >
                    {lineNum}
                  </span>
                )}
                <span
                  className="athena-passage-line-text"
                  dangerouslySetInnerHTML={{ __html: lineHtml || '&nbsp;' }}
                />
              </div>
            );
          })}
        </div>

        {/* Footnotes */}
        {footnotes.length > 0 && (
          <footer className="athena-passage-footnotes">
            <h3 className="athena-passage-footnotes-title">Footnotes</h3>
            <ol className="athena-passage-footnotes-list">
              {footnotes.map((footnote) => (
                <li
                  key={footnote.num}
                  id={`${widgetId}-footnote-${footnote.num}`}
                  className="athena-passage-footnote"
                >
                  {footnote.text}
                </li>
              ))}
            </ol>
          </footer>
        )}

        {/* Selection info */}
        {selectedLineRange && (
          <div className="athena-passage-selection-info" role="status" aria-live="polite">
            {selectedLineRange[0] === selectedLineRange[1]
              ? `Line ${selectedLineRange[0]} selected`
              : `Lines ${selectedLineRange[0]}-${selectedLineRange[1]} selected`}
            <button
              type="button"
              className="athena-passage-clear-selection"
              onClick={() => setSelectedLineRange(null)}
              aria-label="Clear selection"
            >
              Clear
            </button>
          </div>
        )}
      </article>
    </BaseWidgetWrapper>
  );
}

export default PassageWidget;

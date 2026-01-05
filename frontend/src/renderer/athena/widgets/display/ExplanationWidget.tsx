/**
 * Explanation Widget
 *
 * Collapsible explanation that can be expanded.
 */

import React, { useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { processContent } from '../../utils/ContentRendererUtils';

interface ExplanationOptions {
  showPrompt?: string;
  hidePrompt?: string;
  explanation: string;
  widgets?: Record<string, unknown>;
}

export interface ExplanationWidgetProps extends WidgetProps<ExplanationOptions> { }

export function ExplanationWidget({
  widgetId,
  widget,
  theme = 'light',
}: ExplanationWidgetProps) {
  const options = widget.options || {};
  const [expanded, setExpanded] = useState(false);

  const themeStyles = {
    light: { bg: '#f9fafb', border: '#e5e7eb', text: '#374151', accent: '#3b82f6' },
    dark: { bg: '#374151', border: '#4b5563', text: '#f3f4f6', accent: '#60a5fa' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff', accent: '#fff' },
  }[theme];

  const formatExplanationContent = (content: string) => {
    if (!content) return '';

    // If the content looks like a list but doesn't have bullet points, add them
    // This handles the case where multiple lines start with common instruction words
    const lines = content.split('\n');
    const listStarters = ['If', 'You', "Don't", 'When', 'Note'];

    // Count how many lines start with these words
    const matches = lines.filter(line =>
      listStarters.some(starter => line.trim().startsWith(starter))
    ).length;

    // If more than 3 lines look like list items and there are no existing bullets
    const hasExistingBullets = lines.some(line => /^\s*[*+-]\s/.test(line));

    let processedContent = content;
    if (matches >= 3 && !hasExistingBullets) {
      processedContent = lines.map(line => {
        const trimmed = line.trim();
        if (listStarters.some(starter => trimmed.startsWith(starter))) {
          return `* ${trimmed}`;
        }
        return line;
      }).join('\n');
    }

    return processContent(processedContent);
  };

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="explanation">
      <div className="athena-explanation">
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: 'transparent',
            border: `1px solid ${themeStyles.border}`,
            borderRadius: '4px',
            color: themeStyles.accent,
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500,
          }}
        >
          <span style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>
            ▶
          </span>
          {expanded ? (options.hidePrompt || 'Hide explanation') : (options.showPrompt || 'Show explanation')}
        </button>

        {expanded && (
          <div
            style={{
              marginTop: '12px',
              padding: '16px',
              backgroundColor: themeStyles.bg,
              border: `1px solid ${themeStyles.border}`,
              borderRadius: '8px',
              color: themeStyles.text,
              fontSize: '14px',
              lineHeight: 1.6,
            }}
          >
            <div
              className="athena-explanation-content"
              dangerouslySetInnerHTML={{
                __html: formatExplanationContent(options.explanation || 'No explanation provided')
              }}
            />
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default ExplanationWidget;

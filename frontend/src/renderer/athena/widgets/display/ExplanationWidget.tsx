/**
 * Explanation Widget
 *
 * Collapsible explanation that can be expanded.
 */

import React, { useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

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
              whiteSpace: 'pre-wrap',
            }}
          >
            <div dangerouslySetInnerHTML={{
              __html: (options.explanation || 'No explanation provided')
                // Parse Links: [text](url)
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:#1865f2;text-decoration:none;">$1</a>')
                // Parse Bold: **text**
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                // Parse Italic: *text* or _text_
                .replace(/(?<!\*)\*([^*]+)\*(?!\*)|_([^_]+)_/g, '<em>$1$2</em>')
                // Convert newlines to breaks
                .replace(/\n/g, '<br />')
            }} />
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default ExplanationWidget;

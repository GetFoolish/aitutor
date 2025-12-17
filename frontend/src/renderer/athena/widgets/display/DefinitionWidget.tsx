/**
 * Definition Widget
 *
 * Expandable term definitions that can be toggled.
 */

import React, { useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

interface DefinitionOptions {
  togglePrompt?: string;  // Perseus uses togglePrompt for the displayed term
  term?: string;          // Legacy support
  definition?: string;
}

export interface DefinitionWidgetProps extends WidgetProps<DefinitionOptions> {}

export function DefinitionWidget({
  widgetId,
  widget,
  theme = 'light',
}: DefinitionWidgetProps) {
  const options = widget.options || {};
  const [expanded, setExpanded] = useState(false);

  const themeStyles = {
    light: { bg: '#eff6ff', border: '#3b82f6', text: '#1e40af' },
    dark: { bg: '#1e3a5f', border: '#60a5fa', text: '#93c5fd' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="definition" inline>
      <span
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'inline',
          cursor: 'pointer',
          color: themeStyles.text,
          borderBottom: `2px dotted ${themeStyles.border}`,
          fontWeight: 500,
        }}
        title="Click for definition"
      >
        {options.togglePrompt || options.term || '[Term]'}
        {expanded && (
          <span
            style={{
              display: 'inline-block',
              marginLeft: '8px',
              padding: '4px 8px',
              backgroundColor: themeStyles.bg,
              borderRadius: '4px',
              fontSize: '14px',
              fontWeight: 'normal',
            }}
          >
            {options.definition || 'No definition provided'}
          </span>
        )}
      </span>
    </BaseWidgetWrapper>
  );
}

export default DefinitionWidget;

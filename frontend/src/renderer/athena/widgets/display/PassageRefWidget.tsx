/**
 * Passage Reference Widget
 *
 * References specific lines in a passage.
 */

import React from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

interface PassageRefOptions {
  passageNumber?: number;
  referenceNumber?: number;
  summaryText?: string;
}

export interface PassageRefWidgetProps extends WidgetProps<PassageRefOptions> {}

export function PassageRefWidget({
  widgetId,
  widget,
  theme = 'light',
}: PassageRefWidgetProps) {
  const options = widget.options || {};

  const themeStyles = {
    light: { bg: '#fef3c7', text: '#92400e' },
    dark: { bg: '#78350f', text: '#fef3c7' },
    'high-contrast': { bg: '#ff0', text: '#000' },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="passage-ref">
      <span
        style={{
          display: 'inline',
          padding: '2px 6px',
          backgroundColor: themeStyles.bg,
          color: themeStyles.text,
          borderRadius: '4px',
          fontSize: '14px',
          fontWeight: 500,
        }}
        title={`Reference to passage ${options.passageNumber || 1}`}
      >
        {options.summaryText || `[Ref ${options.referenceNumber || 1}]`}
      </span>
    </BaseWidgetWrapper>
  );
}

export default PassageRefWidget;

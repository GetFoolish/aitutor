/**
 * Free Response Widget
 *
 * Open-ended text input for free-form answers.
 */

import React, { useState, useCallback } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

interface FreeResponseOptions {
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
  rows?: number;
}

export interface FreeResponseWidgetProps extends WidgetProps<FreeResponseOptions> {}

export function FreeResponseWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  theme = 'light',
}: FreeResponseWidgetProps) {
  const options = widget.options || {};
  const [text, setText] = useState((value as string) || '');

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      setText(newValue);
      onChange?.(newValue);
    },
    [onChange]
  );

  const themeStyles = {
    light: { bg: '#fff', border: '#e5e7eb', text: '#374151' },
    dark: { bg: '#374151', border: '#4b5563', text: '#f3f4f6' },
    'high-contrast': { bg: '#000', border: '#fff', text: '#fff' },
  }[theme];

  const charCount = text.length;
  const minLength = options.minLength || 0;
  const maxLength = options.maxLength || 1000;

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="free-response">
      <div className="athena-free-response">
        <textarea
          value={text}
          onChange={handleChange}
          placeholder={options.placeholder || 'Type your response here...'}
          disabled={disabled || readOnly}
          rows={options.rows || 5}
          maxLength={maxLength}
          style={{
            width: '100%',
            padding: '12px',
            border: `2px solid ${themeStyles.border}`,
            borderRadius: '8px',
            backgroundColor: themeStyles.bg,
            color: themeStyles.text,
            fontSize: '16px',
            lineHeight: 1.5,
            resize: 'vertical',
            minHeight: '120px',
          }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: '8px',
            fontSize: '14px',
            color: '#6b7280',
          }}
        >
          <span>
            {charCount < minLength && (
              <span style={{ color: '#ef4444' }}>
                {minLength - charCount} more characters required
              </span>
            )}
          </span>
          <span>
            {charCount}/{maxLength} characters
          </span>
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

export default FreeResponseWidget;

import React, { useCallback, useMemo } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { processContent } from '../../utils/ContentRendererUtils';
import { HtmlWithInlineWidgets } from '../../components/HtmlWithInlineWidgets';

interface GroupOptions {
  content?: string;
  widgets?: Record<string, any>;
  images?: Record<string, any>;
  title?: string;
}

export function GroupWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly = false,
  reviewMode = false,
  theme = 'light',
}: WidgetProps<GroupOptions>) {
  const options = widget.options || {};
  const content = options.content || '';
  const innerWidgets = options.widgets || {};

  // Current state of inner widgets
  const groupState = useMemo(() => {
    return (value as Record<string, unknown>) || {};
  }, [value]);

  // Handle inner widget answer change
  const handleAnswerChange = useCallback((innerWidgetId: string, newValue: unknown) => {
    if (onChange) {
      onChange({
        ...groupState,
        [innerWidgetId]: newValue,
      });
    }
  }, [groupState, onChange]);

  // Process content
  const processedContent = useMemo(() => {
    return processContent(content);
  }, [content]);

  // Mock state object for HtmlWithInlineWidgets
  const mockState = useMemo(() => ({
    answers: groupState,
    hintsVisible: 0,
    reviewMode,
    showSolutions: 'none',
    readOnly,
    theme,
  }), [groupState, reviewMode, readOnly, theme]);

  return (
    <BaseWidgetWrapper 
      widgetId={widgetId} 
      widgetType="group"
      className="athena-group-widget"
    >
      <div className={`athena-group-container ${options.title ? 'has-title' : ''}`}>
        {options.title && (
          <div className="athena-group-title">
            {options.title}
          </div>
        )}
        
        <div className="athena-group-content">
          <HtmlWithInlineWidgets
            html={processedContent}
            widgets={innerWidgets}
            keyPrefix={`${widgetId}-inner`}
            state={mockState as any}
            setAnswer={handleAnswerChange}
          />
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

export default GroupWidget;

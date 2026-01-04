import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { useAthena } from '../AthenaContext';
import { WidgetFactory } from '../widgets/WidgetFactory';
import { GraphieImage } from '../widgets/display/GraphieImage';

interface HtmlWithInlineWidgetsProps {
  html: string;
  keyPrefix: string;
  widgets: Record<string, any>;
  state?: any;
  setAnswer?: (widgetId: string, value: any) => void;
}

export const HtmlWithInlineWidgets = React.memo(({ html, keyPrefix, widgets, state: propsState, setAnswer: propsSetAnswer }: HtmlWithInlineWidgetsProps) => {
  const context = useAthena();
  
  // Use props if provided (for nested widgets like GroupWidget), otherwise use context
  const state = propsState || context.state;
  const setAnswer = propsSetAnswer || context.setAnswer;

  const containerRef = useRef<HTMLDivElement>(null);
  const [widgetMounts, setWidgetMounts] = useState<Array<{ el: HTMLElement; widgetId: string }>>([]);
  const [graphieMounts, setGraphieMounts] = useState<Array<{ el: HTMLElement; url: string; alt: string }>>([]);

  console.log('[Athena] HtmlWithInlineWidgets rendering:', {
    keyPrefix,
    htmlLength: html.length,
    htmlPreview: html.substring(0, 500),
  });

  // After initial render, find widget and graphie placeholders in the DOM
  useEffect(() => {
    if (!containerRef.current) return;

    // Find widget placeholders
    const placeholders = containerRef.current.querySelectorAll('.athena-widget-inline[data-widget-id]');
    const mounts: Array<{ el: HTMLElement; widgetId: string }> = [];

    placeholders.forEach((el) => {
      const widgetId = el.getAttribute('data-widget-id');
      if (widgetId) {
        mounts.push({ el: el as HTMLElement, widgetId });
      }
    });

    console.log('[Athena] Found widget placeholders:', mounts.length);
    if (mounts.length > 0) {
      setWidgetMounts(mounts);
    }

    // Find graphie image placeholders
    const graphiePlaceholders = containerRef.current.querySelectorAll('.athena-graphie-placeholder[data-graphie-url]');
    const gMounts: Array<{ el: HTMLElement; url: string; alt: string }> = [];

    graphiePlaceholders.forEach((el) => {
      const url = el.getAttribute('data-graphie-url');
      const alt = el.getAttribute('data-graphie-alt') || '';
      if (url) {
        gMounts.push({ el: el as HTMLElement, url, alt });
      }
    });

    console.log('[Athena] Found graphie placeholders:', gMounts.length);
    if (gMounts.length > 0) {
      setGraphieMounts(gMounts);
    }
  }, [html]);

  // Render widgets into their placeholders using portals
  const widgetPortals = widgetMounts.map(({ el, widgetId }, idx) => {
    const widget = widgets[widgetId];
    if (!widget) {
      return ReactDOM.createPortal(
        <span className="athena-widget-error">[Widget not found: {widgetId}]</span>,
        el,
        `${keyPrefix}-portal-${idx}`
      );
    }

    const safeWidget = {
      ...widget,
      options: widget.options || {},
      type: widget.type || 'unknown',
    };
    const userValue = state.answers[widgetId];
    const isReadOnly = state.readOnly || (safeWidget.static ?? false);

    return ReactDOM.createPortal(
      <WidgetFactory
        widgetId={widgetId}
        widget={safeWidget as any}
        value={userValue}
        onChange={(value) => !isReadOnly && setAnswer(widgetId, value)}
        readOnly={isReadOnly}
        reviewMode={state.reviewMode}
        theme={state.theme}
      />,
      el,
      `${keyPrefix}-portal-${idx}`
    );
  });

  // Render graphie images into their placeholders using portals
  const graphiePortals = graphieMounts.map(({ el, url, alt }, idx) => {
    return ReactDOM.createPortal(
      <GraphieImage
        url={url}
        alt={alt}
        style={{ maxWidth: '100%' }}
      />,
      el,
      `${keyPrefix}-graphie-portal-${idx}`
    );
  });

  return (
    <>
      <div
        ref={containerRef}
        className="athena-inline-widgets-container"
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {widgetPortals}
      {graphiePortals}
    </>
  );
});

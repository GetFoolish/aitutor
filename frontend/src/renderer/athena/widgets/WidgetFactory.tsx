/**
 * Widget Factory
 *
 * Dynamically instantiates widget components based on type.
 * Handles lazy loading and error boundaries.
 */

import React, { Suspense, useMemo } from 'react';
import { WidgetRegistry, type WidgetProps, registerDefaultWidgets } from './WidgetRegistry';
import type { AthenaWidget, WidgetType } from '../core/types';

// Ensure default widgets are registered
registerDefaultWidgets();

export interface WidgetFactoryProps extends Omit<WidgetProps, 'widget'> {
  /** Widget type (overrides widget.type) */
  type?: WidgetType | string;
  /** Widget configuration */
  widget: AthenaWidget;
  /** Loading fallback */
  loadingFallback?: React.ReactNode;
  /** Error fallback */
  errorFallback?: React.ReactNode;
}

/**
 * Factory component for rendering widgets
 */
export function WidgetFactory({
  type,
  widget,
  widgetId,
  loadingFallback,
  errorFallback,
  ...props
}: WidgetFactoryProps) {
  const widgetType = type || widget.type;

  // Get component from registry
  const Component = useMemo(() => {
    return WidgetRegistry.getComponent(widgetType);
  }, [widgetType]);

  // Default loading fallback
  const loading = loadingFallback ?? (
    <div className="athena-widget-loading">
      <div className="athena-widget-loading-spinner" />
      <span className="athena-widget-loading-text">Loading widget...</span>
    </div>
  );

  // If component not found
  if (!Component) {
    return (
      errorFallback ?? (
        <div className="athena-widget-error">
          <strong>Unknown widget type:</strong> {widgetType}
        </div>
      )
    );
  }

  return (
    <WidgetErrorBoundary
      widgetId={widgetId}
      widgetType={widgetType}
      fallback={errorFallback}
    >
      <Suspense fallback={loading}>
        <Component widgetId={widgetId} widget={widget} {...props} />
      </Suspense>
    </WidgetErrorBoundary>
  );
}

/**
 * Error boundary for widgets
 */
interface WidgetErrorBoundaryProps {
  widgetId: string;
  widgetType: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

interface WidgetErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class WidgetErrorBoundary extends React.Component<
  WidgetErrorBoundaryProps,
  WidgetErrorBoundaryState
> {
  constructor(props: WidgetErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): WidgetErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error(
      `Widget error [${this.props.widgetType}:${this.props.widgetId}]:`,
      error,
      errorInfo
    );
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="athena-widget-error">
            <strong>Widget Error</strong>
            <p>
              Failed to render {this.props.widgetType} widget (ID:{' '}
              {this.props.widgetId})
            </p>
            {this.state.error && (
              <details>
                <summary>Error details</summary>
                <pre>{this.state.error.message}</pre>
              </details>
            )}
          </div>
        )
      );
    }

    return this.props.children;
  }
}

/**
 * Render multiple widgets
 */
export function WidgetList({
  widgets,
  values,
  onChange,
  ...props
}: {
  widgets: Record<string, AthenaWidget>;
  values?: Record<string, unknown>;
  onChange?: (widgetId: string, value: unknown) => void;
} & Omit<WidgetFactoryProps, 'widget' | 'widgetId' | 'value' | 'onChange'>) {
  return (
    <>
      {Object.entries(widgets).map(([widgetId, widget]) => (
        <WidgetFactory
          key={widgetId}
          widgetId={widgetId}
          widget={widget}
          value={values?.[widgetId]}
          onChange={(value) => onChange?.(widgetId, value)}
          {...props}
        />
      ))}
    </>
  );
}

/**
 * Hook for rendering a widget
 */
export function useWidget(
  widgetId: string,
  widget: AthenaWidget,
  options?: {
    value?: unknown;
    onChange?: (value: unknown) => void;
    readOnly?: boolean;
    reviewMode?: boolean;
  }
) {
  const Component = useMemo(() => {
    return WidgetRegistry.getComponent(widget.type);
  }, [widget.type]);

  const render = useMemo(() => {
    if (!Component) {
      return () => null;
    }

    return (additionalProps?: Partial<WidgetProps>) => (
      <Suspense fallback={<div>Loading...</div>}>
        <Component
          widgetId={widgetId}
          widget={widget}
          value={options?.value}
          onChange={options?.onChange}
          readOnly={options?.readOnly}
          reviewMode={options?.reviewMode}
          {...additionalProps}
        />
      </Suspense>
    );
  }, [Component, widgetId, widget, options]);

  return {
    Component,
    render,
    isRegistered: !!Component,
    isGradable: WidgetRegistry.isGradable(widget.type),
    isStatic: WidgetRegistry.isStatic(widget.type),
  };
}

export default WidgetFactory;

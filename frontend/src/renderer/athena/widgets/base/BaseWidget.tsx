/**
 * Base Widget
 *
 * Base component and utilities for creating widgets.
 */

import React, { useCallback, useId, useMemo } from 'react';
import type { AthenaWidget, WidgetType } from '../../core/types';
import type { WidgetProps } from '../WidgetRegistry';

export interface UseWidgetStateOptions<T> {
  /** Initial value */
  initialValue?: T;
  /** Callback when value changes */
  onChange?: (value: T) => void;
  /** Whether to validate on change */
  validateOnChange?: boolean;
  /** Custom validation function */
  validate?: (value: T) => string | null;
}

/**
 * Hook for managing widget state
 */
export function useWidgetState<T>(
  initialValue: T | undefined,
  onChange?: (value: T) => void,
  options?: UseWidgetStateOptions<T>
) {
  const [internalValue, setInternalValue] = React.useState<T | undefined>(
    initialValue ?? options?.initialValue
  );
  const [error, setError] = React.useState<string | null>(null);
  const [touched, setTouched] = React.useState(false);

  // Use external value if provided, otherwise internal
  const value = initialValue !== undefined ? initialValue : internalValue;

  const handleChange = useCallback(
    (newValue: T) => {
      setTouched(true);
      setInternalValue(newValue);

      // Validate if needed
      if (options?.validateOnChange && options.validate) {
        const validationError = options.validate(newValue);
        setError(validationError);
      }

      // Notify parent
      onChange?.(newValue);
    },
    [onChange, options]
  );

  const handleBlur = useCallback(() => {
    setTouched(true);

    // Validate on blur
    if (options?.validate && value !== undefined) {
      const validationError = options.validate(value);
      setError(validationError);
    }
  }, [options, value]);

  const reset = useCallback(() => {
    setInternalValue(options?.initialValue);
    setError(null);
    setTouched(false);
  }, [options?.initialValue]);

  return {
    value,
    setValue: handleChange,
    error,
    setError,
    touched,
    setTouched,
    onBlur: handleBlur,
    reset,
    isDirty: value !== options?.initialValue,
  };
}

/**
 * Hook for generating unique IDs for widget elements
 */
export function useWidgetId(prefix: string) {
  const baseId = useId();
  return useMemo(() => `${prefix}-${baseId}`, [prefix, baseId]);
}

/**
 * Hook for widget ARIA attributes
 */
export function useWidgetAria(options: {
  widgetId: string;
  widgetType: WidgetType | string;
  label?: string;
  description?: string;
  required?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
}) {
  const describedById = useWidgetId(`${options.widgetId}-desc`);
  const labelId = useWidgetId(`${options.widgetId}-label`);
  const errorId = useWidgetId(`${options.widgetId}-error`);

  return {
    labelId,
    describedById,
    errorId,
    containerProps: {
      role: 'group',
      'aria-labelledby': options.label ? labelId : undefined,
      'aria-describedby': options.description ? describedById : undefined,
    },
    inputProps: {
      'aria-required': options.required,
      'aria-invalid': options.invalid,
      'aria-disabled': options.disabled,
      'aria-readonly': options.readOnly,
    },
  };
}

/**
 * Base widget wrapper component
 */
export interface BaseWidgetWrapperProps {
  widgetId: string;
  widgetType: WidgetType | string;
  className?: string;
  label?: string;
  description?: string;
  error?: string | null;
  required?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
  reviewMode?: boolean;
  /** Render as inline element (for dropdowns, etc.) */
  inline?: boolean;
  children: React.ReactNode;
}

export function BaseWidgetWrapper({
  widgetId,
  widgetType,
  className = '',
  label,
  description,
  error,
  required,
  disabled,
  readOnly,
  reviewMode,
  inline = false,
  children,
}: BaseWidgetWrapperProps) {
  const { labelId, describedById, errorId, containerProps } = useWidgetAria({
    widgetId,
    widgetType,
    label,
    description,
    required,
    invalid: !!error,
    disabled,
    readOnly,
  });

  const Tag = inline ? 'span' : 'div';

  return (
    <Tag
      className={`athena-widget athena-widget-${widgetType} ${className} ${
        disabled ? 'disabled' : ''
      } ${readOnly ? 'readonly' : ''} ${reviewMode ? 'review-mode' : ''} ${
        error ? 'has-error' : ''
      } ${inline ? 'athena-widget-inline' : ''}`}
      data-widget-id={widgetId}
      data-widget-type={widgetType}
      {...containerProps}
    >
      {label && (
        <label id={labelId} className="athena-widget-label">
          {label}
          {required && <span className="athena-widget-required">*</span>}
        </label>
      )}

      {description && (
        <div id={describedById} className="athena-widget-description">
          {description}
        </div>
      )}

      {inline ? (
        children
      ) : (
        <div className="athena-widget-content">{children}</div>
      )}

      {error && (
        <div id={errorId} className="athena-widget-error" role="alert">
          {error}
        </div>
      )}
    </Tag>
  );
}

/**
 * Create a widget component with common functionality
 */
export function createWidget<TOptions, TValue>(
  displayName: string,
  render: (props: {
    widgetId: string;
    options: TOptions;
    value: TValue | undefined;
    onChange: (value: TValue) => void;
    state: ReturnType<typeof useWidgetState<TValue>>;
    readOnly: boolean;
    disabled: boolean;
    reviewMode: boolean;
    theme: 'light' | 'dark' | 'high-contrast';
  }) => React.ReactElement
) {
  const WidgetComponent: React.FC<WidgetProps<TOptions>> = ({
    widgetId,
    widget,
    value,
    onChange,
    readOnly = false,
    disabled = false,
    reviewMode = false,
    theme = 'light',
  }) => {
    const state = useWidgetState<TValue>(
      value as TValue | undefined,
      onChange as ((value: TValue) => void) | undefined
    );

    return render({
      widgetId,
      options: widget.options as TOptions,
      value: value as TValue | undefined,
      onChange: state.setValue,
      state,
      readOnly: readOnly || widget.static,
      disabled,
      reviewMode,
      theme,
    });
  };

  WidgetComponent.displayName = displayName;

  return WidgetComponent;
}

export default BaseWidgetWrapper;

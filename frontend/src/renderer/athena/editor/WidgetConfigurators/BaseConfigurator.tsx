/**
 * Base Widget Configurator
 *
 * Base components and utilities for widget configuration UIs.
 */

import React, { useState, useCallback } from 'react';
import type { AthenaWidget, WidgetType } from '../../core/types';

export interface ConfiguratorProps<T extends Record<string, unknown> = Record<string, unknown>> {
  /** Widget being configured */
  widget: AthenaWidget;
  /** Widget ID */
  widgetId: string;
  /** Called when widget options change */
  onChange: (options: T) => void;
  /** Called when configuration is complete */
  onDone?: () => void;
  /** Whether configurator is disabled */
  disabled?: boolean;
  /** Custom class name */
  className?: string;
}

export interface ConfiguratorFieldProps {
  /** Field label */
  label: string;
  /** Help text */
  help?: string;
  /** Whether field is required */
  required?: boolean;
  /** Whether field has error */
  error?: string;
  /** Children */
  children: React.ReactNode;
  /** Custom class name */
  className?: string;
}

/**
 * Field wrapper component
 */
export function ConfiguratorField({
  label,
  help,
  required,
  error,
  children,
  className = '',
}: ConfiguratorFieldProps) {
  return (
    <div className={`athena-configurator-field ${error ? 'athena-configurator-field--error' : ''} ${className}`}>
      <label className="athena-configurator-label">
        {label}
        {required && <span className="athena-configurator-required">*</span>}
      </label>
      {children}
      {help && !error && (
        <span className="athena-configurator-help">{help}</span>
      )}
      {error && (
        <span className="athena-configurator-error">{error}</span>
      )}
    </div>
  );
}

/**
 * Section component for grouping fields
 */
export function ConfiguratorSection({
  title,
  description,
  children,
  collapsible = false,
  defaultExpanded = true,
  className = '',
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  className?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`athena-configurator-section ${className}`}>
      <div
        className={`athena-configurator-section-header ${collapsible ? 'athena-configurator-section-header--collapsible' : ''}`}
        onClick={collapsible ? () => setIsExpanded(!isExpanded) : undefined}
      >
        <h4 className="athena-configurator-section-title">{title}</h4>
        {collapsible && (
          <span className={`athena-configurator-section-toggle ${isExpanded ? 'athena-configurator-section-toggle--open' : ''}`}>
            ▼
          </span>
        )}
      </div>
      {description && (
        <p className="athena-configurator-section-description">{description}</p>
      )}
      {(!collapsible || isExpanded) && (
        <div className="athena-configurator-section-content">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Text input component
 */
export function ConfiguratorInput({
  value,
  onChange,
  type = 'text',
  placeholder,
  disabled,
  min,
  max,
  step,
  className = '',
}: {
  value: string | number;
  onChange: (value: string) => void;
  type?: 'text' | 'number' | 'email' | 'url';
  placeholder?: string;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      min={min}
      max={max}
      step={step}
      className={`athena-configurator-input ${className}`}
    />
  );
}

/**
 * Textarea component
 */
export function ConfiguratorTextarea({
  value,
  onChange,
  placeholder,
  disabled,
  rows = 4,
  className = '',
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
  className?: string;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      rows={rows}
      className={`athena-configurator-textarea ${className}`}
    />
  );
}

/**
 * Checkbox component
 */
export function ConfiguratorCheckbox({
  checked,
  onChange,
  label,
  disabled,
  className = '',
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <label className={`athena-configurator-checkbox ${className}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="athena-configurator-checkbox-label">{label}</span>
    </label>
  );
}

/**
 * Select component
 */
export function ConfiguratorSelect<T extends string = string>({
  value,
  onChange,
  options,
  placeholder,
  disabled,
  className = '',
}: {
  value: T;
  onChange: (value: T) => void;
  options: Array<{ value: T; label: string }>;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      disabled={disabled}
      className={`athena-configurator-select ${className}`}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

/**
 * Number input with stepper
 */
export function ConfiguratorNumber({
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled,
  className = '',
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  className?: string;
}) {
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    if (!isNaN(newValue)) {
      onChange(newValue);
    }
  }, [onChange]);

  const handleIncrement = useCallback(() => {
    const newValue = value + step;
    if (max === undefined || newValue <= max) {
      onChange(newValue);
    }
  }, [value, step, max, onChange]);

  const handleDecrement = useCallback(() => {
    const newValue = value - step;
    if (min === undefined || newValue >= min) {
      onChange(newValue);
    }
  }, [value, step, min, onChange]);

  return (
    <div className={`athena-configurator-number ${className}`}>
      <button
        type="button"
        className="athena-configurator-number-btn"
        onClick={handleDecrement}
        disabled={disabled || (min !== undefined && value <= min)}
      >
        −
      </button>
      <input
        type="number"
        value={value}
        onChange={handleChange}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className="athena-configurator-number-input"
      />
      <button
        type="button"
        className="athena-configurator-number-btn"
        onClick={handleIncrement}
        disabled={disabled || (max !== undefined && value >= max)}
      >
        +
      </button>
    </div>
  );
}

/**
 * Array editor component for lists of items
 */
export function ConfiguratorArray<T>({
  items,
  onChange,
  renderItem,
  createItem,
  maxItems,
  minItems = 0,
  addLabel = 'Add Item',
  disabled,
  className = '',
}: {
  items: T[];
  onChange: (items: T[]) => void;
  renderItem: (item: T, index: number, update: (item: T) => void, remove: () => void) => React.ReactNode;
  createItem: () => T;
  maxItems?: number;
  minItems?: number;
  addLabel?: string;
  disabled?: boolean;
  className?: string;
}) {
  const handleAdd = useCallback(() => {
    if (maxItems && items.length >= maxItems) return;
    onChange([...items, createItem()]);
  }, [items, maxItems, createItem, onChange]);

  const handleUpdate = useCallback((index: number, item: T) => {
    const newItems = [...items];
    newItems[index] = item;
    onChange(newItems);
  }, [items, onChange]);

  const handleRemove = useCallback((index: number) => {
    if (items.length <= minItems) return;
    onChange(items.filter((_, i) => i !== index));
  }, [items, minItems, onChange]);

  const handleMove = useCallback((fromIndex: number, toIndex: number) => {
    const newItems = [...items];
    const [removed] = newItems.splice(fromIndex, 1);
    newItems.splice(toIndex, 0, removed);
    onChange(newItems);
  }, [items, onChange]);

  return (
    <div className={`athena-configurator-array ${className}`}>
      <div className="athena-configurator-array-items">
        {items.map((item, index) => (
          <div key={index} className="athena-configurator-array-item">
            <div className="athena-configurator-array-item-handle">
              {index > 0 && (
                <button
                  type="button"
                  className="athena-configurator-array-move"
                  onClick={() => handleMove(index, index - 1)}
                  disabled={disabled}
                >
                  ↑
                </button>
              )}
              {index < items.length - 1 && (
                <button
                  type="button"
                  className="athena-configurator-array-move"
                  onClick={() => handleMove(index, index + 1)}
                  disabled={disabled}
                >
                  ↓
                </button>
              )}
            </div>
            <div className="athena-configurator-array-item-content">
              {renderItem(
                item,
                index,
                (updated) => handleUpdate(index, updated),
                () => handleRemove(index)
              )}
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="athena-configurator-array-add"
        onClick={handleAdd}
        disabled={disabled || (maxItems !== undefined && items.length >= maxItems)}
      >
        + {addLabel}
      </button>
    </div>
  );
}

/**
 * Base configurator wrapper
 */
export function BaseConfigurator({
  title,
  children,
  onDone,
  className = '',
}: {
  title: string;
  children: React.ReactNode;
  onDone?: () => void;
  className?: string;
}) {
  return (
    <div className={`athena-configurator ${className}`}>
      <div className="athena-configurator-header">
        <h3 className="athena-configurator-title">{title}</h3>
      </div>
      <div className="athena-configurator-body">
        {children}
      </div>
      {onDone && (
        <div className="athena-configurator-footer">
          <button
            type="button"
            className="athena-configurator-btn athena-configurator-btn--primary"
            onClick={onDone}
          >
            Done
          </button>
        </div>
      )}
    </div>
  );
}

export default BaseConfigurator;

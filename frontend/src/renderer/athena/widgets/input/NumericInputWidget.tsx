/**
 * Numeric Input Widget
 *
 * Accepts numeric answers with support for:
 * - Integer and decimal values
 * - Fractions
 * - Scientific notation
 */

import React, { useCallback, useRef, useId, useMemo, useState } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { NumericInputOptions } from '../../core/types';
import { BaseWidgetWrapper, useWidgetState } from '../base/BaseWidget';

export interface NumericInputWidgetProps extends WidgetProps<NumericInputOptions> {}

// Validation helper
function validateNumericInput(value: string, options: NumericInputOptions): { isValid: boolean; message: string | null } {
  if (!value || value.trim() === '') {
    return { isValid: true, message: null };
  }

  const trimmed = value.trim();

  // Check for fraction format (e.g., 1/2)
  if (trimmed.includes('/')) {
    const parts = trimmed.split('/');
    if (parts.length !== 2) {
      return { isValid: false, message: 'Invalid fraction format. Use format: numerator/denominator' };
    }
    const [num, den] = parts;
    if (isNaN(Number(num)) || isNaN(Number(den))) {
      return { isValid: false, message: 'Fraction must contain numbers only' };
    }
    if (Number(den) === 0) {
      return { isValid: false, message: 'Denominator cannot be zero' };
    }
    return { isValid: true, message: null };
  }

  // Check for scientific notation (e.g., 1e5, 2.5E-3)
  if (trimmed.toLowerCase().includes('e')) {
    const sciRegex = /^-?\d+\.?\d*e[+-]?\d+$/i;
    if (!sciRegex.test(trimmed)) {
      return { isValid: false, message: 'Invalid scientific notation. Use format: 1.5e10' };
    }
    return { isValid: true, message: null };
  }

  // Check for valid number
  if (isNaN(Number(trimmed))) {
    return { isValid: false, message: 'Please enter a valid number' };
  }

  // Check for integer requirement
  if (options.simplify === 'required' && trimmed.includes('.')) {
    return { isValid: false, message: 'Please enter a whole number' };
  }

  return { isValid: true, message: null };
}

export function NumericInputWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly = false,
  disabled = false,
  reviewMode = false,
  theme = 'light',
}: NumericInputWidgetProps) {
  const options = widget.options || {};
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const state = useWidgetState<string>(
    value as string | undefined,
    onChange as ((value: string) => void) | undefined
  );

  const [showValidation, setShowValidation] = useState(false);

  // Validate input
  const validation = useMemo(() => {
    return validateNumericInput(state.value || '', options);
  }, [state.value, options]);

  // Get format hint based on options
  const formatHint = useMemo(() => {
    const hints: string[] = [];
    if (options.coefficient) {
      hints.push('coefficient');
    }
    // Check answer types from answers array
    const answerTypes = options.answers?.map(a => a.answerType || 'number') || [];
    if (answerTypes.includes('pi')) {
      hints.push('You can use π or "pi"');
    }
    if (answerTypes.some(t => t === 'rational' || t === 'improper' || t === 'mixed')) {
      hints.push('Fractions accepted (e.g., 1/2)');
    }
    if (answerTypes.includes('percent')) {
      hints.push('Enter as percentage');
    }
    return hints.join(' • ');
  }, [options]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      state.setValue(e.target.value);
    },
    [state]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      // Allow: backspace, delete, tab, escape, enter, decimal point, minus
      if (
        [8, 46, 9, 27, 13, 110, 190, 189, 109].includes(e.keyCode) ||
        // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
        (e.keyCode === 65 && e.ctrlKey) ||
        (e.keyCode === 67 && e.ctrlKey) ||
        (e.keyCode === 86 && e.ctrlKey) ||
        (e.keyCode === 88 && e.ctrlKey) ||
        // Allow: home, end, left, right
        (e.keyCode >= 35 && e.keyCode <= 39)
      ) {
        return;
      }

      // Allow numbers
      if (
        (e.shiftKey && e.keyCode >= 48 && e.keyCode <= 57) ||
        (e.keyCode >= 48 && e.keyCode <= 57) ||
        (e.keyCode >= 96 && e.keyCode <= 105)
      ) {
        return;
      }

      // Allow slash for fractions
      if (e.keyCode === 191 || e.keyCode === 111) {
        return;
      }

      // Allow 'e' for scientific notation
      if (e.keyCode === 69) {
        return;
      }

      // Prevent default for other keys
      e.preventDefault();
    },
    []
  );

  // Get correct answer for review mode
  const correctAnswer = reviewMode
    ? options.answers?.find((a) => a.status === 'correct')?.value
    : undefined;

  const isCorrect = reviewMode && correctAnswer !== undefined
    ? Math.abs(parseFloat(state.value || '') - correctAnswer) < 1e-9 // Use tolerance
    : undefined;

  // Note: Don't render label here - the question content already includes the label text
  // before the widget placeholder (e.g., "Your answer: [[☃ numeric-input 1]]")
  return (
    <BaseWidgetWrapper
      widgetId={widgetId}
      widgetType="numeric-input"
      disabled={disabled}
      readOnly={readOnly}
      reviewMode={reviewMode}
      className={`athena-numeric-input-${options.size || 'normal'}`}
    >
      <div className="athena-numeric-input-container">
        {options.coefficient && (
          <span className="athena-numeric-input-coefficient">×</span>
        )}

        <input
          ref={inputRef}
          id={inputId}
          type="text"
          inputMode="decimal"
          className={`athena-numeric-input-field ${
            options.rightAlign ? 'right-align' : ''
          } ${isCorrect === true ? 'correct' : ''} ${
            isCorrect === false ? 'incorrect' : ''
          } ${!validation.isValid && showValidation ? 'validation-error' : ''}`}
          value={state.value || ''}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            state.onBlur?.();
            setShowValidation(true);
          }}
          onFocus={() => setShowValidation(false)}
          disabled={disabled}
          readOnly={readOnly}
          aria-label={options.labelText || 'Answer'}
          aria-invalid={(!validation.isValid && showValidation) ? 'true' : undefined}
          aria-describedby={formatHint ? `${inputId}-hint` : undefined}
          placeholder=""
        />

        {/* Format hint */}
        {formatHint && !reviewMode && (
          <div
            id={`${inputId}-hint`}
            className="athena-numeric-input-hint"
            style={{
              fontSize: '12px',
              color: '#666',
              marginTop: '4px',
            }}
          >
            {formatHint}
          </div>
        )}

        {/* Validation feedback */}
        {!validation.isValid && showValidation && (
          <div
            className="athena-numeric-input-validation"
            role="alert"
            style={{
              fontSize: '13px',
              color: '#dc2626',
              marginTop: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {validation.message}
          </div>
        )}

        {reviewMode && correctAnswer !== undefined && (
          <div className="athena-numeric-input-correct-answer">
            Correct answer: {correctAnswer}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default NumericInputWidget;

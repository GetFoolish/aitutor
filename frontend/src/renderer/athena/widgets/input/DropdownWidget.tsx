/**
 * Dropdown Widget
 *
 * Select from a list of choices.
 */

import React, { useCallback, useId } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { DropdownOptions } from '../../core/types';
import { BaseWidgetWrapper, useWidgetState } from '../base/BaseWidget';

export interface DropdownWidgetProps extends WidgetProps<DropdownOptions> {}

export function DropdownWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly = false,
  disabled = false,
  reviewMode = false,
  theme = 'light',
}: DropdownWidgetProps) {
  const options = widget.options || {};
  const selectId = useId();

  const state = useWidgetState<number>(
    value as number | undefined,
    onChange as ((value: number) => void) | undefined
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const selectedIndex = parseInt(e.target.value, 10);
      state.setValue(selectedIndex);
    },
    [state]
  );

  // Find correct choice index for review mode
  const correctIndex = reviewMode
    ? options.choices?.findIndex((choice) => choice.correct)
    : -1;

  const isCorrect = reviewMode && state.value !== undefined
    ? state.value === correctIndex
    : undefined;

  return (
    <BaseWidgetWrapper
      widgetId={widgetId}
      widgetType="dropdown"
      disabled={disabled}
      readOnly={readOnly}
      reviewMode={reviewMode}
      inline={true}
    >
      <span className="athena-dropdown-container" style={{ display: 'inline-flex', alignItems: 'center', verticalAlign: 'middle' }}>
        <select
          id={selectId}
          className={`athena-dropdown-select ${
            isCorrect === true ? 'correct' : ''
          } ${isCorrect === false ? 'incorrect' : ''}`}
          value={state.value ?? ''}
          onChange={handleChange}
          disabled={disabled || readOnly}
          aria-label={options.placeholder || 'Select an answer'}
        >
          <option value="" disabled>
            {options.placeholder || 'Select an answer'}
          </option>

          {options.choices?.map((choice, index) => (
            <option key={index} value={index}>
              {typeof choice === 'string' ? choice : choice.content}
            </option>
          ))}
        </select>

        <ChevronIcon />

        {/* Review mode: show correct answer indicator */}
        {reviewMode && state.value !== undefined && (
          <span className="athena-dropdown-status">
            {isCorrect ? (
              <CorrectIcon />
            ) : (
              <IncorrectIcon />
            )}
          </span>
        )}
      </span>

      {/* Review mode: show correct answer if wrong */}
      {reviewMode && isCorrect === false && correctIndex >= 0 && (
        <span className="athena-dropdown-correct-answer" style={{ marginLeft: '8px', color: '#22c55e' }}>
          (Correct: {(() => {
            const choice = options.choices?.[correctIndex];
            return typeof choice === 'string' ? choice : choice?.content;
          })()})
        </span>
      )}
    </BaseWidgetWrapper>
  );
}

function ChevronIcon() {
  return (
    <svg
      className="athena-dropdown-chevron"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CorrectIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="correct-icon">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  );
}

function IncorrectIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" className="incorrect-icon">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  );
}

export default DropdownWidget;

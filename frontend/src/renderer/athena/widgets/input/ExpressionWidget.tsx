/**
 * Expression Widget
 *
 * Math expression input widget with:
 * - MathQuill-based input
 * - Touch-friendly keypad
 * - LaTeX output
 */

import React, { useCallback, useRef } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { ExpressionOptions } from '../../core/types';
import { BaseWidgetWrapper, useWidgetState } from '../base/BaseWidget';
import { ExpressionInput, type ExpressionInputRef } from '../../math-input/ExpressionInput';
import type { ButtonSetId } from '../../math-input/ButtonSets';

export interface ExpressionWidgetProps extends WidgetProps<ExpressionOptions> {}

export function ExpressionWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly = false,
  disabled = false,
  reviewMode = false,
  theme = 'light',
  apiOptions,
}: ExpressionWidgetProps) {
  const options = widget.options || {};
  const inputRef = useRef<ExpressionInputRef>(null);

  const state = useWidgetState<string>(
    value as string | undefined,
    onChange as ((value: string) => void) | undefined
  );

  // Map button sets from options
  const buttonSets: ButtonSetId[] = (options.buttonSets || ['basic']).map(
    (set) => set as ButtonSetId
  );

  const handleChange = useCallback(
    (latex: string) => {
      state.setValue(latex);
    },
    [state]
  );

  const handleSubmit = useCallback(
    (latex: string) => {
      // Could trigger validation or submission
      state.setValue(latex);
    },
    [state]
  );

  // Get correct answer for review mode
  const correctAnswer = reviewMode
    ? options.answerForms?.find((form) => form.considered === 'correct')?.value
    : undefined;

  // Determine keypad position
  const keypadPosition = apiOptions?.isMobile ? 'bottom' : 'floating';

  return (
    <BaseWidgetWrapper
      widgetId={widgetId}
      widgetType="expression"
      disabled={disabled}
      readOnly={readOnly}
      reviewMode={reviewMode}
    >
      <ExpressionInput
        ref={inputRef}
        value={state.value || ''}
        onChange={handleChange}
        onSubmit={handleSubmit}
        readOnly={readOnly}
        disabled={disabled}
        placeholder="Enter your answer..."
        buttonSets={buttonSets}
        showKeypad={!readOnly && !disabled}
        keypadPosition={readOnly ? 'none' : keypadPosition}
        showKeypadToggle={!readOnly && !disabled}
        ariaLabel="Math expression input"
      />

      {/* Review mode: show correct answer */}
      {reviewMode && correctAnswer && (
        <div className="athena-expression-correct-answer">
          <span className="athena-expression-correct-label">Correct answer:</span>
          <span className="athena-expression-correct-value">{correctAnswer}</span>
        </div>
      )}

      {/* Hint about times symbol */}
      {options.times && !readOnly && (
        <div className="athena-expression-hint">
          Use × for multiplication
        </div>
      )}
    </BaseWidgetWrapper>
  );
}

export default ExpressionWidget;

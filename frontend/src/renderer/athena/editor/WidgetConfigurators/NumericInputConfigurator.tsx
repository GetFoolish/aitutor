/**
 * Numeric Input Configurator
 *
 * Configuration UI for numeric input widgets.
 */

import React, { useCallback } from 'react';
import {
  BaseConfigurator,
  ConfiguratorProps,
  ConfiguratorField,
  ConfiguratorSection,
  ConfiguratorInput,
  ConfiguratorNumber,
  ConfiguratorCheckbox,
  ConfiguratorSelect,
  ConfiguratorArray,
} from './BaseConfigurator';
import type { NumericInputOptions } from '../../core/types';

interface NumericAnswer {
  value: number;
  status: 'correct' | 'wrong' | 'ungraded';
  maxError?: number;
  simplify?: 'required' | 'optional' | 'enforced';
  message?: string;
}

// Using Record<string, unknown> compatible interface
interface NumericInputConfigOptions {
  [key: string]: unknown;
  answers: NumericAnswer[];
  size: 'small' | 'normal' | 'large';
  coefficient: boolean;
  labelText: string;
  rightAlign: boolean;
  static: boolean;
}

/**
 * Numeric input configurator
 */
export function NumericInputConfigurator({
  widget,
  widgetId,
  onChange,
  onDone,
  disabled,
  className = '',
}: ConfiguratorProps<NumericInputConfigOptions>) {
  const options = widget.options as NumericInputConfigOptions;

  // Update single option
  const updateOption = useCallback(<K extends keyof NumericInputConfigOptions>(
    key: K,
    value: NumericInputConfigOptions[K]
  ) => {
    onChange({ ...options, [key]: value });
  }, [options, onChange]);

  // Update answer
  const updateAnswer = useCallback((index: number, updates: Partial<NumericAnswer>) => {
    const newAnswers = [...(options.answers || [])];
    newAnswers[index] = { ...newAnswers[index], ...updates };
    updateOption('answers', newAnswers);
  }, [options.answers, updateOption]);

  // Add answer
  const addAnswer = useCallback(() => {
    const newAnswers = [
      ...(options.answers || []),
      { value: 0, status: 'correct' as const, maxError: 0 },
    ];
    updateOption('answers', newAnswers);
  }, [options.answers, updateOption]);

  // Remove answer
  const removeAnswer = useCallback((index: number) => {
    const newAnswers = (options.answers || []).filter((_, i) => i !== index);
    updateOption('answers', newAnswers);
  }, [options.answers, updateOption]);

  return (
    <BaseConfigurator
      title="Numeric Input Configuration"
      onDone={onDone}
      className={className}
    >
      {/* Answers section */}
      <ConfiguratorSection title="Answers" description="Configure correct and alternative answers">
        <ConfiguratorArray
          items={options.answers || []}
          onChange={(answers) => updateOption('answers', answers)}
          createItem={() => ({ value: 0, status: 'correct' as const, maxError: 0 })}
          minItems={1}
          maxItems={10}
          addLabel="Add Answer"
          disabled={disabled}
          renderItem={(answer, index, update, remove) => (
            <div className="athena-numeric-answer-item">
              <div className="athena-numeric-answer-row">
                <ConfiguratorField label="Value" required>
                  <ConfiguratorInput
                    type="number"
                    value={answer.value}
                    onChange={(v) => update({ ...answer, value: parseFloat(v) || 0 })}
                    disabled={disabled}
                  />
                </ConfiguratorField>

                <ConfiguratorField label="Status">
                  <ConfiguratorSelect
                    value={answer.status}
                    onChange={(v) => update({ ...answer, status: v as NumericAnswer['status'] })}
                    options={[
                      { value: 'correct', label: 'Correct' },
                      { value: 'wrong', label: 'Wrong' },
                      { value: 'ungraded', label: 'Ungraded' },
                    ]}
                    disabled={disabled}
                  />
                </ConfiguratorField>

                <ConfiguratorField label="Tolerance">
                  <ConfiguratorInput
                    type="number"
                    value={answer.maxError || 0}
                    onChange={(v) => update({ ...answer, maxError: parseFloat(v) || 0 })}
                    placeholder="0"
                    disabled={disabled}
                  />
                </ConfiguratorField>

                {(options.answers || []).length > 1 && (
                  <button
                    type="button"
                    className="athena-configurator-remove-btn"
                    onClick={remove}
                    disabled={disabled}
                    aria-label="Remove answer"
                  >
                    ×
                  </button>
                )}
              </div>

              <ConfiguratorField label="Custom message (optional)">
                <ConfiguratorInput
                  value={answer.message || ''}
                  onChange={(v) => update({ ...answer, message: v || undefined })}
                  placeholder="Feedback message for this answer"
                  disabled={disabled}
                />
              </ConfiguratorField>
            </div>
          )}
        />
      </ConfiguratorSection>

      {/* Display options */}
      <ConfiguratorSection title="Display Options" collapsible defaultExpanded={false}>
        <ConfiguratorField label="Input Size">
          <ConfiguratorSelect
            value={options.size || 'normal'}
            onChange={(v) => updateOption('size', v as NumericInputConfigOptions['size'])}
            options={[
              { value: 'small', label: 'Small' },
              { value: 'normal', label: 'Normal' },
              { value: 'large', label: 'Large' },
            ]}
            disabled={disabled}
          />
        </ConfiguratorField>

        <ConfiguratorField label="Label">
          <ConfiguratorInput
            value={options.labelText || ''}
            onChange={(v) => updateOption('labelText', v)}
            placeholder="Optional label text"
            disabled={disabled}
          />
        </ConfiguratorField>

        <ConfiguratorCheckbox
          checked={options.rightAlign || false}
          onChange={(v) => updateOption('rightAlign', v)}
          label="Right-align input"
          disabled={disabled}
        />

        <ConfiguratorCheckbox
          checked={options.coefficient || false}
          onChange={(v) => updateOption('coefficient', v)}
          label="Accept coefficient (e.g., '1' = 'x')"
          disabled={disabled}
        />
      </ConfiguratorSection>

      {/* Answer format options */}
      <ConfiguratorSection title="Answer Format" collapsible defaultExpanded={false}>
        <p className="athena-configurator-help-text">
          Configure what formats are accepted for answers.
        </p>

        <ConfiguratorCheckbox
          checked={options.static || false}
          onChange={(v) => updateOption('static', v)}
          label="Read-only (display only, not interactive)"
          disabled={disabled}
        />
      </ConfiguratorSection>
    </BaseConfigurator>
  );
}

export default NumericInputConfigurator;

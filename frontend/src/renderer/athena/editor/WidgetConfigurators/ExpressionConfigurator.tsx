/**
 * Expression Configurator
 *
 * Configuration UI for mathematical expression widgets.
 */

import React, { useCallback } from 'react';
import {
  BaseConfigurator,
  ConfiguratorProps,
  ConfiguratorField,
  ConfiguratorSection,
  ConfiguratorInput,
  ConfiguratorCheckbox,
  ConfiguratorSelect,
  ConfiguratorArray,
} from './BaseConfigurator';
import type { ExpressionOptions } from '../../core/types';

interface AnswerForm {
  value: string;
  form: boolean;
  simplify: boolean;
  considered?: 'correct' | 'wrong' | 'ungraded';
  key?: string;
}

// Using Record<string, unknown> compatible interface
interface ExpressionConfigOptions {
  [key: string]: unknown;
  answerForms: AnswerForm[];
  buttonSets: string[];
  functions: string[];
  times: boolean;
  visibleLabel?: string;
  ariaLabel?: string;
}

const BUTTON_SET_OPTIONS = [
  { value: 'basic', label: 'Basic (numbers, +, -, ×, ÷)' },
  { value: 'basic+div', label: 'Basic with fractions' },
  { value: 'trig', label: 'Trigonometry' },
  { value: 'prealgebra', label: 'Pre-algebra' },
  { value: 'logarithms', label: 'Logarithms' },
  { value: 'basic relations', label: 'Relations (<, >, =)' },
  { value: 'advanced relations', label: 'Advanced relations' },
];

/**
 * Expression configurator
 */
export function ExpressionConfigurator({
  widget,
  widgetId,
  onChange,
  onDone,
  disabled,
  className = '',
}: ConfiguratorProps<ExpressionConfigOptions>) {
  const options = widget.options as ExpressionConfigOptions;

  // Update single option
  const updateOption = useCallback(<K extends keyof ExpressionConfigOptions>(
    key: K,
    value: ExpressionConfigOptions[K]
  ) => {
    onChange({ ...options, [key]: value });
  }, [options, onChange]);

  // Toggle button set
  const toggleButtonSet = useCallback((set: string) => {
    const current = options.buttonSets || [];
    const newSets = current.includes(set)
      ? current.filter(s => s !== set)
      : [...current, set];
    updateOption('buttonSets', newSets);
  }, [options.buttonSets, updateOption]);

  return (
    <BaseConfigurator
      title="Expression Configuration"
      onDone={onDone}
      className={className}
    >
      {/* Answer forms section */}
      <ConfiguratorSection
        title="Correct Answers"
        description="Enter valid expressions. Multiple equivalent forms can be accepted."
      >
        <ConfiguratorArray
          items={options.answerForms || []}
          onChange={(forms) => updateOption('answerForms', forms)}
          createItem={() => ({ value: '', form: true, simplify: false, considered: 'correct' as const })}
          minItems={1}
          maxItems={10}
          addLabel="Add Answer Form"
          disabled={disabled}
          renderItem={(form, index, update, remove) => (
            <div className="athena-expression-form-item">
              <div className="athena-expression-form-row">
                <ConfiguratorField label="Expression" required>
                  <ConfiguratorInput
                    value={form.value}
                    onChange={(v) => update({ ...form, value: v })}
                    placeholder="e.g., x^2+2x+1 or (x+1)^2"
                    disabled={disabled}
                  />
                </ConfiguratorField>

                <ConfiguratorField label="Status">
                  <ConfiguratorSelect
                    value={form.considered || 'correct'}
                    onChange={(v) => update({ ...form, considered: v as AnswerForm['considered'] })}
                    options={[
                      { value: 'correct', label: 'Correct' },
                      { value: 'wrong', label: 'Wrong' },
                      { value: 'ungraded', label: 'Ungraded' },
                    ]}
                    disabled={disabled}
                  />
                </ConfiguratorField>

                {(options.answerForms || []).length > 1 && (
                  <button
                    type="button"
                    className="athena-configurator-remove-btn"
                    onClick={remove}
                    disabled={disabled}
                    aria-label="Remove answer form"
                  >
                    ×
                  </button>
                )}
              </div>

              <div className="athena-expression-form-options">
                <ConfiguratorCheckbox
                  checked={form.form}
                  onChange={(v) => update({ ...form, form: v })}
                  label="Check form (not just value)"
                  disabled={disabled}
                />
                <ConfiguratorCheckbox
                  checked={form.simplify}
                  onChange={(v) => update({ ...form, simplify: v })}
                  label="Require simplified"
                  disabled={disabled}
                />
              </div>

              {/* Preview */}
              {form.value && (
                <div className="athena-expression-preview">
                  <span className="athena-expression-preview-label">Preview:</span>
                  <span className="athena-expression-preview-value">{form.value}</span>
                </div>
              )}
            </div>
          )}
        />
      </ConfiguratorSection>

      {/* Button sets */}
      <ConfiguratorSection title="Keypad Buttons" description="Select which button sets to show">
        <div className="athena-expression-button-sets">
          {BUTTON_SET_OPTIONS.map((set) => (
            <ConfiguratorCheckbox
              key={set.value}
              checked={(options.buttonSets || []).includes(set.value)}
              onChange={() => toggleButtonSet(set.value)}
              label={set.label}
              disabled={disabled}
            />
          ))}
        </div>
      </ConfiguratorSection>

      {/* Display options */}
      <ConfiguratorSection title="Display Options" collapsible defaultExpanded={false}>
        <ConfiguratorCheckbox
          checked={options.times || false}
          onChange={(v) => updateOption('times', v)}
          label="Use × for multiplication (instead of ·)"
          disabled={disabled}
        />

        <ConfiguratorField label="Visible label">
          <ConfiguratorInput
            value={options.visibleLabel || ''}
            onChange={(v) => updateOption('visibleLabel', v || undefined)}
            placeholder="Label shown next to input"
            disabled={disabled}
          />
        </ConfiguratorField>

        <ConfiguratorField label="Screen reader label">
          <ConfiguratorInput
            value={options.ariaLabel || ''}
            onChange={(v) => updateOption('ariaLabel', v || undefined)}
            placeholder="Description for accessibility"
            disabled={disabled}
          />
        </ConfiguratorField>
      </ConfiguratorSection>

      {/* Custom functions */}
      <ConfiguratorSection title="Custom Functions" collapsible defaultExpanded={false}>
        <ConfiguratorField
          label="Additional functions"
          help="Comma-separated list of function names to allow (e.g., f, g, h)"
        >
          <ConfiguratorInput
            value={(options.functions || []).join(', ')}
            onChange={(v) => updateOption('functions', v.split(',').map(s => s.trim()).filter(Boolean))}
            placeholder="f, g, h"
            disabled={disabled}
          />
        </ConfiguratorField>
      </ConfiguratorSection>

      {/* Help section */}
      <ConfiguratorSection title="Help" collapsible defaultExpanded={false}>
        <div className="athena-configurator-help-block">
          <h5>Expression Format</h5>
          <ul>
            <li><code>x^2</code> - Exponents</li>
            <li><code>sqrt(x)</code> or <code>x^(1/2)</code> - Square root</li>
            <li><code>x/y</code> - Division/fractions</li>
            <li><code>sin(x)</code>, <code>cos(x)</code>, <code>tan(x)</code> - Trig functions</li>
            <li><code>log(x)</code>, <code>ln(x)</code> - Logarithms</li>
            <li><code>pi</code>, <code>e</code> - Constants</li>
          </ul>

          <h5>Equivalence Checking</h5>
          <p>
            The system checks if student answers are mathematically equivalent
            to correct answers. For example, <code>x+1</code> and <code>1+x</code> are
            treated as equivalent.
          </p>
          <p>
            Use "Check form" to require a specific format (e.g., factored vs expanded).
          </p>
        </div>
      </ConfiguratorSection>
    </BaseConfigurator>
  );
}

export default ExpressionConfigurator;

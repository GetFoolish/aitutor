/**
 * Radio (Multiple Choice) Configurator
 *
 * Configuration UI for radio/multiple choice widgets.
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
  ConfiguratorTextarea,
  ConfiguratorArray,
} from './BaseConfigurator';
import type { RadioOptions } from '../../core/types';

interface RadioChoice {
  content: string;
  correct?: boolean;
  clue?: string;
  isNoneOfTheAbove?: boolean;
}

// Using Record<string, unknown> compatible interface
interface RadioConfigOptions {
  [key: string]: unknown;
  choices: RadioChoice[];
  randomize: boolean;
  multipleSelect: boolean;
  displayCount: number | null;
  deselectEnabled: boolean;
  noneOfTheAbove: boolean;
}

/**
 * Radio configurator
 */
export function RadioConfigurator({
  widget,
  widgetId,
  onChange,
  onDone,
  disabled,
  className = '',
}: ConfiguratorProps<RadioConfigOptions>) {
  const options = widget.options as RadioConfigOptions;

  // Update single option
  const updateOption = useCallback(<K extends keyof RadioConfigOptions>(
    key: K,
    value: RadioConfigOptions[K]
  ) => {
    onChange({ ...options, [key]: value });
  }, [options, onChange]);

  // Add choice
  const addChoice = useCallback(() => {
    const newChoices = [
      ...(options.choices || []),
      { content: '', correct: false },
    ];
    updateOption('choices', newChoices);
  }, [options.choices, updateOption]);

  // Count correct answers
  const correctCount = (options.choices || []).filter(c => c.correct).length;

  return (
    <BaseConfigurator
      title="Multiple Choice Configuration"
      onDone={onDone}
      className={className}
    >
      {/* Choices section */}
      <ConfiguratorSection title="Answer Choices">
        <ConfiguratorArray
          items={options.choices || []}
          onChange={(choices) => updateOption('choices', choices)}
          createItem={() => ({ content: '', correct: false })}
          minItems={2}
          maxItems={10}
          addLabel="Add Choice"
          disabled={disabled}
          renderItem={(choice, index, update, remove) => (
            <div className={`athena-radio-choice-item ${choice.correct ? 'athena-radio-choice-item--correct' : ''}`}>
              <div className="athena-radio-choice-main">
                <ConfiguratorCheckbox
                  checked={choice.correct || false}
                  onChange={(v) => {
                    if (!options.multipleSelect) {
                      // Single select: uncheck others
                      const newChoices = (options.choices || []).map((c, i) => ({
                        ...c,
                        correct: i === index ? v : false,
                      }));
                      updateOption('choices', newChoices);
                    } else {
                      update({ ...choice, correct: v });
                    }
                  }}
                  label=""
                  disabled={disabled}
                />

                <div className="athena-radio-choice-content">
                  <ConfiguratorTextarea
                    value={choice.content}
                    onChange={(v) => update({ ...choice, content: v })}
                    placeholder={`Choice ${index + 1} content (supports Markdown and $math$)`}
                    rows={2}
                    disabled={disabled}
                  />
                </div>

                {(options.choices || []).length > 2 && (
                  <button
                    type="button"
                    className="athena-configurator-remove-btn"
                    onClick={remove}
                    disabled={disabled}
                    aria-label="Remove choice"
                  >
                    ×
                  </button>
                )}
              </div>

              {/* Clue/feedback */}
              <div className="athena-radio-choice-clue">
                <ConfiguratorInput
                  value={choice.clue || ''}
                  onChange={(v) => update({ ...choice, clue: v || undefined })}
                  placeholder="Optional: Feedback shown when this choice is selected"
                  disabled={disabled}
                />
              </div>
            </div>
          )}
        />

        {correctCount === 0 && (
          <div className="athena-configurator-warning">
            Warning: No correct answer selected!
          </div>
        )}

        {options.multipleSelect && correctCount < 2 && (
          <div className="athena-configurator-info">
            Tip: For multiple select, you can mark multiple choices as correct.
          </div>
        )}
      </ConfiguratorSection>

      {/* Selection options */}
      <ConfiguratorSection title="Selection Options" collapsible defaultExpanded={false}>
        <ConfiguratorCheckbox
          checked={options.multipleSelect || false}
          onChange={(v) => {
            // If switching from multi to single, keep only first correct
            if (!v && correctCount > 1) {
              let foundFirst = false;
              const newChoices = (options.choices || []).map(c => {
                if (c.correct && !foundFirst) {
                  foundFirst = true;
                  return c;
                }
                return { ...c, correct: false };
              });
              onChange({ ...options, multipleSelect: v, choices: newChoices });
            } else {
              updateOption('multipleSelect', v);
            }
          }}
          label="Allow multiple selections"
          disabled={disabled}
        />

        <ConfiguratorCheckbox
          checked={options.deselectEnabled || false}
          onChange={(v) => updateOption('deselectEnabled', v)}
          label="Allow deselecting (click selected to deselect)"
          disabled={disabled}
        />

        <ConfiguratorCheckbox
          checked={options.noneOfTheAbove || false}
          onChange={(v) => updateOption('noneOfTheAbove', v)}
          label="Add 'None of the above' option"
          disabled={disabled}
        />
      </ConfiguratorSection>

      {/* Display options */}
      <ConfiguratorSection title="Display Options" collapsible defaultExpanded={false}>
        <ConfiguratorCheckbox
          checked={options.randomize || false}
          onChange={(v) => updateOption('randomize', v)}
          label="Randomize choice order"
          disabled={disabled}
        />

        <ConfiguratorField
          label="Display count"
          help="Number of choices to show (leave empty to show all)"
        >
          <ConfiguratorInput
            type="number"
            value={options.displayCount || ''}
            onChange={(v) => updateOption('displayCount', v ? parseInt(v) : null)}
            placeholder="Show all"
            min={2}
            max={(options.choices || []).length}
            disabled={disabled}
          />
        </ConfiguratorField>
      </ConfiguratorSection>
    </BaseConfigurator>
  );
}

export default RadioConfigurator;

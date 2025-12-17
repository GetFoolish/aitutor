/**
 * ARIA Labels
 *
 * Utility functions for generating accessible labels.
 */

import type { WidgetType } from '../core/types';

/**
 * Get ARIA label for a widget type
 */
export function getWidgetAriaLabel(
  widgetType: WidgetType | string,
  context?: {
    problemNum?: number;
    widgetId?: string;
    label?: string;
  }
): string {
  const baseLabels: Record<string, string> = {
    'numeric-input': 'Enter a numeric answer',
    'input-number': 'Enter a number',
    radio: 'Select an answer',
    expression: 'Enter a mathematical expression',
    dropdown: 'Select from the options',
    'free-response': 'Enter your response',
    image: 'Image',
    passage: 'Reading passage',
    video: 'Video content',
    definition: 'Definition',
    explanation: 'Explanation',
    'interactive-graph': 'Interactive graph',
    grapher: 'Function grapher',
    plotter: 'Plot data points',
    table: 'Fill in the table',
    'number-line': 'Number line',
    measurer: 'Measurement tool',
    categorizer: 'Categorize items',
    sorter: 'Sort items in order',
    matcher: 'Match items',
    orderer: 'Order items',
    molecule: 'Molecule structure',
    'cs-program': 'Code editor',
    iframe: 'Interactive content',
  };

  let label = baseLabels[widgetType] || 'Interactive widget';

  if (context?.label) {
    label = context.label;
  }

  if (context?.problemNum) {
    label = `Question ${context.problemNum}: ${label}`;
  }

  return label;
}

/**
 * Get ARIA description for widget state
 */
export function getWidgetStateDescription(
  state: 'empty' | 'answered' | 'correct' | 'incorrect' | 'disabled' | 'readonly'
): string {
  const descriptions: Record<string, string> = {
    empty: 'Not yet answered',
    answered: 'Answer provided',
    correct: 'Answer is correct',
    incorrect: 'Answer is incorrect',
    disabled: 'This field is disabled',
    readonly: 'This field is read-only',
  };

  return descriptions[state] || '';
}

/**
 * Get ARIA label for hint button
 */
export function getHintButtonAriaLabel(
  hintsAvailable: number,
  hintsRevealed: number
): string {
  const remaining = hintsAvailable - hintsRevealed;
  if (remaining === 0) {
    return 'All hints have been revealed';
  }
  if (remaining === 1) {
    return 'Show hint (1 remaining)';
  }
  return `Show hint (${remaining} remaining)`;
}

/**
 * Get ARIA label for score result
 */
export function getScoreAriaLabel(
  correct: boolean,
  earned: number,
  total: number
): string {
  if (correct) {
    return `Correct! You earned ${earned} out of ${total} points.`;
  }
  return `Incorrect. You earned ${earned} out of ${total} points.`;
}

/**
 * Get ARIA live region announcement for state change
 */
export function getStateChangeAnnouncement(
  action: 'answered' | 'cleared' | 'submitted' | 'hint_revealed' | 'scored'
): string {
  const announcements: Record<string, string> = {
    answered: 'Answer recorded',
    cleared: 'Answer cleared',
    submitted: 'Answer submitted',
    hint_revealed: 'New hint revealed',
    scored: 'Your answer has been scored',
  };

  return announcements[action] || '';
}

/**
 * Format number for screen reader
 */
export function formatNumberForScreenReader(
  value: number,
  options?: {
    currency?: string;
    percent?: boolean;
    ordinal?: boolean;
  }
): string {
  if (options?.percent) {
    return `${value} percent`;
  }

  if (options?.currency) {
    return `${value} ${options.currency}`;
  }

  if (options?.ordinal) {
    const suffixes = ['th', 'st', 'nd', 'rd'];
    const v = value % 100;
    const suffix = suffixes[(v - 20) % 10] || suffixes[v] || suffixes[0];
    return `${value}${suffix}`;
  }

  return String(value);
}

/**
 * Format math expression for screen reader
 */
export function formatMathForScreenReader(latex: string): string {
  // Simple LaTeX to text conversion for common expressions
  let text = latex
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '$1 over $2')
    .replace(/\\sqrt\{([^}]+)\}/g, 'square root of $1')
    .replace(/\\sqrt\[([^\]]+)\]\{([^}]+)\}/g, '$1 root of $2')
    .replace(/\^2/g, ' squared')
    .replace(/\^3/g, ' cubed')
    .replace(/\^\{([^}]+)\}/g, ' to the power of $1')
    .replace(/\^(\d)/g, ' to the power of $1')
    .replace(/\\times/g, ' times ')
    .replace(/\\div/g, ' divided by ')
    .replace(/\\pm/g, ' plus or minus ')
    .replace(/\\leq/g, ' less than or equal to ')
    .replace(/\\geq/g, ' greater than or equal to ')
    .replace(/\\neq/g, ' not equal to ')
    .replace(/\\pi/g, ' pi ')
    .replace(/\\theta/g, ' theta ')
    .replace(/\\alpha/g, ' alpha ')
    .replace(/\\beta/g, ' beta ')
    .replace(/\\sin/g, ' sine of ')
    .replace(/\\cos/g, ' cosine of ')
    .replace(/\\tan/g, ' tangent of ')
    .replace(/\\log/g, ' log of ')
    .replace(/\\ln/g, ' natural log of ')
    .replace(/\\infty/g, ' infinity ')
    .replace(/\\sum/g, ' sum ')
    .replace(/\\int/g, ' integral ')
    .replace(/\\_\{([^}]+)\}/g, ' sub $1 ')
    .replace(/([a-zA-Z])_(\d)/g, '$1 sub $2')
    .replace(/\{/g, '')
    .replace(/\}/g, '')
    .replace(/\\/g, '');

  // Clean up extra spaces
  text = text.replace(/\s+/g, ' ').trim();

  return text;
}

/**
 * Get keyboard shortcut description
 */
export function getKeyboardShortcutDescription(
  action: string
): string {
  const shortcuts: Record<string, string> = {
    submit: 'Press Enter to submit',
    nextWidget: 'Press Tab to move to next input',
    prevWidget: 'Press Shift+Tab to move to previous input',
    showHint: 'Press H to show hint',
    clear: 'Press Escape to clear',
    undo: 'Press Ctrl+Z to undo',
    redo: 'Press Ctrl+Y or Ctrl+Shift+Z to redo',
  };

  return shortcuts[action] || '';
}

export default {
  getWidgetAriaLabel,
  getWidgetStateDescription,
  getHintButtonAriaLabel,
  getScoreAriaLabel,
  getStateChangeAnnouncement,
  formatNumberForScreenReader,
  formatMathForScreenReader,
  getKeyboardShortcutDescription,
};

/**
 * Button Sets
 *
 * Defines keypad button configurations for different math contexts.
 * Each button set contains buttons appropriate for that level of math.
 */

export interface MathButton {
  /** Unique identifier */
  id: string;
  /** Display label (can be LaTeX) */
  label: string;
  /** LaTeX to insert when pressed */
  latex: string;
  /** ARIA label for accessibility */
  ariaLabel: string;
  /** Button type for styling */
  type: 'number' | 'operator' | 'function' | 'symbol' | 'action' | 'variable';
  /** Optional width multiplier (default 1) */
  width?: number;
  /** Whether this moves cursor */
  moveCursor?: 'left' | 'right' | 'up' | 'down';
}

export interface ButtonSet {
  /** Set identifier */
  id: string;
  /** Display name */
  name: string;
  /** Buttons organized by rows */
  rows: MathButton[][];
  /** Whether to include basic numbers */
  includeNumbers?: boolean;
}

// ============================================================================
// Individual Buttons
// ============================================================================

const NUMBER_BUTTONS: MathButton[] = [
  { id: '7', label: '7', latex: '7', ariaLabel: '7', type: 'number' },
  { id: '8', label: '8', latex: '8', ariaLabel: '8', type: 'number' },
  { id: '9', label: '9', latex: '9', ariaLabel: '9', type: 'number' },
  { id: '4', label: '4', latex: '4', ariaLabel: '4', type: 'number' },
  { id: '5', label: '5', latex: '5', ariaLabel: '5', type: 'number' },
  { id: '6', label: '6', latex: '6', ariaLabel: '6', type: 'number' },
  { id: '1', label: '1', latex: '1', ariaLabel: '1', type: 'number' },
  { id: '2', label: '2', latex: '2', ariaLabel: '2', type: 'number' },
  { id: '3', label: '3', latex: '3', ariaLabel: '3', type: 'number' },
  { id: '0', label: '0', latex: '0', ariaLabel: '0', type: 'number' },
  { id: 'decimal', label: '.', latex: '.', ariaLabel: 'decimal point', type: 'number' },
  { id: 'negative', label: '−', latex: '-', ariaLabel: 'negative', type: 'operator' },
];

const BASIC_OPERATORS: MathButton[] = [
  { id: 'plus', label: '+', latex: '+', ariaLabel: 'plus', type: 'operator' },
  { id: 'minus', label: '−', latex: '-', ariaLabel: 'minus', type: 'operator' },
  { id: 'times', label: '×', latex: '\\times', ariaLabel: 'times', type: 'operator' },
  { id: 'divide', label: '÷', latex: '\\div', ariaLabel: 'divided by', type: 'operator' },
  { id: 'equals', label: '=', latex: '=', ariaLabel: 'equals', type: 'operator' },
];

const PARENTHESES: MathButton[] = [
  { id: 'leftParen', label: '(', latex: '(', ariaLabel: 'left parenthesis', type: 'symbol' },
  { id: 'rightParen', label: ')', latex: ')', ariaLabel: 'right parenthesis', type: 'symbol' },
];

const ACTION_BUTTONS: MathButton[] = [
  { id: 'backspace', label: '⌫', latex: '', ariaLabel: 'backspace', type: 'action' },
  { id: 'left', label: '←', latex: '', ariaLabel: 'move left', type: 'action', moveCursor: 'left' },
  { id: 'right', label: '→', latex: '', ariaLabel: 'move right', type: 'action', moveCursor: 'right' },
  { id: 'clear', label: 'C', latex: '', ariaLabel: 'clear all', type: 'action' },
];

// ============================================================================
// Button Sets
// ============================================================================

/**
 * Basic button set - Numbers and basic arithmetic
 */
export const BASIC_SET: ButtonSet = {
  id: 'basic',
  name: 'Basic',
  includeNumbers: true,
  rows: [
    [
      { id: '7', label: '7', latex: '7', ariaLabel: '7', type: 'number' },
      { id: '8', label: '8', latex: '8', ariaLabel: '8', type: 'number' },
      { id: '9', label: '9', latex: '9', ariaLabel: '9', type: 'number' },
      { id: 'divide', label: '÷', latex: '\\div', ariaLabel: 'divided by', type: 'operator' },
    ],
    [
      { id: '4', label: '4', latex: '4', ariaLabel: '4', type: 'number' },
      { id: '5', label: '5', latex: '5', ariaLabel: '5', type: 'number' },
      { id: '6', label: '6', latex: '6', ariaLabel: '6', type: 'number' },
      { id: 'times', label: '×', latex: '\\times', ariaLabel: 'times', type: 'operator' },
    ],
    [
      { id: '1', label: '1', latex: '1', ariaLabel: '1', type: 'number' },
      { id: '2', label: '2', latex: '2', ariaLabel: '2', type: 'number' },
      { id: '3', label: '3', latex: '3', ariaLabel: '3', type: 'number' },
      { id: 'minus', label: '−', latex: '-', ariaLabel: 'minus', type: 'operator' },
    ],
    [
      { id: '0', label: '0', latex: '0', ariaLabel: '0', type: 'number' },
      { id: 'decimal', label: '.', latex: '.', ariaLabel: 'decimal point', type: 'number' },
      { id: 'equals', label: '=', latex: '=', ariaLabel: 'equals', type: 'operator' },
      { id: 'plus', label: '+', latex: '+', ariaLabel: 'plus', type: 'operator' },
    ],
    [
      { id: 'leftParen', label: '(', latex: '(', ariaLabel: 'left parenthesis', type: 'symbol' },
      { id: 'rightParen', label: ')', latex: ')', ariaLabel: 'right parenthesis', type: 'symbol' },
      { id: 'backspace', label: '⌫', latex: '', ariaLabel: 'backspace', type: 'action' },
      { id: 'clear', label: 'C', latex: '', ariaLabel: 'clear all', type: 'action' },
    ],
  ],
};

/**
 * Algebra button set - Variables, exponents, fractions
 */
export const ALGEBRA_SET: ButtonSet = {
  id: 'algebra',
  name: 'Algebra',
  rows: [
    [
      { id: 'x', label: 'x', latex: 'x', ariaLabel: 'x', type: 'variable' },
      { id: 'y', label: 'y', latex: 'y', ariaLabel: 'y', type: 'variable' },
      { id: 'z', label: 'z', latex: 'z', ariaLabel: 'z', type: 'variable' },
      { id: 'n', label: 'n', latex: 'n', ariaLabel: 'n', type: 'variable' },
    ],
    [
      { id: 'power', label: 'x^n', latex: '^{ }', ariaLabel: 'exponent', type: 'operator' },
      { id: 'squared', label: 'x²', latex: '^2', ariaLabel: 'squared', type: 'operator' },
      { id: 'cubed', label: 'x³', latex: '^3', ariaLabel: 'cubed', type: 'operator' },
      { id: 'sqrt', label: '√', latex: '\\sqrt{ }', ariaLabel: 'square root', type: 'function' },
    ],
    [
      { id: 'fraction', label: 'a/b', latex: '\\frac{ }{ }', ariaLabel: 'fraction', type: 'operator' },
      { id: 'subscript', label: 'xₙ', latex: '_{ }', ariaLabel: 'subscript', type: 'operator' },
      { id: 'abs', label: '|x|', latex: '\\left| \\right|', ariaLabel: 'absolute value', type: 'function' },
      { id: 'nthroot', label: 'ⁿ√', latex: '\\sqrt[n]{ }', ariaLabel: 'nth root', type: 'function' },
    ],
    [
      { id: 'leq', label: '≤', latex: '\\leq', ariaLabel: 'less than or equal', type: 'operator' },
      { id: 'geq', label: '≥', latex: '\\geq', ariaLabel: 'greater than or equal', type: 'operator' },
      { id: 'neq', label: '≠', latex: '\\neq', ariaLabel: 'not equal', type: 'operator' },
      { id: 'plusminus', label: '±', latex: '\\pm', ariaLabel: 'plus or minus', type: 'operator' },
    ],
  ],
};

/**
 * Trigonometry button set - Trig functions and pi
 */
export const TRIG_SET: ButtonSet = {
  id: 'trig',
  name: 'Trig',
  rows: [
    [
      { id: 'sin', label: 'sin', latex: '\\sin\\left( \\right)', ariaLabel: 'sine', type: 'function' },
      { id: 'cos', label: 'cos', latex: '\\cos\\left( \\right)', ariaLabel: 'cosine', type: 'function' },
      { id: 'tan', label: 'tan', latex: '\\tan\\left( \\right)', ariaLabel: 'tangent', type: 'function' },
    ],
    [
      { id: 'arcsin', label: 'sin⁻¹', latex: '\\sin^{-1}\\left( \\right)', ariaLabel: 'arc sine', type: 'function' },
      { id: 'arccos', label: 'cos⁻¹', latex: '\\cos^{-1}\\left( \\right)', ariaLabel: 'arc cosine', type: 'function' },
      { id: 'arctan', label: 'tan⁻¹', latex: '\\tan^{-1}\\left( \\right)', ariaLabel: 'arc tangent', type: 'function' },
    ],
    [
      { id: 'csc', label: 'csc', latex: '\\csc\\left( \\right)', ariaLabel: 'cosecant', type: 'function' },
      { id: 'sec', label: 'sec', latex: '\\sec\\left( \\right)', ariaLabel: 'secant', type: 'function' },
      { id: 'cot', label: 'cot', latex: '\\cot\\left( \\right)', ariaLabel: 'cotangent', type: 'function' },
    ],
    [
      { id: 'pi', label: 'π', latex: '\\pi', ariaLabel: 'pi', type: 'symbol' },
      { id: 'theta', label: 'θ', latex: '\\theta', ariaLabel: 'theta', type: 'variable' },
      { id: 'degree', label: '°', latex: '^\\circ', ariaLabel: 'degree', type: 'symbol' },
    ],
  ],
};

/**
 * Calculus button set - Integrals, derivatives, limits
 */
export const CALCULUS_SET: ButtonSet = {
  id: 'calculus',
  name: 'Calculus',
  rows: [
    [
      { id: 'integral', label: '∫', latex: '\\int', ariaLabel: 'integral', type: 'operator' },
      { id: 'defintegral', label: '∫ᵇₐ', latex: '\\int_{ }^{ }', ariaLabel: 'definite integral', type: 'operator' },
      { id: 'sum', label: '∑', latex: '\\sum', ariaLabel: 'sum', type: 'operator' },
      { id: 'product', label: '∏', latex: '\\prod', ariaLabel: 'product', type: 'operator' },
    ],
    [
      { id: 'diff', label: 'd/dx', latex: '\\frac{d}{dx}', ariaLabel: 'derivative', type: 'operator' },
      { id: 'partial', label: '∂', latex: '\\partial', ariaLabel: 'partial derivative', type: 'operator' },
      { id: 'nabla', label: '∇', latex: '\\nabla', ariaLabel: 'nabla', type: 'operator' },
      { id: 'dx', label: 'dx', latex: '\\,dx', ariaLabel: 'd x', type: 'symbol' },
    ],
    [
      { id: 'limit', label: 'lim', latex: '\\lim_{ \\to }', ariaLabel: 'limit', type: 'function' },
      { id: 'infty', label: '∞', latex: '\\infty', ariaLabel: 'infinity', type: 'symbol' },
      { id: 'rightarrow', label: '→', latex: '\\to', ariaLabel: 'approaches', type: 'operator' },
      { id: 'approx', label: '≈', latex: '\\approx', ariaLabel: 'approximately equal', type: 'operator' },
    ],
    [
      { id: 'ln', label: 'ln', latex: '\\ln\\left( \\right)', ariaLabel: 'natural log', type: 'function' },
      { id: 'log', label: 'log', latex: '\\log\\left( \\right)', ariaLabel: 'logarithm', type: 'function' },
      { id: 'e', label: 'e', latex: 'e', ariaLabel: 'e', type: 'symbol' },
      { id: 'exp', label: 'eˣ', latex: 'e^{ }', ariaLabel: 'e to the power', type: 'function' },
    ],
  ],
};

/**
 * Chemistry button set - Subscripts, arrows, Greek letters
 */
export const CHEMISTRY_SET: ButtonSet = {
  id: 'chemistry',
  name: 'Chemistry',
  rows: [
    [
      { id: 'subscript', label: 'Xₙ', latex: '_{ }', ariaLabel: 'subscript', type: 'operator' },
      { id: 'superscript', label: 'Xⁿ', latex: '^{ }', ariaLabel: 'superscript', type: 'operator' },
      { id: 'rightarrow', label: '→', latex: '\\rightarrow', ariaLabel: 'reaction arrow', type: 'operator' },
      { id: 'equilibrium', label: '⇌', latex: '\\rightleftharpoons', ariaLabel: 'equilibrium', type: 'operator' },
    ],
    [
      { id: 'plus', label: '+', latex: '+', ariaLabel: 'plus', type: 'operator' },
      { id: 'delta', label: 'Δ', latex: '\\Delta', ariaLabel: 'delta', type: 'symbol' },
      { id: 'leftParen', label: '(', latex: '(', ariaLabel: 'left parenthesis', type: 'symbol' },
      { id: 'rightParen', label: ')', latex: ')', ariaLabel: 'right parenthesis', type: 'symbol' },
    ],
    [
      { id: 'state_s', label: '(s)', latex: '(s)', ariaLabel: 'solid state', type: 'symbol' },
      { id: 'state_l', label: '(l)', latex: '(l)', ariaLabel: 'liquid state', type: 'symbol' },
      { id: 'state_g', label: '(g)', latex: '(g)', ariaLabel: 'gas state', type: 'symbol' },
      { id: 'state_aq', label: '(aq)', latex: '(aq)', ariaLabel: 'aqueous', type: 'symbol' },
    ],
    [
      { id: 'charge_plus', label: '⁺', latex: '^+', ariaLabel: 'positive charge', type: 'symbol' },
      { id: 'charge_minus', label: '⁻', latex: '^-', ariaLabel: 'negative charge', type: 'symbol' },
      { id: 'cdot', label: '·', latex: '\\cdot', ariaLabel: 'dot', type: 'operator' },
      { id: 'degree', label: '°', latex: '^\\circ', ariaLabel: 'degree', type: 'symbol' },
    ],
  ],
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get button set by ID
 */
export function getButtonSet(id: string): ButtonSet | null {
  const sets: Record<string, ButtonSet> = {
    basic: BASIC_SET,
    algebra: ALGEBRA_SET,
    trig: TRIG_SET,
    calculus: CALCULUS_SET,
    chemistry: CHEMISTRY_SET,
  };
  return sets[id] || null;
}

/**
 * Get multiple button sets combined
 */
export function combineButtonSets(ids: string[]): ButtonSet {
  const combined: ButtonSet = {
    id: ids.join('-'),
    name: ids.map((id) => id.charAt(0).toUpperCase() + id.slice(1)).join(' + '),
    rows: [],
  };

  for (const id of ids) {
    const set = getButtonSet(id);
    if (set) {
      combined.rows.push(...set.rows);
    }
  }

  return combined;
}

/**
 * Get all available button set IDs
 */
export function getAvailableButtonSets(): string[] {
  return ['basic', 'algebra', 'trig', 'calculus', 'chemistry'];
}

/**
 * Create a custom button set from a list of buttons
 */
export function createCustomButtonSet(
  id: string,
  name: string,
  buttons: MathButton[],
  buttonsPerRow: number = 4
): ButtonSet {
  const rows: MathButton[][] = [];
  for (let i = 0; i < buttons.length; i += buttonsPerRow) {
    rows.push(buttons.slice(i, i + buttonsPerRow));
  }
  return { id, name, rows };
}

export type ButtonSetId = 'basic' | 'algebra' | 'trig' | 'calculus' | 'chemistry';

export default {
  BASIC_SET,
  ALGEBRA_SET,
  TRIG_SET,
  CALCULUS_SET,
  CHEMISTRY_SET,
  getButtonSet,
  combineButtonSets,
  getAvailableButtonSets,
  createCustomButtonSet,
};

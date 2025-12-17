/**
 * Numeric Validator
 *
 * Validates numeric input answers with support for:
 * - Exact value matching
 * - Tolerance (absolute and relative)
 * - Significant figures
 * - Multiple acceptable answers
 */

import type { AthenaWidget, NumericInputOptions } from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface NumericValidatorOptions {
  /** Default tolerance for comparison */
  defaultTolerance?: number;
  /** Whether to use relative tolerance */
  useRelativeTolerance?: boolean;
  /** Whether to check significant figures */
  checkSignificantFigures?: boolean;
}

/**
 * Validates numeric input answers
 */
export class NumericValidator implements Validator {
  private options: NumericValidatorOptions;

  constructor(options: NumericValidatorOptions = {}) {
    this.options = {
      defaultTolerance: 0.001,
      useRelativeTolerance: false,
      checkSignificantFigures: false,
      ...options,
    };
  }

  /**
   * Validate a numeric answer
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as NumericInputOptions;

    // Check for empty answer
    if (userAnswer === undefined || userAnswer === null || userAnswer === '') {
      return ScoringEngine.emptyResult();
    }

    // Parse user answer
    const parsedAnswer = this.parseNumber(userAnswer);
    if (parsedAnswer === null) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: 'Please enter a valid number',
      };
    }

    // Check against each acceptable answer
    if (!options.answers || options.answers.length === 0) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    for (const answer of options.answers) {
      if (answer.status !== 'correct') {
        continue;
      }

      const isMatch = this.compareValues(
        parsedAnswer,
        answer.value,
        answer.maxError ?? this.options.defaultTolerance ?? 0.001,
        answer.strict ?? false
      );

      if (isMatch) {
        return ScoringEngine.correctResult(1, answer.message);
      }
    }

    // Check for specific wrong answers with messages
    for (const answer of options.answers) {
      if (answer.status === 'wrong') {
        const isMatch = this.compareValues(
          parsedAnswer,
          answer.value,
          answer.maxError ?? this.options.defaultTolerance ?? 0.001,
          answer.strict ?? false
        );

        if (isMatch) {
          return {
            correct: false,
            empty: false,
            earned: 0,
            total: 1,
            message: answer.message,
          };
        }
      }
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Parse a user input into a number
   */
  private parseNumber(input: unknown): number | null {
    if (typeof input === 'number') {
      return isNaN(input) ? null : input;
    }

    if (typeof input === 'string') {
      // Remove whitespace
      const cleaned = input.trim();

      if (cleaned === '') {
        return null;
      }

      // Handle fractions like "1/2"
      if (cleaned.includes('/')) {
        return this.parseFraction(cleaned);
      }

      // Handle percentages like "50%"
      if (cleaned.endsWith('%')) {
        const value = parseFloat(cleaned.slice(0, -1));
        return isNaN(value) ? null : value / 100;
      }

      // Handle scientific notation like "1e-5" or "1×10^5"
      const sciMatch = cleaned.match(/^([+-]?\d*\.?\d+)\s*[×x]\s*10\^([+-]?\d+)$/i);
      if (sciMatch) {
        const base = parseFloat(sciMatch[1]);
        const exp = parseInt(sciMatch[2], 10);
        return isNaN(base) || isNaN(exp) ? null : base * Math.pow(10, exp);
      }

      // Handle comma as decimal separator
      const normalized = cleaned.replace(/,/g, '.');

      // Remove spaces in numbers like "1 000"
      const noSpaces = normalized.replace(/\s/g, '');

      const value = parseFloat(noSpaces);
      return isNaN(value) ? null : value;
    }

    return null;
  }

  /**
   * Parse a fraction string like "1/2" or "3/4"
   */
  private parseFraction(input: string): number | null {
    const parts = input.split('/');
    if (parts.length !== 2) {
      return null;
    }

    const numerator = parseFloat(parts[0].trim());
    const denominator = parseFloat(parts[1].trim());

    if (isNaN(numerator) || isNaN(denominator) || denominator === 0) {
      return null;
    }

    return numerator / denominator;
  }

  /**
   * Compare two values with tolerance
   */
  private compareValues(
    userValue: number,
    correctValue: number,
    tolerance: number,
    strict: boolean
  ): boolean {
    // Strict comparison - no tolerance
    if (strict) {
      return userValue === correctValue;
    }

    // Handle special values
    if (!isFinite(userValue) || !isFinite(correctValue)) {
      return Object.is(userValue, correctValue);
    }

    // Handle zero
    if (correctValue === 0) {
      return Math.abs(userValue) <= tolerance;
    }

    // Relative or absolute tolerance
    if (this.options.useRelativeTolerance) {
      const relativeDiff = Math.abs((userValue - correctValue) / correctValue);
      return relativeDiff <= tolerance;
    } else {
      const absoluteDiff = Math.abs(userValue - correctValue);
      return absoluteDiff <= tolerance;
    }
  }

  /**
   * Count significant figures in a number string
   */
  countSignificantFigures(numStr: string): number {
    // Remove leading/trailing whitespace and any leading zeros before decimal
    const cleaned = numStr.trim().replace(/^-/, '').replace(/^0+(?=\d)/, '');

    // Remove decimal point
    const withoutDecimal = cleaned.replace('.', '');

    // If the number is between -1 and 1, don't count leading zeros after decimal
    if (cleaned.startsWith('0.')) {
      const afterDecimal = cleaned.slice(2);
      const withoutLeadingZeros = afterDecimal.replace(/^0+/, '');
      return withoutLeadingZeros.length;
    }

    // Count trailing zeros only if there's a decimal point
    if (cleaned.includes('.')) {
      // With decimal point, all digits are significant
      return withoutDecimal.replace(/^0+/, '').length;
    } else {
      // Without decimal, trailing zeros may not be significant
      return withoutDecimal.replace(/^0+/, '').replace(/0+$/, '').length || 1;
    }
  }

  /**
   * Check if user answer has correct number of significant figures
   */
  checkSignificantFigures(userStr: string, requiredSigFigs: number): boolean {
    const userSigFigs = this.countSignificantFigures(userStr);
    return userSigFigs === requiredSigFigs;
  }

  /**
   * Round a number to specified significant figures
   */
  roundToSignificantFigures(value: number, sigFigs: number): number {
    if (value === 0) return 0;

    const magnitude = Math.floor(Math.log10(Math.abs(value)));
    const factor = Math.pow(10, sigFigs - magnitude - 1);

    return Math.round(value * factor) / factor;
  }
}

export default NumericValidator;

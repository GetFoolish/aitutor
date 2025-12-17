/**
 * Radio Validator
 *
 * Validates multiple choice answers (radio buttons and dropdowns).
 * Supports:
 * - Single selection
 * - Multiple selection
 * - None of the above
 */

import type { AthenaWidget, RadioOptions, DropdownOptions } from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface RadioValidatorOptions {
  /** Whether to allow partial credit for multiple select */
  allowPartialCredit?: boolean;
}

/**
 * Validates multiple choice answers
 */
export class RadioValidator implements Validator {
  private options: RadioValidatorOptions;

  constructor(options: RadioValidatorOptions = {}) {
    this.options = {
      allowPartialCredit: true,
      ...options,
    };
  }

  /**
   * Validate a radio/dropdown answer
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    if (widget.type === 'dropdown') {
      return this.validateDropdown(userAnswer, widget);
    }

    return this.validateRadio(userAnswer, widget);
  }

  /**
   * Validate radio button answer
   */
  private validateRadio(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as RadioOptions;

    // Check for empty answer
    if (userAnswer === undefined || userAnswer === null) {
      return ScoringEngine.emptyResult();
    }

    // Handle multiple select
    if (options.multipleSelect) {
      return this.validateMultipleSelect(userAnswer, options);
    }

    // Handle single select
    return this.validateSingleSelect(userAnswer, options);
  }

  /**
   * Validate single selection
   */
  private validateSingleSelect(userAnswer: unknown, options: RadioOptions): ValidatorResult {
    // User answer should be an index or array with single element
    let selectedIndex: number;

    if (typeof userAnswer === 'number') {
      selectedIndex = userAnswer;
    } else if (Array.isArray(userAnswer) && userAnswer.length === 1) {
      selectedIndex = userAnswer[0];
    } else if (Array.isArray(userAnswer) && userAnswer.length === 0) {
      return ScoringEngine.emptyResult();
    } else {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: 'Invalid answer format',
      };
    }

    // Validate index
    if (!options.choices || selectedIndex < 0 || selectedIndex >= options.choices.length) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: 'Invalid choice selected',
      };
    }

    const selectedChoice = options.choices[selectedIndex];

    if (selectedChoice.correct) {
      return ScoringEngine.correctResult(1);
    }

    // Return with clue if available
    return {
      correct: false,
      empty: false,
      earned: 0,
      total: 1,
      message: selectedChoice.clue,
    };
  }

  /**
   * Validate multiple selection
   */
  private validateMultipleSelect(userAnswer: unknown, options: RadioOptions): ValidatorResult {
    if (!Array.isArray(userAnswer)) {
      return ScoringEngine.emptyResult();
    }

    if (userAnswer.length === 0) {
      return ScoringEngine.emptyResult();
    }

    // Get correct indices
    const correctIndices = new Set<number>();
    options.choices.forEach((choice, index) => {
      if (choice.correct) {
        correctIndices.add(index);
      }
    });

    const selectedIndices = new Set<number>(userAnswer);
    const totalCorrect = correctIndices.size;

    if (totalCorrect === 0) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // Count matches and errors
    let correctSelections = 0;
    let incorrectSelections = 0;

    for (const index of selectedIndices) {
      if (correctIndices.has(index)) {
        correctSelections++;
      } else {
        incorrectSelections++;
      }
    }

    // Calculate score
    if (this.options.allowPartialCredit) {
      // Partial credit: correct selections minus incorrect selections
      const earned = Math.max(0, correctSelections - incorrectSelections);
      const isFullyCorrect = correctSelections === totalCorrect && incorrectSelections === 0;

      return {
        correct: isFullyCorrect,
        empty: false,
        earned,
        total: totalCorrect,
        message: isFullyCorrect
          ? undefined
          : `${correctSelections} of ${totalCorrect} correct choices selected`,
      };
    } else {
      // All or nothing
      const isCorrect = correctSelections === totalCorrect && incorrectSelections === 0;
      return isCorrect
        ? ScoringEngine.correctResult(totalCorrect)
        : ScoringEngine.incorrectResult(totalCorrect);
    }
  }

  /**
   * Validate dropdown answer
   */
  private validateDropdown(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as DropdownOptions;

    // Check for empty answer
    if (userAnswer === undefined || userAnswer === null || userAnswer === '') {
      return ScoringEngine.emptyResult();
    }

    let selectedIndex: number;

    if (typeof userAnswer === 'number') {
      selectedIndex = userAnswer;
    } else if (typeof userAnswer === 'string') {
      // Find matching choice by content
      selectedIndex = options.choices.findIndex(
        (choice) => choice.content === userAnswer
      );
    } else {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: 'Invalid answer format',
      };
    }

    // Validate index
    if (selectedIndex < 0 || selectedIndex >= options.choices.length) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: 'Invalid choice selected',
      };
    }

    const selectedChoice = options.choices[selectedIndex];

    if (selectedChoice.correct) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Get the indices of correct choices
   */
  getCorrectIndices(options: RadioOptions | DropdownOptions): number[] {
    return options.choices
      .map((choice, index) => (choice.correct ? index : -1))
      .filter((index) => index >= 0);
  }

  /**
   * Check if this is a valid choice index
   */
  isValidIndex(index: number, options: RadioOptions | DropdownOptions): boolean {
    return index >= 0 && index < options.choices.length;
  }
}

export default RadioValidator;

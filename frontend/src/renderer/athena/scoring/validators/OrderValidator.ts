/**
 * Order Validator
 *
 * Validates ordering and categorization answers:
 * - Sorter (order items)
 * - Orderer (sequential order)
 * - Matcher (pair items)
 * - Categorizer (group items)
 */

import type {
  AthenaWidget,
  SorterOptions,
  MatcherOptions,
  CategorizerOptions,
} from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface OrderValidatorOptions {
  /** Whether to allow partial credit */
  allowPartialCredit?: boolean;
  /** Whether order matters for matching */
  orderMatters?: boolean;
}

/**
 * Validates ordering and categorization answers
 */
export class OrderValidator implements Validator {
  private options: OrderValidatorOptions;

  constructor(options: OrderValidatorOptions = {}) {
    this.options = {
      allowPartialCredit: true,
      orderMatters: true,
      ...options,
    };
  }

  /**
   * Validate based on widget type
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    switch (widget.type) {
      case 'sorter':
        return this.validateSorter(userAnswer, widget);

      case 'orderer':
        return this.validateOrderer(userAnswer, widget);

      case 'matcher':
        return this.validateMatcher(userAnswer, widget);

      case 'categorizer':
        return this.validateCategorizer(userAnswer, widget);

      default:
        return ScoringEngine.incorrectResult(1, `Unknown order widget type: ${widget.type}`);
    }
  }

  /**
   * Validate sorter (drag items into correct order)
   */
  private validateSorter(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as SorterOptions;

    if (!Array.isArray(userAnswer) || userAnswer.length === 0) {
      return ScoringEngine.emptyResult();
    }

    const correct = options.correct;
    if (!correct || !Array.isArray(correct)) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // Check exact order match
    if (userAnswer.length !== correct.length) {
      return ScoringEngine.incorrectResult(
        correct.length,
        `Expected ${correct.length} items`
      );
    }

    let correctCount = 0;
    for (let i = 0; i < correct.length; i++) {
      if (this.itemsMatch(userAnswer[i], correct[i])) {
        correctCount++;
      }
    }

    if (correctCount === correct.length) {
      return ScoringEngine.correctResult(correct.length);
    }

    if (this.options.allowPartialCredit) {
      return ScoringEngine.partialResult(
        correctCount,
        correct.length,
        `${correctCount} of ${correct.length} items in correct position`
      );
    }

    return ScoringEngine.incorrectResult(correct.length);
  }

  /**
   * Validate orderer (select items in sequence)
   */
  private validateOrderer(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as Record<string, unknown>;

    if (!Array.isArray(userAnswer) || userAnswer.length === 0) {
      return ScoringEngine.emptyResult();
    }

    const correct = (options.correctOptions || options.correct) as string[];
    if (!correct || !Array.isArray(correct)) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // Must select all correct items in order
    if (userAnswer.length !== correct.length) {
      return ScoringEngine.incorrectResult(
        correct.length,
        `Expected ${correct.length} items`
      );
    }

    let correctCount = 0;
    let longestSequence = 0;
    let currentSequence = 0;

    for (let i = 0; i < correct.length; i++) {
      if (this.itemsMatch(userAnswer[i], correct[i])) {
        correctCount++;
        currentSequence++;
        longestSequence = Math.max(longestSequence, currentSequence);
      } else {
        currentSequence = 0;
      }
    }

    if (correctCount === correct.length) {
      return ScoringEngine.correctResult(correct.length);
    }

    if (this.options.allowPartialCredit) {
      return ScoringEngine.partialResult(
        correctCount,
        correct.length,
        `${correctCount} of ${correct.length} items in correct position`
      );
    }

    return ScoringEngine.incorrectResult(correct.length);
  }

  /**
   * Validate matcher (connect pairs)
   */
  private validateMatcher(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as MatcherOptions;

    if (!userAnswer || typeof userAnswer !== 'object') {
      return ScoringEngine.emptyResult();
    }

    const left = options.left || [];
    const right = options.right || [];

    if (left.length === 0 || right.length === 0) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // User answer should be an array of pairs or mapping
    const userPairs = this.extractPairs(userAnswer, left, right);

    if (userPairs.length === 0) {
      return ScoringEngine.emptyResult();
    }

    // Build correct pairs (left[i] matches right[i])
    const correctPairs = left.map((_, i) => [i, i]);

    // Count correct matches
    let correctCount = 0;
    const totalPairs = Math.min(left.length, right.length);

    for (const [leftIdx, rightIdx] of userPairs) {
      // Check if this is a correct pair
      if (leftIdx === rightIdx && leftIdx < totalPairs) {
        correctCount++;
      }
    }

    if (correctCount === totalPairs) {
      return ScoringEngine.correctResult(totalPairs);
    }

    if (this.options.allowPartialCredit) {
      return ScoringEngine.partialResult(
        correctCount,
        totalPairs,
        `${correctCount} of ${totalPairs} pairs correct`
      );
    }

    return ScoringEngine.incorrectResult(totalPairs);
  }

  /**
   * Validate categorizer (group items into categories)
   */
  private validateCategorizer(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as CategorizerOptions;

    if (!userAnswer || typeof userAnswer !== 'object') {
      return ScoringEngine.emptyResult();
    }

    const items = options.items || [];
    const categories = options.categories || [];
    const correctValues = options.values || [];

    if (items.length === 0 || correctValues.length === 0) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // User answer should be mapping of item index to category index
    const userValues = this.extractCategoryValues(userAnswer, items);

    if (userValues.length === 0) {
      return ScoringEngine.emptyResult();
    }

    // Count correct categorizations
    let correctCount = 0;
    const total = Math.min(items.length, correctValues.length);

    for (let i = 0; i < total; i++) {
      if (userValues[i] === correctValues[i]) {
        correctCount++;
      }
    }

    if (correctCount === total) {
      return ScoringEngine.correctResult(total);
    }

    if (this.options.allowPartialCredit) {
      return ScoringEngine.partialResult(
        correctCount,
        total,
        `${correctCount} of ${total} items correctly categorized`
      );
    }

    return ScoringEngine.incorrectResult(total);
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Check if two items match (handling strings and indices)
   */
  private itemsMatch(a: unknown, b: unknown): boolean {
    if (a === b) return true;

    // String comparison (trim and case-insensitive)
    if (typeof a === 'string' && typeof b === 'string') {
      return a.trim().toLowerCase() === b.trim().toLowerCase();
    }

    // Index comparison
    if (typeof a === 'number' && typeof b === 'number') {
      return a === b;
    }

    return false;
  }

  /**
   * Extract pairs from user answer
   */
  private extractPairs(
    answer: unknown,
    left: string[],
    right: string[]
  ): Array<[number, number]> {
    const pairs: Array<[number, number]> = [];

    if (Array.isArray(answer)) {
      // Array of [leftIdx, rightIdx] pairs
      for (const pair of answer) {
        if (Array.isArray(pair) && pair.length === 2) {
          pairs.push([pair[0], pair[1]]);
        }
      }
    } else if (typeof answer === 'object') {
      // Object mapping leftIdx -> rightIdx
      for (const [leftKey, rightVal] of Object.entries(answer as Record<string, unknown>)) {
        const leftIdx = parseInt(leftKey, 10);
        const rightIdx = typeof rightVal === 'number' ? rightVal : parseInt(String(rightVal), 10);

        if (!isNaN(leftIdx) && !isNaN(rightIdx)) {
          pairs.push([leftIdx, rightIdx]);
        }
      }
    }

    return pairs;
  }

  /**
   * Extract category values from user answer
   */
  private extractCategoryValues(answer: unknown, items: string[]): number[] {
    const values: number[] = [];

    if (Array.isArray(answer)) {
      // Direct array of category indices
      return answer.map((v) => (typeof v === 'number' ? v : parseInt(String(v), 10)));
    }

    if (typeof answer === 'object') {
      // Object mapping item index to category index
      const mapping = answer as Record<string, unknown>;
      for (let i = 0; i < items.length; i++) {
        const val = mapping[String(i)];
        values.push(typeof val === 'number' ? val : parseInt(String(val), 10));
      }
    }

    return values;
  }

  /**
   * Calculate Levenshtein distance for partial sequence matching
   */
  levenshteinDistance(a: unknown[], b: unknown[]): number {
    const matrix: number[][] = [];

    for (let i = 0; i <= a.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= b.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        const cost = this.itemsMatch(a[i - 1], b[j - 1]) ? 0 : 1;
        matrix[i][j] = Math.min(
          matrix[i - 1][j] + 1,      // deletion
          matrix[i][j - 1] + 1,      // insertion
          matrix[i - 1][j - 1] + cost // substitution
        );
      }
    }

    return matrix[a.length][b.length];
  }

  /**
   * Calculate longest common subsequence
   */
  longestCommonSubsequence(a: unknown[], b: unknown[]): number {
    const dp: number[][] = Array(a.length + 1)
      .fill(null)
      .map(() => Array(b.length + 1).fill(0));

    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        if (this.itemsMatch(a[i - 1], b[j - 1])) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
        } else {
          dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
        }
      }
    }

    return dp[a.length][b.length];
  }
}

export default OrderValidator;

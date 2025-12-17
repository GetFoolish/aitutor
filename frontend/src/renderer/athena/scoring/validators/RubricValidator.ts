/**
 * Rubric Validator
 *
 * Validates free response answers using:
 * - Keyword matching
 * - Regular expression patterns
 * - Length requirements
 * - AI-assisted scoring (future)
 */

import type { AthenaWidget } from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface RubricCriterion {
  /** Criterion identifier */
  id: string;
  /** Description of what this criterion checks */
  description: string;
  /** Points for this criterion */
  points: number;
  /** Type of check */
  type: 'keyword' | 'regex' | 'length' | 'custom';
  /** Keywords to look for */
  keywords?: string[];
  /** Whether all keywords must be present */
  requireAll?: boolean;
  /** Regular expression pattern */
  pattern?: string;
  /** Minimum length requirement */
  minLength?: number;
  /** Maximum length requirement */
  maxLength?: number;
  /** Case sensitive matching */
  caseSensitive?: boolean;
  /** Custom validator function */
  validator?: (response: string) => boolean;
}

export interface FreeResponseOptions {
  /** Rubric criteria */
  rubric?: RubricCriterion[];
  /** Minimum required length */
  minLength?: number;
  /** Maximum allowed length */
  maxLength?: number;
  /** Placeholder text */
  placeholder?: string;
  /** Whether empty responses are allowed */
  allowEmptyResponse?: boolean;
}

export interface RubricValidatorOptions {
  /** Whether to allow partial credit */
  allowPartialCredit?: boolean;
  /** Default case sensitivity */
  caseSensitive?: boolean;
}

/**
 * Validates free response answers using rubrics
 */
export class RubricValidator implements Validator {
  private options: RubricValidatorOptions;

  constructor(options: RubricValidatorOptions = {}) {
    this.options = {
      allowPartialCredit: true,
      caseSensitive: false,
      ...options,
    };
  }

  /**
   * Validate a free response answer
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as FreeResponseOptions;

    // Check for empty answer
    if (userAnswer === undefined || userAnswer === null) {
      if (options.allowEmptyResponse) {
        return ScoringEngine.correctResult(0);
      }
      return ScoringEngine.emptyResult();
    }

    const response = String(userAnswer).trim();

    if (response === '') {
      if (options.allowEmptyResponse) {
        return ScoringEngine.correctResult(0);
      }
      return ScoringEngine.emptyResult();
    }

    // Check length requirements
    if (options.minLength && response.length < options.minLength) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: this.getTotalPoints(options.rubric),
        message: `Response must be at least ${options.minLength} characters`,
      };
    }

    if (options.maxLength && response.length > options.maxLength) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: this.getTotalPoints(options.rubric),
        message: `Response must be no more than ${options.maxLength} characters`,
      };
    }

    // If no rubric, treat any non-empty response as valid
    if (!options.rubric || options.rubric.length === 0) {
      return ScoringEngine.correctResult(1);
    }

    // Evaluate against rubric
    return this.evaluateRubric(response, options.rubric);
  }

  /**
   * Evaluate response against rubric criteria
   */
  private evaluateRubric(response: string, rubric: RubricCriterion[]): ValidatorResult {
    let earnedPoints = 0;
    let totalPoints = 0;
    const feedback: string[] = [];

    for (const criterion of rubric) {
      totalPoints += criterion.points;

      const passed = this.evaluateCriterion(response, criterion);

      if (passed) {
        earnedPoints += criterion.points;
      } else {
        feedback.push(criterion.description);
      }
    }

    const allCorrect = earnedPoints === totalPoints;

    if (allCorrect) {
      return ScoringEngine.correctResult(totalPoints);
    }

    if (this.options.allowPartialCredit && earnedPoints > 0) {
      return {
        correct: false,
        empty: false,
        earned: earnedPoints,
        total: totalPoints,
        message: feedback.length > 0
          ? `Missing: ${feedback.slice(0, 2).join(', ')}${feedback.length > 2 ? '...' : ''}`
          : undefined,
      };
    }

    return {
      correct: false,
      empty: false,
      earned: 0,
      total: totalPoints,
      message: feedback.length > 0
        ? `Missing: ${feedback.slice(0, 2).join(', ')}${feedback.length > 2 ? '...' : ''}`
        : undefined,
    };
  }

  /**
   * Evaluate a single criterion
   */
  private evaluateCriterion(response: string, criterion: RubricCriterion): boolean {
    const caseSensitive = criterion.caseSensitive ?? this.options.caseSensitive ?? false;
    const normalizedResponse = caseSensitive ? response : response.toLowerCase();

    switch (criterion.type) {
      case 'keyword':
        return this.evaluateKeywords(normalizedResponse, criterion, caseSensitive);

      case 'regex':
        return this.evaluateRegex(response, criterion, caseSensitive);

      case 'length':
        return this.evaluateLength(response, criterion);

      case 'custom':
        return criterion.validator ? criterion.validator(response) : false;

      default:
        return false;
    }
  }

  /**
   * Evaluate keyword criterion
   */
  private evaluateKeywords(
    response: string,
    criterion: RubricCriterion,
    caseSensitive: boolean
  ): boolean {
    if (!criterion.keywords || criterion.keywords.length === 0) {
      return true;
    }

    const keywords = caseSensitive
      ? criterion.keywords
      : criterion.keywords.map((k) => k.toLowerCase());

    if (criterion.requireAll) {
      return keywords.every((keyword) => response.includes(keyword));
    } else {
      return keywords.some((keyword) => response.includes(keyword));
    }
  }

  /**
   * Evaluate regex criterion
   */
  private evaluateRegex(
    response: string,
    criterion: RubricCriterion,
    caseSensitive: boolean
  ): boolean {
    if (!criterion.pattern) {
      return true;
    }

    try {
      const flags = caseSensitive ? '' : 'i';
      const regex = new RegExp(criterion.pattern, flags);
      return regex.test(response);
    } catch {
      console.warn(`Invalid regex pattern: ${criterion.pattern}`);
      return false;
    }
  }

  /**
   * Evaluate length criterion
   */
  private evaluateLength(response: string, criterion: RubricCriterion): boolean {
    const length = response.length;

    if (criterion.minLength && length < criterion.minLength) {
      return false;
    }

    if (criterion.maxLength && length > criterion.maxLength) {
      return false;
    }

    return true;
  }

  /**
   * Get total points from rubric
   */
  private getTotalPoints(rubric?: RubricCriterion[]): number {
    if (!rubric) return 1;
    return rubric.reduce((sum, c) => sum + c.points, 0) || 1;
  }

  /**
   * Create a simple keyword rubric
   */
  static createKeywordRubric(
    keywords: string[],
    requireAll: boolean = false,
    points: number = 1
  ): RubricCriterion {
    return {
      id: 'keywords',
      description: requireAll
        ? `Include all of: ${keywords.join(', ')}`
        : `Include at least one of: ${keywords.join(', ')}`,
      points,
      type: 'keyword',
      keywords,
      requireAll,
    };
  }

  /**
   * Create a length requirement rubric
   */
  static createLengthRubric(
    minLength?: number,
    maxLength?: number,
    points: number = 1
  ): RubricCriterion {
    let description = 'Response length: ';
    if (minLength && maxLength) {
      description += `${minLength}-${maxLength} characters`;
    } else if (minLength) {
      description += `at least ${minLength} characters`;
    } else if (maxLength) {
      description += `at most ${maxLength} characters`;
    }

    return {
      id: 'length',
      description,
      points,
      type: 'length',
      minLength,
      maxLength,
    };
  }

  /**
   * Create a regex pattern rubric
   */
  static createPatternRubric(
    pattern: string,
    description: string,
    points: number = 1,
    caseSensitive: boolean = false
  ): RubricCriterion {
    return {
      id: 'pattern',
      description,
      points,
      type: 'regex',
      pattern,
      caseSensitive,
    };
  }

  /**
   * Analyze a response and suggest improvements
   */
  analyzeResponse(response: string, rubric: RubricCriterion[]): {
    score: number;
    maxScore: number;
    passed: RubricCriterion[];
    failed: RubricCriterion[];
    suggestions: string[];
  } {
    const passed: RubricCriterion[] = [];
    const failed: RubricCriterion[] = [];
    const suggestions: string[] = [];

    for (const criterion of rubric) {
      if (this.evaluateCriterion(response, criterion)) {
        passed.push(criterion);
      } else {
        failed.push(criterion);
        suggestions.push(`Consider addressing: ${criterion.description}`);
      }
    }

    return {
      score: passed.reduce((sum, c) => sum + c.points, 0),
      maxScore: rubric.reduce((sum, c) => sum + c.points, 0),
      passed,
      failed,
      suggestions,
    };
  }
}

export default RubricValidator;

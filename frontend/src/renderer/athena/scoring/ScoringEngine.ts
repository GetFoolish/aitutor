/**
 * Scoring Engine
 *
 * Main orchestrator for scoring user answers against correct answers.
 * Supports multiple widget types and scoring strategies.
 */

import type {
  AthenaItem,
  AthenaWidget,
  ScoringResult,
  WidgetScoreDetail,
  WidgetType,
} from '../core/types';

import { NumericValidator } from './validators/NumericValidator';
import { ExpressionValidator } from './validators/ExpressionValidator';
import { RadioValidator } from './validators/RadioValidator';
import { GraphValidator } from './validators/GraphValidator';
import { OrderValidator } from './validators/OrderValidator';
import { RubricValidator } from './validators/RubricValidator';

export interface ValidatorResult {
  correct: boolean;
  empty: boolean;
  message?: string;
  earned: number;
  total: number;
}

export interface Validator {
  validate(userAnswer: unknown, widget: AthenaWidget, locale?: string): ValidatorResult;
}

export interface ScoringEngineOptions {
  /** Custom validators for specific widget types */
  customValidators?: Record<string, Validator>;
  /** Default locale for messages */
  locale?: string;
  /** Whether to include detailed results */
  includeDetails?: boolean;
  /** Whether to calculate partial credit */
  allowPartialCredit?: boolean;
}

/**
 * Main scoring engine for evaluating user answers
 */
export class ScoringEngine {
  private validators: Map<string, Validator>;
  private options: ScoringEngineOptions;

  constructor(options: ScoringEngineOptions = {}) {
    this.options = {
      locale: 'en',
      includeDetails: true,
      allowPartialCredit: true,
      ...options,
    };

    this.validators = new Map();
    this.registerDefaultValidators();

    // Register custom validators
    if (options.customValidators) {
      for (const [type, validator] of Object.entries(options.customValidators)) {
        this.validators.set(type, validator);
      }
    }
  }

  /**
   * Register default validators for all widget types
   */
  private registerDefaultValidators(): void {
    // Numeric validators
    const numericValidator = new NumericValidator();
    this.validators.set('numeric-input', numericValidator);
    this.validators.set('input-number', numericValidator);

    // Expression validator
    const expressionValidator = new ExpressionValidator();
    this.validators.set('expression', expressionValidator);

    // Radio validator
    const radioValidator = new RadioValidator();
    this.validators.set('radio', radioValidator);
    this.validators.set('dropdown', radioValidator);

    // Graph validator
    const graphValidator = new GraphValidator();
    this.validators.set('interactive-graph', graphValidator);
    this.validators.set('grapher', graphValidator);
    this.validators.set('plotter', graphValidator);

    // Order validators
    const orderValidator = new OrderValidator();
    this.validators.set('sorter', orderValidator);
    this.validators.set('orderer', orderValidator);
    this.validators.set('matcher', orderValidator);
    this.validators.set('categorizer', orderValidator);

    // Rubric validator for free response
    const rubricValidator = new RubricValidator();
    this.validators.set('free-response', rubricValidator);

    // Static widgets (always correct, don't affect score)
    const staticValidator: Validator = {
      validate: () => ({ correct: true, empty: false, earned: 0, total: 0 }),
    };
    this.validators.set('image', staticValidator);
    this.validators.set('passage', staticValidator);
    this.validators.set('video', staticValidator);
    this.validators.set('definition', staticValidator);
    this.validators.set('explanation', staticValidator);
    this.validators.set('iframe', staticValidator);
  }

  /**
   * Register a custom validator for a widget type
   */
  registerValidator(widgetType: string, validator: Validator): void {
    this.validators.set(widgetType, validator);
  }

  /**
   * Score an entire item
   */
  scoreItem(
    item: AthenaItem,
    userAnswers: Record<string, unknown>
  ): ScoringResult {
    const details: WidgetScoreDetail[] = [];
    let totalEarned = 0;
    let totalPossible = 0;
    let allEmpty = true;
    let allCorrect = true;

    // Score question widgets
    for (const [widgetId, widget] of Object.entries(item.question.widgets)) {
      // Skip static widgets
      if (widget.static) {
        continue;
      }

      // Skip ungraded widgets
      if (!widget.graded) {
        continue;
      }

      const userAnswer = userAnswers[widgetId];
      const result = this.scoreWidget(widgetId, widget, userAnswer);

      details.push(result);

      totalEarned += result.earned;
      totalPossible += result.total;

      if (!result.correct) {
        allCorrect = false;
      }

      if (userAnswer !== undefined && userAnswer !== null && userAnswer !== '') {
        allEmpty = false;
      }
    }

    // Calculate overall correctness
    const correct = allCorrect && !allEmpty;
    const empty = allEmpty;

    // Generate message
    let message: string | undefined;
    if (empty) {
      message = this.getMessage('empty');
    } else if (correct) {
      message = this.getMessage('correct');
    } else {
      message = this.getMessage('incorrect');
    }

    return {
      correct,
      empty,
      message,
      earned: totalEarned,
      total: totalPossible,
      details: this.options.includeDetails ? details : [],
    };
  }

  /**
   * Score a single widget
   */
  scoreWidget(
    widgetId: string,
    widget: AthenaWidget,
    userAnswer: unknown
  ): WidgetScoreDetail {
    const validator = this.validators.get(widget.type);

    if (!validator) {
      console.warn(`No validator for widget type: ${widget.type}`);
      return {
        widgetId,
        widgetType: widget.type as WidgetType,
        correct: false,
        earned: 0,
        total: 1,
        message: `Unknown widget type: ${widget.type}`,
      };
    }

    try {
      const result = validator.validate(userAnswer, widget, this.options.locale);

      return {
        widgetId,
        widgetType: widget.type as WidgetType,
        correct: result.correct,
        earned: result.earned,
        total: result.total,
        message: result.message,
      };
    } catch (error) {
      console.error(`Error scoring widget ${widgetId}:`, error);
      return {
        widgetId,
        widgetType: widget.type as WidgetType,
        correct: false,
        earned: 0,
        total: 1,
        message: `Error scoring: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Check if an answer is empty
   */
  isAnswerEmpty(userAnswer: unknown): boolean {
    if (userAnswer === undefined || userAnswer === null) {
      return true;
    }

    if (typeof userAnswer === 'string') {
      return userAnswer.trim() === '';
    }

    if (Array.isArray(userAnswer)) {
      return userAnswer.length === 0 || userAnswer.every((v) => this.isAnswerEmpty(v));
    }

    if (typeof userAnswer === 'object') {
      const values = Object.values(userAnswer);
      return values.length === 0 || values.every((v) => this.isAnswerEmpty(v));
    }

    return false;
  }

  /**
   * Get localized message
   */
  private getMessage(key: 'correct' | 'incorrect' | 'empty' | 'partial'): string {
    const messages: Record<string, Record<string, string>> = {
      en: {
        correct: 'Correct!',
        incorrect: 'Incorrect. Try again.',
        empty: 'Please provide an answer.',
        partial: 'Partially correct.',
      },
      es: {
        correct: '¡Correcto!',
        incorrect: 'Incorrecto. Inténtalo de nuevo.',
        empty: 'Por favor, proporciona una respuesta.',
        partial: 'Parcialmente correcto.',
      },
    };

    const locale = this.options.locale || 'en';
    return messages[locale]?.[key] || messages.en[key];
  }

  /**
   * Get graded widgets from an item
   */
  getGradedWidgets(item: AthenaItem): Array<{ id: string; widget: AthenaWidget }> {
    return Object.entries(item.question.widgets)
      .filter(([_, widget]) => widget.graded && !widget.static)
      .map(([id, widget]) => ({ id, widget }));
  }

  /**
   * Check if item is fully answerable (has graded widgets)
   */
  isAnswerable(item: AthenaItem): boolean {
    return this.getGradedWidgets(item).length > 0;
  }

  /**
   * Get the maximum score for an item
   */
  getMaxScore(item: AthenaItem): number {
    return this.getGradedWidgets(item).length;
  }

  /**
   * Create a validator result for empty answers
   */
  static emptyResult(total: number = 1): ValidatorResult {
    return {
      correct: false,
      empty: true,
      earned: 0,
      total,
      message: 'No answer provided',
    };
  }

  /**
   * Create a validator result for correct answers
   */
  static correctResult(total: number = 1, message?: string): ValidatorResult {
    return {
      correct: true,
      empty: false,
      earned: total,
      total,
      message,
    };
  }

  /**
   * Create a validator result for incorrect answers
   */
  static incorrectResult(total: number = 1, message?: string): ValidatorResult {
    return {
      correct: false,
      empty: false,
      earned: 0,
      total,
      message,
    };
  }

  /**
   * Create a validator result for partial credit
   */
  static partialResult(earned: number, total: number, message?: string): ValidatorResult {
    return {
      correct: earned === total,
      empty: false,
      earned,
      total,
      message,
    };
  }
}

export default ScoringEngine;

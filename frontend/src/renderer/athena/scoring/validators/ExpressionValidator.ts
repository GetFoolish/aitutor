/**
 * Expression Validator
 *
 * Validates mathematical expression answers using symbolic comparison.
 * Supports:
 * - Symbolic equivalence (x+1 == 1+x)
 * - Form checking (factored, expanded, simplified)
 * - Function evaluation
 */

import type { AthenaWidget, ExpressionOptions } from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface ExpressionValidatorOptions {
  /** Whether to allow equivalent forms by default */
  allowEquivalent?: boolean;
  /** Whether to require simplification */
  requireSimplified?: boolean;
  /** Custom functions to allow */
  allowedFunctions?: string[];
}

/**
 * Validates mathematical expression answers
 */
export class ExpressionValidator implements Validator {
  private options: ExpressionValidatorOptions;

  constructor(options: ExpressionValidatorOptions = {}) {
    this.options = {
      allowEquivalent: true,
      requireSimplified: false,
      allowedFunctions: ['sin', 'cos', 'tan', 'sqrt', 'abs', 'log', 'ln', 'exp'],
      ...options,
    };
  }

  /**
   * Validate an expression answer
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as ExpressionOptions;

    // Check for empty answer
    if (userAnswer === undefined || userAnswer === null) {
      return ScoringEngine.emptyResult();
    }

    const userExpr = String(userAnswer).trim();
    if (userExpr === '') {
      return ScoringEngine.emptyResult();
    }

    // Validate expression syntax
    const syntaxError = this.checkSyntax(userExpr);
    if (syntaxError) {
      return {
        correct: false,
        empty: false,
        earned: 0,
        total: 1,
        message: syntaxError,
      };
    }

    // Check against each answer form
    if (!options.answerForms || options.answerForms.length === 0) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    for (const answerForm of options.answerForms) {
      if (answerForm.considered !== 'correct') {
        continue;
      }

      const isMatch = this.compareExpressions(
        userExpr,
        answerForm.value,
        answerForm.form,
        answerForm.simplify
      );

      if (isMatch) {
        return ScoringEngine.correctResult(1);
      }
    }

    // Check for specific wrong answers with feedback
    for (const answerForm of options.answerForms) {
      if (answerForm.considered === 'wrong') {
        const isMatch = this.compareExpressions(
          userExpr,
          answerForm.value,
          false,
          false
        );

        if (isMatch) {
          return {
            correct: false,
            empty: false,
            earned: 0,
            total: 1,
            message: 'That answer is not quite right. Check your work.',
          };
        }
      }
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Check expression syntax
   */
  private checkSyntax(expr: string): string | null {
    // Check for balanced parentheses
    let depth = 0;
    for (const char of expr) {
      if (char === '(' || char === '[' || char === '{') {
        depth++;
      } else if (char === ')' || char === ']' || char === '}') {
        depth--;
        if (depth < 0) {
          return 'Unbalanced parentheses';
        }
      }
    }
    if (depth !== 0) {
      return 'Unbalanced parentheses';
    }

    // Check for empty expressions
    if (expr.replace(/[^a-zA-Z0-9]/g, '').length === 0) {
      return 'Expression cannot be empty';
    }

    // Check for consecutive operators
    if (/[+\-*/^]{2,}/.test(expr.replace(/\*\*/g, '^'))) {
      return 'Invalid operator sequence';
    }

    return null;
  }

  /**
   * Compare two expressions
   */
  private compareExpressions(
    userExpr: string,
    correctExpr: string,
    requireForm: boolean,
    requireSimplified: boolean
  ): boolean {
    // Normalize expressions
    const normalizedUser = this.normalizeExpression(userExpr);
    const normalizedCorrect = this.normalizeExpression(correctExpr);

    // Exact match after normalization
    if (normalizedUser === normalizedCorrect) {
      return true;
    }

    // If form is required, check structural equality
    if (requireForm) {
      return this.compareStructure(normalizedUser, normalizedCorrect);
    }

    // Check symbolic equivalence
    if (this.options.allowEquivalent) {
      return this.checkEquivalence(normalizedUser, normalizedCorrect);
    }

    return false;
  }

  /**
   * Normalize an expression for comparison
   */
  private normalizeExpression(expr: string): string {
    let normalized = expr
      .toLowerCase()
      .replace(/\s+/g, '')                    // Remove whitespace
      .replace(/\*\*/g, '^')                  // ** -> ^
      .replace(/\*/g, '·')                    // * -> ·
      .replace(/×/g, '·')                     // × -> ·
      .replace(/÷/g, '/')                     // ÷ -> /
      .replace(/\(([+-]?\d+)\)/g, '$1')       // Remove unnecessary parens around numbers
      .replace(/\+-/g, '-')                   // +- -> -
      .replace(/-\+/g, '-')                   // -+ -> -
      .replace(/--/g, '+')                    // -- -> +
      .replace(/^\+/, '')                     // Remove leading +
      .replace(/\^1(?![0-9])/g, '')           // Remove ^1
      .replace(/·1(?![0-9])/g, '')            // Remove ·1
      .replace(/1·/g, '');                    // Remove 1·

    return normalized;
  }

  /**
   * Compare structural form of expressions
   */
  private compareStructure(expr1: string, expr2: string): boolean {
    // This is a simplified structural comparison
    // A full implementation would use expression trees
    return expr1 === expr2;
  }

  /**
   * Check symbolic equivalence using evaluation
   */
  private checkEquivalence(expr1: string, expr2: string): boolean {
    // Test with multiple random values
    const testValues = [0, 1, -1, 2, -2, 0.5, -0.5, Math.PI, Math.E];
    const variables = this.extractVariables(expr1 + expr2);

    if (variables.length === 0) {
      // Pure numeric expressions - evaluate once
      try {
        const val1 = this.evaluateExpression(expr1, {});
        const val2 = this.evaluateExpression(expr2, {});
        return this.approximatelyEqual(val1, val2);
      } catch {
        return false;
      }
    }

    // Test with combinations of values
    const testCases = this.generateTestCases(variables, testValues);
    let matches = 0;
    let total = 0;

    for (const testCase of testCases) {
      try {
        const val1 = this.evaluateExpression(expr1, testCase);
        const val2 = this.evaluateExpression(expr2, testCase);

        // Skip undefined results
        if (!isFinite(val1) || !isFinite(val2)) {
          continue;
        }

        total++;
        if (this.approximatelyEqual(val1, val2)) {
          matches++;
        }
      } catch {
        // Evaluation error - skip this test case
      }
    }

    // Require high match rate
    return total > 0 && matches / total >= 0.95;
  }

  /**
   * Extract variable names from expression
   */
  private extractVariables(expr: string): string[] {
    const variables = new Set<string>();
    const normalized = expr.replace(/sin|cos|tan|sqrt|abs|log|ln|exp/gi, '');
    const matches = normalized.match(/[a-z]/gi);

    if (matches) {
      for (const v of matches) {
        if (!['e', 'i'].includes(v.toLowerCase())) {
          variables.add(v.toLowerCase());
        }
      }
    }

    return Array.from(variables);
  }

  /**
   * Generate test cases for variables
   */
  private generateTestCases(
    variables: string[],
    values: number[]
  ): Array<Record<string, number>> {
    if (variables.length === 0) {
      return [{}];
    }

    const testCases: Array<Record<string, number>> = [];

    // Use a subset of values to keep test count manageable
    const testValues = values.slice(0, 5);

    if (variables.length === 1) {
      for (const v of testValues) {
        testCases.push({ [variables[0]]: v });
      }
    } else {
      // For multiple variables, use combinations
      for (const v1 of testValues) {
        for (const v2 of testValues) {
          const testCase: Record<string, number> = {};
          testCase[variables[0]] = v1;
          if (variables.length > 1) {
            testCase[variables[1]] = v2;
          }
          testCases.push(testCase);
        }
      }
    }

    return testCases;
  }

  /**
   * Evaluate an expression with given variable values
   */
  private evaluateExpression(expr: string, vars: Record<string, number>): number {
    // Convert expression to JavaScript
    let jsExpr = expr
      .replace(/·/g, '*')
      .replace(/\^/g, '**')
      .replace(/sin/gi, 'Math.sin')
      .replace(/cos/gi, 'Math.cos')
      .replace(/tan/gi, 'Math.tan')
      .replace(/sqrt/gi, 'Math.sqrt')
      .replace(/abs/gi, 'Math.abs')
      .replace(/log/gi, 'Math.log10')
      .replace(/ln/gi, 'Math.log')
      .replace(/exp/gi, 'Math.exp')
      .replace(/pi/gi, 'Math.PI')
      .replace(/(?<![a-z])e(?![a-z])/gi, 'Math.E');

    // Replace variables with values
    for (const [name, value] of Object.entries(vars)) {
      jsExpr = jsExpr.replace(new RegExp(`\\b${name}\\b`, 'gi'), String(value));
    }

    // Add implicit multiplication
    jsExpr = jsExpr.replace(/(\d)([a-z])/gi, '$1*$2');
    jsExpr = jsExpr.replace(/(\))(\d)/g, '$1*$2');
    jsExpr = jsExpr.replace(/(\d)(\()/g, '$1*$2');
    jsExpr = jsExpr.replace(/(\))([a-z])/gi, '$1*$2');
    jsExpr = jsExpr.replace(/(\))(\()/g, '$1*$2');

    // Evaluate safely
    try {
      // Use Function constructor instead of eval for slightly better security
      const fn = new Function(`return ${jsExpr}`);
      const result = fn();
      return typeof result === 'number' ? result : NaN;
    } catch {
      return NaN;
    }
  }

  /**
   * Check if two numbers are approximately equal
   */
  private approximatelyEqual(a: number, b: number, tolerance: number = 1e-9): boolean {
    if (a === b) return true;
    if (!isFinite(a) || !isFinite(b)) return false;

    const diff = Math.abs(a - b);
    const maxAbs = Math.max(Math.abs(a), Math.abs(b));

    // Use relative tolerance for large numbers, absolute for small
    return diff <= tolerance || diff <= maxAbs * tolerance;
  }

  /**
   * Check if expression is in a specific form
   */
  isInForm(expr: string, form: 'factored' | 'expanded' | 'simplified'): boolean {
    const normalized = this.normalizeExpression(expr);

    switch (form) {
      case 'factored':
        // Check if expression contains multiplication of parenthesized terms
        return /\([^)]+\)\s*·\s*\([^)]+\)/.test(normalized) ||
               /[a-z]\s*\([^)]+\)/.test(normalized);

      case 'expanded':
        // Check if expression is polynomial-like without nested parens
        return !/\([^)]*\([^)]*\)[^)]*\)/.test(normalized);

      case 'simplified':
        // Check if no obvious simplifications possible
        return !this.canBeSimplified(normalized);

      default:
        return true;
    }
  }

  /**
   * Check if expression can be simplified
   */
  private canBeSimplified(expr: string): boolean {
    // Check for obvious simplifications
    return /0\+/.test(expr) ||           // 0 + something
           /\+0/.test(expr) ||           // something + 0
           /1·/.test(expr) ||            // 1 * something
           /·1(?![0-9])/.test(expr) ||   // something * 1
           /0·/.test(expr) ||            // 0 * something
           /·0/.test(expr) ||            // something * 0
           /\^0(?![0-9])/.test(expr) ||  // something ^ 0
           /\^1(?![0-9])/.test(expr);    // something ^ 1
  }
}

export default ExpressionValidator;

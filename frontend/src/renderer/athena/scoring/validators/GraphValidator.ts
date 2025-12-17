/**
 * Graph Validator
 *
 * Validates interactive graph answers including:
 * - Points
 * - Lines (segments, rays, lines)
 * - Polygons
 * - Circles
 * - Functions
 */

import type { AthenaWidget, InteractiveGraphOptions } from '../../core/types';
import type { Validator, ValidatorResult } from '../ScoringEngine';
import { ScoringEngine } from '../ScoringEngine';

export interface Point {
  x: number;
  y: number;
}

export interface Line {
  start: Point;
  end: Point;
}

export interface Circle {
  center: Point;
  radius: number;
}

export interface Polygon {
  points: Point[];
}

export interface GraphAnswer {
  type: string;
  coords?: Point[];
  points?: Point[];
  lines?: Line[];
  circle?: Circle;
  polygon?: Polygon;
}

export interface GraphValidatorOptions {
  /** Tolerance for point matching */
  pointTolerance?: number;
  /** Whether to check for geometric equivalence */
  checkEquivalence?: boolean;
}

/**
 * Validates interactive graph answers
 */
export class GraphValidator implements Validator {
  private options: GraphValidatorOptions;

  constructor(options: GraphValidatorOptions = {}) {
    this.options = {
      pointTolerance: 0.1,
      checkEquivalence: true,
      ...options,
    };
  }

  /**
   * Validate a graph answer
   */
  validate(userAnswer: unknown, widget: AthenaWidget): ValidatorResult {
    const options = widget.options as InteractiveGraphOptions;

    // Check for empty answer
    if (!userAnswer || typeof userAnswer !== 'object') {
      return ScoringEngine.emptyResult();
    }

    const userGraph = userAnswer as GraphAnswer;
    const correctGraph = options.correct as GraphAnswer;

    if (!correctGraph) {
      return ScoringEngine.incorrectResult(1, 'No correct answer defined');
    }

    // Validate based on graph type
    const graphType = options.graph?.type || 'point';

    switch (graphType) {
      case 'point':
        return this.validatePoints(userGraph, correctGraph);

      case 'linear':
      case 'segment':
      case 'ray':
        return this.validateLine(userGraph, correctGraph, graphType);

      case 'polygon':
        return this.validatePolygon(userGraph, correctGraph);

      case 'circle':
        return this.validateCircle(userGraph, correctGraph);

      case 'quadratic':
      case 'polynomial':
      case 'exponential':
      case 'logarithmic':
      case 'trigonometric':
        return this.validateFunction(userGraph, correctGraph, graphType);

      case 'linear-system':
        return this.validateLinearSystem(userGraph, correctGraph);

      default:
        return this.validateGeneric(userGraph, correctGraph);
    }
  }

  /**
   * Validate point placement
   */
  private validatePoints(user: GraphAnswer, correct: GraphAnswer): ValidatorResult {
    const userPoints = user.coords || user.points || [];
    const correctPoints = correct.coords || correct.points || [];

    if (userPoints.length === 0) {
      return ScoringEngine.emptyResult();
    }

    if (userPoints.length !== correctPoints.length) {
      return ScoringEngine.incorrectResult(
        correctPoints.length,
        `Expected ${correctPoints.length} point(s), got ${userPoints.length}`
      );
    }

    // Check if all points match (order may not matter)
    let matchCount = 0;
    const matchedCorrect = new Set<number>();

    for (const userPoint of userPoints) {
      for (let i = 0; i < correctPoints.length; i++) {
        if (matchedCorrect.has(i)) continue;

        if (this.pointsMatch(userPoint, correctPoints[i])) {
          matchCount++;
          matchedCorrect.add(i);
          break;
        }
      }
    }

    if (matchCount === correctPoints.length) {
      return ScoringEngine.correctResult(correctPoints.length);
    }

    return ScoringEngine.partialResult(
      matchCount,
      correctPoints.length,
      `${matchCount} of ${correctPoints.length} points correct`
    );
  }

  /**
   * Validate line (segment, ray, or full line)
   */
  private validateLine(
    user: GraphAnswer,
    correct: GraphAnswer,
    lineType: string
  ): ValidatorResult {
    const userPoints = user.coords || user.points || [];
    const correctPoints = correct.coords || correct.points || [];

    if (userPoints.length < 2) {
      return ScoringEngine.emptyResult();
    }

    if (correctPoints.length < 2) {
      return ScoringEngine.incorrectResult(1, 'Invalid correct answer');
    }

    // For a line, check if points are collinear and define the same line
    if (lineType === 'linear') {
      const userSlope = this.calculateSlope(userPoints[0], userPoints[1]);
      const correctSlope = this.calculateSlope(correctPoints[0], correctPoints[1]);

      // Check slope match
      if (!this.slopesMatch(userSlope, correctSlope)) {
        return ScoringEngine.incorrectResult(1, 'Line slope is incorrect');
      }

      // Check if lines are the same (share a point or have same y-intercept)
      const userIntercept = this.calculateYIntercept(userPoints[0], userSlope);
      const correctIntercept = this.calculateYIntercept(correctPoints[0], correctSlope);

      if (Math.abs(userIntercept - correctIntercept) <= this.options.pointTolerance!) {
        return ScoringEngine.correctResult(1);
      }

      return ScoringEngine.incorrectResult(1, 'Line position is incorrect');
    }

    // For segment or ray, check endpoints
    const startMatch = this.pointsMatch(userPoints[0], correctPoints[0]);
    const endMatch = this.pointsMatch(userPoints[1], correctPoints[1]);

    if (startMatch && endMatch) {
      return ScoringEngine.correctResult(1);
    }

    // Check reversed order
    if (
      lineType === 'segment' &&
      this.pointsMatch(userPoints[0], correctPoints[1]) &&
      this.pointsMatch(userPoints[1], correctPoints[0])
    ) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Validate polygon
   */
  private validatePolygon(user: GraphAnswer, correct: GraphAnswer): ValidatorResult {
    const userPoints = user.coords || user.polygon?.points || [];
    const correctPoints = correct.coords || correct.polygon?.points || [];

    if (userPoints.length < 3) {
      return ScoringEngine.emptyResult();
    }

    if (userPoints.length !== correctPoints.length) {
      return ScoringEngine.incorrectResult(
        1,
        `Expected ${correctPoints.length} vertices, got ${userPoints.length}`
      );
    }

    // Check if polygons match (may be rotated/reflected)
    if (this.polygonsMatch(userPoints, correctPoints)) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Validate circle
   */
  private validateCircle(user: GraphAnswer, correct: GraphAnswer): ValidatorResult {
    const userCircle = user.circle;
    const correctCircle = correct.circle;

    if (!userCircle || !userCircle.center || userCircle.radius === undefined) {
      // Try to extract from coords (center and edge point)
      const userPoints = user.coords || [];
      if (userPoints.length >= 2) {
        const center = userPoints[0];
        const edgePoint = userPoints[1];
        const radius = this.distance(center, edgePoint);

        return this.validateCircleParams(
          { center, radius },
          correctCircle!
        );
      }
      return ScoringEngine.emptyResult();
    }

    return this.validateCircleParams(userCircle, correctCircle!);
  }

  /**
   * Validate circle parameters
   */
  private validateCircleParams(user: Circle, correct: Circle): ValidatorResult {
    const tolerance = this.options.pointTolerance!;

    const centerMatch = this.pointsMatch(user.center, correct.center);
    const radiusMatch = Math.abs(user.radius - correct.radius) <= tolerance;

    if (centerMatch && radiusMatch) {
      return ScoringEngine.correctResult(1);
    }

    if (centerMatch) {
      return ScoringEngine.incorrectResult(1, 'Radius is incorrect');
    }

    if (radiusMatch) {
      return ScoringEngine.incorrectResult(1, 'Center position is incorrect');
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Validate function graph
   */
  private validateFunction(
    user: GraphAnswer,
    correct: GraphAnswer,
    funcType: string
  ): ValidatorResult {
    const userPoints = user.coords || [];
    const correctPoints = correct.coords || [];

    if (userPoints.length < 2) {
      return ScoringEngine.emptyResult();
    }

    // For functions, we need to check if the defining points match
    // This is simplified - a full implementation would compare functions
    let matchCount = 0;
    const tolerance = this.options.pointTolerance!;

    for (const userPoint of userPoints) {
      for (const correctPoint of correctPoints) {
        if (this.pointsMatch(userPoint, correctPoint)) {
          matchCount++;
          break;
        }
      }
    }

    const minRequired = Math.min(userPoints.length, correctPoints.length);
    if (matchCount >= minRequired) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.incorrectResult(1);
  }

  /**
   * Validate linear system
   */
  private validateLinearSystem(user: GraphAnswer, correct: GraphAnswer): ValidatorResult {
    // Linear system should have two lines
    const userLines = user.lines || [];
    const correctLines = correct.lines || [];

    if (userLines.length === 0 && user.coords) {
      // Convert coords to lines (every 2 points = 1 line)
      for (let i = 0; i < user.coords.length - 1; i += 2) {
        userLines.push({
          start: user.coords[i],
          end: user.coords[i + 1],
        });
      }
    }

    if (userLines.length < 2) {
      return ScoringEngine.emptyResult();
    }

    // Check if both lines match
    let matches = 0;
    for (const userLine of userLines) {
      for (const correctLine of correctLines) {
        if (this.linesMatch(userLine, correctLine)) {
          matches++;
          break;
        }
      }
    }

    if (matches === 2) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.partialResult(matches, 2, `${matches} of 2 lines correct`);
  }

  /**
   * Generic validation (fallback)
   */
  private validateGeneric(user: GraphAnswer, correct: GraphAnswer): ValidatorResult {
    const userPoints = user.coords || user.points || [];
    const correctPoints = correct.coords || correct.points || [];

    if (userPoints.length === 0) {
      return ScoringEngine.emptyResult();
    }

    // Simple point-by-point comparison
    if (JSON.stringify(userPoints) === JSON.stringify(correctPoints)) {
      return ScoringEngine.correctResult(1);
    }

    return ScoringEngine.incorrectResult(1);
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  private pointsMatch(p1: Point, p2: Point): boolean {
    const tolerance = this.options.pointTolerance!;
    return (
      Math.abs(p1.x - p2.x) <= tolerance &&
      Math.abs(p1.y - p2.y) <= tolerance
    );
  }

  private distance(p1: Point, p2: Point): number {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  }

  private calculateSlope(p1: Point, p2: Point): number {
    if (p2.x === p1.x) {
      return Infinity;
    }
    return (p2.y - p1.y) / (p2.x - p1.x);
  }

  private calculateYIntercept(point: Point, slope: number): number {
    if (!isFinite(slope)) {
      return NaN;
    }
    return point.y - slope * point.x;
  }

  private slopesMatch(s1: number, s2: number): boolean {
    if (!isFinite(s1) && !isFinite(s2)) {
      return true;
    }
    if (!isFinite(s1) || !isFinite(s2)) {
      return false;
    }
    return Math.abs(s1 - s2) <= this.options.pointTolerance!;
  }

  private linesMatch(l1: Line, l2: Line): boolean {
    // Check if lines have same slope and intercept
    const slope1 = this.calculateSlope(l1.start, l1.end);
    const slope2 = this.calculateSlope(l2.start, l2.end);

    if (!this.slopesMatch(slope1, slope2)) {
      return false;
    }

    const intercept1 = this.calculateYIntercept(l1.start, slope1);
    const intercept2 = this.calculateYIntercept(l2.start, slope2);

    return Math.abs(intercept1 - intercept2) <= this.options.pointTolerance!;
  }

  private polygonsMatch(p1: Point[], p2: Point[]): boolean {
    if (p1.length !== p2.length) {
      return false;
    }

    // Try all rotations
    for (let rotation = 0; rotation < p1.length; rotation++) {
      let allMatch = true;
      for (let i = 0; i < p1.length; i++) {
        const j = (i + rotation) % p1.length;
        if (!this.pointsMatch(p1[i], p2[j])) {
          allMatch = false;
          break;
        }
      }
      if (allMatch) return true;

      // Try reversed order (reflection)
      allMatch = true;
      for (let i = 0; i < p1.length; i++) {
        const j = (p1.length - i + rotation) % p1.length;
        if (!this.pointsMatch(p1[i], p2[j])) {
          allMatch = false;
          break;
        }
      }
      if (allMatch) return true;
    }

    return false;
  }
}

export default GraphValidator;

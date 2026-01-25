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

    // Special handling for dot plots and pictographs
    // These use count arrays instead of coordinate arrays
    if (Array.isArray(options.correct) && typeof options.correct[0] === 'number') {
      return this.validateDotPlot(userGraph, options.correct as number[], options);
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

    // 1. Strict Match (Original Logic)
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

    // 2. Distribution Match Fallback (For Dot Plots defined as Points)
    // If strict (x,y) matching fails, check if the X-distribution matches.
    // This handles cases where Y-stacking is slightly off or floating point x errors exist.
    const getDistribution = (points: Point[]) => {
      return points.map(p => Math.round(p.x)).sort((a, b) => a - b);
    };

    const userDist = getDistribution(userPoints);
    const correctDist = getDistribution(correctPoints);

    let distMatch = true;
    for (let i = 0; i < correctDist.length; i++) {
      if (userDist[i] !== correctDist[i]) {
        distMatch = false;
        break;
      }
    }

    if (distMatch) {
      console.log('Distribution Match (Fallback) passed.');
      return ScoringEngine.correctResult(correctPoints.length);
    }

    // 3. Sliding Window Distribution Fallback
    // Handles offset issues (e.g. range starts -1 but data is 0-based)
    // We try shifting the user distribution to match the correct distribution
    if (userDist.length > 0) {
      const diff = correctDist[0] - userDist[0];
      // Check if consistent shift applies to all
      let shiftMatch = true;
      for (let i = 0; i < correctDist.length; i++) {
        if (correctDist[i] - userDist[i] !== diff) {
          shiftMatch = false;
          break;
        }
      }
      if (shiftMatch && Math.abs(diff) <= 2) { // Allow shift of +/- 2 integer units
        console.log(`Distribution Shift Match (diff=${diff}) passed.`);
        return ScoringEngine.correctResult(correctPoints.length);
      }
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
   * Validate dot plot or pictograph (count-based)
   */
  private validateDotPlot(
    user: any,
    correctCounts: number[],
    options: InteractiveGraphOptions
  ): ValidatorResult {
    // Determine user points - could be raw array [[x,y],...] or GraphAnswer object
    let userPoints: any[] = [];
    if (Array.isArray(user)) {
      userPoints = user;
    } else if (user && typeof user === 'object') {
      userPoints = user.coords || user.points || [];
    }

    if (userPoints.length === 0) {
      if (correctCounts.every(c => c === 0)) return ScoringEngine.correctResult(1);
      return ScoringEngine.emptyResult();
    }

    // Attempt validation strategies
    // 1. Using range-based origin (standard)
    // 2. Using absolute origin 0 (fallback for misconfigured ranges)
    const rangeOrigin = (Array.isArray(options.range) && Array.isArray(options.range[0]))
      ? options.range[0][0]
      : 0;

    // >>> DEBUG LOGGING START
    console.group('GraphValidator: validateDotPlot');
    console.log('User Points:', userPoints);
    console.log('Correct Counts:', correctCounts);
    console.log('Options Range:', options.range);
    // <<< DEBUG LOGGING END

    // Check robustly with potential origin candidates
    const originsToCheck = [rangeOrigin];
    if (rangeOrigin !== 0 && !originsToCheck.includes(0)) originsToCheck.push(0);
    // Add neighbor integer offsets to handle slight range misconfigurations
    [-1, 1].forEach(offset => {
      const candidate = Math.floor(rangeOrigin) + offset;
      if (!originsToCheck.includes(candidate)) originsToCheck.push(candidate);
    });

    let bestResult: ValidatorResult | null = null;
    let maxMatchCount = -1;

    // Strategy 1: Fixed Origin Checks
    for (const xOrigin of originsToCheck) {
      const userCounts: number[] = new Array(correctCounts.length).fill(0);
      let validPointCount = 0;

      for (const point of userPoints) {
        const x = Array.isArray(point) ? point[0] : (point?.x ?? 0);
        const categoryIndex = Math.round(x - xOrigin);
        if (categoryIndex >= 0 && categoryIndex < correctCounts.length) {
          userCounts[categoryIndex]++;
          validPointCount++;
        }
      }

      // If no points fall in valid range with this origin, skip
      if (validPointCount === 0 && userPoints.length > 0) continue;

      let allMatch = true;
      let matchCount = 0;
      for (let i = 0; i < correctCounts.length; i++) {
        if (userCounts[i] === correctCounts[i]) {
          matchCount++;
        } else {
          allMatch = false;
        }
      }

      if (allMatch) {
        console.log(`Match found with xOrigin: ${xOrigin}`);
        console.groupEnd();
        return ScoringEngine.correctResult(1);
      }

      if (matchCount > maxMatchCount) {
        maxMatchCount = matchCount;
        bestResult = ScoringEngine.partialResult(matchCount, correctCounts.length, `${matchCount} correct`);
      }
    }

    // Strategy 2: Sliding Window / Indel-tolerant check
    // If strict absolute positioning fails, check if the *pattern* of distributions matches
    // anywhere within the correct counts (handling offset shifts).

    // Convert user points to a sparse map relative to 0
    const userMap = new Map<number, number>();
    let minUserIdx = Infinity;
    let maxUserIdx = -Infinity;

    for (const point of userPoints) {
      const x = Array.isArray(point) ? point[0] : (point?.x ?? 0);
      const idx = Math.round(x); // Assume points are integers or close to them
      userMap.set(idx, (userMap.get(idx) || 0) + 1);
      if (idx < minUserIdx) minUserIdx = idx;
      if (idx > maxUserIdx) maxUserIdx = idx;
    }

    if (userMap.size > 0) {
      const userLen = maxUserIdx - minUserIdx + 1;
      const userPattern = new Array(userLen).fill(0);
      for (let i = 0; i < userLen; i++) {
        userPattern[i] = userMap.get(minUserIdx + i) || 0;
      }

      console.log('Using Sliding Window Strategy.');
      console.log('User Pattern:', userPattern);
      console.log('Correct Counts:', correctCounts);

      // Try to find userPattern inside correctCounts
      const maxShift = correctCounts.length - userPattern.length;

      for (let shift = 0; shift <= maxShift; shift++) {
        let patternMatch = true;

        // 1. Check if the pattern matches at `shift`
        for (let i = 0; i < userPattern.length; i++) {
          if (correctCounts[shift + i] !== userPattern[i]) {
            patternMatch = false;
            break;
          }
        }

        // 2. Check if the rest of correctCounts is empty (zeros)
        if (patternMatch) {
          for (let i = 0; i < shift; i++) {
            if (correctCounts[i] !== 0) { patternMatch = false; break; }
          }
          for (let i = shift + userPattern.length; i < correctCounts.length; i++) {
            if (correctCounts[i] !== 0) { patternMatch = false; break; }
          }
        }

        if (patternMatch) {
          console.log(`Sliding Window Match found at shift: ${shift}`);
          console.groupEnd();
          return ScoringEngine.correctResult(1);
        }
      }
    }

    console.log('Validation Failed. Best Result:', bestResult);
    console.groupEnd();

    return bestResult || ScoringEngine.incorrectResult(correctCounts.length);
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

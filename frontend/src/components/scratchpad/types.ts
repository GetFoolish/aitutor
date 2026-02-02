/**
 * Scratchpad Teacher Types
 * 
 * TypeScript interfaces for the visual teaching instruction system.
 * Matches the backend API format from /api/scratchpad/generate
 */

import { TLDefaultColorStyle } from 'tldraw';

// ============================================================================
// Position and Style Types
// ============================================================================

export interface Position {
  x: number;
  y: number;
}

export interface Style {
  size?: 'small' | 'medium' | 'large' | 'xlarge';
  color?: string;
  fill?: string;
  width?: number;
}

// ============================================================================
// Action Types
// ============================================================================

export type ActionType = 
  | 'write'
  | 'draw_line'
  | 'draw_arrow'
  | 'draw_shape'
  | 'draw_groups'
  | 'number_line'
  | 'fraction_bar'
  | 'highlight'
  | 'erase';

// ============================================================================
// Individual Action Interfaces
// ============================================================================

export interface WriteAction {
  action: 'write';
  step_id: number;
  position: Position;
  text: string;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface DrawLineAction {
  action: 'draw_line';
  step_id: number;
  from: Position;
  to: Position;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface DrawArrowAction {
  action: 'draw_arrow';
  step_id: number;
  from: Position;
  to: Position;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface DrawShapeAction {
  action: 'draw_shape';
  step_id: number;
  position: Position;
  shape: 'rectangle' | 'circle' | 'ellipse';
  width: number;
  height: number;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface DrawGroupsAction {
  action: 'draw_groups';
  step_id: number;
  position: Position;
  object: string;  // emoji or symbol to draw
  rows: number;
  cols: number;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface NumberLineAction {
  action: 'number_line';
  step_id: number;
  position: Position;
  start: number;
  end: number;
  ticks?: number;
  labels?: number[];
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface FractionBarAction {
  action: 'fraction_bar';
  step_id: number;
  position: Position;
  numerator: number;
  denominator: number;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;
}

export interface HighlightAction {
  action: 'highlight';
  step_id: number;
  position: Position;
  width: number;
  height: number;
  color?: string;
  opacity?: number;
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;  // Add style property for consistency
}

export interface EraseAction {
  action: 'erase';
  step_id: number;
  target_shape_ids?: string[];
  target_area?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  delay_ms: number;
  duration_ms: number;
  narration?: string;
  style?: Style;  // Add style property for consistency
}

// ============================================================================
// Union Type for All Actions
// ============================================================================

export type TeachingStep =
  | WriteAction
  | DrawLineAction
  | DrawArrowAction
  | DrawShapeAction
  | DrawGroupsAction
  | NumberLineAction
  | FractionBarAction
  | HighlightAction
  | EraseAction;

// ============================================================================
// Instruction Set (API Response)
// ============================================================================

export interface InstructionSet {
  explanation_id: string;
  concept: string;
  grade_level: string;
  total_duration_ms: number;
  steps: TeachingStep[];
  _fallback?: boolean;
}

// ============================================================================
// Component Props
// ============================================================================

export type PlaybackSpeed = 0.5 | 1 | 1.5 | 2;

export interface ScratchpadTeacherProps {
  /** Concept to teach (e.g., "7x6", "fractions", "place value") */
  concept: string;
  /** Grade level for age-appropriate explanations (e.g., "K-2", "3-5", "6-8") */
  gradeLevel: string;
  /** Optional context for personalization */
  context?: string;
  /** Initial playback speed (0.5x - 2x) */
  initialSpeed?: PlaybackSpeed;
  /** Called when playback completes */
  onComplete?: () => void;
  /** Called when playback starts */
  onPlay?: () => void;
  /** Called when playback pauses */
  onPause?: () => void;
  /** Called when a step is executed (for narration) */
  onStep?: (step: TeachingStep, index: number) => void;
  /** Custom className for the container */
  className?: string;
  /** Whether to show the control panel */
  showControls?: boolean;
  /** Whether to loop the animation */
  loop?: boolean;
  /** Auto-start playback on mount */
  autoPlay?: boolean;
  /** API base URL (defaults to env or localhost) */
  apiBaseUrl?: string;
}

// ============================================================================
// Internal Types
// ============================================================================

export interface AnimationState {
  isPlaying: boolean;
  isComplete: boolean;
  currentStepIndex: number;
  progress: number;
  speed: PlaybackSpeed;
}

export type ColorMap = Record<string, TLDefaultColorStyle>;

// Color mapping from API colors to tldraw colors
export const COLOR_MAP: ColorMap = {
  black: 'black',
  blue: 'blue',
  green: 'green',
  red: 'red',
  violet: 'violet',
  yellow: 'yellow',
  orange: 'orange',
  pink: 'light-red' as TLDefaultColorStyle,  // Map pink to light-red as tldraw doesn't have pink
  gray: 'grey',
  grey: 'grey',
  lightblue: 'light-blue',
  lightgreen: 'light-green',
  lightred: 'light-red',
  lightviolet: 'light-violet',
  white: 'white',
};

// Size mapping from API sizes to tldraw sizes
export const SIZE_MAP: Record<string, 's' | 'm' | 'l' | 'xl'> = {
  small: 's',
  medium: 'm',
  large: 'l',
  xlarge: 'xl',
};

// ============================================================================
// Type Guards
// ============================================================================

export function isWriteAction(step: TeachingStep): step is WriteAction {
  return step.action === 'write';
}

export function isDrawLineAction(step: TeachingStep): step is DrawLineAction {
  return step.action === 'draw_line';
}

export function isDrawArrowAction(step: TeachingStep): step is DrawArrowAction {
  return step.action === 'draw_arrow';
}

export function isDrawShapeAction(step: TeachingStep): step is DrawShapeAction {
  return step.action === 'draw_shape';
}

export function isDrawGroupsAction(step: TeachingStep): step is DrawGroupsAction {
  return step.action === 'draw_groups';
}

export function isNumberLineAction(step: TeachingStep): step is NumberLineAction {
  return step.action === 'number_line';
}

export function isFractionBarAction(step: TeachingStep): step is FractionBarAction {
  return step.action === 'fraction_bar';
}

export function isHighlightAction(step: TeachingStep): step is HighlightAction {
  return step.action === 'highlight';
}

export function isEraseAction(step: TeachingStep): step is EraseAction {
  return step.action === 'erase';
}

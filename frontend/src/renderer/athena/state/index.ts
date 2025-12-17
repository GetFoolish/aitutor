/**
 * Athena State Module
 *
 * State management utilities for answer tracking and persistence.
 */

export { AnswerStateManager } from './AnswerStateManager';
export type { AnswerState, AnswerStateManagerOptions } from './AnswerStateManager';

export { useAnswerState, useWidgetAnswer } from './useAnswerState';
export type { UseAnswerStateOptions, UseAnswerStateResult } from './useAnswerState';

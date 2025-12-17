/**
 * useAnswerState Hook
 *
 * React hook for using AnswerStateManager in components.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { AnswerStateManager, type AnswerState, type AnswerStateManagerOptions } from './AnswerStateManager';
import type { SerializedState } from '../core/types';

export interface UseAnswerStateOptions extends AnswerStateManagerOptions {
  /** Initial state to restore */
  initialState?: SerializedState;
}

export interface UseAnswerStateResult {
  /** Get answer for a widget */
  getAnswer: (widgetId: string) => unknown;
  /** Set answer for a widget */
  setAnswer: (widgetId: string, value: unknown) => void;
  /** Clear answer for a widget */
  clearAnswer: (widgetId: string) => void;
  /** Clear all answers */
  clearAll: () => void;
  /** Get all answers as record */
  getAllAnswers: () => Record<string, unknown>;
  /** Get all states */
  getAllStates: () => Record<string, AnswerState>;
  /** Serialize state */
  serialize: () => SerializedState;
  /** Restore state */
  restore: (state: SerializedState) => void;
  /** Undo last action */
  undo: () => boolean;
  /** Redo last undone action */
  redo: () => boolean;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
  /** Whether any answer exists */
  hasAnswers: boolean;
  /** Check if widget has answer */
  hasAnswer: (widgetId: string) => boolean;
  /** Answer statistics */
  stats: ReturnType<AnswerStateManager['getStats']>;
  /** The underlying manager instance */
  manager: AnswerStateManager;
}

/**
 * Hook for managing answer state
 */
export function useAnswerState(options: UseAnswerStateOptions = {}): UseAnswerStateResult {
  // Create manager once
  const managerRef = useRef<AnswerStateManager | null>(null);
  if (!managerRef.current) {
    managerRef.current = new AnswerStateManager(options);
    if (options.initialState) {
      managerRef.current.restoreState(options.initialState);
    }
  }
  const manager = managerRef.current;

  // State for re-renders
  const [, forceUpdate] = useState({});
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  // Subscribe to manager changes
  useEffect(() => {
    const unsubscribe = manager.subscribe(() => {
      setCanUndo(manager.canUndo());
      setCanRedo(manager.canRedo());
      forceUpdate({});
    });

    return () => {
      unsubscribe();
    };
  }, [manager]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      manager.dispose();
    };
  }, [manager]);

  // Memoized methods
  const getAnswer = useCallback((widgetId: string) => manager.getAnswer(widgetId), [manager]);
  const setAnswer = useCallback((widgetId: string, value: unknown) => manager.setAnswer(widgetId, value), [manager]);
  const clearAnswer = useCallback((widgetId: string) => manager.clearAnswer(widgetId), [manager]);
  const clearAll = useCallback(() => manager.clearAll(), [manager]);
  const getAllAnswers = useCallback(() => manager.getAllAnswers(), [manager]);
  const getAllStates = useCallback(() => manager.getAllStates(), [manager]);
  const serialize = useCallback(() => manager.serialize(), [manager]);
  const restore = useCallback((state: SerializedState) => manager.restoreState(state), [manager]);
  const undo = useCallback(() => manager.undo(), [manager]);
  const redo = useCallback(() => manager.redo(), [manager]);
  const hasAnswer = useCallback((widgetId: string) => manager.hasAnswer(widgetId), [manager]);

  const hasAnswers = manager.hasAnswers();
  const stats = useMemo(() => manager.getStats(), [manager, hasAnswers]);

  return {
    getAnswer,
    setAnswer,
    clearAnswer,
    clearAll,
    getAllAnswers,
    getAllStates,
    serialize,
    restore,
    undo,
    redo,
    canUndo,
    canRedo,
    hasAnswers,
    hasAnswer,
    stats,
    manager,
  };
}

/**
 * Hook for a single widget's answer
 */
export function useWidgetAnswer<T = unknown>(
  manager: AnswerStateManager,
  widgetId: string,
  defaultValue?: T
): [T | undefined, (value: T) => void] {
  const [value, setValue] = useState<T | undefined>(
    () => (manager.getAnswer(widgetId) as T) ?? defaultValue
  );

  useEffect(() => {
    const unsubscribe = manager.subscribe((states) => {
      const state = states[widgetId];
      setValue((state?.value as T) ?? defaultValue);
    });

    return unsubscribe;
  }, [manager, widgetId, defaultValue]);

  const setWidgetValue = useCallback(
    (newValue: T) => {
      manager.setAnswer(widgetId, newValue);
    },
    [manager, widgetId]
  );

  return [value, setWidgetValue];
}

export default useAnswerState;

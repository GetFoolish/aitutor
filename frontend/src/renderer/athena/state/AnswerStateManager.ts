/**
 * Answer State Manager
 *
 * Manages user answer state including:
 * - Answer tracking per widget
 * - State serialization/restoration
 * - LocalStorage persistence
 * - Undo/redo support
 */

import type { SerializedState, WidgetUserInput } from '../core/types';

export interface AnswerState {
  /** Widget ID */
  widgetId: string;
  /** Current answer value */
  value: unknown;
  /** Timestamp of last change */
  timestamp: number;
  /** Number of attempts */
  attempts: number;
  /** Whether answer has been submitted */
  submitted: boolean;
}

export interface AnswerStateManagerOptions {
  /** Key for localStorage persistence */
  storageKey?: string;
  /** Whether to auto-save to localStorage */
  autoPersist?: boolean;
  /** Debounce delay for auto-persist (ms) */
  persistDelay?: number;
  /** Maximum undo history size */
  maxUndoHistory?: number;
  /** Callback on state change */
  onChange?: (state: Record<string, AnswerState>) => void;
}

/**
 * Manages user answer state
 */
export class AnswerStateManager {
  private state: Map<string, AnswerState>;
  private options: AnswerStateManagerOptions;
  private listeners: Set<(state: Record<string, AnswerState>) => void>;
  private undoStack: Array<Map<string, AnswerState>>;
  private redoStack: Array<Map<string, AnswerState>>;
  private persistTimeout: ReturnType<typeof setTimeout> | null;

  constructor(options: AnswerStateManagerOptions = {}) {
    this.options = {
      autoPersist: false,
      persistDelay: 1000,
      maxUndoHistory: 20,
      ...options,
    };

    this.state = new Map();
    this.listeners = new Set();
    this.undoStack = [];
    this.redoStack = [];
    this.persistTimeout = null;

    // Restore from localStorage if key provided
    if (this.options.storageKey) {
      this.restore();
    }
  }

  /**
   * Get answer for a widget
   */
  getAnswer(widgetId: string): unknown {
    return this.state.get(widgetId)?.value;
  }

  /**
   * Get answer state for a widget
   */
  getAnswerState(widgetId: string): AnswerState | undefined {
    return this.state.get(widgetId);
  }

  /**
   * Set answer for a widget
   */
  setAnswer(widgetId: string, value: unknown): void {
    // Save current state for undo
    this.pushUndoState();

    // Get or create answer state
    const existing = this.state.get(widgetId);
    const newState: AnswerState = {
      widgetId,
      value,
      timestamp: Date.now(),
      attempts: (existing?.attempts || 0) + (value !== existing?.value ? 1 : 0),
      submitted: existing?.submitted || false,
    };

    this.state.set(widgetId, newState);

    // Clear redo stack on new action
    this.redoStack = [];

    // Notify listeners
    this.notifyListeners();

    // Auto-persist if enabled
    if (this.options.autoPersist) {
      this.schedulePersist();
    }
  }

  /**
   * Mark answer as submitted
   */
  markSubmitted(widgetId: string): void {
    const existing = this.state.get(widgetId);
    if (existing) {
      this.state.set(widgetId, {
        ...existing,
        submitted: true,
        timestamp: Date.now(),
      });
      this.notifyListeners();
    }
  }

  /**
   * Clear answer for a widget
   */
  clearAnswer(widgetId: string): void {
    this.pushUndoState();
    this.state.delete(widgetId);
    this.notifyListeners();
  }

  /**
   * Clear all answers
   */
  clearAll(): void {
    this.pushUndoState();
    this.state.clear();
    this.notifyListeners();

    // Clear persisted state
    if (this.options.storageKey) {
      try {
        localStorage.removeItem(this.options.storageKey);
      } catch (e) {
        console.warn('Failed to clear persisted state:', e);
      }
    }
  }

  /**
   * Get all answers as a record
   */
  getAllAnswers(): Record<string, unknown> {
    const answers: Record<string, unknown> = {};
    this.state.forEach((state, widgetId) => {
      answers[widgetId] = state.value;
    });
    return answers;
  }

  /**
   * Get all answer states
   */
  getAllStates(): Record<string, AnswerState> {
    const states: Record<string, AnswerState> = {};
    this.state.forEach((state, widgetId) => {
      states[widgetId] = state;
    });
    return states;
  }

  /**
   * Serialize state for persistence
   */
  serialize(): SerializedState {
    const question: Record<string, unknown> = {};
    this.state.forEach((state, widgetId) => {
      question[widgetId] = {
        value: state.value,
        attempts: state.attempts,
        submitted: state.submitted,
      };
    });
    return { question };
  }

  /**
   * Restore state from serialized data
   */
  restoreState(serialized: SerializedState): void {
    this.state.clear();

    if (serialized.question) {
      for (const [widgetId, data] of Object.entries(serialized.question)) {
        const stateData = data as Record<string, unknown>;
        this.state.set(widgetId, {
          widgetId,
          value: stateData.value,
          timestamp: Date.now(),
          attempts: (stateData.attempts as number) || 0,
          submitted: (stateData.submitted as boolean) || false,
        });
      }
    }

    this.notifyListeners();
  }

  /**
   * Persist state to localStorage
   */
  persist(): void {
    if (!this.options.storageKey) {
      return;
    }

    try {
      const serialized = this.serialize();
      localStorage.setItem(this.options.storageKey, JSON.stringify(serialized));
    } catch (e) {
      console.warn('Failed to persist state:', e);
    }
  }

  /**
   * Restore state from localStorage
   */
  restore(): void {
    if (!this.options.storageKey) {
      return;
    }

    try {
      const stored = localStorage.getItem(this.options.storageKey);
      if (stored) {
        const serialized = JSON.parse(stored) as SerializedState;
        this.restoreState(serialized);
      }
    } catch (e) {
      console.warn('Failed to restore state:', e);
    }
  }

  /**
   * Undo last action
   */
  undo(): boolean {
    if (this.undoStack.length === 0) {
      return false;
    }

    // Save current state to redo stack
    this.redoStack.push(new Map(this.state));

    // Restore previous state
    const previousState = this.undoStack.pop()!;
    this.state = previousState;

    this.notifyListeners();
    return true;
  }

  /**
   * Redo last undone action
   */
  redo(): boolean {
    if (this.redoStack.length === 0) {
      return false;
    }

    // Save current state to undo stack
    this.undoStack.push(new Map(this.state));

    // Restore next state
    const nextState = this.redoStack.pop()!;
    this.state = nextState;

    this.notifyListeners();
    return true;
  }

  /**
   * Check if undo is available
   */
  canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  /**
   * Check if redo is available
   */
  canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: (state: Record<string, AnswerState>) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Check if any answer has been provided
   */
  hasAnswers(): boolean {
    return this.state.size > 0;
  }

  /**
   * Check if specific widget has answer
   */
  hasAnswer(widgetId: string): boolean {
    const state = this.state.get(widgetId);
    if (!state) return false;
    return state.value !== undefined && state.value !== null && state.value !== '';
  }

  /**
   * Get statistics about answers
   */
  getStats(): {
    totalWidgets: number;
    answeredWidgets: number;
    totalAttempts: number;
    submittedCount: number;
  } {
    let totalAttempts = 0;
    let submittedCount = 0;

    this.state.forEach((state) => {
      totalAttempts += state.attempts;
      if (state.submitted) submittedCount++;
    });

    return {
      totalWidgets: this.state.size,
      answeredWidgets: Array.from(this.state.values()).filter(
        (s) => s.value !== undefined && s.value !== null && s.value !== ''
      ).length,
      totalAttempts,
      submittedCount,
    };
  }

  /**
   * Push current state to undo stack
   */
  private pushUndoState(): void {
    this.undoStack.push(new Map(this.state));

    // Limit undo history size
    while (this.undoStack.length > (this.options.maxUndoHistory || 20)) {
      this.undoStack.shift();
    }
  }

  /**
   * Notify all listeners
   */
  private notifyListeners(): void {
    const states = this.getAllStates();
    this.listeners.forEach((listener) => listener(states));
    this.options.onChange?.(states);
  }

  /**
   * Schedule persist with debounce
   */
  private schedulePersist(): void {
    if (this.persistTimeout) {
      clearTimeout(this.persistTimeout);
    }

    this.persistTimeout = setTimeout(() => {
      this.persist();
      this.persistTimeout = null;
    }, this.options.persistDelay || 1000);
  }

  /**
   * Dispose manager and cleanup
   */
  dispose(): void {
    if (this.persistTimeout) {
      clearTimeout(this.persistTimeout);
    }
    this.listeners.clear();
  }
}

export default AnswerStateManager;

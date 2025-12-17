/**
 * Hints State Manager
 *
 * Manages the state of hints including:
 * - Which hints have been revealed
 * - Progressive hint unlock
 * - Hint usage tracking
 */

import type { AthenaHint } from '../core/types';

export interface HintState {
  /** Index of the hint */
  index: number;
  /** Whether the hint is visible */
  visible: boolean;
  /** Timestamp when hint was revealed */
  revealedAt?: number;
  /** Whether hint was viewed by user */
  viewed: boolean;
}

export interface HintsState {
  /** Total number of hints available */
  totalHints: number;
  /** Number of hints currently visible */
  visibleCount: number;
  /** State of each hint */
  hints: HintState[];
  /** Whether all hints have been revealed */
  allRevealed: boolean;
  /** Whether hints are available */
  hasHints: boolean;
}

export interface HintsStateManagerOptions {
  /** Initial visible hint count */
  initialVisibleCount?: number;
  /** Whether to allow revealing hints */
  allowReveal?: boolean;
  /** Maximum hints to reveal at once */
  maxRevealAtOnce?: number;
  /** Callback when hint is revealed */
  onHintReveal?: (index: number) => void;
  /** Callback when hint is viewed */
  onHintView?: (index: number) => void;
}

/**
 * Manages hints state
 */
export class HintsStateManager {
  private hints: AthenaHint[];
  private state: HintsState;
  private options: HintsStateManagerOptions;
  private listeners: Set<(state: HintsState) => void>;

  constructor(hints: AthenaHint[], options: HintsStateManagerOptions = {}) {
    this.hints = hints;
    this.options = {
      initialVisibleCount: 0,
      allowReveal: true,
      maxRevealAtOnce: 1,
      ...options,
    };
    this.listeners = new Set();

    // Initialize state
    this.state = this.createInitialState();
  }

  /**
   * Create initial state
   */
  private createInitialState(): HintsState {
    const initialCount = Math.min(
      this.options.initialVisibleCount || 0,
      this.hints.length
    );

    const hintStates: HintState[] = this.hints.map((_, index) => ({
      index,
      visible: index < initialCount,
      viewed: false,
      revealedAt: index < initialCount ? Date.now() : undefined,
    }));

    return {
      totalHints: this.hints.length,
      visibleCount: initialCount,
      hints: hintStates,
      allRevealed: initialCount >= this.hints.length,
      hasHints: this.hints.length > 0,
    };
  }

  /**
   * Get current state
   */
  getState(): HintsState {
    return { ...this.state };
  }

  /**
   * Get hints data
   */
  getHints(): AthenaHint[] {
    return this.hints;
  }

  /**
   * Get visible hints
   */
  getVisibleHints(): AthenaHint[] {
    return this.hints.slice(0, this.state.visibleCount);
  }

  /**
   * Get next hidden hint (if any)
   */
  getNextHint(): AthenaHint | null {
    if (this.state.visibleCount >= this.hints.length) {
      return null;
    }
    return this.hints[this.state.visibleCount];
  }

  /**
   * Reveal the next hint
   */
  revealNext(): boolean {
    if (!this.options.allowReveal) {
      return false;
    }

    if (this.state.visibleCount >= this.hints.length) {
      return false;
    }

    const newIndex = this.state.visibleCount;
    this.state.hints[newIndex] = {
      ...this.state.hints[newIndex],
      visible: true,
      revealedAt: Date.now(),
    };

    this.state.visibleCount++;
    this.state.allRevealed = this.state.visibleCount >= this.hints.length;

    this.options.onHintReveal?.(newIndex);
    this.notifyListeners();

    return true;
  }

  /**
   * Reveal multiple hints at once
   */
  revealMultiple(count: number): number {
    if (!this.options.allowReveal) {
      return 0;
    }

    const maxToReveal = Math.min(
      count,
      this.options.maxRevealAtOnce || count,
      this.hints.length - this.state.visibleCount
    );

    let revealed = 0;
    for (let i = 0; i < maxToReveal; i++) {
      if (this.revealNextInternal()) {
        revealed++;
      }
    }

    if (revealed > 0) {
      this.notifyListeners();
    }

    return revealed;
  }

  /**
   * Internal reveal without notification
   */
  private revealNextInternal(): boolean {
    if (this.state.visibleCount >= this.hints.length) {
      return false;
    }

    const newIndex = this.state.visibleCount;
    this.state.hints[newIndex] = {
      ...this.state.hints[newIndex],
      visible: true,
      revealedAt: Date.now(),
    };

    this.state.visibleCount++;
    this.state.allRevealed = this.state.visibleCount >= this.hints.length;

    this.options.onHintReveal?.(newIndex);

    return true;
  }

  /**
   * Reveal all hints
   */
  revealAll(): number {
    const toReveal = this.hints.length - this.state.visibleCount;
    return this.revealMultiple(toReveal);
  }

  /**
   * Mark a hint as viewed
   */
  markViewed(index: number): void {
    if (index < 0 || index >= this.state.visibleCount) {
      return;
    }

    if (!this.state.hints[index].viewed) {
      this.state.hints[index] = {
        ...this.state.hints[index],
        viewed: true,
      };

      this.options.onHintView?.(index);
      this.notifyListeners();
    }
  }

  /**
   * Reset hints to initial state
   */
  reset(): void {
    this.state = this.createInitialState();
    this.notifyListeners();
  }

  /**
   * Set visible count directly (for review mode)
   */
  setVisibleCount(count: number): void {
    const validCount = Math.max(0, Math.min(count, this.hints.length));

    this.state.hints = this.hints.map((_, index) => ({
      index,
      visible: index < validCount,
      viewed: this.state.hints[index]?.viewed || false,
      revealedAt: index < validCount ? (this.state.hints[index]?.revealedAt || Date.now()) : undefined,
    }));

    this.state.visibleCount = validCount;
    this.state.allRevealed = validCount >= this.hints.length;

    this.notifyListeners();
  }

  /**
   * Check if more hints are available
   */
  hasMoreHints(): boolean {
    return this.state.visibleCount < this.hints.length;
  }

  /**
   * Get count of remaining hints
   */
  getRemainingCount(): number {
    return this.hints.length - this.state.visibleCount;
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: (state: HintsState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Notify all listeners
   */
  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach((listener) => listener(state));
  }

  /**
   * Serialize state for persistence
   */
  serialize(): {
    visibleCount: number;
    viewedIndices: number[];
  } {
    return {
      visibleCount: this.state.visibleCount,
      viewedIndices: this.state.hints
        .filter((h) => h.viewed)
        .map((h) => h.index),
    };
  }

  /**
   * Restore state from serialized data
   */
  restore(data: { visibleCount: number; viewedIndices: number[] }): void {
    this.setVisibleCount(data.visibleCount);

    for (const index of data.viewedIndices) {
      if (index < this.state.hints.length) {
        this.state.hints[index].viewed = true;
      }
    }

    this.notifyListeners();
  }

  /**
   * Get usage statistics
   */
  getStats(): {
    total: number;
    revealed: number;
    viewed: number;
    remaining: number;
    percentRevealed: number;
    percentViewed: number;
  } {
    const total = this.hints.length;
    const revealed = this.state.visibleCount;
    const viewed = this.state.hints.filter((h) => h.viewed).length;
    const remaining = total - revealed;

    return {
      total,
      revealed,
      viewed,
      remaining,
      percentRevealed: total > 0 ? (revealed / total) * 100 : 0,
      percentViewed: revealed > 0 ? (viewed / revealed) * 100 : 0,
    };
  }
}

export default HintsStateManager;

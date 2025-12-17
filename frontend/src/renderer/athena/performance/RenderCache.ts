/**
 * Render Cache
 *
 * Memoization and caching utilities for rendered content.
 */

export interface CacheEntry<T> {
  value: T;
  timestamp: number;
  hits: number;
  size?: number;
}

export interface CacheOptions {
  /** Maximum number of entries */
  maxSize?: number;
  /** Time to live in ms */
  ttl?: number;
  /** Whether to track hit counts */
  trackHits?: boolean;
  /** Eviction strategy */
  eviction?: 'lru' | 'lfu' | 'fifo';
}

/**
 * LRU Cache implementation
 */
export class LRUCache<K, V> {
  private cache: Map<K, CacheEntry<V>> = new Map();
  private maxSize: number;
  private ttl: number;
  private trackHits: boolean;

  constructor(options: CacheOptions = {}) {
    this.maxSize = options.maxSize ?? 100;
    this.ttl = options.ttl ?? 0;
    this.trackHits = options.trackHits ?? false;
  }

  /**
   * Get a value from cache
   */
  get(key: K): V | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    // Check TTL
    if (this.ttl > 0 && Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return undefined;
    }

    // Update hit count and move to end (LRU)
    if (this.trackHits) {
      entry.hits++;
    }

    // Move to end for LRU ordering
    this.cache.delete(key);
    this.cache.set(key, entry);

    return entry.value;
  }

  /**
   * Set a value in cache
   */
  set(key: K, value: V, size?: number): void {
    // Evict if at capacity
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }

    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      hits: 0,
      size,
    });
  }

  /**
   * Check if key exists
   */
  has(key: K): boolean {
    const entry = this.cache.get(key);
    if (!entry) return false;

    // Check TTL
    if (this.ttl > 0 && Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return false;
    }

    return true;
  }

  /**
   * Delete a key
   */
  delete(key: K): boolean {
    return this.cache.delete(key);
  }

  /**
   * Clear all entries
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache size
   */
  get size(): number {
    return this.cache.size;
  }

  /**
   * Get cache stats
   */
  getStats(): {
    size: number;
    maxSize: number;
    totalHits: number;
    entries: Array<{ key: K; hits: number; age: number }>;
  } {
    let totalHits = 0;
    const entries: Array<{ key: K; hits: number; age: number }> = [];
    const now = Date.now();

    this.cache.forEach((entry, key) => {
      totalHits += entry.hits;
      entries.push({
        key,
        hits: entry.hits,
        age: now - entry.timestamp,
      });
    });

    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      totalHits,
      entries,
    };
  }
}

/**
 * Render cache for memoizing rendered content
 */
export class RenderCache {
  private cache: LRUCache<string, string>;
  private hashFn: (input: unknown) => string;

  constructor(options: CacheOptions = {}) {
    this.cache = new LRUCache(options);
    this.hashFn = defaultHash;
  }

  /**
   * Get or compute cached render
   */
  getOrCompute(
    key: string,
    input: unknown,
    computeFn: () => string
  ): string {
    const fullKey = `${key}:${this.hashFn(input)}`;
    const cached = this.cache.get(fullKey);
    if (cached !== undefined) {
      return cached;
    }

    const result = computeFn();
    this.cache.set(fullKey, result, result.length);
    return result;
  }

  /**
   * Invalidate cache entries matching a pattern
   */
  invalidate(pattern: string | RegExp): number {
    let count = 0;
    const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern;

    // Note: LRU cache doesn't expose iteration, so we track keys separately
    // For now, just clear all
    this.cache.clear();
    return count;
  }

  /**
   * Clear all cached renders
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache stats
   */
  getStats() {
    return this.cache.getStats();
  }
}

/**
 * Default hash function
 */
function defaultHash(input: unknown): string {
  const str = JSON.stringify(input);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(36);
}

/**
 * Create a memoized function
 */
export function memoize<T extends (...args: any[]) => any>(
  fn: T,
  options: CacheOptions & {
    keyFn?: (...args: Parameters<T>) => string;
  } = {}
): T & { cache: LRUCache<string, ReturnType<T>>; clear: () => void } {
  const cache = new LRUCache<string, ReturnType<T>>(options);
  const keyFn = options.keyFn ?? ((...args) => JSON.stringify(args));

  const memoized = ((...args: Parameters<T>): ReturnType<T> => {
    const key = keyFn(...args);
    const cached = cache.get(key);
    if (cached !== undefined) {
      return cached;
    }

    const result = fn(...args);
    cache.set(key, result);
    return result;
  }) as T & { cache: LRUCache<string, ReturnType<T>>; clear: () => void };

  memoized.cache = cache;
  memoized.clear = () => cache.clear();

  return memoized;
}

/**
 * Create a memoized async function
 */
export function memoizeAsync<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: CacheOptions & {
    keyFn?: (...args: Parameters<T>) => string;
  } = {}
): T & { cache: LRUCache<string, Awaited<ReturnType<T>>>; clear: () => void } {
  const cache = new LRUCache<string, Awaited<ReturnType<T>>>(options);
  const pendingPromises = new Map<string, Promise<Awaited<ReturnType<T>>>>();
  const keyFn = options.keyFn ?? ((...args) => JSON.stringify(args));

  const memoized = (async (...args: Parameters<T>): Promise<Awaited<ReturnType<T>>> => {
    const key = keyFn(...args);

    // Check cache
    const cached = cache.get(key);
    if (cached !== undefined) {
      return cached;
    }

    // Check pending
    const pending = pendingPromises.get(key);
    if (pending) {
      return pending;
    }

    // Create new promise
    const promise = fn(...args).then((result) => {
      cache.set(key, result);
      pendingPromises.delete(key);
      return result;
    });

    pendingPromises.set(key, promise);
    return promise;
  }) as T & { cache: LRUCache<string, Awaited<ReturnType<T>>>; clear: () => void };

  memoized.cache = cache;
  memoized.clear = () => {
    cache.clear();
    pendingPromises.clear();
  };

  return memoized;
}

/**
 * Global render cache instance
 */
export const renderCache = new RenderCache({
  maxSize: 500,
  ttl: 5 * 60 * 1000, // 5 minutes
  trackHits: true,
});

export default {
  LRUCache,
  RenderCache,
  memoize,
  memoizeAsync,
  renderCache,
};

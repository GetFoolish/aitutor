/**
 * Lazy Loader
 *
 * Utilities for lazy loading modules and components.
 */

import React from 'react';

export interface LazyModule<T> {
  /** Module loader function */
  loader: () => Promise<T>;
  /** Whether module is loaded */
  loaded: boolean;
  /** Cached module reference */
  module: T | null;
  /** Loading promise */
  promise: Promise<T> | null;
  /** Error if loading failed */
  error: Error | null;
}

export interface LazyLoaderOptions {
  /** Retry count on failure */
  retries?: number;
  /** Retry delay in ms */
  retryDelay?: number;
  /** Timeout in ms */
  timeout?: number;
  /** Called when loading starts */
  onLoadStart?: () => void;
  /** Called when loading completes */
  onLoadComplete?: (module: unknown) => void;
  /** Called on error */
  onError?: (error: Error) => void;
}

/**
 * Create a lazy loader for a module
 */
export function createLazyLoader<T>(
  loader: () => Promise<T>,
  options: LazyLoaderOptions = {}
): LazyModule<T> {
  const {
    retries = 3,
    retryDelay = 1000,
    timeout = 30000,
    onLoadStart,
    onLoadComplete,
    onError,
  } = options;

  const lazyModule: LazyModule<T> = {
    loader,
    loaded: false,
    module: null,
    promise: null,
    error: null,
  };

  return lazyModule;
}

/**
 * Load a lazy module
 */
export async function loadModule<T>(
  lazyModule: LazyModule<T>,
  options: LazyLoaderOptions = {}
): Promise<T> {
  const {
    retries = 3,
    retryDelay = 1000,
    timeout = 30000,
    onLoadStart,
    onLoadComplete,
    onError,
  } = options;

  // Return cached module if already loaded
  if (lazyModule.loaded && lazyModule.module) {
    return lazyModule.module;
  }

  // Return existing promise if loading
  if (lazyModule.promise) {
    return lazyModule.promise;
  }

  onLoadStart?.();

  // Create loading promise with retries
  lazyModule.promise = (async () => {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        // Add timeout
        const result = await Promise.race([
          lazyModule.loader(),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Module load timeout')), timeout)
          ),
        ]);

        lazyModule.module = result;
        lazyModule.loaded = true;
        lazyModule.error = null;
        onLoadComplete?.(result);
        return result;
      } catch (error) {
        lastError = error as Error;
        lazyModule.error = lastError;

        if (attempt < retries) {
          await new Promise((resolve) => setTimeout(resolve, retryDelay));
        }
      }
    }

    onError?.(lastError!);
    throw lastError;
  })();

  return lazyModule.promise;
}

/**
 * Preload multiple modules in parallel
 */
export async function preloadModules<T extends Record<string, LazyModule<unknown>>>(
  modules: T,
  options?: LazyLoaderOptions
): Promise<{ [K in keyof T]: Awaited<ReturnType<T[K]['loader']>> }> {
  const entries = Object.entries(modules);
  const results = await Promise.all(
    entries.map(([key, mod]) => loadModule(mod, options).then((m) => [key, m] as const))
  );
  return Object.fromEntries(results) as { [K in keyof T]: Awaited<ReturnType<T[K]['loader']>> };
}

/**
 * Create a component lazy loader with React.lazy
 */
export function createLazyComponent<T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T } | T>
): React.LazyExoticComponent<T> {
  return React.lazy(async () => {
    const mod = await importFn();
    if ('default' in mod) {
      return mod;
    }
    return { default: mod };
  });
}

/**
 * Module registry for managing lazy modules
 */
export class ModuleRegistry {
  private modules: Map<string, LazyModule<unknown>> = new Map();
  private loadedModules: Set<string> = new Set();

  /**
   * Register a lazy module
   */
  register<T>(name: string, loader: () => Promise<T>): void {
    if (this.modules.has(name)) {
      console.warn(`Module '${name}' is already registered`);
      return;
    }

    this.modules.set(name, createLazyLoader(loader));
  }

  /**
   * Get a module by name
   */
  async get<T>(name: string, options?: LazyLoaderOptions): Promise<T> {
    const module = this.modules.get(name);
    if (!module) {
      throw new Error(`Module '${name}' not found in registry`);
    }

    const result = await loadModule(module as LazyModule<T>, options);
    this.loadedModules.add(name);
    return result;
  }

  /**
   * Check if a module is loaded
   */
  isLoaded(name: string): boolean {
    return this.loadedModules.has(name);
  }

  /**
   * Check if a module is registered
   */
  isRegistered(name: string): boolean {
    return this.modules.has(name);
  }

  /**
   * Preload specified modules
   */
  async preload(names: string[], options?: LazyLoaderOptions): Promise<void> {
    await Promise.all(names.map((name) => this.get(name, options)));
  }

  /**
   * Get all loaded modules
   */
  getLoadedModules(): string[] {
    return Array.from(this.loadedModules);
  }

  /**
   * Clear all cached modules
   */
  clear(): void {
    this.modules.forEach((mod) => {
      mod.loaded = false;
      mod.module = null;
      mod.promise = null;
      mod.error = null;
    });
    this.loadedModules.clear();
  }
}

// Global module registry instance
export const moduleRegistry = new ModuleRegistry();

/**
 * Dynamic import with chunk name
 */
export function dynamicImport<T>(
  importFn: () => Promise<T>,
  chunkName?: string
): () => Promise<T> {
  return importFn;
}

/**
 * Prefetch a module (browser-level prefetching)
 */
export function prefetchModule(url: string): void {
  if (typeof document === 'undefined') return;

  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = url;
  document.head.appendChild(link);
}

/**
 * Preload a module (browser-level preloading)
 */
export function preloadModule(url: string): void {
  if (typeof document === 'undefined') return;

  const link = document.createElement('link');
  link.rel = 'modulepreload';
  link.href = url;
  document.head.appendChild(link);
}

export default {
  createLazyLoader,
  loadModule,
  preloadModules,
  createLazyComponent,
  ModuleRegistry,
  moduleRegistry,
  dynamicImport,
  prefetchModule,
  preloadModule,
};

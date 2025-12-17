/**
 * useNotationEngine Hook
 *
 * React hook for using notation engines within components.
 * Handles lazy loading, caching, and status tracking.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { NotationEngineManager, NotationEngineManagerClass } from './NotationEngineManager';
import type { NotationType, NotationEngine, NotationRenderOptions } from '../core/types';

interface UseNotationEngineResult {
  // Status
  isLoading: boolean;
  isLoaded: boolean;
  error: Error | null;

  // Engine instance (null if not loaded)
  engine: NotationEngine | null;

  // Convenience methods
  render: (content: string, container: HTMLElement, options?: NotationRenderOptions) => Promise<void>;
  renderToString: (content: string, options?: NotationRenderOptions) => Promise<string>;

  // Manual control
  preload: () => Promise<void>;
}

/**
 * Hook for using a specific notation engine
 */
export function useNotationEngine(type: NotationType): UseNotationEngineResult {
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(NotationEngineManager.isLoaded(type));
  const [error, setError] = useState<Error | null>(null);
  const [engine, setEngine] = useState<NotationEngine | null>(
    NotationEngineManager.isLoaded(type) ? NotationEngineManager.getEngine(type) : null
  );

  // Track mounted state to avoid state updates after unmount
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    // Subscribe to engine status changes
    const unsubscribe = NotationEngineManager.subscribe((changedType, status) => {
      if (changedType === type && mountedRef.current) {
        setIsLoading(status === 'loading');
        setIsLoaded(status === 'loaded');

        if (status === 'loaded') {
          try {
            setEngine(NotationEngineManager.getEngine(type));
          } catch (e) {
            // Engine not actually loaded
          }
        } else if (status === 'error') {
          setError(new Error(`Failed to load ${type} engine`));
        }
      }
    });

    return () => {
      mountedRef.current = false;
      unsubscribe();
    };
  }, [type]);

  // Preload function
  const preload = useCallback(async () => {
    if (isLoaded || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      await NotationEngineManager.loadEngine(type);
      if (mountedRef.current) {
        setEngine(NotationEngineManager.getEngine(type));
        setIsLoaded(true);
      }
    } catch (e) {
      if (mountedRef.current) {
        setError(e instanceof Error ? e : new Error(String(e)));
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [type, isLoaded, isLoading]);

  // Render function
  const render = useCallback(
    async (content: string, container: HTMLElement, options?: NotationRenderOptions) => {
      await NotationEngineManager.render(type, content, container, options);
    },
    [type]
  );

  // Render to string function
  const renderToString = useCallback(
    async (content: string, options?: NotationRenderOptions) => {
      return NotationEngineManager.renderToString(type, content, options);
    },
    [type]
  );

  return {
    isLoading,
    isLoaded,
    error,
    engine,
    render,
    renderToString,
    preload,
  };
}

/**
 * Hook for detecting and preloading required notation engines
 */
export function useNotationDetection(content: string): {
  detectedTypes: NotationType[];
  preloadAll: () => Promise<void>;
  allLoaded: boolean;
} {
  const [detectedTypes, setDetectedTypes] = useState<NotationType[]>([]);
  const [loadedEngines, setLoadedEngines] = useState<Set<NotationType>>(new Set());

  // Detect notation types in content
  useEffect(() => {
    const types = NotationEngineManagerClass.detectNotationTypes(content);
    setDetectedTypes(types);

    // Check which are already loaded
    const loaded = new Set<NotationType>();
    types.forEach((type: NotationType) => {
      if (NotationEngineManager.isLoaded(type)) {
        loaded.add(type);
      }
    });
    setLoadedEngines(loaded);
  }, [content]);

  // Subscribe to engine loading
  useEffect(() => {
    const unsubscribe = NotationEngineManager.subscribe((type, status) => {
      if (detectedTypes.includes(type) && status === 'loaded') {
        setLoadedEngines((prev) => new Set([...prev, type]));
      }
    });

    return unsubscribe;
  }, [detectedTypes]);

  // Preload all detected engines
  const preloadAll = useCallback(async () => {
    await Promise.all(detectedTypes.map((type) => NotationEngineManager.loadEngine(type)));
  }, [detectedTypes]);

  // Check if all detected engines are loaded
  const allLoaded = detectedTypes.every((type) => loadedEngines.has(type));

  return {
    detectedTypes,
    preloadAll,
    allLoaded,
  };
}

/**
 * Hook for rendering notation content
 */
export function useNotationRender(
  type: NotationType,
  content: string,
  options?: NotationRenderOptions
): {
  html: string;
  isLoading: boolean;
  error: Error | null;
} {
  const [html, setHtml] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    setIsLoading(true);
    setError(null);

    NotationEngineManager.renderToString(type, content, options)
      .then((result) => {
        if (!cancelled) {
          setHtml(result);
          setIsLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error(String(e)));
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [type, content, options]);

  return { html, isLoading, error };
}

export default useNotationEngine;

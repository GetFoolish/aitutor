/**
 * Athena Context Provider
 *
 * Provides shared state and configuration for all Athena components.
 * Handles theming, dependencies, and notation engine management.
 */

import React, {
  createContext,
  useContext,
  useCallback,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react';
import type {
  AthenaAPIOptions,
  AthenaDependencies,
  AthenaEvent,
  NotationType,
  SerializedState,
} from './core/types';

// ============================================================================
// STATE TYPES
// ============================================================================

interface AthenaState {
  // Theme
  theme: 'light' | 'dark' | 'high-contrast';

  // Answer state per widget
  answers: Record<string, unknown>;

  // Loading states for notation engines
  loadingEngines: Set<NotationType>;
  loadedEngines: Set<NotationType>;

  // Hint visibility
  hintsVisible: number;

  // Review mode
  reviewMode: boolean;
  showSolutions: 'none' | 'all' | 'attempted';

  // Read-only mode
  readOnly: boolean;

  // Errors
  errors: Array<{ widgetId?: string; message: string; timestamp: number }>;
}

type AthenaAction =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' | 'high-contrast' }
  | { type: 'SET_ANSWER'; payload: { widgetId: string; value: unknown } }
  | { type: 'CLEAR_ANSWERS' }
  | { type: 'RESTORE_STATE'; payload: SerializedState }
  | { type: 'ENGINE_LOADING'; payload: NotationType }
  | { type: 'ENGINE_LOADED'; payload: NotationType }
  | { type: 'ENGINE_ERROR'; payload: { engine: NotationType; error: string } }
  | { type: 'SET_HINTS_VISIBLE'; payload: number }
  | { type: 'SET_REVIEW_MODE'; payload: boolean }
  | { type: 'SET_SHOW_SOLUTIONS'; payload: 'none' | 'all' | 'attempted' }
  | { type: 'SET_READ_ONLY'; payload: boolean }
  | { type: 'ADD_ERROR'; payload: { widgetId?: string; message: string } }
  | { type: 'CLEAR_ERRORS' };

// ============================================================================
// CONTEXT TYPES
// ============================================================================

interface AthenaContextValue {
  // State
  state: AthenaState;

  // State actions
  setTheme: (theme: 'light' | 'dark' | 'high-contrast') => void;
  setAnswer: (widgetId: string, value: unknown) => void;
  clearAnswers: () => void;
  restoreState: (state: SerializedState) => void;
  setHintsVisible: (count: number) => void;
  setReviewMode: (enabled: boolean) => void;
  setShowSolutions: (mode: 'none' | 'all' | 'attempted') => void;
  addError: (message: string, widgetId?: string) => void;
  clearErrors: () => void;

  // Notation engine management
  markEngineLoading: (engine: NotationType) => void;
  markEngineLoaded: (engine: NotationType) => void;
  isEngineLoaded: (engine: NotationType) => boolean;

  // Dependencies
  dependencies: AthenaDependencies;
  apiOptions: AthenaAPIOptions;

  // Event dispatch
  dispatchEvent: (event: AthenaEvent) => void;

  // Utility functions
  resolveStaticUrl: (url: string) => string;
  getLocale: () => string;
  getString: (key: string, fallback?: string) => string;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: AthenaState = {
  theme: 'light',
  answers: {},
  loadingEngines: new Set(),
  loadedEngines: new Set(),
  hintsVisible: 0,
  reviewMode: false,
  showSolutions: 'none',
  readOnly: false,
  errors: [],
};

// ============================================================================
// REDUCER
// ============================================================================

function athenaReducer(state: AthenaState, action: AthenaAction): AthenaState {
  switch (action.type) {
    case 'SET_THEME':
      return { ...state, theme: action.payload };

    case 'SET_ANSWER':
      return {
        ...state,
        answers: {
          ...state.answers,
          [action.payload.widgetId]: action.payload.value,
        },
      };

    case 'CLEAR_ANSWERS':
      return { ...state, answers: {} };

    case 'RESTORE_STATE':
      return {
        ...state,
        answers: action.payload.question || {},
      };

    case 'ENGINE_LOADING': {
      const newLoading = new Set(state.loadingEngines);
      newLoading.add(action.payload);
      return { ...state, loadingEngines: newLoading };
    }

    case 'ENGINE_LOADED': {
      const newLoading = new Set(state.loadingEngines);
      newLoading.delete(action.payload);
      const newLoaded = new Set(state.loadedEngines);
      newLoaded.add(action.payload);
      return { ...state, loadingEngines: newLoading, loadedEngines: newLoaded };
    }

    case 'ENGINE_ERROR': {
      const newLoading = new Set(state.loadingEngines);
      newLoading.delete(action.payload.engine);
      return {
        ...state,
        loadingEngines: newLoading,
        errors: [
          ...state.errors,
          {
            message: `Failed to load ${action.payload.engine} engine: ${action.payload.error}`,
            timestamp: Date.now(),
          },
        ],
      };
    }

    case 'SET_HINTS_VISIBLE':
      return { ...state, hintsVisible: action.payload };

    case 'SET_REVIEW_MODE':
      return { ...state, reviewMode: action.payload };

    case 'SET_SHOW_SOLUTIONS':
      return { ...state, showSolutions: action.payload };

    case 'SET_READ_ONLY':
      return { ...state, readOnly: action.payload };

    case 'ADD_ERROR':
      return {
        ...state,
        errors: [
          ...state.errors,
          {
            widgetId: action.payload.widgetId,
            message: action.payload.message,
            timestamp: Date.now(),
          },
        ],
      };

    case 'CLEAR_ERRORS':
      return { ...state, errors: [] };

    default:
      return state;
  }
}

// ============================================================================
// CONTEXT
// ============================================================================

const AthenaContext = createContext<AthenaContextValue | null>(null);

// ============================================================================
// PROVIDER
// ============================================================================

interface AthenaProviderProps {
  children: ReactNode;
  theme?: 'light' | 'dark' | 'high-contrast';
  dependencies?: AthenaDependencies;
  apiOptions?: AthenaAPIOptions;
  initialAnswers?: Record<string, unknown>;
  hintsVisible?: number;
  reviewMode?: boolean;
  showSolutions?: 'none' | 'all' | 'attempted';
  readOnly?: boolean;
  onEvent?: (event: AthenaEvent) => void;
}

export function AthenaProvider({
  children,
  theme = 'light',
  dependencies = {},
  apiOptions = {},
  initialAnswers = {},
  hintsVisible = 0,
  reviewMode = false,
  showSolutions = 'none',
  readOnly = false,
  onEvent,
}: AthenaProviderProps) {
  const [state, dispatch] = useReducer(athenaReducer, {
    ...initialState,
    theme,
    answers: initialAnswers,
    hintsVisible,
    reviewMode,
    showSolutions,
    readOnly,
  });

  // Memoized dependencies with defaults
  const resolvedDependencies = useMemo<AthenaDependencies>(
    () => ({
      staticUrl: dependencies.staticUrl || ((url) => url),
      locale: dependencies.locale || 'en',
      strings: dependencies.strings || {},
      onEvent: dependencies.onEvent || onEvent,
      ...dependencies,
    }),
    [dependencies, onEvent]
  );

  // Memoized API options with defaults
  const resolvedApiOptions = useMemo<AthenaAPIOptions>(
    () => ({
      isMobile: apiOptions.isMobile || false,
      readOnly: apiOptions.readOnly || readOnly,
      ...apiOptions,
    }),
    [apiOptions, readOnly]
  );

  // Actions
  const setTheme = useCallback(
    (newTheme: 'light' | 'dark' | 'high-contrast') => {
      dispatch({ type: 'SET_THEME', payload: newTheme });
    },
    []
  );

  const setAnswer = useCallback((widgetId: string, value: unknown) => {
    dispatch({ type: 'SET_ANSWER', payload: { widgetId, value } });
    // Dispatch answer-change event to notify parent component
    resolvedDependencies.onEvent?.({
      type: 'answer-change',
      timestamp: Date.now(),
      data: { widgetId, value },
    });
  }, [resolvedDependencies]);

  const clearAnswers = useCallback(() => {
    dispatch({ type: 'CLEAR_ANSWERS' });
  }, []);

  const restoreState = useCallback((serializedState: SerializedState) => {
    dispatch({ type: 'RESTORE_STATE', payload: serializedState });
  }, []);

  const setHintsVisible = useCallback((count: number) => {
    dispatch({ type: 'SET_HINTS_VISIBLE', payload: count });
  }, []);

  const setReviewMode = useCallback((enabled: boolean) => {
    dispatch({ type: 'SET_REVIEW_MODE', payload: enabled });
  }, []);

  const setShowSolutions = useCallback(
    (mode: 'none' | 'all' | 'attempted') => {
      dispatch({ type: 'SET_SHOW_SOLUTIONS', payload: mode });
    },
    []
  );

  const addError = useCallback((message: string, widgetId?: string) => {
    dispatch({ type: 'ADD_ERROR', payload: { message, widgetId } });
  }, []);

  const clearErrors = useCallback(() => {
    dispatch({ type: 'CLEAR_ERRORS' });
  }, []);

  // Engine management
  const markEngineLoading = useCallback((engine: NotationType) => {
    dispatch({ type: 'ENGINE_LOADING', payload: engine });
  }, []);

  const markEngineLoaded = useCallback((engine: NotationType) => {
    dispatch({ type: 'ENGINE_LOADED', payload: engine });
  }, []);

  const isEngineLoaded = useCallback(
    (engine: NotationType) => state.loadedEngines.has(engine),
    [state.loadedEngines]
  );

  // Event dispatch
  const dispatchEvent = useCallback(
    (event: AthenaEvent) => {
      resolvedDependencies.onEvent?.(event);
    },
    [resolvedDependencies]
  );

  // Utility functions
  const resolveStaticUrl = useCallback(
    (url: string) => {
      // Handle web+graphie:// URLs (Perseus format)
      if (url.startsWith('web+graphie://')) {
        const graphieId = url.replace('web+graphie://', '');
        return `https://cdn.kastatic.org/ka-perseus-graphie/${graphieId}.svg`;
      }
      return resolvedDependencies.staticUrl?.(url) || url;
    },
    [resolvedDependencies]
  );

  const getLocale = useCallback(
    () => resolvedDependencies.locale || 'en',
    [resolvedDependencies.locale]
  );

  const getString = useCallback(
    (key: string, fallback?: string) => {
      return resolvedDependencies.strings?.[key] || fallback || key;
    },
    [resolvedDependencies.strings]
  );

  // Context value
  const contextValue = useMemo<AthenaContextValue>(
    () => ({
      state,
      setTheme,
      setAnswer,
      clearAnswers,
      restoreState,
      setHintsVisible,
      setReviewMode,
      setShowSolutions,
      addError,
      clearErrors,
      markEngineLoading,
      markEngineLoaded,
      isEngineLoaded,
      dependencies: resolvedDependencies,
      apiOptions: resolvedApiOptions,
      dispatchEvent,
      resolveStaticUrl,
      getLocale,
      getString,
    }),
    [
      state,
      setTheme,
      setAnswer,
      clearAnswers,
      restoreState,
      setHintsVisible,
      setReviewMode,
      setShowSolutions,
      addError,
      clearErrors,
      markEngineLoading,
      markEngineLoaded,
      isEngineLoaded,
      resolvedDependencies,
      resolvedApiOptions,
      dispatchEvent,
      resolveStaticUrl,
      getLocale,
      getString,
    ]
  );

  return (
    <AthenaContext.Provider value={contextValue}>
      {children}
    </AthenaContext.Provider>
  );
}

// ============================================================================
// HOOKS
// ============================================================================

export function useAthena(): AthenaContextValue {
  const context = useContext(AthenaContext);
  if (!context) {
    throw new Error('useAthena must be used within an AthenaProvider');
  }
  return context;
}

export function useAthenaTheme() {
  const { state, setTheme } = useAthena();
  return { theme: state.theme, setTheme };
}

export function useAthenaAnswers() {
  const { state, setAnswer, clearAnswers, restoreState } = useAthena();
  return {
    answers: state.answers,
    setAnswer,
    clearAnswers,
    restoreState,
  };
}

export function useAthenaHints() {
  const { state, setHintsVisible } = useAthena();
  return {
    hintsVisible: state.hintsVisible,
    setHintsVisible,
    requestNextHint: () => setHintsVisible(state.hintsVisible + 1),
  };
}

export function useAthenaReviewMode() {
  const { state, setReviewMode, setShowSolutions } = useAthena();
  return {
    reviewMode: state.reviewMode,
    showSolutions: state.showSolutions,
    setReviewMode,
    setShowSolutions,
  };
}

export function useAthenaErrors() {
  const { state, addError, clearErrors } = useAthena();
  return {
    errors: state.errors,
    addError,
    clearErrors,
    hasErrors: state.errors.length > 0,
  };
}

export function useAthenaEngine(engineType: NotationType) {
  const { state, markEngineLoading, markEngineLoaded, isEngineLoaded } = useAthena();
  return {
    isLoading: state.loadingEngines.has(engineType),
    isLoaded: isEngineLoaded(engineType),
    markLoading: () => markEngineLoading(engineType),
    markLoaded: () => markEngineLoaded(engineType),
  };
}

export default AthenaContext;

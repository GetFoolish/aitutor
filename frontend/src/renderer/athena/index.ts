/**
 * Athena Content Renderer
 *
 * A modern, performant content renderer for educational content.
 * Supports multiple subjects including Math, Chemistry, Music, History, and more.
 *
 * @packageDocumentation
 */

// ============================================================================
// MAIN COMPONENTS
// ============================================================================

export { AthenaRenderer, default } from './AthenaRenderer';
export { AthenaProvider, useAthena } from './AthenaContext';

// ============================================================================
// HOOKS
// ============================================================================

export {
  useAthenaTheme,
  useAthenaAnswers,
  useAthenaHints,
  useAthenaReviewMode,
  useAthenaErrors,
  useAthenaEngine,
} from './AthenaContext';

// ============================================================================
// TYPES
// ============================================================================

export type {
  // Notation types
  NotationType,
  NotationEngine,
  NotationRenderOptions,

  // Widget types
  WidgetType,
  AthenaWidget,
  BaseWidgetOptions,

  // Content types
  AthenaImage,
  AthenaHint,
  AthenaQuestion,
  AthenaAnswerArea,
  AthenaItem,

  // Perseus compatibility
  PerseusItem,
  PerseusWidget,
  PerseusQuestion,
  PerseusHint,
  PerseusAnswerArea,

  // Scoring types
  ScoreResult,
  WidgetScoreDetail,
  ScoringResult,

  // State types
  WidgetUserInput,
  SerializedState,

  // Renderer types
  AthenaRendererRef,
  AthenaRendererProps,
  AthenaAPIOptions,
  AthenaDependencies,

  // Event types
  AthenaEventType,
  AthenaEvent,

  // Editor types
  AthenaEditorProps,
  WidgetConfiguratorProps,

  // Widget option types
  NumericInputOptions,
  RadioOptions,
  ExpressionOptions,
  ImageOptions,
  DropdownOptions,
  InteractiveGraphOptions,
  PassageOptions,
  TableOptions,
  CategorizerOptions,
  SorterOptions,
  MatcherOptions,
  MoleculeOptions,
  VideoOptions,
  CodeOptions,
  WidgetOptionsMap,
} from './core/types';

// ============================================================================
// NOTATION ENGINES
// ============================================================================

export { NotationEngineManager } from './notation/NotationEngineManager';
export {
  useNotationEngine,
  useNotationDetection,
  useNotationRender,
} from './notation/useNotationEngine';

// ============================================================================
// CONTENT PARSING
// ============================================================================

export { ContentParser } from './core/ContentParser';
export type { ParsedSegment, ParseResult } from './core/ContentParser';

export { MarkdownProcessor } from './core/MarkdownProcessor';
export type { MarkdownOptions, ProcessedMarkdown } from './core/MarkdownProcessor';

// ============================================================================
// MIGRATION UTILITIES
// ============================================================================

export { PerseusAdapter } from './migration/PerseusAdapter';
export type {
  MigrationResult,
  MigrationError,
  MigrationWarning,
  PerseusAdapterOptions,
} from './migration/PerseusAdapter';

export { WidgetMigrator } from './migration/WidgetMigrator';
export type { WidgetMigratorFn } from './migration/WidgetMigrator';

export { ImageURLMigrator } from './migration/ImageURLMigrator';
export type { ImageMigrationOptions } from './migration/ImageURLMigrator';

export { BatchMigrationScript, runBatchMigration } from './migration/BatchMigrationScript';
export type { BatchMigrationOptions, BatchMigrationResult } from './migration/BatchMigrationScript';

export {
  migratePerseus,
  migrateBatch,
  migrateImageUrl,
  validateMigration,
  printMigrationReport,
} from './migration/PerseusMigrator';
export type {
  MigrationResult as PerseusMigrationResult,
  MigrationStats,
  MigrationOptions,
  BatchMigrationResult as PerseusBatchMigrationResult,
} from './migration/PerseusMigrator';

// ============================================================================
// WIDGETS SYSTEM
// ============================================================================

export { WidgetRegistry, registerDefaultWidgets } from './widgets/WidgetRegistry';
export type { WidgetComponent, WidgetProps, WidgetDefinition } from './widgets/WidgetRegistry';
export { WidgetFactory, WidgetList, useWidget } from './widgets/WidgetFactory';
export { BaseWidgetWrapper, useWidgetState, useWidgetId, createWidget } from './widgets/base/BaseWidget';

// Widget Components - Input
export { NumericInputWidget } from './widgets/input/NumericInputWidget';
export { RadioWidget } from './widgets/input/RadioWidget';
export { ExpressionWidget } from './widgets/input/ExpressionWidget';
export { DropdownWidget } from './widgets/input/DropdownWidget';
export { FreeResponseWidget } from './widgets/input/FreeResponseWidget';

// Widget Components - Display
export { ImageWidget } from './widgets/display/ImageWidget';
export { PassageWidget } from './widgets/display/PassageWidget';
export { VideoWidget } from './widgets/display/VideoWidget';
export { DefinitionWidget } from './widgets/display/DefinitionWidget';
export { ExplanationWidget } from './widgets/display/ExplanationWidget';
export { PassageRefWidget } from './widgets/display/PassageRefWidget';

// Widget Components - Interactive
export { InteractiveGraphWidget } from './widgets/interactive/InteractiveGraphWidget';
export { TableWidget } from './widgets/interactive/TableWidget';
export { NumberLineWidget } from './widgets/interactive/NumberLineWidget';
export { GrapherWidget } from './widgets/interactive/GrapherWidget';
export { PlotterWidget } from './widgets/interactive/PlotterWidget';

// Widget Components - Assessment
export { SorterWidget } from './widgets/assessment/SorterWidget';
export { MatcherWidget } from './widgets/assessment/MatcherWidget';
export { CategorizerWidget } from './widgets/assessment/CategorizerWidget';

// Widget Components - Specialized
export { LabelImageWidget } from './widgets/specialized/LabelImageWidget';

// ============================================================================
// HINTS SYSTEM
// ============================================================================

export { HintsRenderer, ProgressiveHints, useHints } from './hints/HintsRenderer';
export { HintsStateManager } from './hints/HintsStateManager';
export type { HintState, HintsState, HintsStateManagerOptions } from './hints/HintsStateManager';

// ============================================================================
// MATH INPUT SYSTEM
// ============================================================================

export { MathKeypad, FloatingMathKeypad, useMathKeypad } from './math-input/MathKeypad';
export { MathQuillWrapper, StaticMath } from './math-input/MathQuillWrapper';
export { ExpressionInput, ExpressionDisplay } from './math-input/ExpressionInput';
export {
  BASIC_SET,
  ALGEBRA_SET,
  TRIG_SET,
  CALCULUS_SET,
  CHEMISTRY_SET,
  getButtonSet,
  combineButtonSets,
} from './math-input/ButtonSets';
export type { MathButton, ButtonSet, ButtonSetId } from './math-input/ButtonSets';

// ============================================================================
// SCORING SYSTEM
// ============================================================================

export { ScoringEngine } from './scoring/ScoringEngine';
export type { Validator, ValidatorResult, ScoringEngineOptions } from './scoring/ScoringEngine';

export { NumericValidator } from './scoring/validators/NumericValidator';
export { ExpressionValidator } from './scoring/validators/ExpressionValidator';
export { RadioValidator } from './scoring/validators/RadioValidator';
export { GraphValidator } from './scoring/validators/GraphValidator';
export { OrderValidator } from './scoring/validators/OrderValidator';
export { RubricValidator } from './scoring/validators/RubricValidator';

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

export { AnswerStateManager } from './state/AnswerStateManager';
export type { AnswerState, AnswerStateManagerOptions } from './state/AnswerStateManager';

export { useAnswerState, useWidgetAnswer } from './state/useAnswerState';
export type { UseAnswerStateOptions, UseAnswerStateResult } from './state/useAnswerState';

// ============================================================================
// ACCESSIBILITY
// ============================================================================

export {
  getWidgetAriaLabel,
  getWidgetStateDescription,
  getHintButtonAriaLabel,
  getScoreAriaLabel,
  getStateChangeAnnouncement,
  formatNumberForScreenReader,
  formatMathForScreenReader,
  getKeyboardShortcutDescription,
} from './accessibility/AriaLabels';

export {
  useKeyboardNavigation,
  FocusTrap,
  SkipLink,
  useRovingTabIndex,
} from './accessibility/KeyboardNavigation';
export type { KeyboardNavigationOptions, FocusTrapProps } from './accessibility/KeyboardNavigation';

export {
  ScreenReaderAnnouncerProvider,
  useScreenReaderAnnouncer,
  ScreenReaderAnnouncer,
  VisuallyHidden,
  useAnnounceOnChange,
} from './accessibility/ScreenReaderAnnouncer';
export type {
  Announcement,
  AnnouncementPoliteness,
  ScreenReaderAnnouncerContextValue,
} from './accessibility/ScreenReaderAnnouncer';

// ============================================================================
// EDITOR SYSTEM
// ============================================================================

export {
  EditorFrame,
  useEditorContext,
  EditorContext,
  ContentEditor,
  PreviewPane,
  JSONPane,
  WidgetInserter,
  HintEditor,
  BaseConfigurator,
  ConfiguratorField,
  ConfiguratorSection,
  NumericInputConfigurator,
  RadioConfigurator,
  ExpressionConfigurator,
  getWidgetConfigurator,
} from './editor';
export type {
  EditorFrameProps,
  EditorFrameRef,
  EditorTab,
  EditorContextValue,
  ContentEditorProps,
  ContentEditorRef,
  PreviewPaneProps,
  JSONPaneProps,
  WidgetInserterProps,
  WidgetTemplate,
  HintEditorProps,
  ConfiguratorProps,
  ConfiguratorFieldProps,
} from './editor';

// ============================================================================
// PERFORMANCE
// ============================================================================

export {
  createLazyLoader,
  loadModule,
  preloadModules,
  createLazyComponent,
  ModuleRegistry,
  moduleRegistry,
  LRUCache,
  RenderCache,
  memoize,
  memoizeAsync,
  renderCache,
  VirtualScroller,
  useVirtualScroller,
} from './performance';
export type {
  LazyModule,
  LazyLoaderOptions,
  CacheEntry,
  CacheOptions,
  VirtualScrollerProps,
  VirtualScrollerRef,
} from './performance';

// ============================================================================
// TESTING
// ============================================================================

export {
  runBenchmark,
  createBenchmarkSuite,
  runBenchmarkSuite,
  formatBenchmarkResults,
  compareBenchmarks,
  MemoryTracker,
  RenderProfiler,
  memoryTracker,
  renderProfiler,
  PERFORMANCE_TARGETS,
  runAccessibilityAudit,
  formatAuditReport,
  WCAG_CRITERIA,
  ATHENA_CHECKS,
} from './testing';
export type {
  BenchmarkResult,
  BenchmarkOptions,
  BenchmarkSuite,
  AccessibilityIssue,
  AuditResult,
  AuditOptions,
} from './testing';

// ============================================================================
// DEMO
// ============================================================================

export { AthenaDemo } from './AthenaDemo';
export type { AthenaDemoProps } from './AthenaDemo';

export { ComparisonDemo } from './demo/ComparisonDemo';

// Performance Benchmark utilities
export {
  measureRenderTime,
  measureRenderTimeAsync,
  getBundleSizeMetrics,
  getPerformanceComparison,
  performanceMonitor,
  useRenderTime,
  PerformanceMonitor,
} from './performance/PerformanceBenchmark';
export type { BundleSizeMetrics } from './performance/PerformanceBenchmark';

// ============================================================================
// INTEGRATION (Perseus replacement)
// ============================================================================

export {
  AthenaQuestionRenderer,
  useAthenaQuestion,
  migratePerseusQuestions,
} from './integration';
export type { AthenaQuestionRendererProps } from './integration';

// ============================================================================
// VERSION
// ============================================================================

export const ATHENA_VERSION = '1.0.0';

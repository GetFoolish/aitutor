/**
 * Athena Content Renderer - Core Type Definitions
 *
 * Supports Perseus JSON v2.0 format for backward compatibility
 * while providing a modern, extensible type system.
 */

// ============================================================================
// NOTATION TYPES
// ============================================================================

export type NotationType =
  | 'math'
  | 'chemistry'
  | 'music'
  | 'diagram'
  | 'code'
  | 'physics'
  | 'economics'
  | 'geography';

export interface NotationEngine {
  type: NotationType;
  render(content: string, container: HTMLElement, options?: NotationRenderOptions): Promise<void>;
  renderToString(content: string, options?: NotationRenderOptions): Promise<string>;
  isLoaded(): boolean;
  preload(): Promise<void>;
}

export interface NotationRenderOptions {
  displayMode?: boolean;
  theme?: 'light' | 'dark' | 'high-contrast';
  fontSize?: number;
  language?: string;
}

// ============================================================================
// WIDGET TYPES
// ============================================================================

export type WidgetType =
  // Input widgets
  | 'numeric-input'
  | 'input-number'
  | 'radio'
  | 'expression'
  | 'dropdown'
  | 'free-response'
  // Display widgets
  | 'image'
  | 'passage'
  | 'passage-ref'
  | 'passage-ref-target'
  | 'video'
  | 'definition'
  | 'explanation'
  // Interactive widgets
  | 'interactive-graph'
  | 'grapher'
  | 'plotter'
  | 'table'
  | 'number-line'
  | 'measurer'
  // Assessment widgets
  | 'categorizer'
  | 'sorter'
  | 'matcher'
  | 'orderer'
  // Specialized widgets
  | 'molecule'
  | 'reaction-diagram'
  | 'music-notation'
  | 'cs-program'
  | 'iframe'
  | 'timeline'
  | 'map'
  | 'label-image'
  // Group widgets
  | 'group'
  | 'graded-group'
  | 'graded-group-set';

export interface BaseWidgetOptions {
  static?: boolean;
}

export interface AthenaWidget<TOptions = unknown> {
  type: WidgetType;
  alignment: 'default' | 'block' | 'inline' | 'full-width';
  static: boolean;
  graded: boolean;
  options: TOptions;
  version: { major: number; minor: number };
}

// ============================================================================
// CONTENT TYPES
// ============================================================================

export interface AthenaImage {
  url: string;
  width: number;
  height: number;
  alt?: string;
  caption?: string;
}

export interface AthenaHint {
  content: string;
  widgets: Record<string, AthenaWidget>;
  images: Record<string, AthenaImage>;
  replace?: boolean;
}

export interface AthenaQuestion {
  content: string;
  widgets: Record<string, AthenaWidget>;
  images: Record<string, AthenaImage>;
}

export interface AthenaAnswerArea {
  type?: string;
  options?: Record<string, unknown>;
  widgets?: Record<string, AthenaWidget>;
  calculator?: boolean;
  periodicTable?: boolean;
  zTable?: boolean;
  tTable?: boolean;
  chi2Table?: boolean;
}

export interface AthenaItem {
  question: AthenaQuestion;
  hints: AthenaHint[];
  answerArea: AthenaAnswerArea;
  itemDataVersion: { major: number; minor: number };
}

// ============================================================================
// PERSEUS COMPATIBILITY TYPES (for backward compatibility)
// ============================================================================

export interface PerseusWidget {
  type: string;
  alignment: string;
  static: boolean;
  graded: boolean;
  options: Record<string, unknown>;
  version: { major: number; minor: number };
}

export interface PerseusQuestion {
  content: string;
  widgets: Record<string, PerseusWidget>;
  images: Record<string, AthenaImage>;
}

export interface PerseusHint {
  content: string;
  widgets: Record<string, PerseusWidget>;
  images: Record<string, AthenaImage>;
  replace?: boolean;
}

export interface PerseusAnswerArea {
  type?: string;
  options?: Record<string, unknown>;
  calculator?: boolean;
  periodicTable?: boolean;
  zTable?: boolean;
  tTable?: boolean;
  chi2Table?: boolean;
}

export interface PerseusItem {
  question: PerseusQuestion;
  hints?: PerseusHint[];
  answerArea?: PerseusAnswerArea;
  itemDataVersion?: { major: number; minor: number };
}

// ============================================================================
// SCORING TYPES
// ============================================================================

export interface ScoreResult {
  correct: boolean;
  empty: boolean;
  message?: string;
  earned: number;
  total: number;
  guess?: unknown;
}

export interface WidgetScoreDetail {
  widgetId: string;
  widgetType: WidgetType;
  correct: boolean;
  earned: number;
  total: number;
  message?: string;
}

export interface ScoringResult {
  correct: boolean;
  empty: boolean;
  message?: string;
  earned: number;
  total: number;
  details: WidgetScoreDetail[];
}

// ============================================================================
// ANSWER STATE TYPES
// ============================================================================

export interface WidgetUserInput {
  widgetId: string;
  widgetType: WidgetType;
  value: unknown;
  timestamp: number;
}

export interface SerializedState {
  question: Record<string, unknown>;
  hints?: Record<string, unknown>[];
}

// ============================================================================
// RENDERER PROPS & CONFIGURATION
// ============================================================================

export interface AthenaRendererRef {
  getUserInput(): Record<string, unknown>;
  getUserInputLegacy(): unknown[];
  getSerializedState(): SerializedState;
  restoreState(state: SerializedState): void;
  focus(): void;
  blur(): void;
  score(): ScoringResult;
}

export interface AthenaRendererProps {
  // Content
  item: PerseusItem | AthenaItem;
  problemNum?: number;

  // Hints
  hintsVisible?: number;

  // Review mode
  reviewMode?: boolean;
  showSolutions?: 'none' | 'all' | 'attempted';

  // State management
  initialState?: SerializedState;
  onStateChange?: (state: SerializedState) => void;
  onAnswerChange?: (widgetId: string, value: unknown) => void;

  // Interactivity
  readOnly?: boolean;

  // Theming
  theme?: 'light' | 'dark' | 'high-contrast';

  // Accessibility
  ariaLabel?: string;

  // API options (for customization)
  apiOptions?: AthenaAPIOptions;

  // Dependencies (for advanced customization)
  dependencies?: AthenaDependencies;
}

export interface AthenaAPIOptions {
  // Render options
  isMobile?: boolean;
  satStyling?: boolean;

  // Interaction options
  readOnly?: boolean;
  answerableCallback?: (answerable: boolean) => void;

  // Custom renderers
  customRenderers?: Record<string, React.ComponentType<unknown>>;

  // Feature flags
  flags?: Record<string, boolean>;
}

export interface AthenaDependencies {
  // Static URL resolver
  staticUrl?: (url: string) => string;

  // Image loader
  imageLoader?: (url: string) => Promise<HTMLImageElement>;

  // Analytics/logging
  onEvent?: (event: AthenaEvent) => void;

  // i18n
  locale?: string;
  strings?: Record<string, string>;
}

// ============================================================================
// EVENT TYPES
// ============================================================================

export type AthenaEventType =
  | 'render-start'
  | 'render-complete'
  | 'widget-focus'
  | 'widget-blur'
  | 'answer-change'
  | 'hint-request'
  | 'score-complete'
  | 'error';

export interface AthenaEvent {
  type: AthenaEventType;
  timestamp: number;
  data?: Record<string, unknown>;
}

// ============================================================================
// EDITOR TYPES
// ============================================================================

export interface AthenaEditorProps {
  // Initial content
  item?: AthenaItem;

  // Change handlers
  onChange?: (item: AthenaItem) => void;
  onSave?: (item: AthenaItem) => void;

  // Configuration
  allowedWidgets?: WidgetType[];
  showPreview?: boolean;
  showJSON?: boolean;

  // Theming
  theme?: 'light' | 'dark';
}

export interface WidgetConfiguratorProps<TOptions = unknown> {
  widgetId: string;
  options: TOptions;
  onChange: (options: TOptions) => void;
  onRemove: () => void;
}

// ============================================================================
// SPECIFIC WIDGET OPTION TYPES
// ============================================================================

export interface NumericInputOptions extends BaseWidgetOptions {
  answers: Array<{
    value: number;
    status: 'correct' | 'wrong';
    message?: string;
    strict?: boolean;
    maxError?: number;
    answerType?: string;
  }>;
  size: 'normal' | 'small';
  coefficient?: boolean;
  labelText?: string;
  rightAlign?: boolean;
  simplify?: string;
}

export interface RadioOptions extends BaseWidgetOptions {
  choices: Array<{
    content: string;
    correct?: boolean;
    clue?: string;
    isNoneOfTheAbove?: boolean;
  }>;
  randomize?: boolean;
  multipleSelect?: boolean;
  displayCount?: number;
  deselectEnabled?: boolean;
  noneOfTheAbove?: boolean;
}

export interface ExpressionOptions extends BaseWidgetOptions {
  answerForms: Array<{
    value: string;
    form: boolean;
    simplify: boolean;
    considered?: 'correct' | 'wrong' | 'ungraded';
  }>;
  times?: boolean;
  buttonSets: Array<'basic' | 'algebra' | 'trig' | 'calculus' | 'chemistry'>;
  functions?: string[];
}

export interface ImageOptions extends BaseWidgetOptions {
  backgroundImage: {
    url: string;
    width: number;
    height: number;
  };
  labels?: Array<{
    content: string;
    coordinates: [number, number];
    alignment: string;
  }>;
  alt: string;
  caption?: string;
}

export interface DropdownOptions extends BaseWidgetOptions {
  placeholder: string;
  choices: Array<{
    content: string;
    correct: boolean;
  }>;
}

export interface InteractiveGraphOptions extends BaseWidgetOptions {
  graph: {
    type: 'linear' | 'quadratic' | 'polynomial' | 'exponential' | 'logarithmic' | 'trigonometric' | 'circle' | 'polygon' | 'point' | 'segment' | 'ray' | 'linear-system' | 'none';
    rulerLabel: string;
    rulerTicks: number;
    numPoints?: number;
    backgroundImage?: {
      url: string;
      width: number;
      height: number;
    };
    coords?: unknown[];
  };
  backgroundImage?: {
    url: string;
    width: number;
    height: number;
  };
  range: [[number, number], [number, number]];
  step: [number, number];
  gridStep: [number, number];
  snapStep: [number, number];
  markings: 'graph' | 'grid' | 'none';
  showProtractor?: boolean;
  showRuler?: boolean;
  showCoordinates?: boolean;
  correct: unknown;
  title?: string;
}

export interface PassageOptions extends BaseWidgetOptions {
  passageTitle: string;
  passageText: string;
  footnotes?: string;
  showLineNumbers?: boolean;
}

export interface TableOptions extends BaseWidgetOptions {
  headers: string[];
  rows: number;
  columns: number;
  answers?: string[][];
  data?: string[][];
  editableColumns?: number[];
  title?: string;
  caption?: string;
}

export interface CategorizerCategory {
  id: string;
  name: string;
}

export interface CategorizerOptions extends BaseWidgetOptions {
  items: string[];
  categories: CategorizerCategory[];
  values?: number[];
  correct?: Record<string, string>;
  randomizeItems?: boolean;
  title?: string;
}

export interface SorterOptions extends BaseWidgetOptions {
  correct?: string[];
  choices?: string[];
  layout?: 'horizontal' | 'vertical';
  padding?: boolean;
  title?: string;
  // Orderer widget format (alternative to correct/choices)
  correctOptions?: Array<string | { content: string; text?: string }>;
  otherOptions?: Array<string | { content: string; text?: string }>;
}

export interface MatcherOptions extends BaseWidgetOptions {
  left: string[];
  right: string[];
  labels: [string, string];
  leftLabel?: string;
  rightLabel?: string;
  orderMatters?: boolean;
  padding?: boolean;
  title?: string;
  correctPairs?: Array<{ left: number; right: number }>;
}

export interface MoleculeOptions extends BaseWidgetOptions {
  smiles: string;
  rotationAngle?: number;
}

export interface VideoOptions extends BaseWidgetOptions {
  location: string;
  aspectRatio?: string;
  caption?: string;
}

export interface CodeOptions extends BaseWidgetOptions {
  code: string;
  language: string;
  showLineNumbers?: boolean;
  highlightLines?: number[];
}

// Type helper to get options type for a widget
export type WidgetOptionsMap = {
  'numeric-input': NumericInputOptions;
  'input-number': NumericInputOptions;
  'radio': RadioOptions;
  'expression': ExpressionOptions;
  'image': ImageOptions;
  'dropdown': DropdownOptions;
  'interactive-graph': InteractiveGraphOptions;
  'passage': PassageOptions;
  'table': TableOptions;
  'categorizer': CategorizerOptions;
  'sorter': SorterOptions;
  'matcher': MatcherOptions;
  'molecule': MoleculeOptions;
  'video': VideoOptions;
  'cs-program': CodeOptions;
};

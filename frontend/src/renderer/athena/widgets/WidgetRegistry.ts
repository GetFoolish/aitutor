/**
 * Widget Registry
 *
 * Maps ALL 34 Khan Academy widget types to their React components.
 * Supports lazy loading and custom widget registration.
 */

import React from 'react';
import type { WidgetType, AthenaWidget } from '../core/types';

export interface WidgetComponent<T = unknown> {
  (props: WidgetProps<T>): React.ReactElement | null;
}

export interface WidgetProps<T = unknown> {
  /** Unique widget ID */
  widgetId: string;
  /** Widget configuration */
  widget: AthenaWidget<T>;
  /** Current user answer */
  value?: unknown;
  /** Callback when answer changes */
  onChange?: (value: unknown) => void;
  /** Whether the widget is read-only */
  readOnly?: boolean;
  /** Whether the widget is disabled */
  disabled?: boolean;
  /** Whether in review mode */
  reviewMode?: boolean;
  /** Theme */
  theme?: 'light' | 'dark' | 'high-contrast';
  /** Problem number for ARIA */
  problemNum?: number;
  /** API options */
  apiOptions?: Record<string, unknown>;
  /** Dependencies */
  dependencies?: Record<string, unknown>;
}

export interface WidgetDefinition {
  /** Widget type */
  type: WidgetType | string;
  /** Display name */
  displayName: string;
  /** React component (sync or lazy) */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: WidgetComponent<any> | React.LazyExoticComponent<WidgetComponent<any>>;
  /** Whether this widget is gradable */
  gradable: boolean;
  /** Whether this widget is static (display only) */
  static: boolean;
  /** Default options */
  defaultOptions?: Record<string, unknown>;
  /** Supported versions */
  supportedVersions?: { major: number; minor: number }[];
}

/**
 * Registry for widget types and their components
 */
class WidgetRegistryClass {
  private widgets: Map<string, WidgetDefinition> = new Map();
  private aliases: Map<string, string> = new Map();

  /**
   * Register a widget
   */
  register(definition: WidgetDefinition): void {
    this.widgets.set(definition.type, definition);
  }

  /**
   * Register an alias for a widget type
   */
  registerAlias(alias: string, targetType: string): void {
    this.aliases.set(alias, targetType);
  }

  /**
   * Get widget definition
   */
  get(type: string): WidgetDefinition | undefined {
    // Check for alias
    const resolvedType = this.aliases.get(type) || type;
    return this.widgets.get(resolvedType);
  }

  /**
   * Get widget component
   */
  getComponent(type: string): WidgetComponent | React.LazyExoticComponent<WidgetComponent> | undefined {
    return this.get(type)?.component;
  }

  /**
   * Check if widget type is registered
   */
  has(type: string): boolean {
    const resolvedType = this.aliases.get(type) || type;
    return this.widgets.has(resolvedType);
  }

  /**
   * Check if widget type is gradable
   */
  isGradable(type: string): boolean {
    return this.get(type)?.gradable ?? false;
  }

  /**
   * Check if widget type is static
   */
  isStatic(type: string): boolean {
    return this.get(type)?.static ?? false;
  }

  /**
   * Get all registered widget types
   */
  getTypes(): string[] {
    return Array.from(this.widgets.keys());
  }

  /**
   * Get all gradable widget types
   */
  getGradableTypes(): string[] {
    return Array.from(this.widgets.entries())
      .filter(([_, def]) => def.gradable)
      .map(([type]) => type);
  }

  /**
   * Get default options for a widget type
   */
  getDefaultOptions(type: string): Record<string, unknown> {
    return this.get(type)?.defaultOptions || {};
  }

  /**
   * Unregister a widget
   */
  unregister(type: string): boolean {
    return this.widgets.delete(type);
  }

  /**
   * Clear all registrations
   */
  clear(): void {
    this.widgets.clear();
    this.aliases.clear();
  }
}

// Singleton instance
export const WidgetRegistry = new WidgetRegistryClass();

/**
 * Register ALL 34 Khan Academy widget types
 */
export function registerDefaultWidgets(): void {
  // ============================================================================
  // INPUT WIDGETS (6 types) - Gradable
  // ============================================================================

  // 1. numeric-input
  WidgetRegistry.register({
    type: 'numeric-input',
    displayName: 'Numeric Input',
    component: React.lazy(() => import('./input/NumericInputWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      answers: [{ value: 0, status: 'correct' }],
      size: 'normal',
    },
  });

  // 2. input-number (alias)
  WidgetRegistry.registerAlias('input-number', 'numeric-input');

  // 3. radio
  WidgetRegistry.register({
    type: 'radio',
    displayName: 'Multiple Choice',
    component: React.lazy(() => import('./input/RadioWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      choices: [],
      randomize: false,
      multipleSelect: false,
    },
  });

  // 4. expression
  WidgetRegistry.register({
    type: 'expression',
    displayName: 'Expression',
    component: React.lazy(() => import('./input/ExpressionWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      answerForms: [],
      buttonSets: ['basic'],
    },
  });

  // 5. dropdown
  WidgetRegistry.register({
    type: 'dropdown',
    displayName: 'Dropdown',
    component: React.lazy(() => import('./input/DropdownWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      choices: [],
      placeholder: 'Select an answer',
    },
  });

  // 6. free-response
  WidgetRegistry.register({
    type: 'free-response',
    displayName: 'Free Response',
    component: React.lazy(() => import('./input/FreeResponseWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      placeholder: 'Type your response...',
      minLength: 0,
      maxLength: 1000,
    },
  });

  // ============================================================================
  // DISPLAY WIDGETS (7 types) - Static, non-gradable
  // ============================================================================

  // 7. image
  WidgetRegistry.register({
    type: 'image',
    displayName: 'Image',
    component: React.lazy(() => import('./display/ImageWidget')),
    gradable: false,
    static: true,
  });

  // 8. passage
  WidgetRegistry.register({
    type: 'passage',
    displayName: 'Passage',
    component: React.lazy(() => import('./display/PassageWidget')),
    gradable: false,
    static: true,
  });

  // 9. passage-ref
  WidgetRegistry.register({
    type: 'passage-ref',
    displayName: 'Passage Reference',
    component: React.lazy(() => import('./display/PassageRefWidget')),
    gradable: false,
    static: true,
  });

  // 10. passage-ref-target
  WidgetRegistry.register({
    type: 'passage-ref-target',
    displayName: 'Passage Reference Target',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.PassageRefTargetWidget }))),
    gradable: false,
    static: true,
  });

  // 11. video
  WidgetRegistry.register({
    type: 'video',
    displayName: 'Video',
    component: React.lazy(() => import('./display/VideoWidget')),
    gradable: false,
    static: true,
    defaultOptions: {
      location: '',
      aspectRatio: '16:9',
    },
  });

  // 12. definition
  WidgetRegistry.register({
    type: 'definition',
    displayName: 'Definition',
    component: React.lazy(() => import('./display/DefinitionWidget')),
    gradable: false,
    static: true,
  });

  // 13. explanation
  WidgetRegistry.register({
    type: 'explanation',
    displayName: 'Explanation',
    component: React.lazy(() => import('./display/ExplanationWidget')),
    gradable: false,
    static: true,
  });

  // ============================================================================
  // INTERACTIVE WIDGETS (6 types)
  // ============================================================================

  // 14. interactive-graph
  WidgetRegistry.register({
    type: 'interactive-graph',
    displayName: 'Interactive Graph',
    component: React.lazy(() => import('./interactive/InteractiveGraphWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      range: [[-10, 10], [-10, 10]],
      step: [1, 1],
      graph: { type: 'point', numPoints: 1 },
    },
  });

  // 15. grapher
  WidgetRegistry.register({
    type: 'grapher',
    displayName: 'Function Grapher',
    component: React.lazy(() => import('./interactive/GrapherWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      range: [[-5, 5], [-5, 5]],
      graph: { type: 'linear' },
    },
  });

  // 16. plotter
  WidgetRegistry.register({
    type: 'plotter',
    displayName: 'Scatter Plotter',
    component: React.lazy(() => import('./interactive/PlotterWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      range: [[0, 5], [0, 8]],
      starting: [],
      correct: [],
    },
  });

  // 17. table
  WidgetRegistry.register({
    type: 'table',
    displayName: 'Table',
    component: React.lazy(() => import('./interactive/TableWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      rows: 3,
      columns: 3,
      headers: [],
      editableColumns: [],
    },
  });

  // 17b. matrix - grid of input fields for matrix values
  WidgetRegistry.register({
    type: 'matrix',
    displayName: 'Matrix',
    component: React.lazy(() => import('./specialized/MatrixWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      matrixBoardSize: [3, 3],
      answers: [],
      prefix: '',
      suffix: '',
    },
  });

  // 18. number-line
  WidgetRegistry.register({
    type: 'number-line',
    displayName: 'Number Line',
    component: React.lazy(() => import('./interactive/NumberLineWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      range: [-5, 5],
      tickStep: 1,
      snapDivisions: 1,
      labelTicks: true,
    },
  });

  // 19. measurer
  WidgetRegistry.register({
    type: 'measurer',
    displayName: 'Measurer',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.MeasurerWidget }))),
    gradable: true,
    static: false,
  });

  // ============================================================================
  // ASSESSMENT WIDGETS (4 types) - Drag-drop, matching, sorting
  // ============================================================================

  // 20. categorizer
  WidgetRegistry.register({
    type: 'categorizer',
    displayName: 'Categorizer',
    component: React.lazy(() => import('./assessment/CategorizerWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      categories: [],
      items: [],
      correct: {},
    },
  });

  // 21. sorter
  WidgetRegistry.register({
    type: 'sorter',
    displayName: 'Sorter',
    component: React.lazy(() => import('./assessment/SorterWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      choices: [],
      correct: [],
    },
  });

  // 22. matcher
  WidgetRegistry.register({
    type: 'matcher',
    displayName: 'Matcher',
    component: React.lazy(() => import('./assessment/MatcherWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      left: [],
      right: [],
      correctPairs: [],
    },
  });

  // 23. orderer
  WidgetRegistry.register({
    type: 'orderer',
    displayName: 'Orderer',
    component: React.lazy(() => import('./assessment/OrdererWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      options: [],
      correctOptions: [],
      otherOptions: [],
      layout: 'horizontal',
    },
  });

  // ============================================================================
  // SPECIALIZED WIDGETS (8 types)
  // ============================================================================

  // 24. molecule
  WidgetRegistry.register({
    type: 'molecule',
    displayName: 'Molecule Viewer',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.MoleculeWidget }))),
    gradable: false,
    static: true,
  });

  // 25. reaction-diagram
  WidgetRegistry.register({
    type: 'reaction-diagram',
    displayName: 'Chemical Reaction',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.ReactionDiagramWidget }))),
    gradable: false,
    static: true,
  });

  // 26. music-notation
  WidgetRegistry.register({
    type: 'music-notation',
    displayName: 'Music Notation',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.MusicNotationWidget }))),
    gradable: false,
    static: true,
  });

  // 27. cs-program
  WidgetRegistry.register({
    type: 'cs-program',
    displayName: 'Code Editor',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.CSProgramWidget }))),
    gradable: false,
    static: true,
  });

  // 28. iframe
  WidgetRegistry.register({
    type: 'iframe',
    displayName: 'Embedded Content',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.IframeWidget }))),
    gradable: false,
    static: true,
  });

  // 29. timeline
  WidgetRegistry.register({
    type: 'timeline',
    displayName: 'Timeline',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.TimelineWidget }))),
    gradable: false,
    static: true,
  });

  // 30. map
  WidgetRegistry.register({
    type: 'map',
    displayName: 'Interactive Map',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.MapWidget }))),
    gradable: true,
    static: false,
  });

  // 31. label-image
  WidgetRegistry.register({
    type: 'label-image',
    displayName: 'Label Image',
    component: React.lazy(() => import('./specialized/LabelImageWidget')),
    gradable: true,
    static: false,
    defaultOptions: {
      imageUrl: '',
      choices: [],
      markers: [],
    },
  });

  // ============================================================================
  // GROUP WIDGETS (3 types)
  // ============================================================================

  // 32. group
  WidgetRegistry.register({
    type: 'group',
    displayName: 'Widget Group',
    component: React.lazy(() => import('./group/GroupWidget').then(m => ({ default: m.GroupWidget }))),
    gradable: true,
    static: false,
  });

  // 33. graded-group
  WidgetRegistry.register({
    type: 'graded-group',
    displayName: 'Graded Group',
    component: React.lazy(() => import('./group/GroupWidget').then(m => ({ default: m.GroupWidget }))),
    gradable: true,
    static: false,
  });

  // 34. graded-group-set
  WidgetRegistry.register({
    type: 'graded-group-set',
    displayName: 'Graded Group Set',
    component: React.lazy(() => import('./specialized/PlaceholderWidgets').then(m => ({ default: m.GradedGroupSetWidget }))),
    gradable: true,
    static: false,
  });
}

export default WidgetRegistry;

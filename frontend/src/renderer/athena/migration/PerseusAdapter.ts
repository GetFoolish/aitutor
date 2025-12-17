/**
 * Perseus Adapter
 *
 * Converts Perseus JSON v2.0 format to Athena internal format.
 * Provides backward compatibility with existing question banks.
 */

import type {
  PerseusItem,
  PerseusWidget,
  PerseusQuestion,
  PerseusHint,
  AthenaItem,
  AthenaWidget,
  AthenaQuestion,
  AthenaHint,
  AthenaImage,
  WidgetType,
} from '../core/types';
import { WidgetMigrator } from './WidgetMigrator';
import { ImageURLMigrator } from './ImageURLMigrator';

export interface MigrationResult<T> {
  success: boolean;
  data?: T;
  errors: MigrationError[];
  warnings: MigrationWarning[];
}

export interface MigrationError {
  code: string;
  message: string;
  path?: string;
  original?: unknown;
}

export interface MigrationWarning {
  code: string;
  message: string;
  path?: string;
}

export interface PerseusAdapterOptions {
  /** Whether to strictly validate Perseus format */
  strictMode?: boolean;
  /** CDN base URL for image migration */
  cdnBaseUrl?: string;
  /** Whether to include source Perseus data in output */
  includeSource?: boolean;
  /** Custom widget migrators */
  customMigrators?: Record<string, (options: unknown) => unknown>;
}

/**
 * Adapter for converting Perseus items to Athena format
 */
export class PerseusAdapter {
  private options: PerseusAdapterOptions;
  private widgetMigrator: WidgetMigrator;
  private imageMigrator: ImageURLMigrator;

  constructor(options: PerseusAdapterOptions = {}) {
    this.options = {
      strictMode: false,
      cdnBaseUrl: 'https://ka-perseus-images.s3.amazonaws.com',
      includeSource: false,
      ...options,
    };
    this.widgetMigrator = new WidgetMigrator(options.customMigrators);
    this.imageMigrator = new ImageURLMigrator(this.options.cdnBaseUrl);
  }

  /**
   * Check if an item is in Perseus format (vs already Athena)
   */
  isPerseusFormat(item: unknown): item is PerseusItem {
    if (!item || typeof item !== 'object') return false;

    const obj = item as Record<string, unknown>;

    // Perseus items have a question object with content and widgets
    if (!obj.question || typeof obj.question !== 'object') return false;

    const question = obj.question as Record<string, unknown>;

    // Perseus uses string content and widgets record
    if (typeof question.content !== 'string') return false;
    if (!question.widgets || typeof question.widgets !== 'object') return false;

    // Check for Perseus-specific widget format
    const widgets = question.widgets as Record<string, unknown>;
    for (const widget of Object.values(widgets)) {
      if (widget && typeof widget === 'object') {
        const w = widget as Record<string, unknown>;
        // Perseus widgets have type, options, version
        if (typeof w.type !== 'string') return false;
        if (!w.options || typeof w.options !== 'object') return false;
      }
    }

    return true;
  }

  /**
   * Convert a Perseus item to Athena format
   */
  convertItem(perseusItem: PerseusItem): MigrationResult<AthenaItem> {
    const errors: MigrationError[] = [];
    const warnings: MigrationWarning[] = [];

    try {
      // Validate input
      if (!perseusItem?.question) {
        errors.push({
          code: 'MISSING_QUESTION',
          message: 'Perseus item must have a question property',
        });
        return { success: false, errors, warnings };
      }

      // Convert question
      const questionResult = this.convertQuestion(perseusItem.question);
      errors.push(...questionResult.errors);
      warnings.push(...questionResult.warnings);

      if (!questionResult.success || !questionResult.data) {
        return { success: false, errors, warnings };
      }

      // Convert hints
      const hints: AthenaHint[] = [];
      if (perseusItem.hints) {
        for (let i = 0; i < perseusItem.hints.length; i++) {
          const hintResult = this.convertHint(perseusItem.hints[i], i);
          errors.push(...hintResult.errors);
          warnings.push(...hintResult.warnings);

          if (hintResult.success && hintResult.data) {
            hints.push(hintResult.data);
          }
        }
      }

      // Build Athena item
      const athenaItem: AthenaItem = {
        question: questionResult.data,
        hints,
        answerArea: perseusItem.answerArea || {},
        itemDataVersion: perseusItem.itemDataVersion || { major: 0, minor: 0 },
      };

      return {
        success: errors.length === 0,
        data: athenaItem,
        errors,
        warnings,
      };
    } catch (error) {
      errors.push({
        code: 'CONVERSION_ERROR',
        message: error instanceof Error ? error.message : String(error),
      });
      return { success: false, errors, warnings };
    }
  }

  /**
   * Convert a Perseus question to Athena format
   */
  private convertQuestion(perseusQuestion: PerseusQuestion): MigrationResult<AthenaQuestion> {
    const errors: MigrationError[] = [];
    const warnings: MigrationWarning[] = [];

    // Convert content (process image URLs)
    let content = perseusQuestion.content || '';
    content = this.imageMigrator.migrateContent(content);

    // Convert widgets
    const widgets: Record<string, AthenaWidget> = {};
    if (perseusQuestion.widgets) {
      for (const [widgetId, perseusWidget] of Object.entries(perseusQuestion.widgets)) {
        const widgetResult = this.convertWidget(widgetId, perseusWidget);
        errors.push(...widgetResult.errors);
        warnings.push(...widgetResult.warnings);

        if (widgetResult.success && widgetResult.data) {
          widgets[widgetId] = widgetResult.data;
        }
      }
    }

    // Convert images
    const images: Record<string, AthenaImage> = {};
    if (perseusQuestion.images) {
      for (const [imageId, imageData] of Object.entries(perseusQuestion.images)) {
        images[imageId] = this.imageMigrator.migrateImageData(imageData);
      }
    }

    return {
      success: errors.length === 0,
      data: { content, widgets, images },
      errors,
      warnings,
    };
  }

  /**
   * Convert a Perseus hint to Athena format
   */
  private convertHint(perseusHint: PerseusHint, index: number): MigrationResult<AthenaHint> {
    const errors: MigrationError[] = [];
    const warnings: MigrationWarning[] = [];

    // Convert content
    let content = perseusHint.content || '';
    content = this.imageMigrator.migrateContent(content);

    // Convert widgets
    const widgets: Record<string, AthenaWidget> = {};
    if (perseusHint.widgets) {
      for (const [widgetId, perseusWidget] of Object.entries(perseusHint.widgets)) {
        const widgetResult = this.convertWidget(widgetId, perseusWidget);
        errors.push(
          ...widgetResult.errors.map((e) => ({
            ...e,
            path: `hints[${index}].${e.path || widgetId}`,
          }))
        );
        warnings.push(
          ...widgetResult.warnings.map((w) => ({
            ...w,
            path: `hints[${index}].${w.path || widgetId}`,
          }))
        );

        if (widgetResult.success && widgetResult.data) {
          widgets[widgetId] = widgetResult.data;
        }
      }
    }

    // Convert images
    const images: Record<string, AthenaImage> = {};
    if (perseusHint.images) {
      for (const [imageId, imageData] of Object.entries(perseusHint.images)) {
        images[imageId] = this.imageMigrator.migrateImageData(imageData);
      }
    }

    return {
      success: errors.length === 0,
      data: {
        content,
        widgets,
        images,
        replace: perseusHint.replace,
      },
      errors,
      warnings,
    };
  }

  /**
   * Convert a Perseus widget to Athena format
   */
  private convertWidget(
    widgetId: string,
    perseusWidget: PerseusWidget
  ): MigrationResult<AthenaWidget> {
    const errors: MigrationError[] = [];
    const warnings: MigrationWarning[] = [];

    // Validate widget type
    const widgetType = this.normalizeWidgetType(perseusWidget.type);
    if (!widgetType) {
      if (this.options.strictMode) {
        errors.push({
          code: 'UNKNOWN_WIDGET_TYPE',
          message: `Unknown widget type: ${perseusWidget.type}`,
          path: widgetId,
        });
        return { success: false, errors, warnings };
      } else {
        warnings.push({
          code: 'UNKNOWN_WIDGET_TYPE',
          message: `Unknown widget type: ${perseusWidget.type}, treating as generic`,
          path: widgetId,
        });
      }
    }

    // Migrate widget options
    const migratedOptions = this.widgetMigrator.migrateOptions(
      widgetType || (perseusWidget.type as WidgetType),
      perseusWidget.options
    );

    // Migrate any image URLs in options
    const processedOptions = this.imageMigrator.migrateObject(migratedOptions);

    const athenaWidget: AthenaWidget = {
      type: widgetType || (perseusWidget.type as WidgetType),
      alignment: this.normalizeAlignment(perseusWidget.alignment),
      static: perseusWidget.static ?? false,
      graded: perseusWidget.graded ?? true,
      options: processedOptions,
      version: perseusWidget.version || { major: 0, minor: 0 },
    };

    return {
      success: errors.length === 0,
      data: athenaWidget,
      errors,
      warnings,
    };
  }

  /**
   * Normalize Perseus widget type to Athena widget type
   */
  private normalizeWidgetType(perseusType: string): WidgetType | null {
    const typeMap: Record<string, WidgetType> = {
      'numeric-input': 'numeric-input',
      'input-number': 'input-number',
      radio: 'radio',
      expression: 'expression',
      dropdown: 'dropdown',
      'free-response': 'free-response',
      image: 'image',
      passage: 'passage',
      'passage-ref': 'passage-ref',
      'passage-ref-target': 'passage-ref-target',
      video: 'video',
      definition: 'definition',
      explanation: 'explanation',
      'interactive-graph': 'interactive-graph',
      grapher: 'grapher',
      plotter: 'plotter',
      table: 'table',
      'number-line': 'number-line',
      measurer: 'measurer',
      categorizer: 'categorizer',
      sorter: 'sorter',
      matcher: 'matcher',
      orderer: 'orderer',
      molecule: 'molecule',
      'reaction-diagram': 'reaction-diagram',
      'cs-program': 'cs-program',
      iframe: 'iframe',
      group: 'group',
      'graded-group': 'graded-group',
      'graded-group-set': 'graded-group-set',
      // Aliases
      'label-image': 'label-image',
      transformer: 'interactive-graph', // Map transformer to interactive-graph
      simulator: 'iframe', // Map simulator to iframe
    };

    return typeMap[perseusType] || null;
  }

  /**
   * Normalize alignment value
   */
  private normalizeAlignment(
    alignment: string
  ): 'default' | 'block' | 'inline' | 'full-width' {
    switch (alignment?.toLowerCase()) {
      case 'block':
        return 'block';
      case 'inline':
      case 'inline-block':
        return 'inline';
      case 'full-width':
      case 'fullwidth':
        return 'full-width';
      default:
        return 'default';
    }
  }

  /**
   * Convert Athena item back to Perseus format (for export/compatibility)
   */
  convertToPerseusFormat(athenaItem: AthenaItem): PerseusItem {
    return {
      question: {
        content: athenaItem.question.content,
        widgets: athenaItem.question.widgets as unknown as Record<string, PerseusWidget>,
        images: athenaItem.question.images,
      },
      hints: athenaItem.hints.map((hint) => ({
        content: hint.content,
        widgets: hint.widgets as unknown as Record<string, PerseusWidget>,
        images: hint.images,
        replace: hint.replace,
      })),
      answerArea: athenaItem.answerArea,
      itemDataVersion: athenaItem.itemDataVersion,
    };
  }

  /**
   * Batch convert multiple Perseus items
   */
  convertItems(
    items: PerseusItem[]
  ): Array<{ index: number; result: MigrationResult<AthenaItem> }> {
    return items.map((item, index) => ({
      index,
      result: this.convertItem(item),
    }));
  }

  /**
   * Get migration statistics for a batch conversion
   */
  getMigrationStats(
    results: Array<{ index: number; result: MigrationResult<AthenaItem> }>
  ): {
    total: number;
    successful: number;
    failed: number;
    totalErrors: number;
    totalWarnings: number;
    errorsByCode: Record<string, number>;
    warningsByCode: Record<string, number>;
  } {
    const stats = {
      total: results.length,
      successful: 0,
      failed: 0,
      totalErrors: 0,
      totalWarnings: 0,
      errorsByCode: {} as Record<string, number>,
      warningsByCode: {} as Record<string, number>,
    };

    for (const { result } of results) {
      if (result.success) {
        stats.successful++;
      } else {
        stats.failed++;
      }

      stats.totalErrors += result.errors.length;
      stats.totalWarnings += result.warnings.length;

      for (const error of result.errors) {
        stats.errorsByCode[error.code] = (stats.errorsByCode[error.code] || 0) + 1;
      }

      for (const warning of result.warnings) {
        stats.warningsByCode[warning.code] = (stats.warningsByCode[warning.code] || 0) + 1;
      }
    }

    return stats;
  }
}

export default PerseusAdapter;

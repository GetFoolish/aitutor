/**
 * Perseus to Athena Migration Script
 *
 * Converts Perseus JSON format questions to Athena format.
 * Handles all 35+ widget types, image URL migration, and validation.
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
  WidgetType,
} from '../core/types';

// ============================================================================
// TYPES
// ============================================================================

export interface MigrationResult {
  success: boolean;
  item: AthenaItem | null;
  warnings: string[];
  errors: string[];
  stats: MigrationStats;
}

export interface MigrationStats {
  totalWidgets: number;
  migratedWidgets: number;
  skippedWidgets: number;
  imagesMigrated: number;
  hintsCount: number;
  duration: number;
}

export interface BatchMigrationResult {
  total: number;
  success: number;
  failed: number;
  items: MigrationResult[];
  stats: {
    totalWidgets: number;
    totalImages: number;
    totalHints: number;
    duration: number;
  };
}

export interface MigrationOptions {
  /** Convert web+graphie:// URLs to CDN URLs */
  migrateImageUrls?: boolean;
  /** Base URL for CDN images */
  cdnBaseUrl?: string;
  /** Skip unknown widget types instead of failing */
  skipUnknownWidgets?: boolean;
  /** Validate output against schema */
  validateOutput?: boolean;
  /** Include original Perseus data in output */
  includeOriginal?: boolean;
}

// ============================================================================
// DEFAULT OPTIONS
// ============================================================================

const DEFAULT_OPTIONS: MigrationOptions = {
  migrateImageUrls: true,
  cdnBaseUrl: 'https://ka-perseus-graphie.s3.amazonaws.com',
  skipUnknownWidgets: true,
  validateOutput: true,
  includeOriginal: false,
};

// ============================================================================
// KNOWN WIDGET TYPES
// ============================================================================

const KNOWN_WIDGET_TYPES: Set<WidgetType | string> = new Set([
  // Input widgets
  'numeric-input', 'input-number', 'radio', 'expression', 'dropdown', 'free-response',
  // Display widgets
  'image', 'passage', 'passage-ref', 'passage-ref-target', 'video', 'definition', 'explanation',
  // Interactive widgets
  'interactive-graph', 'grapher', 'plotter', 'table', 'number-line', 'measurer',
  // Assessment widgets
  'categorizer', 'sorter', 'matcher', 'orderer',
  // Specialized widgets
  'molecule', 'reaction-diagram', 'music-notation', 'cs-program', 'iframe', 'timeline', 'map', 'label-image',
  // Group widgets
  'group', 'graded-group', 'graded-group-set',
  // Legacy/deprecated
  'deprecated-standin', 'interaction', 'matrix', 'python-program',
]);

// ============================================================================
// IMAGE URL MIGRATION
// ============================================================================

/**
 * Convert web+graphie:// URLs to HTTPS CDN URLs
 */
export function migrateImageUrl(url: string, cdnBaseUrl: string): string {
  if (!url) return url;

  // Handle web+graphie:// protocol
  if (url.startsWith('web+graphie://')) {
    const path = url.replace('web+graphie://', '');
    // Add .svg extension if not present
    const finalPath = path.includes('.') ? path : `${path}.svg`;
    return `https://${finalPath}`;
  }

  // Handle ka-perseus-graphie URLs without protocol
  if (url.includes('ka-perseus-graphie') && !url.startsWith('http')) {
    return `https://${url}`;
  }

  // Handle relative URLs
  if (url.startsWith('/')) {
    return `${cdnBaseUrl}${url}`;
  }

  return url;
}

/**
 * Migrate all image URLs in widget options
 */
function migrateWidgetImageUrls(options: Record<string, unknown>, cdnBaseUrl: string): Record<string, unknown> {
  const result = { ...options };

  // Background image
  if (result.backgroundImage && typeof result.backgroundImage === 'object') {
    const bgImage = result.backgroundImage as Record<string, unknown>;
    if (bgImage.url && typeof bgImage.url === 'string') {
      bgImage.url = migrateImageUrl(bgImage.url, cdnBaseUrl);
    }
  }

  // Image URL (label-image, etc.)
  if (result.imageUrl && typeof result.imageUrl === 'string') {
    result.imageUrl = migrateImageUrl(result.imageUrl, cdnBaseUrl);
  }

  // URL field
  if (result.url && typeof result.url === 'string') {
    result.url = migrateImageUrl(result.url, cdnBaseUrl);
  }

  return result;
}

// ============================================================================
// WIDGET MIGRATION
// ============================================================================

/**
 * Migrate a single Perseus widget to Athena format
 */
export function migrateWidget(
  widgetId: string,
  widget: PerseusWidget,
  options: MigrationOptions
): { widget: AthenaWidget | null; warning?: string } {
  const widgetType = widget.type as WidgetType;

  // Check if widget type is known
  if (!KNOWN_WIDGET_TYPES.has(widgetType)) {
    if (options.skipUnknownWidgets) {
      return {
        widget: null,
        warning: `Unknown widget type: ${widgetType}`,
      };
    }
  }

  // Migrate image URLs in options
  let migratedOptions = { ...widget.options };
  if (options.migrateImageUrls && options.cdnBaseUrl) {
    migratedOptions = migrateWidgetImageUrls(migratedOptions, options.cdnBaseUrl);
  }

  // Create Athena widget
  const athenaWidget: AthenaWidget = {
    type: widgetType,
    alignment: (widget.alignment || 'default') as AthenaWidget['alignment'],
    static: widget.static ?? false,
    graded: widget.graded ?? true,
    options: migratedOptions,
    version: widget.version || { major: 0, minor: 0 },
  };

  return { widget: athenaWidget };
}

/**
 * Migrate all widgets in a content section
 */
function migrateWidgets(
  widgets: Record<string, PerseusWidget>,
  options: MigrationOptions
): { widgets: Record<string, AthenaWidget>; warnings: string[]; stats: { migrated: number; skipped: number } } {
  const result: Record<string, AthenaWidget> = {};
  const warnings: string[] = [];
  let migrated = 0;
  let skipped = 0;

  for (const [widgetId, widget] of Object.entries(widgets)) {
    const { widget: migratedWidget, warning } = migrateWidget(widgetId, widget, options);

    if (migratedWidget) {
      result[widgetId] = migratedWidget;
      migrated++;
    } else {
      skipped++;
    }

    if (warning) {
      warnings.push(`[${widgetId}] ${warning}`);
    }
  }

  return { widgets: result, warnings, stats: { migrated, skipped } };
}

// ============================================================================
// QUESTION MIGRATION
// ============================================================================

/**
 * Migrate Perseus question to Athena format
 */
function migrateQuestion(
  question: PerseusQuestion,
  options: MigrationOptions
): { question: AthenaQuestion; warnings: string[]; stats: { migrated: number; skipped: number } } {
  const { widgets, warnings, stats } = migrateWidgets(question.widgets || {}, options);

  // Migrate images in content
  const images = { ...question.images };
  if (options.migrateImageUrls && options.cdnBaseUrl) {
    for (const [imageId, imageData] of Object.entries(images)) {
      if (imageData.url) {
        images[imageId] = {
          ...imageData,
          url: migrateImageUrl(imageData.url, options.cdnBaseUrl),
        };
      }
    }
  }

  return {
    question: {
      content: question.content || '',
      widgets,
      images,
    },
    warnings,
    stats,
  };
}

// ============================================================================
// HINT MIGRATION
// ============================================================================

/**
 * Migrate Perseus hints to Athena format
 */
function migrateHints(
  hints: PerseusHint[] | undefined,
  options: MigrationOptions
): { hints: AthenaHint[]; warnings: string[]; stats: { migrated: number; skipped: number } } {
  if (!hints || hints.length === 0) {
    return { hints: [], warnings: [], stats: { migrated: 0, skipped: 0 } };
  }

  const result: AthenaHint[] = [];
  const allWarnings: string[] = [];
  let totalMigrated = 0;
  let totalSkipped = 0;

  for (let i = 0; i < hints.length; i++) {
    const hint = hints[i];
    const { widgets, warnings, stats } = migrateWidgets(hint.widgets || {}, options);

    // Migrate images in hint
    const images = { ...hint.images };
    if (options.migrateImageUrls && options.cdnBaseUrl) {
      for (const [imageId, imageData] of Object.entries(images)) {
        if (imageData.url) {
          images[imageId] = {
            ...imageData,
            url: migrateImageUrl(imageData.url, options.cdnBaseUrl),
          };
        }
      }
    }

    result.push({
      content: hint.content || '',
      widgets,
      images,
      replace: hint.replace,
    });

    allWarnings.push(...warnings.map(w => `[Hint ${i + 1}] ${w}`));
    totalMigrated += stats.migrated;
    totalSkipped += stats.skipped;
  }

  return {
    hints: result,
    warnings: allWarnings,
    stats: { migrated: totalMigrated, skipped: totalSkipped },
  };
}

// ============================================================================
// MAIN MIGRATION FUNCTIONS
// ============================================================================

/**
 * Migrate a single Perseus item to Athena format
 */
export function migratePerseus(
  perseusItem: PerseusItem,
  options: Partial<MigrationOptions> = {}
): MigrationResult {
  const startTime = performance.now();
  const opts = { ...DEFAULT_OPTIONS, ...options };

  const warnings: string[] = [];
  const errors: string[] = [];

  try {
    // Migrate question
    const {
      question,
      warnings: questionWarnings,
      stats: questionStats,
    } = migrateQuestion(perseusItem.question, opts);

    warnings.push(...questionWarnings);

    // Migrate hints
    const {
      hints,
      warnings: hintWarnings,
      stats: hintStats,
    } = migrateHints(perseusItem.hints, opts);

    warnings.push(...hintWarnings);

    // Count images
    const imageCount =
      Object.keys(question.images).length +
      hints.reduce((sum, h) => sum + Object.keys(h.images).length, 0);

    // Create Athena item
    const athenaItem: AthenaItem = {
      question,
      hints,
      answerArea: {
        type: perseusItem.answerArea?.type,
        calculator: perseusItem.answerArea?.calculator,
        periodicTable: perseusItem.answerArea?.periodicTable,
        zTable: perseusItem.answerArea?.zTable,
        tTable: perseusItem.answerArea?.tTable,
        chi2Table: perseusItem.answerArea?.chi2Table,
      },
      itemDataVersion: perseusItem.itemDataVersion || { major: 2, minor: 0 },
    };

    const duration = performance.now() - startTime;

    return {
      success: true,
      item: athenaItem,
      warnings,
      errors,
      stats: {
        totalWidgets: questionStats.migrated + questionStats.skipped + hintStats.migrated + hintStats.skipped,
        migratedWidgets: questionStats.migrated + hintStats.migrated,
        skippedWidgets: questionStats.skipped + hintStats.skipped,
        imagesMigrated: imageCount,
        hintsCount: hints.length,
        duration,
      },
    };
  } catch (error) {
    errors.push(`Migration failed: ${error instanceof Error ? error.message : String(error)}`);

    return {
      success: false,
      item: null,
      warnings,
      errors,
      stats: {
        totalWidgets: 0,
        migratedWidgets: 0,
        skippedWidgets: 0,
        imagesMigrated: 0,
        hintsCount: 0,
        duration: performance.now() - startTime,
      },
    };
  }
}

/**
 * Migrate multiple Perseus items in batch
 */
export function migrateBatch(
  perseusItems: PerseusItem[],
  options: Partial<MigrationOptions> = {}
): BatchMigrationResult {
  const startTime = performance.now();
  const results: MigrationResult[] = [];
  let success = 0;
  let failed = 0;
  let totalWidgets = 0;
  let totalImages = 0;
  let totalHints = 0;

  for (const item of perseusItems) {
    const result = migratePerseus(item, options);
    results.push(result);

    if (result.success) {
      success++;
    } else {
      failed++;
    }

    totalWidgets += result.stats.migratedWidgets;
    totalImages += result.stats.imagesMigrated;
    totalHints += result.stats.hintsCount;
  }

  return {
    total: perseusItems.length,
    success,
    failed,
    items: results,
    stats: {
      totalWidgets,
      totalImages,
      totalHints,
      duration: performance.now() - startTime,
    },
  };
}

/**
 * Validate that an item was migrated correctly
 */
export function validateMigration(athenaItem: AthenaItem): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check required fields
  if (!athenaItem.question) {
    errors.push('Missing question');
  }

  if (!athenaItem.question?.content && Object.keys(athenaItem.question?.widgets || {}).length === 0) {
    errors.push('Question has no content and no widgets');
  }

  // Check widget structure
  if (athenaItem.question?.widgets) {
    for (const [widgetId, widget] of Object.entries(athenaItem.question.widgets)) {
      if (!widget.type) {
        errors.push(`Widget ${widgetId} missing type`);
      }
      if (!widget.options) {
        errors.push(`Widget ${widgetId} missing options`);
      }
    }
  }

  // Check hints structure
  if (athenaItem.hints) {
    for (let i = 0; i < athenaItem.hints.length; i++) {
      const hint = athenaItem.hints[i];
      if (!hint.content && Object.keys(hint.widgets || {}).length === 0) {
        errors.push(`Hint ${i + 1} has no content and no widgets`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// ============================================================================
// CLI HELPER
// ============================================================================

/**
 * Print migration report
 */
export function printMigrationReport(result: BatchMigrationResult): string {
  const lines: string[] = [
    '═══════════════════════════════════════════════════════════════════════════',
    '                    PERSEUS → ATHENA MIGRATION REPORT                      ',
    '═══════════════════════════════════════════════════════════════════════════',
    '',
    `  Total Items:     ${result.total}`,
    `  Successful:      ${result.success} (${Math.round((result.success / result.total) * 100)}%)`,
    `  Failed:          ${result.failed}`,
    '',
    '  Statistics:',
    `    - Widgets:     ${result.stats.totalWidgets}`,
    `    - Images:      ${result.stats.totalImages}`,
    `    - Hints:       ${result.stats.totalHints}`,
    `    - Duration:    ${result.stats.duration.toFixed(2)}ms`,
    '',
  ];

  // Show warnings and errors
  const warnings = result.items.flatMap(r => r.warnings);
  const errors = result.items.flatMap(r => r.errors);

  if (warnings.length > 0) {
    lines.push(`  Warnings (${warnings.length}):`);
    warnings.slice(0, 10).forEach(w => lines.push(`    - ${w}`));
    if (warnings.length > 10) {
      lines.push(`    ... and ${warnings.length - 10} more`);
    }
    lines.push('');
  }

  if (errors.length > 0) {
    lines.push(`  Errors (${errors.length}):`);
    errors.slice(0, 10).forEach(e => lines.push(`    - ${e}`));
    if (errors.length > 10) {
      lines.push(`    ... and ${errors.length - 10} more`);
    }
    lines.push('');
  }

  lines.push('═══════════════════════════════════════════════════════════════════════════');

  return lines.join('\n');
}

export default {
  migratePerseus,
  migrateBatch,
  migrateImageUrl,
  validateMigration,
  printMigrationReport,
};

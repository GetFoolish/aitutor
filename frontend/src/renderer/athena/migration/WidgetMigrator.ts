/**
 * Widget Migrator
 *
 * Handles transformation of Perseus widget options to Athena format.
 * Different widget versions may have different option structures.
 */

import type { WidgetType } from '../core/types';

export type WidgetMigratorFn = (options: Record<string, unknown>) => Record<string, unknown>;

/**
 * Migrates widget options from Perseus format to Athena format
 */
export class WidgetMigrator {
  private migrators: Map<string, WidgetMigratorFn>;
  private customMigrators: Record<string, WidgetMigratorFn>;

  constructor(customMigrators: Record<string, (options: unknown) => unknown> = {}) {
    this.customMigrators = customMigrators as Record<string, WidgetMigratorFn>;
    this.migrators = new Map();
    this.registerDefaultMigrators();
  }

  /**
   * Register all default widget migrators
   */
  private registerDefaultMigrators(): void {
    // Numeric input
    this.register('numeric-input', this.migrateNumericInput.bind(this));
    this.register('input-number', this.migrateNumericInput.bind(this));

    // Radio (multiple choice)
    this.register('radio', this.migrateRadio.bind(this));

    // Expression (math input)
    this.register('expression', this.migrateExpression.bind(this));

    // Interactive graph
    this.register('interactive-graph', this.migrateInteractiveGraph.bind(this));

    // Image
    this.register('image', this.migrateImage.bind(this));

    // Dropdown
    this.register('dropdown', this.migrateDropdown.bind(this));

    // Passage
    this.register('passage', this.migratePassage.bind(this));

    // Table
    this.register('table', this.migrateTable.bind(this));

    // Categorizer
    this.register('categorizer', this.migrateCategorizer.bind(this));

    // Sorter
    this.register('sorter', this.migrateSorter.bind(this));

    // Matcher
    this.register('matcher', this.migrateMatcher.bind(this));

    // Orderer
    this.register('orderer', this.migrateOrderer.bind(this));

    // Group widgets
    this.register('group', this.migrateGroup.bind(this));
    this.register('graded-group', this.migrateGradedGroup.bind(this));
    this.register('graded-group-set', this.migrateGradedGroupSet.bind(this));

    // Video
    this.register('video', this.migrateVideo.bind(this));

    // CS Program
    this.register('cs-program', this.migrateCSProgram.bind(this));

    // Molecule
    this.register('molecule', this.migrateMolecule.bind(this));

    // Grapher
    this.register('grapher', this.migrateGrapher.bind(this));

    // Number line
    this.register('number-line', this.migrateNumberLine.bind(this));

    // Plotter
    this.register('plotter', this.migratePlotter.bind(this));

    // Measurer
    this.register('measurer', this.migrateMeasurer.bind(this));

    // Definition
    this.register('definition', this.migrateDefinition.bind(this));

    // Explanation
    this.register('explanation', this.migrateExplanation.bind(this));

    // Free response
    this.register('free-response', this.migrateFreeResponse.bind(this));

    // IFrame
    this.register('iframe', this.migrateIFrame.bind(this));

    // Label image
    this.register('label-image', this.migrateLabelImage.bind(this));
  }

  /**
   * Register a widget migrator
   */
  register(widgetType: string, migrator: WidgetMigratorFn): void {
    this.migrators.set(widgetType, migrator);
  }

  /**
   * Migrate widget options
   */
  migrateOptions(widgetType: WidgetType | string, options: Record<string, unknown>): Record<string, unknown> {
    // Check for custom migrator first
    if (this.customMigrators[widgetType]) {
      return this.customMigrators[widgetType](options);
    }

    // Use default migrator
    const migrator = this.migrators.get(widgetType);
    if (migrator) {
      return migrator(options);
    }

    // No migrator found, return options as-is
    return { ...options };
  }

  // ============================================================================
  // Individual Widget Migrators
  // ============================================================================

  private migrateNumericInput(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure answers array exists and has proper structure
    if (options.answers && Array.isArray(options.answers)) {
      migrated.answers = options.answers.map((answer: unknown) => {
        const ans = answer as Record<string, unknown>;
        return {
          value: ans.value,
          status: ans.status || (ans.correct ? 'correct' : 'wrong'),
          message: ans.message,
          strict: ans.strict ?? false,
          maxError: ans.maxError ?? 0,
        };
      });
    }

    // Normalize size
    migrated.size = options.size === 'small' ? 'small' : 'normal';

    return migrated;
  }

  private migrateRadio(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure choices array has proper structure
    if (options.choices && Array.isArray(options.choices)) {
      migrated.choices = options.choices.map((choice: unknown) => {
        const ch = choice as Record<string, unknown>;
        return {
          content: ch.content || '',
          correct: ch.correct ?? false,
          clue: ch.clue,
          isNoneOfTheAbove: ch.isNoneOfTheAbove ?? false,
        };
      });
    }

    // Handle legacy multipleSelect as countChoices
    if (options.countChoices !== undefined && options.multipleSelect === undefined) {
      migrated.multipleSelect = (options.countChoices as number) > 1;
    }

    return migrated;
  }

  private migrateExpression(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure answerForms array exists
    if (options.answerForms && Array.isArray(options.answerForms)) {
      migrated.answerForms = options.answerForms.map((form: unknown) => {
        const f = form as Record<string, unknown>;
        return {
          value: f.value || '',
          form: f.form ?? false,
          simplify: f.simplify ?? false,
          considered: f.considered || 'correct',
        };
      });
    }

    // Handle legacy value field (single answer)
    if (options.value && !options.answerForms) {
      migrated.answerForms = [
        {
          value: options.value,
          form: false,
          simplify: false,
          considered: 'correct',
        },
      ];
    }

    // Normalize buttonSets
    if (options.buttonSets && Array.isArray(options.buttonSets)) {
      migrated.buttonSets = options.buttonSets;
    } else {
      migrated.buttonSets = ['basic'];
    }

    return migrated;
  }

  private migrateInteractiveGraph(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure graph object exists
    if (!migrated.graph || typeof migrated.graph !== 'object') {
      migrated.graph = { type: 'none', rulerLabel: '', rulerTicks: 10 };
    }

    // Normalize range
    if (!migrated.range || !Array.isArray(migrated.range)) {
      migrated.range = [
        [-10, 10],
        [-10, 10],
      ];
    }

    // Ensure step arrays
    migrated.step = migrated.step || [1, 1];
    migrated.gridStep = migrated.gridStep || [1, 1];
    migrated.snapStep = migrated.snapStep || [0.5, 0.5];

    // Normalize markings
    migrated.markings = migrated.markings || 'graph';

    return migrated;
  }

  private migrateImage(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure backgroundImage object exists
    if (!migrated.backgroundImage || typeof migrated.backgroundImage !== 'object') {
      // Try to use legacy url field
      if (options.url) {
        migrated.backgroundImage = {
          url: options.url,
          width: options.width || 400,
          height: options.height || 300,
        };
      } else {
        migrated.backgroundImage = {
          url: '',
          width: 400,
          height: 300,
        };
      }
    }

    // Ensure alt text
    migrated.alt = migrated.alt || '';

    return migrated;
  }

  private migrateDropdown(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure choices array
    if (options.choices && Array.isArray(options.choices)) {
      migrated.choices = options.choices.map((choice: unknown) => {
        const ch = choice as Record<string, unknown>;
        return {
          content: ch.content || '',
          correct: ch.correct ?? false,
        };
      });
    }

    migrated.placeholder = migrated.placeholder || 'Select an answer';

    return migrated;
  }

  private migratePassage(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.passageTitle = migrated.passageTitle || '';
    migrated.passageText = migrated.passageText || '';
    migrated.showLineNumbers = migrated.showLineNumbers ?? true;

    return migrated;
  }

  private migrateTable(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Ensure headers array
    if (!migrated.headers || !Array.isArray(migrated.headers)) {
      const columns = (options.columns as number) || 2;
      migrated.headers = Array(columns).fill('');
    }

    // Ensure dimensions
    migrated.rows = migrated.rows || 3;
    migrated.columns = migrated.columns || 2;

    // Ensure answers 2D array
    if (!migrated.answers || !Array.isArray(migrated.answers)) {
      const rows = migrated.rows as number;
      const cols = migrated.columns as number;
      migrated.answers = Array(rows)
        .fill(null)
        .map(() => Array(cols).fill(''));
    }

    return migrated;
  }

  private migrateCategorizer(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.items = migrated.items || [];
    migrated.categories = migrated.categories || [];
    migrated.values = migrated.values || [];
    migrated.randomizeItems = migrated.randomizeItems ?? false;

    return migrated;
  }

  private migrateSorter(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.correct = migrated.correct || [];
    migrated.layout = migrated.layout || 'horizontal';
    migrated.padding = migrated.padding ?? true;

    return migrated;
  }

  private migrateMatcher(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.left = migrated.left || [];
    migrated.right = migrated.right || [];
    migrated.labels = migrated.labels || ['', ''];
    migrated.orderMatters = migrated.orderMatters ?? true;
    migrated.padding = migrated.padding ?? true;

    return migrated;
  }

  private migrateOrderer(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.correctOptions = migrated.correctOptions || migrated.options || [];
    migrated.otherOptions = migrated.otherOptions || [];
    migrated.layout = migrated.layout || 'horizontal';

    // Handle legacy options field
    if (options.options && !options.correctOptions) {
      migrated.correctOptions = options.options;
    }

    return migrated;
  }

  private migrateGroup(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Group widgets contain nested content and widgets
    migrated.content = migrated.content || '';
    migrated.widgets = migrated.widgets || {};
    migrated.images = migrated.images || {};

    return migrated;
  }

  private migrateGradedGroup(options: Record<string, unknown>): Record<string, unknown> {
    const migrated = this.migrateGroup(options);
    migrated.title = migrated.title || '';
    return migrated;
  }

  private migrateGradedGroupSet(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Contains array of graded groups
    if (options.gradedGroups && Array.isArray(options.gradedGroups)) {
      migrated.gradedGroups = options.gradedGroups.map((group: unknown) =>
        this.migrateGradedGroup(group as Record<string, unknown>)
      );
    } else {
      migrated.gradedGroups = [];
    }

    return migrated;
  }

  private migrateVideo(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    // Handle different video URL formats
    migrated.location = migrated.location || migrated.url || migrated.youtubeId || '';

    // Convert YouTube ID to URL if needed
    if (options.youtubeId && !options.location) {
      migrated.location = `https://www.youtube.com/watch?v=${options.youtubeId}`;
    }

    return migrated;
  }

  private migrateCSProgram(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.programID = migrated.programID || migrated.programId || '';
    migrated.height = migrated.height || 400;
    migrated.showEditor = migrated.showEditor ?? true;
    migrated.showButtons = migrated.showButtons ?? true;
    migrated.settings = migrated.settings || [];

    return migrated;
  }

  private migrateMolecule(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.smiles = migrated.smiles || migrated.smilesString || '';
    migrated.rotationAngle = migrated.rotationAngle || 0;

    return migrated;
  }

  private migrateGrapher(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.availableTypes = migrated.availableTypes || ['linear'];
    migrated.graph = migrated.graph || { type: 'linear' };

    // Ensure range
    if (!migrated.range || !Array.isArray(migrated.range)) {
      migrated.range = [
        [-10, 10],
        [-10, 10],
      ];
    }

    return migrated;
  }

  private migrateNumberLine(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.range = migrated.range || [0, 10];
    migrated.initialX = migrated.initialX;
    migrated.correctX = migrated.correctX;
    migrated.correctRel = migrated.correctRel || 'eq';
    migrated.divisionRange = migrated.divisionRange || [1, 10];
    migrated.numDivisions = migrated.numDivisions || 5;
    migrated.snapDivisions = migrated.snapDivisions || 2;
    migrated.tickStep = migrated.tickStep || 1;
    migrated.labelRange = migrated.labelRange;
    migrated.labelStyle = migrated.labelStyle || 'decimal';
    migrated.labelTicks = migrated.labelTicks ?? true;
    migrated.isInequality = migrated.isInequality ?? false;

    return migrated;
  }

  private migratePlotter(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.categories = migrated.categories || [];
    migrated.scaleY = migrated.scaleY || 1;
    migrated.maxY = migrated.maxY || 10;
    migrated.snapsPerLine = migrated.snapsPerLine || 2;
    migrated.type = migrated.type || 'bar';
    migrated.labels = migrated.labels || ['', ''];
    migrated.starting = migrated.starting || [];
    migrated.correct = migrated.correct || [];

    return migrated;
  }

  private migrateMeasurer(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.box = migrated.box || [400, 400];
    migrated.image = migrated.image || {};
    migrated.showProtractor = migrated.showProtractor ?? false;
    migrated.showRuler = migrated.showRuler ?? true;
    migrated.rulerLabel = migrated.rulerLabel || '';
    migrated.rulerTicks = migrated.rulerTicks || 10;
    migrated.rulerPixels = migrated.rulerPixels || 40;
    migrated.rulerLength = migrated.rulerLength || 10;

    return migrated;
  }

  private migrateDefinition(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.definition = migrated.definition || '';
    migrated.togglePrompt = migrated.togglePrompt || 'Definition';

    return migrated;
  }

  private migrateExplanation(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.explanation = migrated.explanation || '';
    migrated.hidePrompt = migrated.hidePrompt || 'Hide explanation';
    migrated.showPrompt = migrated.showPrompt || 'Explain';
    migrated.widgets = migrated.widgets || {};

    return migrated;
  }

  private migrateFreeResponse(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.placeholder = migrated.placeholder || '';
    migrated.allowEmptyResponse = migrated.allowEmptyResponse ?? false;

    return migrated;
  }

  private migrateIFrame(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };

    migrated.url = migrated.url || '';
    migrated.width = migrated.width || '100%';
    migrated.height = migrated.height || 400;
    migrated.allowFullscreen = migrated.allowFullscreen ?? false;
    migrated.allowTopNavigation = migrated.allowTopNavigation ?? false;

    return migrated;
  }

  private migrateLabelImage(options: Record<string, unknown>): Record<string, unknown> {
    const migrated: Record<string, unknown> = { ...options };
    const bg = migrated.backgroundImage as Record<string, unknown> | undefined;

    migrated.imageUrl = migrated.imageUrl || bg?.url || '';
    migrated.imageWidth = migrated.imageWidth || bg?.width || 400;
    migrated.imageHeight = migrated.imageHeight || bg?.height || 300;
    migrated.imageAlt = migrated.imageAlt || '';
    migrated.markers = migrated.markers || [];
    migrated.multipleAnswersPerMarker = migrated.multipleAnswersPerMarker ?? false;
    migrated.hideChoicesFromInstructions = migrated.hideChoicesFromInstructions ?? false;

    // Handle legacy backgroundImage format
    if (options.backgroundImage && typeof options.backgroundImage === 'object') {
      const bg = options.backgroundImage as Record<string, unknown>;
      if (!migrated.imageUrl) migrated.imageUrl = bg.url;
      if (!migrated.imageWidth) migrated.imageWidth = bg.width;
      if (!migrated.imageHeight) migrated.imageHeight = bg.height;
    }

    return migrated;
  }
}

export default WidgetMigrator;

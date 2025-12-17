/**
 * Batch Migration Script
 *
 * CLI tool for bulk converting Perseus questions to Athena format.
 * Usage: npx ts-node BatchMigrationScript.ts --input ./questions --output ./migrated
 */

import { PerseusAdapter } from './PerseusAdapter';
import type { PerseusItem, AthenaItem } from '../core/types';
import type { MigrationResult, MigrationError, MigrationWarning } from './PerseusAdapter';

export interface BatchMigrationOptions {
  /** Directory or file containing Perseus JSON */
  input: string;
  /** Output directory for migrated files */
  output: string;
  /** Whether to pretty print output JSON */
  pretty?: boolean;
  /** Whether to continue on errors */
  continueOnError?: boolean;
  /** Whether to generate a report file */
  generateReport?: boolean;
  /** CDN base URL for image migration */
  cdnBaseUrl?: string;
  /** Dry run - don't write files */
  dryRun?: boolean;
  /** Verbose logging */
  verbose?: boolean;
  /** File pattern to match (glob) */
  pattern?: string;
}

export interface BatchMigrationResult {
  success: boolean;
  totalFiles: number;
  successfulFiles: number;
  failedFiles: number;
  totalItems: number;
  successfulItems: number;
  failedItems: number;
  errors: Array<{ file: string; errors: MigrationError[] }>;
  warnings: Array<{ file: string; warnings: MigrationWarning[] }>;
  duration: number;
}

export interface MigrationReport {
  timestamp: string;
  options: BatchMigrationOptions;
  result: BatchMigrationResult;
  details: Array<{
    file: string;
    status: 'success' | 'partial' | 'failed';
    itemCount: number;
    successCount: number;
    errors: MigrationError[];
    warnings: MigrationWarning[];
  }>;
}

/**
 * Batch migration runner for CLI or programmatic use
 */
export class BatchMigrationScript {
  private options: BatchMigrationOptions;
  private adapter: PerseusAdapter;
  private fs: typeof import('fs') | null = null;
  private path: typeof import('path') | null = null;

  constructor(options: BatchMigrationOptions) {
    this.options = {
      pretty: true,
      continueOnError: true,
      generateReport: true,
      dryRun: false,
      verbose: false,
      pattern: '*.json',
      ...options,
    };

    this.adapter = new PerseusAdapter({
      cdnBaseUrl: options.cdnBaseUrl,
      strictMode: false,
    });
  }

  /**
   * Run the batch migration
   */
  async run(): Promise<BatchMigrationResult> {
    const startTime = Date.now();
    const result: BatchMigrationResult = {
      success: true,
      totalFiles: 0,
      successfulFiles: 0,
      failedFiles: 0,
      totalItems: 0,
      successfulItems: 0,
      failedItems: 0,
      errors: [],
      warnings: [],
      duration: 0,
    };

    try {
      // Dynamic import for Node.js modules
      await this.loadNodeModules();

      // Get list of files to process
      const files = await this.getInputFiles();
      result.totalFiles = files.length;

      this.log(`Found ${files.length} files to process`);

      // Process each file
      for (const file of files) {
        try {
          const fileResult = await this.processFile(file);

          result.totalItems += fileResult.totalItems;
          result.successfulItems += fileResult.successfulItems;
          result.failedItems += fileResult.failedItems;

          if (fileResult.errors.length > 0) {
            result.errors.push({ file, errors: fileResult.errors });
          }

          if (fileResult.warnings.length > 0) {
            result.warnings.push({ file, warnings: fileResult.warnings });
          }

          if (fileResult.failedItems === 0) {
            result.successfulFiles++;
          } else if (fileResult.successfulItems > 0) {
            // Partial success
            if (this.options.continueOnError) {
              result.successfulFiles++;
            } else {
              result.failedFiles++;
            }
          } else {
            result.failedFiles++;
          }
        } catch (error) {
          result.failedFiles++;
          result.errors.push({
            file,
            errors: [
              {
                code: 'FILE_ERROR',
                message: error instanceof Error ? error.message : String(error),
              },
            ],
          });

          if (!this.options.continueOnError) {
            throw error;
          }
        }
      }

      // Generate report
      if (this.options.generateReport && !this.options.dryRun) {
        await this.generateReport(result);
      }
    } catch (error) {
      result.success = false;
      this.log(`Migration failed: ${error}`, 'error');
    }

    result.duration = Date.now() - startTime;
    result.success = result.failedFiles === 0;

    this.printSummary(result);

    return result;
  }

  /**
   * Load Node.js modules dynamically (for browser compatibility)
   */
  private async loadNodeModules(): Promise<void> {
    if (typeof window !== 'undefined') {
      throw new Error('Batch migration script is only available in Node.js environment');
    }

    this.fs = await import('fs');
    this.path = await import('path');
  }

  /**
   * Get list of input files to process
   */
  private async getInputFiles(): Promise<string[]> {
    if (!this.fs || !this.path) {
      throw new Error('Node modules not loaded');
    }

    const { input, pattern } = this.options;
    const stats = this.fs.statSync(input);

    if (stats.isFile()) {
      return [input];
    }

    if (stats.isDirectory()) {
      return this.findFiles(input, pattern || '*.json');
    }

    throw new Error(`Input path does not exist: ${input}`);
  }

  /**
   * Find files matching pattern in directory
   */
  private findFiles(dir: string, pattern: string): string[] {
    if (!this.fs || !this.path) {
      throw new Error('Node modules not loaded');
    }

    const files: string[] = [];
    const entries = this.fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = this.path.join(dir, entry.name);

      if (entry.isDirectory()) {
        files.push(...this.findFiles(fullPath, pattern));
      } else if (entry.isFile() && this.matchesPattern(entry.name, pattern)) {
        files.push(fullPath);
      }
    }

    return files;
  }

  /**
   * Simple glob pattern matching
   */
  private matchesPattern(filename: string, pattern: string): boolean {
    // Convert glob to regex
    const regex = pattern
      .replace(/\./g, '\\.')
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.');

    return new RegExp(`^${regex}$`).test(filename);
  }

  /**
   * Process a single file
   */
  private async processFile(filePath: string): Promise<{
    totalItems: number;
    successfulItems: number;
    failedItems: number;
    errors: MigrationError[];
    warnings: MigrationWarning[];
  }> {
    if (!this.fs || !this.path) {
      throw new Error('Node modules not loaded');
    }

    this.log(`Processing: ${filePath}`);

    const content = this.fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(content);

    // Handle both single items and arrays
    const items: PerseusItem[] = Array.isArray(data) ? data : [data];
    const migratedItems: AthenaItem[] = [];
    const allErrors: MigrationError[] = [];
    const allWarnings: MigrationWarning[] = [];
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      // Skip if not Perseus format
      if (!this.adapter.isPerseusFormat(item)) {
        this.log(`  Skipping item ${i}: not Perseus format`, 'warn');
        continue;
      }

      const result = this.adapter.convertItem(item);

      if (result.success && result.data) {
        migratedItems.push(result.data);
        successCount++;
      } else {
        failCount++;
      }

      // Prefix errors/warnings with item index
      allErrors.push(
        ...result.errors.map((e) => ({
          ...e,
          path: `[${i}].${e.path || ''}`,
        }))
      );
      allWarnings.push(
        ...result.warnings.map((w) => ({
          ...w,
          path: `[${i}].${w.path || ''}`,
        }))
      );
    }

    // Write output
    if (!this.options.dryRun && migratedItems.length > 0) {
      await this.writeOutput(filePath, migratedItems);
    }

    return {
      totalItems: items.length,
      successfulItems: successCount,
      failedItems: failCount,
      errors: allErrors,
      warnings: allWarnings,
    };
  }

  /**
   * Write migrated content to output directory
   */
  private async writeOutput(inputPath: string, items: AthenaItem[]): Promise<void> {
    if (!this.fs || !this.path) {
      throw new Error('Node modules not loaded');
    }

    const { output, pretty } = this.options;

    // Create output directory if needed
    if (!this.fs.existsSync(output)) {
      this.fs.mkdirSync(output, { recursive: true });
    }

    // Generate output filename
    const inputFilename = this.path.basename(inputPath);
    const outputPath = this.path.join(output, inputFilename);

    // Write file
    const content = items.length === 1
      ? JSON.stringify(items[0], null, pretty ? 2 : 0)
      : JSON.stringify(items, null, pretty ? 2 : 0);

    this.fs.writeFileSync(outputPath, content, 'utf-8');
    this.log(`  Wrote: ${outputPath}`);
  }

  /**
   * Generate migration report
   */
  private async generateReport(result: BatchMigrationResult): Promise<void> {
    if (!this.fs || !this.path) {
      throw new Error('Node modules not loaded');
    }

    const report: MigrationReport = {
      timestamp: new Date().toISOString(),
      options: this.options,
      result,
      details: [],
    };

    // Add detailed file info
    for (const errorInfo of result.errors) {
      const existing = report.details.find((d) => d.file === errorInfo.file);
      if (existing) {
        existing.errors.push(...errorInfo.errors);
      } else {
        report.details.push({
          file: errorInfo.file,
          status: 'failed',
          itemCount: 0,
          successCount: 0,
          errors: errorInfo.errors,
          warnings: [],
        });
      }
    }

    for (const warningInfo of result.warnings) {
      const existing = report.details.find((d) => d.file === warningInfo.file);
      if (existing) {
        existing.warnings.push(...warningInfo.warnings);
      } else {
        report.details.push({
          file: warningInfo.file,
          status: 'partial',
          itemCount: 0,
          successCount: 0,
          errors: [],
          warnings: warningInfo.warnings,
        });
      }
    }

    const reportPath = this.path.join(this.options.output, 'migration-report.json');
    this.fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');
    this.log(`Report written to: ${reportPath}`);
  }

  /**
   * Print summary to console
   */
  private printSummary(result: BatchMigrationResult): void {
    console.log('\n=== Migration Summary ===');
    console.log(`Status: ${result.success ? 'SUCCESS' : 'FAILED'}`);
    console.log(`Duration: ${(result.duration / 1000).toFixed(2)}s`);
    console.log(`Files: ${result.successfulFiles}/${result.totalFiles} successful`);
    console.log(`Items: ${result.successfulItems}/${result.totalItems} successful`);

    if (result.errors.length > 0) {
      console.log(`\nErrors: ${result.errors.reduce((sum, e) => sum + e.errors.length, 0)}`);
      for (const fileErrors of result.errors.slice(0, 5)) {
        console.log(`  ${fileErrors.file}:`);
        for (const error of fileErrors.errors.slice(0, 3)) {
          console.log(`    - [${error.code}] ${error.message}`);
        }
        if (fileErrors.errors.length > 3) {
          console.log(`    ... and ${fileErrors.errors.length - 3} more`);
        }
      }
      if (result.errors.length > 5) {
        console.log(`  ... and ${result.errors.length - 5} more files with errors`);
      }
    }

    if (result.warnings.length > 0) {
      console.log(`\nWarnings: ${result.warnings.reduce((sum, w) => sum + w.warnings.length, 0)}`);
    }
  }

  /**
   * Log message based on verbosity
   */
  private log(message: string, level: 'info' | 'warn' | 'error' = 'info'): void {
    if (!this.options.verbose && level === 'info') {
      return;
    }

    const prefix = {
      info: '',
      warn: '[WARN] ',
      error: '[ERROR] ',
    }[level];

    console.log(`${prefix}${message}`);
  }
}

/**
 * Run batch migration from command line
 */
export async function runBatchMigration(options: BatchMigrationOptions): Promise<BatchMigrationResult> {
  const script = new BatchMigrationScript(options);
  return script.run();
}

/**
 * CLI entry point
 */
export async function main(): Promise<void> {
  // Parse command line arguments
  const args = process.argv.slice(2);
  const options: BatchMigrationOptions = {
    input: '',
    output: '',
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    switch (arg) {
      case '--input':
      case '-i':
        options.input = args[++i];
        break;
      case '--output':
      case '-o':
        options.output = args[++i];
        break;
      case '--cdn':
        options.cdnBaseUrl = args[++i];
        break;
      case '--dry-run':
        options.dryRun = true;
        break;
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      case '--no-report':
        options.generateReport = false;
        break;
      case '--stop-on-error':
        options.continueOnError = false;
        break;
      case '--pattern':
      case '-p':
        options.pattern = args[++i];
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
    }
  }

  if (!options.input || !options.output) {
    console.error('Error: --input and --output are required');
    printHelp();
    process.exit(1);
  }

  const result = await runBatchMigration(options);
  process.exit(result.success ? 0 : 1);
}

function printHelp(): void {
  console.log(`
Athena Batch Migration Script
Converts Perseus JSON questions to Athena format.

Usage:
  npx ts-node BatchMigrationScript.ts --input <path> --output <path> [options]

Options:
  -i, --input <path>     Input directory or file (required)
  -o, --output <path>    Output directory (required)
  --cdn <url>            CDN base URL for images
  --dry-run              Don't write files, just report
  -v, --verbose          Verbose logging
  --no-report            Don't generate migration report
  --stop-on-error        Stop on first error
  -p, --pattern <glob>   File pattern to match (default: *.json)
  -h, --help             Show this help

Examples:
  npx ts-node BatchMigrationScript.ts -i ./questions -o ./migrated
  npx ts-node BatchMigrationScript.ts -i ./q.json -o ./out --verbose
`);
}

// Run if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  main().catch(console.error);
}

export default BatchMigrationScript;

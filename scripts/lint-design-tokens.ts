#!/usr/bin/env npx tsx
/**
 * Design Token Linter for CI
 *
 * Scans TSX/CSS files for hardcoded spacing values that violate the 8pt grid.
 * Run in CI to catch design system violations before merge.
 *
 * Usage:
 *   npx tsx scripts/lint-design-tokens.ts
 *   npx tsx scripts/lint-design-tokens.ts --fix  (suggests fixes)
 */

import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

const SRC_DIR = path.join(process.cwd(), 'frontend/src');
const VALID_SPACING = [0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80];

interface Violation {
  file: string;
  line: number;
  column: number;
  value: string;
  property: string;
  suggestion: string;
}

function nearestGridValue(value: number): number {
  if (value <= 4) return 4;
  if (value <= 12) return value <= 10 ? 8 : 12;
  return VALID_SPACING.reduce((prev, curr) =>
    Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
  );
}

function lintFile(filePath: string): Violation[] {
  const violations: Violation[] = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  // Patterns to check
  const patterns = [
    // CSS/inline style patterns
    { regex: /(?:padding|margin|gap):\s*['"]?(\d+)px['"]?/g, property: 'spacing' },
    { regex: /(?:padding|margin|gap):\s*(\d+)/g, property: 'spacing' },
    // Tailwind-style patterns (p-X, m-X, gap-X where X is not standard)
    { regex: /(?:^|\s)(?:p|m|gap)-\[(\d+)px\]/g, property: 'tailwind-spacing' },
    // Style object patterns
    { regex: /(?:padding|margin|gap):\s*['"](\d+)(?:px)?['"]/g, property: 'style-object' },
  ];

  lines.forEach((line, lineIndex) => {
    patterns.forEach(({ regex, property }) => {
      let match;
      const lineCopy = line; // Create a copy for iteration
      regex.lastIndex = 0; // Reset regex state

      while ((match = regex.exec(lineCopy)) !== null) {
        const value = parseInt(match[1], 10);

        // Skip valid values
        if (VALID_SPACING.includes(value)) continue;

        // Skip very large values (likely not spacing)
        if (value > 100) continue;

        // Skip values that are clearly not spacing (like z-index, opacity percentages)
        if (line.includes('z-index') || line.includes('opacity') || line.includes('duration')) continue;

        const nearest = nearestGridValue(value);
        violations.push({
          file: filePath,
          line: lineIndex + 1,
          column: match.index + 1,
          value: `${value}px`,
          property,
          suggestion: `${nearest}px`,
        });
      }
    });
  });

  return violations;
}

async function lintDesignTokens(): Promise<void> {
  console.log('=== Design Token Linter ===\n');
  console.log(`Scanning: ${SRC_DIR}\n`);

  const showFix = process.argv.includes('--fix');

  // Find all TSX and CSS files
  const files = await glob('**/*.{tsx,css,scss}', {
    cwd: SRC_DIR,
    ignore: ['**/node_modules/**', '**/build/**', '**/dist/**'],
  });

  console.log(`Found ${files.length} files to check\n`);

  let totalViolations = 0;
  const violationsByFile: Map<string, Violation[]> = new Map();

  for (const file of files) {
    const fullPath = path.join(SRC_DIR, file);
    const violations = lintFile(fullPath);

    if (violations.length > 0) {
      violationsByFile.set(file, violations);
      totalViolations += violations.length;
    }
  }

  if (totalViolations === 0) {
    console.log('✓ No design token violations found!\n');
    console.log('All spacing values follow the 8pt grid.');
    return;
  }

  console.log(`Found ${totalViolations} violations in ${violationsByFile.size} files:\n`);

  for (const [file, violations] of violationsByFile) {
    console.log(`${file}:`);
    violations.forEach((v) => {
      console.log(`  Line ${v.line}: ${v.value} (not 8pt grid)`);
      if (showFix) {
        console.log(`    → Suggest: ${v.suggestion}`);
      }
    });
    console.log('');
  }

  console.log('---');
  console.log(`Total: ${totalViolations} violations`);
  console.log('');
  console.log('Valid 8pt grid values: 0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80');
  console.log('');

  if (!showFix) {
    console.log('Run with --fix to see suggested corrections.');
  }

  // Exit with error code for CI
  process.exit(1);
}

lintDesignTokens().catch((error) => {
  console.error('Linting failed:', error);
  process.exit(1);
});

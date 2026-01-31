#!/usr/bin/env npx tsx
/**
 * Regression Detector for Feedback Loop
 *
 * Compares current screenshots against baseline to detect visual regressions.
 * Uses pixel-by-pixel comparison with configurable threshold.
 *
 * Usage:
 *   npx tsx scripts/regression-detector.ts capture-baseline
 *   npx tsx scripts/regression-detector.ts compare
 */

import { chromium, type Browser } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { PNG } from 'pngjs';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const BASELINE_DIR = path.join(process.cwd(), 'visual-baselines');
const CURRENT_DIR = path.join(process.cwd(), 'visual-current');
const DIFF_DIR = path.join(process.cwd(), 'visual-diffs');

// Pages to capture for regression testing
const PAGES_TO_CAPTURE = [
  { url: '/', name: 'home' },
  { url: '/app', name: 'app' },
  { url: '/app/assessment/dynamic', name: 'dynamic-assessment' },
];

// Threshold for pixel difference (0-1, where 0.1 = 10% different pixels triggers regression)
const DIFF_THRESHOLD = 0.01; // 1% threshold

interface RegressionResult {
  page: string;
  baselinePath: string;
  currentPath: string;
  diffPath?: string;
  diffPercent: number;
  hasRegression: boolean;
  error?: string;
}

interface ComparisonResult {
  timestamp: string;
  results: RegressionResult[];
  hasRegressions: boolean;
  summary: string;
}

/**
 * Simple pixel comparison without external dependencies
 */
function compareImages(baseline: Buffer, current: Buffer): { diffPercent: number; diffImage?: Buffer } {
  try {
    const baselinePng = PNG.sync.read(baseline);
    const currentPng = PNG.sync.read(current);

    // Check dimensions match
    if (baselinePng.width !== currentPng.width || baselinePng.height !== currentPng.height) {
      return { diffPercent: 1.0 }; // 100% different if dimensions don't match
    }

    const { width, height } = baselinePng;
    const diffPng = new PNG({ width, height });
    let diffPixels = 0;
    const totalPixels = width * height;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (width * y + x) * 4;

        const r1 = baselinePng.data[idx];
        const g1 = baselinePng.data[idx + 1];
        const b1 = baselinePng.data[idx + 2];

        const r2 = currentPng.data[idx];
        const g2 = currentPng.data[idx + 1];
        const b2 = currentPng.data[idx + 2];

        // Calculate color difference
        const colorDiff = Math.abs(r1 - r2) + Math.abs(g1 - g2) + Math.abs(b1 - b2);

        if (colorDiff > 30) { // Threshold for considering pixels different
          diffPixels++;
          // Mark different pixels in red
          diffPng.data[idx] = 255;
          diffPng.data[idx + 1] = 0;
          diffPng.data[idx + 2] = 0;
          diffPng.data[idx + 3] = 255;
        } else {
          // Keep original pixel but dimmed
          diffPng.data[idx] = Math.floor(r1 * 0.3);
          diffPng.data[idx + 1] = Math.floor(g1 * 0.3);
          diffPng.data[idx + 2] = Math.floor(b1 * 0.3);
          diffPng.data[idx + 3] = 255;
        }
      }
    }

    const diffPercent = diffPixels / totalPixels;
    const diffImage = PNG.sync.write(diffPng);

    return { diffPercent, diffImage };
  } catch (error) {
    console.error('Image comparison error:', error);
    return { diffPercent: 1.0 };
  }
}

async function captureScreenshots(browser: Browser, outputDir: string): Promise<void> {
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  for (const pageInfo of PAGES_TO_CAPTURE) {
    const page = await browser.newPage();
    const url = `${BASE_URL}${pageInfo.url}`;

    console.log(`Capturing: ${url}`);

    try {
      await page.goto(url, { timeout: 30000 });
      await page.waitForLoadState('networkidle', { timeout: 15000 });

      // Wait a bit for any animations to settle
      await page.waitForTimeout(1000);

      const screenshotPath = path.join(outputDir, `${pageInfo.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`  Saved: ${screenshotPath}`);
    } catch (error) {
      console.error(`  Failed to capture ${pageInfo.name}: ${error}`);
    }

    await page.close();
  }
}

async function captureBaseline(): Promise<void> {
  console.log('=== Capturing Baseline Screenshots ===\n');

  const browser = await chromium.launch({ headless: true });

  try {
    await captureScreenshots(browser, BASELINE_DIR);
    console.log(`\nBaseline screenshots saved to: ${BASELINE_DIR}`);
  } finally {
    await browser.close();
  }
}

async function compareWithBaseline(): Promise<ComparisonResult> {
  console.log('=== Comparing Against Baseline ===\n');

  // Check baseline exists
  if (!fs.existsSync(BASELINE_DIR)) {
    console.error('No baseline found. Run with "capture-baseline" first.');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const results: RegressionResult[] = [];

  try {
    // Capture current screenshots
    await captureScreenshots(browser, CURRENT_DIR);

    // Create diff directory
    if (!fs.existsSync(DIFF_DIR)) {
      fs.mkdirSync(DIFF_DIR, { recursive: true });
    }

    // Compare each page
    console.log('\n--- Comparing Screenshots ---\n');

    for (const pageInfo of PAGES_TO_CAPTURE) {
      const baselinePath = path.join(BASELINE_DIR, `${pageInfo.name}.png`);
      const currentPath = path.join(CURRENT_DIR, `${pageInfo.name}.png`);

      if (!fs.existsSync(baselinePath)) {
        results.push({
          page: pageInfo.name,
          baselinePath,
          currentPath,
          diffPercent: 1.0,
          hasRegression: true,
          error: 'Baseline not found',
        });
        continue;
      }

      if (!fs.existsSync(currentPath)) {
        results.push({
          page: pageInfo.name,
          baselinePath,
          currentPath,
          diffPercent: 1.0,
          hasRegression: true,
          error: 'Current screenshot not found',
        });
        continue;
      }

      const baseline = fs.readFileSync(baselinePath);
      const current = fs.readFileSync(currentPath);

      const { diffPercent, diffImage } = compareImages(baseline, current);
      const hasRegression = diffPercent > DIFF_THRESHOLD;

      let diffPath: string | undefined;
      if (hasRegression && diffImage) {
        diffPath = path.join(DIFF_DIR, `${pageInfo.name}-diff.png`);
        fs.writeFileSync(diffPath, diffImage);
      }

      const status = hasRegression ? '✗ REGRESSION' : '✓ OK';
      console.log(`${pageInfo.name}: ${status} (${(diffPercent * 100).toFixed(2)}% different)`);

      results.push({
        page: pageInfo.name,
        baselinePath,
        currentPath,
        diffPath,
        diffPercent,
        hasRegression,
      });
    }
  } finally {
    await browser.close();
  }

  const hasRegressions = results.some((r) => r.hasRegression);
  const regressionCount = results.filter((r) => r.hasRegression).length;

  const summary = hasRegressions
    ? `REGRESSIONS DETECTED: ${regressionCount}/${results.length} pages changed`
    : `All ${results.length} pages match baseline`;

  const result: ComparisonResult = {
    timestamp: new Date().toISOString(),
    results,
    hasRegressions,
    summary,
  };

  // Write results
  const resultPath = path.join(DIFF_DIR, 'regression-result.json');
  fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));

  console.log(`\n=== Summary ===`);
  console.log(`Status: ${hasRegressions ? 'REGRESSIONS FOUND' : 'NO REGRESSIONS'}`);
  console.log(`${summary}`);
  console.log(`Results saved to: ${resultPath}`);

  if (hasRegressions) {
    console.log('\nPages with regressions:');
    results
      .filter((r) => r.hasRegression)
      .forEach((r) => {
        console.log(`  - ${r.page}: ${(r.diffPercent * 100).toFixed(2)}% different`);
        if (r.diffPath) {
          console.log(`    Diff image: ${r.diffPath}`);
        }
      });
    process.exit(1);
  }

  return result;
}

// Main
const command = process.argv[2];

if (command === 'capture-baseline') {
  captureBaseline().catch((error) => {
    console.error('Failed to capture baseline:', error);
    process.exit(1);
  });
} else if (command === 'compare' || !command) {
  compareWithBaseline().catch((error) => {
    console.error('Failed to compare:', error);
    process.exit(1);
  });
} else {
  console.log('Usage:');
  console.log('  npx tsx scripts/regression-detector.ts capture-baseline');
  console.log('  npx tsx scripts/regression-detector.ts compare');
  process.exit(1);
}

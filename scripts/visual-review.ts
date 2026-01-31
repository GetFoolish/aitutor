#!/usr/bin/env npx tsx
/**
 * Visual Review Script for Feedback Loop
 *
 * Takes screenshots of key pages and validates UI against design system.
 * Used by Claude reviewer to verify visual quality.
 *
 * Usage:
 *   npx tsx scripts/visual-review.ts
 *   npx tsx scripts/visual-review.ts --url http://localhost:3000/app/assessment/dynamic
 */

import { chromium, type Page, type Browser } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const SCREENSHOT_DIR = path.join(process.cwd(), 'visual-review-screenshots');

// Design system validation rules
const DESIGN_RULES = {
  validSpacing: [0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80],
  primaryColor: '#6C63FF',
  backgroundColor: '#FFFDF5',
  borderColor: '#000000',
  borderWidth: 3,
  shadowOffset: 4,
};

interface ValidationResult {
  page: string;
  screenshot: string;
  consoleErrors: string[];
  criticalIssues: string[];
  designViolations: string[];
  passed: boolean;
}

interface ReviewResult {
  timestamp: string;
  baseUrl: string;
  pages: ValidationResult[];
  overallPassed: boolean;
  summary: string;
}

async function checkForCriticalErrors(page: Page): Promise<string[]> {
  const criticalIssues: string[] = [];

  // Check for "No answer choices available" error
  const noChoices = await page.locator('text=No answer choices available').count();
  if (noChoices > 0) {
    criticalIssues.push('CRITICAL: "No answer choices available" error found - question has no choices');
  }

  // Check for validation error
  const validationError = await page.locator('text=question data is incomplete').count();
  if (validationError > 0) {
    criticalIssues.push('CRITICAL: Question validation error - data structure malformed');
  }

  // Check for connection errors
  const connectionError = await page.locator('text=ERR_CONNECTION_REFUSED').count();
  if (connectionError > 0) {
    criticalIssues.push('CRITICAL: Connection refused - backend may not be running');
  }

  return criticalIssues;
}

async function checkDesignViolations(page: Page): Promise<string[]> {
  const violations: string[] = [];

  // Check for spacing violations (look for non-8pt-grid values)
  const spacingViolations = await page.evaluate((validSpacing) => {
    const violations: string[] = [];
    const elements = document.querySelectorAll('*');

    elements.forEach((el) => {
      const style = getComputedStyle(el);
      const props = ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
                     'marginTop', 'marginRight', 'marginBottom', 'marginLeft'];

      props.forEach((prop) => {
        const value = parseInt(style[prop as keyof CSSStyleDeclaration] as string, 10);
        if (value > 0 && !validSpacing.includes(value) && value < 100) {
          // Only flag significant violations
          if (value % 8 !== 0 && value !== 4 && value !== 12) {
            const tagName = el.tagName.toLowerCase();
            const className = el.className ? `.${el.className.split(' ')[0]}` : '';
            violations.push(`${tagName}${className}: ${prop}=${value}px (not 8pt grid)`);
          }
        }
      });
    });

    return violations.slice(0, 10); // Limit to first 10
  }, DESIGN_RULES.validSpacing);

  violations.push(...spacingViolations);

  // Check for blur shadows (should be solid offsets)
  const blurShadowViolations = await page.evaluate(() => {
    const violations: string[] = [];
    const elements = document.querySelectorAll('*');

    elements.forEach((el) => {
      const style = getComputedStyle(el);
      const shadow = style.boxShadow;

      // Check for blur shadows (neo-brutalism uses solid offsets)
      if (shadow && shadow !== 'none') {
        // Parse shadow: offset-x offset-y blur spread color
        const match = shadow.match(/rgba?\([^)]+\)\s*(\d+)px\s*(\d+)px\s*(\d+)px/);
        if (match && parseInt(match[3], 10) > 0) {
          // Has blur value > 0
          const tagName = el.tagName.toLowerCase();
          violations.push(`${tagName}: has blur shadow (should be solid offset)`);
        }
      }
    });

    return violations.slice(0, 5);
  });

  violations.push(...blurShadowViolations);

  return violations;
}

async function validatePage(browser: Browser, url: string, name: string): Promise<ValidationResult> {
  const page = await browser.newPage();
  const consoleErrors: string[] = [];

  // Collect console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (error) => {
    consoleErrors.push(error.message);
  });

  console.log(`Validating: ${url}`);

  try {
    await page.goto(url, { timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 });
  } catch (error) {
    await page.close();
    return {
      page: name,
      screenshot: '',
      consoleErrors: [`Failed to load page: ${error}`],
      criticalIssues: ['Page failed to load'],
      designViolations: [],
      passed: false,
    };
  }

  // Take screenshot
  const screenshotPath = path.join(SCREENSHOT_DIR, `${name.replace(/\//g, '-')}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  // Check for critical issues
  const criticalIssues = await checkForCriticalErrors(page);

  // Check design violations
  const designViolations = await checkDesignViolations(page);

  await page.close();

  // Filter console errors (remove known noisy ones)
  const filteredErrors = consoleErrors.filter(
    (error) =>
      !error.includes('ResizeObserver loop') &&
      !error.includes('Failed to load resource') &&
      !error.includes('favicon.ico')
  );

  const passed = criticalIssues.length === 0 && filteredErrors.length === 0;

  return {
    page: name,
    screenshot: screenshotPath,
    consoleErrors: filteredErrors,
    criticalIssues,
    designViolations,
    passed,
  };
}

async function runVisualReview(): Promise<ReviewResult> {
  // Create screenshot directory
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const results: ValidationResult[] = [];

  // Pages to validate
  const pagesToCheck = [
    { url: `${BASE_URL}`, name: 'home' },
    { url: `${BASE_URL}/app`, name: 'app' },
    { url: `${BASE_URL}/app/assessment/dynamic`, name: 'dynamic-assessment' },
  ];

  // Add custom URL from args
  const customUrl = process.argv.find((arg) => arg.startsWith('--url='));
  if (customUrl) {
    const url = customUrl.split('=')[1];
    pagesToCheck.push({ url, name: 'custom' });
  }

  for (const pageInfo of pagesToCheck) {
    const result = await validatePage(browser, pageInfo.url, pageInfo.name);
    results.push(result);
  }

  await browser.close();

  const overallPassed = results.every((r) => r.passed);
  const criticalCount = results.reduce((sum, r) => sum + r.criticalIssues.length, 0);
  const errorCount = results.reduce((sum, r) => sum + r.consoleErrors.length, 0);
  const violationCount = results.reduce((sum, r) => sum + r.designViolations.length, 0);

  const summary = overallPassed
    ? 'All visual checks passed'
    : `FAILED: ${criticalCount} critical issues, ${errorCount} console errors, ${violationCount} design violations`;

  const reviewResult: ReviewResult = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    pages: results,
    overallPassed,
    summary,
  };

  // Write results to file
  const resultPath = path.join(SCREENSHOT_DIR, 'review-result.json');
  fs.writeFileSync(resultPath, JSON.stringify(reviewResult, null, 2));

  console.log('\n=== Visual Review Results ===');
  console.log(`Status: ${overallPassed ? 'PASSED' : 'FAILED'}`);
  console.log(`Summary: ${summary}`);
  console.log(`Screenshots saved to: ${SCREENSHOT_DIR}`);
  console.log(`Full results: ${resultPath}`);

  if (!overallPassed) {
    console.log('\n--- Issues Found ---');
    for (const result of results) {
      if (!result.passed) {
        console.log(`\n${result.page}:`);
        if (result.criticalIssues.length > 0) {
          console.log('  Critical:', result.criticalIssues.join(', '));
        }
        if (result.consoleErrors.length > 0) {
          console.log('  Console Errors:', result.consoleErrors.join(', '));
        }
        if (result.designViolations.length > 0) {
          console.log('  Design Violations:', result.designViolations.slice(0, 5).join(', '));
        }
      }
    }
    process.exit(1);
  }

  return reviewResult;
}

// Run if called directly
runVisualReview().catch((error) => {
  console.error('Visual review failed:', error);
  process.exit(1);
});

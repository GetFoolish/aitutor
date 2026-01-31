#!/usr/bin/env npx tsx
/**
 * Pre-flight Check Script for Feedback Loop
 *
 * Validates that all required services are running before starting
 * the feedback loop. Blocks the loop if basics fail.
 *
 * Usage:
 *   npx tsx scripts/preflight-check.ts
 */

import { chromium } from 'playwright';

const BACKEND_URL = process.env.VITE_DASH_API_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const CONTENT_API_URL = process.env.VITE_CONTENT_API_URL || 'http://localhost:8001';

interface CheckResult {
  name: string;
  passed: boolean;
  message: string;
  details?: any;
}

interface PreflightResult {
  timestamp: string;
  allPassed: boolean;
  checks: CheckResult[];
}

async function checkBackendHealth(): Promise<CheckResult> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (response.ok) {
      return {
        name: 'backend_health',
        passed: true,
        message: `Backend healthy at ${BACKEND_URL}`,
      };
    }

    return {
      name: 'backend_health',
      passed: false,
      message: `Backend returned ${response.status}`,
    };
  } catch (error: any) {
    return {
      name: 'backend_health',
      passed: false,
      message: `Backend unreachable: ${error.message}`,
    };
  }
}

async function checkContentApiHealth(): Promise<CheckResult> {
  try {
    const response = await fetch(`${CONTENT_API_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (response.ok) {
      return {
        name: 'content_api_health',
        passed: true,
        message: `Content API healthy at ${CONTENT_API_URL}`,
      };
    }

    return {
      name: 'content_api_health',
      passed: false,
      message: `Content API returned ${response.status}`,
    };
  } catch (error: any) {
    // Content API is optional for some flows
    return {
      name: 'content_api_health',
      passed: true, // Soft fail
      message: `Content API not available (optional): ${error.message}`,
    };
  }
}

async function checkFrontendLoads(): Promise<CheckResult> {
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();

    const response = await page.goto(FRONTEND_URL, {
      timeout: 15000,
      waitUntil: 'domcontentloaded'
    });

    if (!response || !response.ok()) {
      await browser.close();
      return {
        name: 'frontend_loads',
        passed: false,
        message: `Frontend returned ${response?.status() || 'no response'}`,
      };
    }

    // Check that it's not an error page
    const title = await page.title();
    const bodyText = await page.locator('body').innerText();

    if (bodyText.includes('Cannot GET') || bodyText.includes('404')) {
      await browser.close();
      return {
        name: 'frontend_loads',
        passed: false,
        message: 'Frontend returned 404 or error page',
      };
    }

    await browser.close();
    return {
      name: 'frontend_loads',
      passed: true,
      message: `Frontend loaded successfully: "${title}"`,
    };
  } catch (error: any) {
    await browser.close();
    return {
      name: 'frontend_loads',
      passed: false,
      message: `Frontend failed to load: ${error.message}`,
    };
  }
}

async function checkScreenshotCapability(): Promise<CheckResult> {
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();
    await page.goto(FRONTEND_URL, { timeout: 15000 });

    // Try to take a screenshot
    const screenshot = await page.screenshot();

    if (!screenshot || screenshot.length === 0) {
      await browser.close();
      return {
        name: 'screenshot_works',
        passed: false,
        message: 'Screenshot capture returned empty buffer',
      };
    }

    await browser.close();
    return {
      name: 'screenshot_works',
      passed: true,
      message: `Screenshot capture works (${screenshot.length} bytes)`,
    };
  } catch (error: any) {
    await browser.close();
    return {
      name: 'screenshot_works',
      passed: false,
      message: `Screenshot capture failed: ${error.message}`,
    };
  }
}

async function checkConsoleErrors(): Promise<CheckResult> {
  const browser = await chromium.launch({ headless: true });
  const consoleErrors: string[] = [];

  try {
    const page = await browser.newPage();

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (error) => {
      consoleErrors.push(error.message);
    });

    await page.goto(FRONTEND_URL, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    await browser.close();

    // Filter known noisy errors
    const filteredErrors = consoleErrors.filter(
      (error) =>
        !error.includes('ResizeObserver loop') &&
        !error.includes('favicon.ico') &&
        !error.includes('Failed to load resource')
    );

    if (filteredErrors.length > 0) {
      return {
        name: 'no_console_errors',
        passed: false,
        message: `${filteredErrors.length} console errors on page load`,
        details: filteredErrors.slice(0, 5),
      };
    }

    return {
      name: 'no_console_errors',
      passed: true,
      message: 'No console errors on page load',
    };
  } catch (error: any) {
    await browser.close();
    return {
      name: 'no_console_errors',
      passed: false,
      message: `Console check failed: ${error.message}`,
    };
  }
}

async function checkDynamicAssessmentRoute(): Promise<CheckResult> {
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();

    await page.goto(`${FRONTEND_URL}/app/assessment/dynamic`, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // Check for subject picker or loading state (not error)
    const hasSubjectPicker = await page.locator('button:has-text("math"), button:has-text("Math")').count();
    const hasLoading = await page.locator('text=Loading').count();
    const hasError = await page.locator('text=ERR_CONNECTION_REFUSED').count();

    await browser.close();

    if (hasError > 0) {
      return {
        name: 'dynamic_assessment_route',
        passed: false,
        message: 'Dynamic assessment page shows connection error',
      };
    }

    if (hasSubjectPicker > 0 || hasLoading > 0) {
      return {
        name: 'dynamic_assessment_route',
        passed: true,
        message: 'Dynamic assessment page loads correctly',
      };
    }

    return {
      name: 'dynamic_assessment_route',
      passed: true, // Soft pass if we can't determine state
      message: 'Dynamic assessment page loaded (state unknown)',
    };
  } catch (error: any) {
    await browser.close();
    return {
      name: 'dynamic_assessment_route',
      passed: false,
      message: `Dynamic assessment route failed: ${error.message}`,
    };
  }
}

async function runPreflightChecks(): Promise<PreflightResult> {
  console.log('=== Pre-flight Checks ===\n');

  const checks: CheckResult[] = [];

  // Run checks in order
  console.log('1. Checking backend health...');
  checks.push(await checkBackendHealth());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '✗'} ${checks[checks.length - 1].message}`);

  console.log('2. Checking content API health...');
  checks.push(await checkContentApiHealth());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '○'} ${checks[checks.length - 1].message}`);

  console.log('3. Checking frontend loads...');
  checks.push(await checkFrontendLoads());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '✗'} ${checks[checks.length - 1].message}`);

  console.log('4. Checking screenshot capability...');
  checks.push(await checkScreenshotCapability());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '✗'} ${checks[checks.length - 1].message}`);

  console.log('5. Checking for console errors...');
  checks.push(await checkConsoleErrors());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '✗'} ${checks[checks.length - 1].message}`);
  if (checks[checks.length - 1].details) {
    console.log(`      Errors: ${JSON.stringify(checks[checks.length - 1].details)}`);
  }

  console.log('6. Checking dynamic assessment route...');
  checks.push(await checkDynamicAssessmentRoute());
  console.log(`   ${checks[checks.length - 1].passed ? '✓' : '✗'} ${checks[checks.length - 1].message}`);

  // Critical checks that must pass
  const criticalChecks = ['backend_health', 'frontend_loads', 'screenshot_works'];
  const criticalPassed = checks
    .filter((c) => criticalChecks.includes(c.name))
    .every((c) => c.passed);

  const allPassed = checks.every((c) => c.passed);

  const result: PreflightResult = {
    timestamp: new Date().toISOString(),
    allPassed: criticalPassed, // Only fail on critical checks
    checks,
  };

  console.log('\n=== Summary ===');
  console.log(`Critical checks: ${criticalPassed ? 'PASSED' : 'FAILED'}`);
  console.log(`All checks: ${allPassed ? 'PASSED' : 'SOME WARNINGS'}`);

  if (!criticalPassed) {
    console.log('\n❌ PRE-FLIGHT FAILED');
    console.log('Fix these issues before starting the feedback loop:');
    checks
      .filter((c) => !c.passed && criticalChecks.includes(c.name))
      .forEach((c) => console.log(`  - ${c.name}: ${c.message}`));
    process.exit(1);
  }

  console.log('\n✓ PRE-FLIGHT PASSED - Ready for feedback loop');
  return result;
}

// Run if called directly
runPreflightChecks().catch((error) => {
  console.error('Pre-flight checks failed:', error);
  process.exit(1);
});

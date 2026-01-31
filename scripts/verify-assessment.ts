#!/usr/bin/env npx tsx
/**
 * Visual Assessment Verification Script
 *
 * This script uses Playwright to:
 * 1. Open the dynamic assessment page
 * 2. Take screenshots
 * 3. Verify answer choices are visible
 * 4. Check for critical errors
 * 5. Return structured pass/fail result
 *
 * Usage: npx tsx scripts/verify-assessment.ts
 */

import { chromium, Browser, Page } from 'playwright';

interface VerificationResult {
  passed: boolean;
  checks: {
    name: string;
    passed: boolean;
    details?: string;
  }[];
  screenshots?: string[];
  errors: string[];
}

async function verifyAssessment(): Promise<VerificationResult> {
  const result: VerificationResult = {
    passed: true,
    checks: [],
    errors: [],
  };

  let browser: Browser | null = null;

  try {
    // Launch browser
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Collect console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Check 1: Frontend loads
    console.log('Check 1: Frontend loads...');
    try {
      await page.goto('http://localhost:3000/app/assessment/dynamic', { timeout: 15000 });
      result.checks.push({ name: 'frontend_loads', passed: true });
    } catch (e) {
      result.checks.push({ name: 'frontend_loads', passed: false, details: String(e) });
      result.passed = false;
      return result;
    }

    // Check 2: Subject picker visible
    console.log('Check 2: Subject picker visible...');
    const subjectButtons = await page.locator('button:has-text("math"), button:has-text("science"), button:has-text("reading")').count();
    result.checks.push({
      name: 'subject_picker_visible',
      passed: subjectButtons >= 3,
      details: `Found ${subjectButtons} subject buttons`
    });
    if (subjectButtons < 3) result.passed = false;

    // Click a subject to start assessment
    console.log('Starting math assessment...');
    await page.locator('button:has-text("math")').first().click();

    // Wait for questions to generate (loading screen)
    console.log('Waiting for questions to generate (loading screen)...');
    await page.waitForTimeout(25000);

    // Now click "let's go" button which appears after loading
    console.log('Looking for let\'s go button...');
    try {
      await page.waitForSelector('text=let\'s go!', { timeout: 10000 });
      await page.click('text=let\'s go!');
      console.log('Clicked let\'s go button!');
    } catch (e) {
      console.log('Could not find let\'s go button:', e);
    }

    // Wait for question to render
    console.log('Waiting for question to render...');
    await page.waitForTimeout(5000);

    // Check 3: No "No answer choices available" error
    console.log('Check 3: No "No answer choices" error...');
    const noChoicesError = await page.locator('text=No answer choices available').count();
    result.checks.push({
      name: 'no_answer_choices_error',
      passed: noChoicesError === 0,
      details: noChoicesError > 0 ? 'CRITICAL: "No answer choices available" visible!' : 'No error found'
    });
    if (noChoicesError > 0) {
      result.passed = false;
      result.errors.push('CRITICAL: Radio widget has no choices - check question_generator.py');
    }

    // Check 4: No "question data is incomplete" error
    console.log('Check 4: No "question data incomplete" error...');
    const incompleteError = await page.locator('text=question data is incomplete').count();
    result.checks.push({
      name: 'no_incomplete_data_error',
      passed: incompleteError === 0,
      details: incompleteError > 0 ? 'CRITICAL: Question data incomplete!' : 'No error found'
    });
    if (incompleteError > 0) {
      result.passed = false;
      result.errors.push('CRITICAL: Question data incomplete - check API response');
    }

    // Check 5: Answer inputs visible (radio buttons, text inputs, etc.)
    console.log('Check 5: Answer inputs visible...');
    const answerInputs = await page.locator(
      'input[type="radio"], input[type="text"], .perseus-radio-option, .perseus-widget-radio, button[class*="choice"]'
    ).count();
    result.checks.push({
      name: 'answer_inputs_visible',
      passed: answerInputs > 0,
      details: `Found ${answerInputs} answer input elements`
    });
    if (answerInputs === 0) {
      result.passed = false;
      result.errors.push('No answer inputs found - user cannot interact');
    }

    // Check 6: Submit button exists
    console.log('Check 6: Submit button exists...');
    const submitBtn = await page.locator('button:has-text("submit"), button:has-text("check"), button:has-text("next")').count();
    result.checks.push({
      name: 'submit_button_exists',
      passed: submitBtn > 0,
      details: `Found ${submitBtn} submit/check buttons`
    });

    // Check 7: Console errors
    console.log('Check 7: Console errors...');
    const criticalConsoleErrors = consoleErrors.filter(e =>
      !e.includes('DevTools') && !e.includes('Extension') && !e.includes('favicon')
    );
    result.checks.push({
      name: 'no_console_errors',
      passed: criticalConsoleErrors.length === 0,
      details: criticalConsoleErrors.length > 0
        ? `${criticalConsoleErrors.length} errors: ${criticalConsoleErrors[0]?.slice(0, 100)}...`
        : 'No critical console errors'
    });

    // Take screenshot
    console.log('Taking screenshot...');
    const screenshotPath = `/tmp/assessment-verification-${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.screenshots = [screenshotPath];

    console.log(`Screenshot saved: ${screenshotPath}`);

  } catch (error) {
    result.passed = false;
    result.errors.push(`Verification failed: ${error}`);
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  return result;
}

// Main execution
async function main() {
  console.log('='.repeat(60));
  console.log('VISUAL ASSESSMENT VERIFICATION');
  console.log('='.repeat(60));
  console.log('');

  const result = await verifyAssessment();

  console.log('');
  console.log('='.repeat(60));
  console.log('RESULTS');
  console.log('='.repeat(60));
  console.log('');

  for (const check of result.checks) {
    const status = check.passed ? '✓ PASS' : '✗ FAIL';
    console.log(`${status}: ${check.name}`);
    if (check.details) {
      console.log(`       ${check.details}`);
    }
  }

  console.log('');

  if (result.errors.length > 0) {
    console.log('ERRORS:');
    for (const err of result.errors) {
      console.log(`  - ${err}`);
    }
    console.log('');
  }

  if (result.screenshots?.length) {
    console.log(`Screenshots: ${result.screenshots.join(', ')}`);
  }

  console.log('');
  console.log(result.passed ? '✅ VERIFICATION PASSED' : '❌ VERIFICATION FAILED');
  console.log('');

  process.exit(result.passed ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});

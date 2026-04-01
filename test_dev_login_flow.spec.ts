import { test, expect } from '@playwright/test';

test.describe('Dev Login Flow - Real Browser Testing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173/app/dev-login');
  });

  test('should load dev-login page', async ({ page }) => {
    await expect(page.locator('text=QUICK TEST LOGIN')).toBeVisible();
    await expect(page.locator('button:has-text("Science")')).toBeVisible();
  });

  test('should navigate to assessment after selecting subject and grade', async ({ page }) => {
    // Click Science
    await page.locator('button:has-text("Science")').click();

    // Click Grade 8
    await page.locator('button:has-text("Grade 8")').click();

    // Should navigate to assessment
    await page.waitForURL('**/app/assessment/**', { timeout: 10000 });

    expect(page.url()).toContain('/app/assessment');
  });

  test('should show error if backend is down', async ({ page }) => {
    // Click Science
    await page.locator('button:has-text("Science")').click();

    // Block auth API
    await page.route('**/auth/dev-login', route => route.abort());

    // Click Grade 8
    await page.locator('button:has-text("Grade 8")').click();

    // Should show error message
    await expect(page.locator('text=/error|failed|unavailable/i')).toBeVisible({ timeout: 5000 });
  });

  test('BUG CHECK: empty answer submission', async ({ page }) => {
    // Navigate through dev-login
    await page.locator('button:has-text("Science")').click();
    await page.locator('button:has-text("Grade 8")').click();

    // Wait for assessment to load
    await page.waitForURL('**/app/assessment/**', { timeout: 10000 });
    await page.waitForSelector('button:has-text("Submit")', { timeout: 15000 });

    // Try to submit without selecting an answer
    await page.locator('button:has-text("Submit")').click();

    // Should NOT advance to next question
    // Should show validation error
    await page.waitForTimeout(2000);

    const currentURL = page.url();
    console.log('URL after empty submit:', currentURL);

    // Check for validation message or that submit button is still visible
    const submitStillVisible = await page.locator('button:has-text("Submit")').isVisible();
    expect(submitStillVisible).toBe(true); // Should not have advanced
  });

  test('should show loading state during question generation', async ({ page }) => {
    await page.locator('button:has-text("Math")').click();
    await page.locator('button:has-text("Grade 5")').click();

    // Check for loading indicator
    const hasLoadingIndicator = await page.locator('text=/loading|generating|wait/i').isVisible().catch(() => false);
    console.log('Has loading indicator:', hasLoadingIndicator);
  });
});

test.describe('Console Errors', () => {
  test('should not have console errors on dev-login page', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('http://localhost:5173/app/dev-login');
    await page.waitForTimeout(2000);

    console.log('Console errors found:', consoleErrors);
    expect(consoleErrors.length).toBe(0);
  });
});

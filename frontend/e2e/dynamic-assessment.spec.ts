import { test, expect } from '@playwright/test';

test.describe('dynamic assessment (smoke)', () => {
  for (const subject of ['math', 'science', 'reading'] as const) {
    test(`can start ${subject} without auth and load first question`, async ({ page }) => {
      // Ensure each run starts from a clean session (subject picker should be visible).
      await page.addInitScript(() => {
        try {
          sessionStorage.clear();
          localStorage.clear();
        } catch {
          // ignore
        }
      });

      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // This route intentionally supports a no-auth local flow.
      await page.goto('/app/assessment/dynamic');

      // With a clean session we might see either the subject picker, or the
      // "could not load" fallback UI. Both expose subject buttons — so click
      // the chosen subject directly.
      await page.getByRole('button', { name: new RegExp(subject, 'i') }).first().click();

      // Assessment generation can take ~10–20s, so wait for the intro CTA.
      const letsGo = page.getByRole('button', { name: /let's go!/i });
      await expect(letsGo).toBeVisible({ timeout: 30_000 });
      await letsGo.click();

      // We should see the assessment chrome (progress header).
      await expect(page.getByText(/question\s+1\s+of/i)).toBeVisible();

      // CRITICAL: Verify no "No answer choices available" error
      // This catches malformed questions with empty choices arrays
      const noChoicesError = page.getByText('No answer choices available');
      await expect(noChoicesError).toHaveCount(0);

      // CRITICAL: Verify no validation error message
      const validationError = page.getByText('question data is incomplete');
      await expect(validationError).toHaveCount(0);

      // Verify question content container exists and has content
      const questionContainer = page.locator('#question-content-container');
      await expect(questionContainer).toBeVisible({ timeout: 10_000 });

      // Verify there's at least one interactive element (radio, input, dropdown, etc.)
      // This ensures the question actually rendered with answer options
      const interactiveElements = page.locator(
        '.perseus-widget-radio, ' +
        '.perseus-widget-numeric-input, ' +
        '.perseus-widget-dropdown, ' +
        '.perseus-widget-orderer, ' +
        'input[type="radio"], ' +
        'input[type="text"], ' +
        'input[type="number"], ' +
        'select'
      );
      const elementCount = await interactiveElements.count();
      expect(elementCount, 'Expected at least one interactive answer element').toBeGreaterThan(0);

      // Sanity check that we didn't land on a generic connection refused error page.
      await expect(page.getByText('ERR_CONNECTION_REFUSED')).toHaveCount(0);

      // If we got here, keep console errors as a strict signal (except known noisy ones).
      const filtered = consoleErrors.filter(
        (line) =>
          !line.includes('ResizeObserver loop limit exceeded') &&
          !line.includes('Failed to load resource')
      );
      expect(filtered, `Console errors seen during ${subject} flow`).toEqual([]);
    });
  }
});

test.describe('answer flow (functional)', () => {
  test('user can select an answer and submit', async ({ page }) => {
    await page.addInitScript(() => {
      try {
        sessionStorage.clear();
        localStorage.clear();
      } catch {
        // ignore
      }
    });

    await page.goto('/app/assessment/dynamic');

    // Start a math assessment
    await page.getByRole('button', { name: /math/i }).first().click();

    const letsGo = page.getByRole('button', { name: /let's go!/i });
    await expect(letsGo).toBeVisible({ timeout: 30_000 });
    await letsGo.click();

    // Wait for question to load
    await expect(page.getByText(/question\s+1\s+of/i)).toBeVisible();

    // Verify no error states
    await expect(page.getByText('No answer choices available')).toHaveCount(0);
    await expect(page.getByText('question data is incomplete')).toHaveCount(0);

    // Find and click an answer option (radio button or any clickable choice)
    const answerOptions = page.locator(
      '.perseus-radio-option, ' +
      '[data-testid="radio-option"], ' +
      '.perseus-widget-radio li, ' +
      'input[type="radio"]'
    );

    // Wait for at least one option to be present
    const firstOption = answerOptions.first();
    await expect(firstOption).toBeVisible({ timeout: 10_000 });

    // Click the first answer option
    await firstOption.click();

    // Verify submit button is enabled and click it
    const submitButton = page.getByRole('button', { name: /submit/i });
    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    // Verify feedback appears (either correct or incorrect)
    const feedback = page.locator('.fixed').filter({ hasText: /correct|not quite/i });
    await expect(feedback).toBeVisible({ timeout: 5_000 });
  });
});

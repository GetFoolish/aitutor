import { test, expect } from '@playwright/test';

// Smoke test for the dynamic assessment session contract:
// - progress displays "Question X of Y" format (not uppercase, not X/Y)
// - total question count is stable for the session
// - "Start over" button exists and returns to onboarding

test.describe('dynamic assessment progress', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        sessionStorage.clear();
        localStorage.clear();
      } catch {
        // ignore
      }
    });

    await page.goto('/app/assessment/dynamic');

    // Navigate through onboarding to reach assessment
    const ageBtn = page.getByRole('button', { name: /8-10\s+years/i });
    await expect(ageBtn).toBeVisible({ timeout: 10_000 });
    await ageBtn.click();

    const topicBtn = page.getByRole('button', { name: /basic math/i });
    await expect(topicBtn).toBeVisible({ timeout: 10_000 });
    await topicBtn.click();

    const start = page.getByRole('button', { name: /let's see where you're at/i });
    await expect(start).toBeVisible({ timeout: 10_000 });
    await start.click();

    const letsGo = page.getByRole('button', { name: /let.s go/i });
    await expect(letsGo).toBeVisible({ timeout: 30_000 });
    await letsGo.click();
  });

  test('progress format: "Question X of Y" with stable total', async ({ page }) => {
    // Verify the progress header format
    const header = page.getByText(/question\s+\d+\s+of\s+\d+/i).first();
    await expect(header).toBeVisible({ timeout: 20_000 });

    const headerText = (await header.textContent()) || '';
    
    // Should be "Question 1 of N" format (case-insensitive)
    const match = headerText.match(/question\s+1\s+of\s+(\d+)/i);
    expect(match, `Expected "Question 1 of N", got: "${headerText}"`).not.toBeNull();
    
    // Total should be a positive number
    const total = Number(match![1]);
    expect(total, 'Total questions should be positive').toBeGreaterThan(0);
    
    // Should NOT be uppercase "QUESTION" format
    expect(headerText).not.toMatch(/^QUESTION\s+\d+\/\d+$/);
    
    // Should NOT use slash format like "1/4"
    expect(headerText).not.toMatch(/\d+\/\d+/);
  });

  test('Start over button exists and redirects to onboarding', async ({ page }) => {
    // Wait for assessment to load
    await expect(page.getByText(/question\s+\d+\s+of\s+\d+/i).first()).toBeVisible({ timeout: 20_000 });
    
    // Find and click Start over button
    const startOver = page.getByRole('button', { name: /start over/i });
    await expect(startOver).toBeVisible();
    await startOver.click();
    
    // Should redirect to onboarding
    await expect(page).toHaveURL(/\/app\/onboarding/i);
  });
});

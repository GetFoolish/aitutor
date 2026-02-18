import { defineConfig } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const jsonReport = process.env.PLAYWRIGHT_JSON_REPORT || '../artifacts/harness/playwright-report.json';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['list'],
    ['json', { outputFile: jsonReport }],
  ],
  use: {
    baseURL,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'off',
    video: 'off',
    viewport: { width: 1440, height: 900 },
  },
});

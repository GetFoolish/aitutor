import { defineConfig } from '@playwright/test';

// Minimal E2E config.
// This suite assumes you already started:
//   - backend: ./run_tutor.sh (DASH API on http://localhost:8000)
//   - frontend: cd frontend && npm run dev
//
// Note: our Vite dev server is pinned to port 3000 (see vite.config.ts).
// If you run it elsewhere, set E2E_BASE_URL accordingly.
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  reporter: [['list']],
});

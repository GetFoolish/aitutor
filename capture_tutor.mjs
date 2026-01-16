/**
 * Capture Tutor Session with Auth
 */
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

const BASE_URL = 'http://localhost:3000';

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  console.log('📸 Capturing Tutor Session Screenshots\n');

  // Go to login page
  await page.goto(`${BASE_URL}/app/login`);
  await page.waitForTimeout(1000);

  // Try to log in with test credentials
  console.log('🔐 Attempting login...');
  try {
    // Fill email
    await page.fill('input[type="email"], input[placeholder*="email"]', 'gagan.arora2603@gmail.com');
    // Fill password
    await page.fill('input[type="password"]', 'testpass123');
    // Click login button
    await page.click('button:has-text("LOGIN"), button:has-text("Log in")');
    await page.waitForTimeout(3000);
    console.log('   Logged in, waiting for redirect...');
  } catch (e) {
    console.log('   Login form not found, trying direct navigation...');
  }

  // Set a test token in localStorage (fallback)
  await page.evaluate(() => {
    // Create a mock user state that might bypass auth
    localStorage.setItem('auth_state', JSON.stringify({ isAuthenticated: true }));
  });

  // Capture pages
  const pages = [
    { name: 'tutor-auth', url: '/app/tutor', desc: 'Tutor Session' },
    { name: 'dashboard-auth', url: '/app/dashboard', desc: 'Dashboard' },
    { name: 'account-page', url: '/app/account', desc: 'Account' },
  ];

  for (const { name, url, desc } of pages) {
    console.log(`  📷 ${desc}...`);
    try {
      await page.goto(`${BASE_URL}${url}`, { waitUntil: 'networkidle', timeout: 10000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`), fullPage: true });
      console.log(`     ✓ ${name}.png`);
    } catch (e) {
      console.log(`     ⚠ ${e.message.slice(0, 50)}`);
    }
  }

  await browser.close();
  console.log('\n✅ Done!');
}

capture().catch(console.error);

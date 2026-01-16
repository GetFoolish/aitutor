import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  // Inject fake auth token to bypass authentication
  await page.goto('http://localhost:3001');

  await page.evaluate(() => {
    // Set fake auth state
    const fakeUser = {
      user_id: 'demo_user_123',
      email: 'demo@teachr.live',
      name: 'Demo Student',
      grade: 5,
      age: 11
    };
    const fakeToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vX3VzZXJfMTIzIiwiZW1haWwiOiJkZW1vQHRlYWNoci5saXZlIn0.fake';

    localStorage.setItem('auth_token', fakeToken);
    localStorage.setItem('teachr_token', fakeToken);
    localStorage.setItem('user', JSON.stringify(fakeUser));
    localStorage.setItem('isAuthenticated', 'true');
    sessionStorage.setItem('auth_token', fakeToken);
  });

  // Navigate to app routes
  const routes = [
    { url: 'http://localhost:3001/app/tutor', name: 'tutor-session' },
    { url: 'http://localhost:3001/app/dashboard', name: 'dashboard' },
    { url: 'http://localhost:3001/app', name: 'main-app' },
  ];

  for (const route of routes) {
    console.log(`Capturing ${route.name}...`);
    try {
      await page.goto(route.url, { waitUntil: 'networkidle', timeout: 10000 });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `screenshots/${route.name}.png`, fullPage: true });
      console.log(`  ✓ ${route.name}.png`);
    } catch (e) {
      console.log(`  ✗ ${e.message.slice(0, 50)}`);
    }
  }

  await browser.close();
}

capture();

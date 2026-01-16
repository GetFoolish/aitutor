/**
 * Capture Authenticated Screenshots of AI Tutor Frontend
 * Uses test user to access protected pages
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:3000';
const AUTH_API = 'http://localhost:8003';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function captureAuthenticatedScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });
  const page = await context.newPage();

  console.log('\n📸 Capturing Authenticated AI Tutor Screenshots\n');

  try {
    // First get a test token
    console.log('🔐 Getting test auth token...');
    const testEmail = 'test@teachr.live';
    const testPassword = 'testpassword123';

    // Try to sign up or login
    let token = null;
    try {
      // Try signup first
      const signupResp = await fetch(`${AUTH_API}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: testEmail, password: testPassword })
      });
      const signupData = await signupResp.json();
      token = signupData.access_token;
    } catch (e) {}

    if (!token) {
      // Try login
      const loginResp = await fetch(`${AUTH_API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: testEmail, password: testPassword })
      });
      const loginData = await loginResp.json();
      token = loginData.access_token;
    }

    if (token) {
      console.log('   ✓ Got auth token');
      // Set token in localStorage
      await page.goto(`${BASE_URL}/app`);
      await page.evaluate((t) => {
        localStorage.setItem('auth_token', t);
        localStorage.setItem('teachr_token', t);
      }, token);
    } else {
      console.log('   ⚠ No token, trying with existing session...');
    }

    // Navigate to each authenticated page
    const pages = [
      { name: 'app-main', url: '/app', desc: 'Main App (After Login)' },
      { name: 'app-tutor', url: '/app/tutor', desc: 'Tutor Session (007-010)' },
      { name: 'app-dashboard', url: '/app/dashboard', desc: 'Student Dashboard' },
      { name: 'app-history', url: '/app/history', desc: 'Practice History (001)' },
      { name: 'app-progress', url: '/app/progress', desc: 'Progress/Streak (003)' },
      { name: 'app-settings', url: '/app/settings', desc: 'Settings' },
      { name: 'app-profile', url: '/app/profile', desc: 'Profile' },
      { name: 'app-onboarding', url: '/app/onboarding', desc: 'Onboarding' },
      { name: 'app-account', url: '/app/account', desc: 'Account Page' },
      { name: 'app-pricing', url: '/app/pricing', desc: 'Pricing Page' },
    ];

    for (const { name, url, desc } of pages) {
      try {
        console.log(`  📷 ${desc} (${url})...`);
        await page.goto(`${BASE_URL}${url}`, {
          waitUntil: 'networkidle',
          timeout: 15000
        });
        await page.waitForTimeout(1000);

        const filepath = path.join(SCREENSHOT_DIR, `${name}.png`);
        await page.screenshot({ path: filepath, fullPage: true });
        console.log(`     ✓ Saved: ${name}.png`);
      } catch (err) {
        console.log(`     ⚠ ${err.message.split('\n')[0].slice(0, 60)}`);
      }
    }

    // Also capture the marketing landing page
    console.log('\n  📷 Marketing Pages...');
    const marketingPages = [
      { name: 'landing-main', url: '/', desc: 'Landing Page' },
      { name: 'landing-features', url: '/features', desc: 'Features' },
      { name: 'landing-comingsoon', url: '/comingsoon', desc: 'Coming Soon' },
    ];

    for (const { name, url, desc } of marketingPages) {
      try {
        console.log(`  📷 ${desc} (${url})...`);
        await page.goto(`${BASE_URL}${url}`, {
          waitUntil: 'networkidle',
          timeout: 10000
        });
        await page.waitForTimeout(500);
        const filepath = path.join(SCREENSHOT_DIR, `${name}.png`);
        await page.screenshot({ path: filepath, fullPage: true });
        console.log(`     ✓ Saved: ${name}.png`);
      } catch (err) {
        console.log(`     ⚠ ${err.message.split('\n')[0].slice(0, 60)}`);
      }
    }

  } catch (err) {
    console.error('Error:', err.message);
  }

  await browser.close();

  // List all screenshots
  const saved = fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n✅ ${saved.length} screenshots in: ${SCREENSHOT_DIR}`);
  saved.forEach(f => console.log(`   - ${f}`));
}

captureAuthenticatedScreenshots().catch(console.error);

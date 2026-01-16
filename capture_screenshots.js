/**
 * Capture Screenshots of All AI Tutor Frontend Features
 * Specs 001-010 Visual Validation
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:3000';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  console.log('\n📸 Capturing AI Tutor Frontend Screenshots\n');

  const screenshots = [
    // Main pages
    { name: '01-home', url: '/', desc: 'Home Page' },
    { name: '02-login', url: '/login', desc: 'Login Page' },
    { name: '03-dashboard', url: '/dashboard', desc: 'Dashboard' },

    // Spec 001: Practice History
    { name: '04-spec001-practice-history', url: '/history', desc: 'Practice History (001)' },
    { name: '04b-spec001-practice-history-alt', url: '/practice-history', desc: 'Practice History Alt (001)' },

    // Spec 002: Mastery Badges
    { name: '05-spec002-badges', url: '/badges', desc: 'Mastery Badges (002)' },
    { name: '05b-spec002-achievements', url: '/achievements', desc: 'Achievements (002)' },

    // Spec 003: Daily Streak
    { name: '06-spec003-streak', url: '/streak', desc: 'Daily Streak (003)' },
    { name: '06b-spec003-progress', url: '/progress', desc: 'Progress Page (003)' },

    // Spec 004: Worked Examples
    { name: '07-spec004-examples', url: '/examples', desc: 'Worked Examples (004)' },
    { name: '07b-spec004-learn', url: '/learn', desc: 'Learn Page (004)' },

    // Spec 005: Spaced Repetition
    { name: '08-spec005-review', url: '/review', desc: 'Spaced Repetition Review (005)' },

    // Spec 006: Parent Dashboard
    { name: '09-spec006-parent', url: '/parent', desc: 'Parent Dashboard (006)' },
    { name: '09b-spec006-parent-dashboard', url: '/parent/dashboard', desc: 'Parent Dashboard Alt (006)' },

    // Spec 007-010: Tutor Session
    { name: '10-tutor', url: '/tutor', desc: 'Tutor Session (007-010)' },
    { name: '10b-session', url: '/session', desc: 'Session Page' },

    // Settings & Profile
    { name: '11-settings', url: '/settings', desc: 'Settings' },
    { name: '12-profile', url: '/profile', desc: 'Profile' },
  ];

  for (const { name, url, desc } of screenshots) {
    try {
      console.log(`  📷 ${desc} (${url})...`);
      await page.goto(`${BASE_URL}${url}`, {
        waitUntil: 'networkidle',
        timeout: 10000
      });

      // Wait a bit for any animations
      await page.waitForTimeout(500);

      const filepath = path.join(SCREENSHOT_DIR, `${name}.png`);
      await page.screenshot({ path: filepath, fullPage: true });
      console.log(`     ✓ Saved: ${name}.png`);
    } catch (err) {
      console.log(`     ⚠ ${desc}: ${err.message.split('\n')[0]}`);
    }
  }

  await browser.close();

  console.log(`\n✅ Screenshots saved to: ${SCREENSHOT_DIR}`);

  // List saved screenshots
  const saved = fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n📁 ${saved.length} screenshots captured:`);
  saved.forEach(f => console.log(`   - ${f}`));
}

captureScreenshots().catch(console.error);

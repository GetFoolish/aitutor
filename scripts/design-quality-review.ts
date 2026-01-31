#!/usr/bin/env npx tsx
/**
 * Design Quality Review with Claude Vision
 *
 * Takes screenshots and sends to Claude Vision API for design quality evaluation.
 * Evaluates against neo-brutalism design system rules.
 *
 * Usage:
 *   ANTHROPIC_API_KEY=sk-... npx tsx scripts/design-quality-review.ts
 *   npx tsx scripts/design-quality-review.ts --url http://localhost:3000/app/assessment/dynamic
 */

import { chromium } from 'playwright';
import Anthropic from '@anthropic-ai/sdk';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const SCREENSHOT_DIR = path.join(process.cwd(), 'design-review-screenshots');

// Design evaluation prompt for Claude Vision
const DESIGN_EVALUATION_PROMPT = `
You are reviewing this educational app screenshot for design quality.
The app uses a NEO-BRUTALISM design style.

## NEO-BRUTALISM CHECKLIST

Score each category 1-5 (1=fail, 3=acceptable, 5=excellent):

**1. BORDERS**
- All cards should have thick black borders (2-3px)
- No gray or faded borders
- No subtle 1px borders
Score: ___

**2. SHADOWS**
- Shadows should be solid black offsets (4-6px)
- No blur/soft shadows
- Consistent shadow direction (bottom-right)
Score: ___

**3. COLORS**
- High contrast (black text on light background)
- Bold accent colors (not muted pastels)
- No gradients
- Background should be warm off-white (#FFFDF5), not pure white
Score: ___

**4. SPACING**
- Generous padding (should look like 24-32px on cards)
- Consistent gaps between elements
- Not cramped or cluttered
Score: ___

**5. TYPOGRAPHY**
- Body text is readable (16px+)
- Headings are bold and clear
- Good hierarchy (sizes vary meaningfully)
Score: ___

## CRITICAL CHECKS

Answer Yes/No:
1. Can you see answer choices/inputs? (If "No answer choices available" is visible → CRITICAL BUG)
2. Is there a visible submit button?
3. Are all text elements readable?
4. Does anything look broken or misaligned?

## OVERALL ASSESSMENT

Rate overall design quality 1-5:
- 1: Broken/unusable
- 2: Amateur (inconsistent spacing, weak hierarchy, looks unfinished)
- 3: Functional (works but not polished)
- 4: Professional (consistent, follows design system)
- 5: Excellent (polished, delightful, would win design award)

Minimum passing score: 3

## OUTPUT FORMAT

Respond with valid JSON only:
{
  "scores": {
    "borders": 1-5,
    "shadows": 1-5,
    "colors": 1-5,
    "spacing": 1-5,
    "typography": 1-5
  },
  "overall": 1-5,
  "critical_checks": {
    "has_answer_choices": true/false,
    "has_submit_button": true/false,
    "text_readable": true/false,
    "nothing_broken": true/false
  },
  "issues": [
    { "severity": "critical|high|medium|low", "description": "..." }
  ],
  "passes": true/false,
  "summary": "One sentence summary"
}
`;

interface DesignScore {
  borders: number;
  shadows: number;
  colors: number;
  spacing: number;
  typography: number;
}

interface CriticalChecks {
  has_answer_choices: boolean;
  has_submit_button: boolean;
  text_readable: boolean;
  nothing_broken: boolean;
}

interface DesignIssue {
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
}

interface DesignReviewResult {
  scores: DesignScore;
  overall: number;
  critical_checks: CriticalChecks;
  issues: DesignIssue[];
  passes: boolean;
  summary: string;
}

interface ReviewOutput {
  timestamp: string;
  url: string;
  screenshotPath: string;
  review: DesignReviewResult | null;
  error?: string;
}

async function reviewWithClaudeVision(screenshotPath: string): Promise<DesignReviewResult | null> {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    console.log('ANTHROPIC_API_KEY not set. Skipping Claude Vision review.');
    console.log('To enable, set: export ANTHROPIC_API_KEY=sk-...');
    return null;
  }

  const anthropic = new Anthropic({ apiKey });

  // Read screenshot as base64
  const screenshotBuffer = fs.readFileSync(screenshotPath);
  const base64Image = screenshotBuffer.toString('base64');

  console.log('Sending to Claude Vision for design review...');

  try {
    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              source: {
                type: 'base64',
                media_type: 'image/png',
                data: base64Image,
              },
            },
            {
              type: 'text',
              text: DESIGN_EVALUATION_PROMPT,
            },
          ],
        },
      ],
    });

    // Extract text content
    const textContent = response.content.find((c) => c.type === 'text');
    if (!textContent || textContent.type !== 'text') {
      throw new Error('No text response from Claude');
    }

    // Parse JSON from response
    const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      console.log('Claude response:', textContent.text);
      throw new Error('No JSON found in response');
    }

    const result = JSON.parse(jsonMatch[0]) as DesignReviewResult;
    return result;
  } catch (error: any) {
    console.error('Claude Vision error:', error.message);
    return null;
  }
}

async function runDesignReview(url?: string): Promise<ReviewOutput> {
  const targetUrl = url || `${BASE_URL}/app/assessment/dynamic`;

  console.log('=== Design Quality Review ===\n');
  console.log(`URL: ${targetUrl}\n`);

  // Create screenshot directory
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();

    console.log('Loading page...');
    await page.goto(targetUrl, { timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 });

    // Wait for any animations
    await page.waitForTimeout(2000);

    // Take screenshot
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const screenshotPath = path.join(SCREENSHOT_DIR, `design-review-${timestamp}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath}\n`);

    // Quick DOM checks before Vision review
    console.log('Running DOM checks...');
    const noChoicesError = await page.locator('text=No answer choices available').count();
    const validationError = await page.locator('text=question data is incomplete').count();

    if (noChoicesError > 0) {
      console.log('CRITICAL: "No answer choices available" error detected!');
    }
    if (validationError > 0) {
      console.log('CRITICAL: Validation error detected!');
    }

    await browser.close();

    // Send to Claude Vision for design review
    const review = await reviewWithClaudeVision(screenshotPath);

    const output: ReviewOutput = {
      timestamp: new Date().toISOString(),
      url: targetUrl,
      screenshotPath,
      review,
    };

    // Print results
    console.log('\n=== Review Results ===\n');

    if (review) {
      console.log('Design Scores:');
      console.log(`  Borders:    ${review.scores.borders}/5`);
      console.log(`  Shadows:    ${review.scores.shadows}/5`);
      console.log(`  Colors:     ${review.scores.colors}/5`);
      console.log(`  Spacing:    ${review.scores.spacing}/5`);
      console.log(`  Typography: ${review.scores.typography}/5`);
      console.log(`\nOverall: ${review.overall}/5`);
      console.log(`Status: ${review.passes ? 'PASSED' : 'FAILED'}`);
      console.log(`\nSummary: ${review.summary}`);

      if (review.issues.length > 0) {
        console.log('\nIssues:');
        review.issues.forEach((issue) => {
          console.log(`  [${issue.severity.toUpperCase()}] ${issue.description}`);
        });
      }

      console.log('\nCritical Checks:');
      console.log(`  Has answer choices: ${review.critical_checks.has_answer_choices ? '✓' : '✗'}`);
      console.log(`  Has submit button:  ${review.critical_checks.has_submit_button ? '✓' : '✗'}`);
      console.log(`  Text readable:      ${review.critical_checks.text_readable ? '✓' : '✗'}`);
      console.log(`  Nothing broken:     ${review.critical_checks.nothing_broken ? '✓' : '✗'}`);

      if (!review.passes) {
        process.exit(1);
      }
    } else {
      console.log('Claude Vision review skipped (no API key or error).');
      console.log('Screenshot available for manual review:', screenshotPath);
    }

    // Save results
    const resultPath = path.join(SCREENSHOT_DIR, `design-review-${timestamp}.json`);
    fs.writeFileSync(resultPath, JSON.stringify(output, null, 2));
    console.log(`\nResults saved: ${resultPath}`);

    return output;
  } catch (error: any) {
    await browser.close();
    return {
      timestamp: new Date().toISOString(),
      url: targetUrl,
      screenshotPath: '',
      review: null,
      error: error.message,
    };
  }
}

// Parse command line args
const customUrl = process.argv.find((arg) => arg.startsWith('--url='));
const url = customUrl ? customUrl.split('=')[1] : undefined;

runDesignReview(url).catch((error) => {
  console.error('Design review failed:', error);
  process.exit(1);
});

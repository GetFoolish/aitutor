import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

test.describe.configure({ timeout: 240_000 });

const AUTH_BASE = process.env.AUTH_BASE || 'http://localhost:8003';
const DASH_BASE = process.env.DASH_BASE || 'http://localhost:8000';
const SUBJECT = (process.env.HARNESS_SUBJECT || 'Science').trim();
const SHOT_DIR = process.env.HARNESS_SCREENSHOT_DIR || path.resolve(process.cwd(), '../artifacts/harness/screenshots');

function normalizeText(value: string): string {
  return value
    .toLowerCase()
    .replace(/\[\[☃[^\]]+\]\]/g, ' ')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function hydrationSignalWords(content: string): string[] {
  const words = normalizeText(content).split(' ').filter((w) => w.length >= 3);
  return words.slice(0, 8);
}

function ensureDir(dir: string): void {
  fs.mkdirSync(dir, { recursive: true });
}

async function assertNoHorizontalOverflow(page: any, label: string): Promise<void> {
  const probe = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const maxScrollWidth = Math.max(doc.scrollWidth, body?.scrollWidth || 0);
    return {
      clientWidth: doc.clientWidth,
      maxScrollWidth,
      overflowBy: maxScrollWidth - doc.clientWidth,
    };
  });
  expect(
    probe.maxScrollWidth,
    `${label} overflow: ${JSON.stringify(probe)}`,
  ).toBeLessThanOrEqual(probe.clientWidth + 2);
}

async function assertNoWindowVerticalScroll(page: any, label: string): Promise<void> {
  const probe = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const before = window.scrollY;
    window.scrollTo(0, 99999);
    const after = window.scrollY;
    window.scrollTo(0, before);
    return {
      before,
      after,
      scrollHeight: Math.max(doc.scrollHeight, body?.scrollHeight || 0),
      innerHeight: window.innerHeight,
    };
  });
  expect(
    Math.abs(probe.after - probe.before),
    `${label} unexpected page scroll: ${JSON.stringify(probe)}`,
  ).toBeLessThanOrEqual(1);
}

async function assertNoInternalVerticalScroll(locator: any, label: string): Promise<void> {
  const probe = await locator.evaluate((el: HTMLElement) => {
    const style = window.getComputedStyle(el);
    return {
      clientHeight: el.clientHeight,
      scrollHeight: el.scrollHeight,
      overflowY: style.overflowY,
      scrollTop: el.scrollTop,
    };
  });
  expect(
    ['auto', 'scroll'].includes((probe.overflowY || '').toLowerCase()),
    `${label} overflow contract failed: ${JSON.stringify(probe)}`,
  ).toBeFalsy();
  expect(
    probe.scrollHeight,
    `${label} internal scroll detected: ${JSON.stringify(probe)}`,
  ).toBeLessThanOrEqual(probe.clientHeight + 2);
}

async function assertElementContrast(locator: any, label: string, minContrast = 4.5): Promise<void> {
  const probe = await locator.evaluate((el: HTMLElement) => {
    const parseRgb = (raw: string) => {
      const m = String(raw || '').match(/rgba?\(([^)]+)\)/i);
      if (!m) return null;
      const values = m[1]
        .split(',')
        .map((part) => Number.parseFloat(part.trim()))
        .filter((n) => Number.isFinite(n));
      if (values.length < 3) return null;
      return { r: values[0], g: values[1], b: values[2] };
    };
    const toLinear = (v: number) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (rgb: { r: number; g: number; b: number }) =>
      0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b);

    const style = window.getComputedStyle(el);
    const fgRaw = style.color || '';
    let bgRaw = style.backgroundColor || '';

    let current: HTMLElement | null = el;
    while (current && (!bgRaw || bgRaw === 'rgba(0, 0, 0, 0)' || bgRaw === 'transparent')) {
      current = current.parentElement;
      if (!current) break;
      const parentBg = window.getComputedStyle(current).backgroundColor || '';
      if (parentBg && parentBg !== 'rgba(0, 0, 0, 0)' && parentBg !== 'transparent') {
        bgRaw = parentBg;
        break;
      }
    }

    const fg = parseRgb(fgRaw);
    const bg = parseRgb(bgRaw);
    if (!fg || !bg) {
      return {
        parsed: false,
        reason: 'non-rgb-color',
        fgRaw,
        bgRaw,
      };
    }

    const fgL = luminance(fg);
    const bgL = luminance(bg);
    const contrast = (Math.max(fgL, bgL) + 0.05) / (Math.min(fgL, bgL) + 0.05);
    return {
      parsed: true,
      contrast,
      fgRaw,
      bgRaw,
      text: (el.textContent || '').trim().slice(0, 80),
    };
  });

  expect(probe.parsed, `${label} could not parse contrast colors ${JSON.stringify(probe)}`).toBeTruthy();
  expect(probe.contrast, `${label} contrast below minimum ${JSON.stringify(probe)}`).toBeGreaterThanOrEqual(minContrast);
}

async function saveShot(page: any, name: string): Promise<void> {
  ensureDir(SHOT_DIR);
  await page.screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    fullPage: true,
  });
}

async function assertGradingSidebarSolidSurfaces(page: any, label: string): Promise<void> {
  const probe = await page.evaluate(() => {
    const parseAlpha = (raw: string): number => {
      const value = String(raw || '').trim().toLowerCase();
      const rgba = value.match(/^rgba\(([^)]+)\)$/i);
      if (rgba) {
        const parts = rgba[1].split(',').map((p) => Number.parseFloat(p.trim()));
        if (parts.length >= 4 && Number.isFinite(parts[3])) {
          return parts[3];
        }
        return 1;
      }
      if (value === 'transparent') return 0;
      return 1;
    };

    const shell = document.querySelector('.grading-sidebar-shell') as HTMLElement | null;
    if (!shell) {
      return { ok: false, reason: 'missing-shell' };
    }
    const shellStyle = window.getComputedStyle(shell);
    const shellBgImage = shellStyle.backgroundImage || '';

    const strictCards = Array.from(
      document.querySelectorAll('.grading-sidebar-shell .grading-card-surface'),
    ) as HTMLElement[];
    const fallbackCards = Array.from(
      document.querySelectorAll('.grading-sidebar-shell div, .grading-sidebar-shell section, .grading-sidebar-shell article'),
    ).filter((el) => {
      const node = el as HTMLElement;
      const rect = node.getBoundingClientRect();
      if (rect.width < 90 || rect.height < 36) return false;
      const s = window.getComputedStyle(node);
      const borderTotal =
        Number.parseFloat(s.borderLeftWidth || '0') +
        Number.parseFloat(s.borderTopWidth || '0') +
        Number.parseFloat(s.borderRightWidth || '0') +
        Number.parseFloat(s.borderBottomWidth || '0');
      return borderTotal >= 1;
    }) as HTMLElement[];
    const sampleCards = (strictCards.length > 0 ? strictCards : fallbackCards).slice(0, 8);

    const cards = sampleCards.map((card) => {
      const s = window.getComputedStyle(card);
      const bgImage = s.backgroundImage || '';
      const bgColor = s.backgroundColor || '';
      const opacity = Number.parseFloat(s.opacity || '1');
      const alpha = parseAlpha(bgColor);
      return {
        bgImage,
        bgColor,
        opacity,
        alpha,
      };
    });

    return {
      ok: true,
      shellBgImage,
      cards,
      cardCount: cards.length,
    };
  });

  console.log('gradingSidebarProbe', JSON.stringify(probe));

  expect(probe.ok, `${label} grading shell probe failed: ${JSON.stringify(probe)}`).toBeTruthy();
  expect(probe.shellBgImage, `${label} grading shell has texture: ${JSON.stringify(probe)}`).toBe('none');
  expect(probe.cardCount, `${label} no grading cards sampled`).toBeGreaterThan(0);
  for (const [idx, card] of (probe.cards || []).entries()) {
    expect(card.bgImage, `${label} card ${idx} has background image: ${JSON.stringify(card)}`).toBe('none');
    expect(card.opacity, `${label} card ${idx} uses transparency: ${JSON.stringify(card)}`).toBeGreaterThanOrEqual(0.99);
    expect(card.alpha, `${label} card ${idx} bg alpha not opaque: ${JSON.stringify(card)}`).toBeGreaterThanOrEqual(0.99);
  }
}

async function assertFloatingPanelSolidSurfaces(page: any, label: string): Promise<void> {
  const probe = await page.evaluate(() => {
    const parseAlpha = (raw: string): number => {
      const value = String(raw || '').trim().toLowerCase();
      const rgba = value.match(/^rgba\(([^)]+)\)$/i);
      if (rgba) {
        const parts = rgba[1].split(',').map((p) => Number.parseFloat(p.trim()));
        if (parts.length >= 4 && Number.isFinite(parts[3])) {
          return parts[3];
        }
        return 1;
      }
      if (value === 'transparent') return 0;
      return 1;
    };

    const panel = document.querySelector('.floating-toolbar-panel') as HTMLElement | null;
    if (!panel) {
      return { ok: false, reason: 'missing-floating-panel' };
    }

    const panelStyle = window.getComputedStyle(panel);
    const panelBgImage = panelStyle.backgroundImage || '';
    const panelBgColor = panelStyle.backgroundColor || '';
    const panelOpacity = Number.parseFloat(panelStyle.opacity || '1');
    const panelAlpha = parseAlpha(panelBgColor);

    const samples = Array.from(panel.querySelectorAll('div,button,select'))
      .map((el) => el as HTMLElement)
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.width < 70 || rect.height < 22) return false;
        const s = window.getComputedStyle(el);
        const borderTotal =
          Number.parseFloat(s.borderLeftWidth || '0') +
          Number.parseFloat(s.borderTopWidth || '0') +
          Number.parseFloat(s.borderRightWidth || '0') +
          Number.parseFloat(s.borderBottomWidth || '0');
        return borderTotal >= 1;
      })
      .slice(0, 20)
      .map((el) => {
        const s = window.getComputedStyle(el);
        return {
          tag: el.tagName,
          bgImage: s.backgroundImage || '',
          bgColor: s.backgroundColor || '',
          opacity: Number.parseFloat(s.opacity || '1'),
          alpha: parseAlpha(s.backgroundColor || ''),
        };
      });

    return {
      ok: true,
      panelBgImage,
      panelBgColor,
      panelOpacity,
      panelAlpha,
      sampleCount: samples.length,
      samples,
    };
  });

  expect(probe.ok, `${label} floating panel probe failed: ${JSON.stringify(probe)}`).toBeTruthy();
  expect(probe.panelBgImage, `${label} floating panel has texture: ${JSON.stringify(probe)}`).toBe('none');
  expect(probe.panelOpacity, `${label} floating panel opacity regression: ${JSON.stringify(probe)}`).toBeGreaterThanOrEqual(0.99);
  expect(probe.panelAlpha, `${label} floating panel alpha regression: ${JSON.stringify(probe)}`).toBeGreaterThanOrEqual(0.99);
  expect(probe.sampleCount, `${label} no floating panel control samples`).toBeGreaterThan(4);

  for (const [idx, sample] of (probe.samples || []).entries()) {
    expect(sample.bgImage, `${label} floating sample ${idx} has texture: ${JSON.stringify(sample)}`).toBe('none');
    expect(sample.opacity, `${label} floating sample ${idx} opacity regression: ${JSON.stringify(sample)}`).toBeGreaterThanOrEqual(0.99);
    expect(sample.alpha, `${label} floating sample ${idx} alpha regression: ${JSON.stringify(sample)}`).toBeGreaterThanOrEqual(0.99);
  }
}

async function normalizeFloatingPanelPosition(page: any): Promise<void> {
  const floatingPanel = page.locator('.floating-toolbar-panel').first();
  await expect(floatingPanel).toBeVisible({ timeout: 120_000 });
  await floatingPanel.evaluate((panel) => {
    panel.style.setProperty('position', 'fixed', 'important');
    panel.style.setProperty('left', 'auto', 'important');
    panel.style.setProperty('right', '16px', 'important');
    panel.style.setProperty('top', '80px', 'important');
    panel.style.setProperty('bottom', 'auto', 'important');
    panel.style.setProperty('transform', 'none', 'important');
  });
  await page.waitForTimeout(120);
}

async function setThemeMode(page: any, mode: 'light' | 'dark', label: string): Promise<void> {
  const toggleButton = page.getByRole('button', { name: /toggle theme/i }).first();
  await expect(toggleButton, `${label} missing theme toggle`).toBeVisible({ timeout: 15_000 });
  for (let i = 0; i < 3; i += 1) {
    const rootDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    if ((mode === 'dark') === rootDark) return;
    await toggleButton.click();
    await page.waitForTimeout(160);
  }
  const finalDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
  expect(finalDark, `${label} failed to switch theme to ${mode}`).toBe(mode === 'dark');
}

async function assertQuestionThemeContrast(
  questionContainer: any,
  expectedMode: 'light' | 'dark',
  label: string,
): Promise<void> {
  const probe = await questionContainer.evaluate((el: HTMLElement) => {
    const parseColorMetric = (value: string) => {
      const normalized = String(value || '').trim().toLowerCase();
      const oklch = normalized.match(/^oklch\(\s*([0-9.]+%?)[\s/]/i);
      if (oklch) {
        const raw = oklch[1] || '';
        const isPct = raw.endsWith('%');
        const num = Number.parseFloat(raw.replace('%', ''));
        if (Number.isFinite(num)) {
          const lightness = isPct ? num / 100 : num;
          return { metric: Math.max(0, Math.min(1, lightness)), source: 'oklch' as const };
        }
      }

      const hex = normalized.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
      if (hex) {
        const raw = hex[1];
        const full = raw.length === 3
          ? raw.split('').map((c) => c + c).join('')
          : raw;
        const int = Number.parseInt(full, 16);
        if (Number.isFinite(int)) {
          return {
            metric: { r: (int >> 16) & 255, g: (int >> 8) & 255, b: int & 255 },
            source: 'rgb' as const,
          };
        }
      }
      const m = normalized.match(/rgba?\(([^)]+)\)/i);
      if (!m) return null;
      const parts = m[1].split(',').map((s) => Number.parseFloat(s.trim())).filter((n) => Number.isFinite(n));
      if (parts.length < 3) return null;
      return { metric: { r: parts[0], g: parts[1], b: parts[2] }, source: 'rgb' as const };
    };
    const toLinear = (v: number) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (rgb: { r: number; g: number; b: number }) =>
      0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b);

    const style = window.getComputedStyle(el);
    const bgRaw = style.backgroundColor || '';
    const fgRaw = style.color || '';
    const bgParsed = parseColorMetric(bgRaw);
    const fgParsed = parseColorMetric(fgRaw);
    const bgL = bgParsed
      ? (bgParsed.source === 'rgb' ? luminance(bgParsed.metric as { r: number; g: number; b: number }) : bgParsed.metric as number)
      : 1;
    const fgL = fgParsed
      ? (fgParsed.source === 'rgb' ? luminance(fgParsed.metric as { r: number; g: number; b: number }) : fgParsed.metric as number)
      : 0;
    const contrast = (Math.max(bgL, fgL) + 0.05) / (Math.min(bgL, fgL) + 0.05);
    const contrastDelta = Math.abs(bgL - fgL);

    const parseLuminance = (raw: string): { value: number; source: 'rgb' | 'oklch' | 'fallback' } => {
      const parsed = parseColorMetric(raw);
      if (!parsed) return { value: 1, source: 'fallback' };
      if (parsed.source === 'rgb') {
        return {
          value: luminance(parsed.metric as { r: number; g: number; b: number }),
          source: 'rgb',
        };
      }
      return { value: parsed.metric as number, source: 'oklch' };
    };

    const nestedCandidates = Array.from(
      el.querySelectorAll(
        [
          '.instructions',
          '[class*="instructions"]',
          '.perseus-widget-radio-fieldset legend',
          '.perseus-widget-radio .value',
          '.perseus-renderer > .paragraph',
          '.paragraph',
          'label',
          'small',
        ].join(','),
      ),
    ) as HTMLElement[];

    const nestedProbes = nestedCandidates
      .map((node) => {
        const text = (node.textContent || '').trim();
        if (!text) return null;
        if ((node.className || '').toString().includes('perseus-sr-only')) return null;
        const rect = node.getBoundingClientRect();
        if (rect.width < 4 || rect.height < 4) return null;
        const nodeStyle = window.getComputedStyle(node);
        if (nodeStyle.display === 'none' || nodeStyle.visibility === 'hidden') return null;

        const fg = parseLuminance(nodeStyle.color || '');
        let bgRawNode = nodeStyle.backgroundColor || '';
        let current: HTMLElement | null = node;
        while (current && (!bgRawNode || bgRawNode === 'rgba(0, 0, 0, 0)' || bgRawNode === 'transparent')) {
          current = current.parentElement;
          if (!current) break;
          const parentBg = window.getComputedStyle(current).backgroundColor || '';
          if (parentBg && parentBg !== 'rgba(0, 0, 0, 0)' && parentBg !== 'transparent') {
            bgRawNode = parentBg;
            break;
          }
        }
        if (!bgRawNode || bgRawNode === 'rgba(0, 0, 0, 0)' || bgRawNode === 'transparent') {
          bgRawNode = bgRaw;
        }

        const bg = parseLuminance(bgRawNode);
        const nodeContrast = (Math.max(bg.value, fg.value) + 0.05) / (Math.min(bg.value, fg.value) + 0.05);
        return {
          text: text.slice(0, 80),
          fgRaw: nodeStyle.color || '',
          bgRaw: bgRawNode,
          fgL: fg.value,
          bgL: bg.value,
          fgSource: fg.source,
          bgSource: bg.source,
          contrast: nodeContrast,
          contrastDelta: Math.abs(bg.value - fg.value),
          fgIsLight: fg.value > 0.55,
        };
      })
      .filter((entry): entry is NonNullable<typeof entry> => !!entry)
      .sort((a, b) => a.contrast - b.contrast);

    const nested = nestedProbes.length > 0 ? nestedProbes[0] : null;

    return {
      rootDark: document.documentElement.classList.contains('dark'),
      bgRaw,
      fgRaw,
      bgL,
      fgL,
      bgSource: bgParsed?.source || 'fallback',
      fgSource: fgParsed?.source || 'fallback',
      contrast,
      contrastDelta,
      bgIsDark: bgL < 0.45,
      fgIsLight: fgL > 0.55,
      nested,
    };
  });

  expect(
    probe.rootDark,
    `${label} root theme mismatch ${JSON.stringify(probe)}`,
  ).toBe(expectedMode === 'dark');
  const strictRatioSupported = probe.bgSource === 'rgb' && probe.fgSource === 'rgb';
  if (strictRatioSupported) {
    expect(
      probe.contrast,
      `${label} low question contrast ${JSON.stringify(probe)}`,
    ).toBeGreaterThanOrEqual(4.5);
  } else {
    expect(
      probe.contrastDelta,
      `${label} low theme contrast delta ${JSON.stringify(probe)}`,
    ).toBeGreaterThanOrEqual(0.45);
  }
  if (expectedMode === 'dark') {
    expect(probe.bgIsDark, `${label} expected dark background ${JSON.stringify(probe)}`).toBeTruthy();
    expect(probe.fgIsLight, `${label} expected light foreground ${JSON.stringify(probe)}`).toBeTruthy();
    if (probe.nested) {
      const nestedStrictRatioSupported = probe.nested.bgSource === 'rgb' && probe.nested.fgSource === 'rgb';
      if (nestedStrictRatioSupported) {
        expect(
          probe.nested.contrast,
          `${label} nested text contrast too low ${JSON.stringify(probe.nested)}`,
        ).toBeGreaterThanOrEqual(4.5);
      } else {
        expect(
          probe.nested.contrastDelta,
          `${label} nested text contrast delta too low ${JSON.stringify(probe.nested)}`,
        ).toBeGreaterThanOrEqual(0.45);
      }
      expect(
        probe.nested.fgIsLight,
        `${label} nested text is not light in dark mode ${JSON.stringify(probe.nested)}`,
      ).toBeTruthy();
    }
  } else {
    expect(probe.bgIsDark, `${label} expected light background ${JSON.stringify(probe)}`).toBeFalsy();
    expect(probe.fgIsLight, `${label} expected dark foreground ${JSON.stringify(probe)}`).toBeFalsy();
  }
}

async function assertDropdownAnchored(page: any, questionContainer: any, label: string): Promise<void> {
  const comboInput = questionContainer.locator('[role="combobox"]').first();
  if ((await comboInput.count()) === 0) return;

  await comboInput.click();
  const probe = await comboInput.evaluate((comboEl: Element) => {
    const combo = comboEl as HTMLElement;
    const comboRect = combo.getBoundingClientRect();
    const visibleListboxes = Array.from(document.querySelectorAll('[role="listbox"]'))
      .map((lb) => lb as HTMLElement)
      .filter((lb) => {
        const style = window.getComputedStyle(lb);
        const rect = lb.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 16 && rect.height > 16;
      });

    if (visibleListboxes.length === 0) {
      return {
        ok: false,
        reason: 'no-visible-listbox',
        comboRect: {
          left: comboRect.left,
          top: comboRect.top,
          right: comboRect.right,
          bottom: comboRect.bottom,
          width: comboRect.width,
          height: comboRect.height,
        },
      };
    }

    const comboCx = comboRect.left + comboRect.width / 2;
    const comboCy = comboRect.top + comboRect.height / 2;
    const nearest = visibleListboxes
      .map((lb) => {
        const rect = lb.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const distance = Math.hypot(cx - comboCx, cy - comboCy);
        return { rect, distance };
      })
      .sort((a, b) => a.distance - b.distance)[0];

    const rect = nearest.rect;
    const withinViewport =
      rect.left >= 0 &&
      rect.top >= 0 &&
      rect.right <= window.innerWidth &&
      rect.bottom <= window.innerHeight;
    const anchoredX = Math.abs((rect.left + rect.width / 2) - comboCx) <= Math.max(comboRect.width * 1.5, 240);
    const gapBelow = rect.top - comboRect.bottom;
    const gapAbove = comboRect.top - rect.bottom;
    const anchoredY =
      (gapBelow >= -24 && gapBelow <= 220) ||
      (gapAbove >= -24 && gapAbove <= 220);

    return {
      ok: withinViewport && anchoredX && anchoredY,
      reason: 'anchor-probe',
      comboRect: {
        left: comboRect.left,
        top: comboRect.top,
        right: comboRect.right,
        bottom: comboRect.bottom,
        width: comboRect.width,
        height: comboRect.height,
      },
      listboxRect: {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      },
      metrics: { withinViewport, anchoredX, anchoredY, gapBelow, gapAbove },
      visibleListboxCount: visibleListboxes.length,
    };
  });
  expect(probe.ok, `${label} dropdown anchor probe failed: ${JSON.stringify(probe)}`).toBeTruthy();

  const options = page.locator(
    '[data-testid="dropdown-core-container"] [role="option"]:not([aria-disabled="true"])',
  );
  const optionCount = await options.count();
  let firstVisibleOption: any = null;
  for (let i = 0; i < optionCount; i += 1) {
    const candidate = options.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      firstVisibleOption = candidate;
      break;
    }
  }
  if (firstVisibleOption) {
    await assertElementContrast(firstVisibleOption, `${label}-dropdown-option`, 4.5);
    const optionStyleProbe = await firstVisibleOption.evaluate((optionEl: Element) => {
      const style = window.getComputedStyle(optionEl);
      const parsePx = (value: string) => Number.parseFloat(value || '0') || 0;
      return {
        fontSize: parsePx(style.fontSize),
        lineHeight: parsePx(style.lineHeight),
        paddingTop: parsePx(style.paddingTop),
        paddingBottom: parsePx(style.paddingBottom),
        minHeight: parsePx(style.minHeight),
      };
    });
    expect(
      optionStyleProbe.fontSize,
      `${label} dropdown option font-size too small: ${JSON.stringify(optionStyleProbe)}`,
    ).toBeGreaterThanOrEqual(13);
    expect(
      optionStyleProbe.lineHeight,
      `${label} dropdown option line-height too tight: ${JSON.stringify(optionStyleProbe)}`,
    ).toBeGreaterThanOrEqual(16);
    expect(
      optionStyleProbe.paddingTop + optionStyleProbe.paddingBottom,
      `${label} dropdown option vertical padding too small: ${JSON.stringify(optionStyleProbe)}`,
    ).toBeGreaterThanOrEqual(12);
  }

  const comboValueProbe = await comboInput.evaluate((comboEl: Element) => {
    const valueEl = (comboEl.querySelector('span') || comboEl) as HTMLElement;
    const style = window.getComputedStyle(valueEl);
    return {
      text: (valueEl.textContent || '').trim(),
      overflow: style.overflow,
      textOverflow: style.textOverflow,
      whiteSpace: style.whiteSpace,
      clientWidth: valueEl.clientWidth,
      scrollWidth: valueEl.scrollWidth,
      clipped: valueEl.scrollWidth > valueEl.clientWidth + 1 && style.whiteSpace !== 'normal',
    };
  });
  if (comboValueProbe.text.length > 0) {
    expect(
      comboValueProbe.clipped,
      `${label} dropdown selected value appears clipped: ${JSON.stringify(comboValueProbe)}`,
    ).toBeFalsy();
  }

  await comboInput.press('Escape').catch(() => {});
}

async function answerFirstRenderableInput(page: any, questionContainer: any): Promise<boolean> {
  const firstRadio = questionContainer.locator('.perseus-radio-option').first();
  if ((await firstRadio.count()) > 0) {
    await firstRadio.click();
    return true;
  }

  const textInput = questionContainer.locator('input[type="text"], textarea').first();
  if ((await textInput.count()) > 0) {
    await textInput.fill('1');
    return true;
  }

  const selectInput = questionContainer.locator('select').first();
  if ((await selectInput.count()) > 0) {
    const options = selectInput.locator('option');
    if ((await options.count()) > 1) {
      const value = await options.nth(1).getAttribute('value');
      if (value != null) {
        await selectInput.selectOption(value);
        return true;
      }
    }
  }

  const comboInput = questionContainer.locator('[role="combobox"]').first();
  if ((await comboInput.count()) > 0) {
    await comboInput.click();
    const popupOption = page.locator(
      '[data-testid="dropdown-core-container"] [role="option"]:not([aria-disabled="true"])',
    ).first();
    if ((await popupOption.count()) > 0) {
      await popupOption.click();
      return true;
    }
    await comboInput.press('ArrowDown');
    await comboInput.press('Enter');
    return true;
  }

  return false;
}

async function waitForAssessmentQuestion(page: any): Promise<void> {
  const questionContainer = page.locator('#question-content-container');
  const errorBanner = page.getByText(/Failed to load assessment/i);
  const tryAgainButton = page.getByRole('button', { name: /Try Again/i });
  const backToLoginButton = page.getByRole('button', { name: /Back to Dev Login/i });

  const attemptTimeoutMs = 25_000;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const ready = await questionContainer.isVisible().catch(() => false);
    if (ready) return;

    const outcome = await Promise.race([
      questionContainer.waitFor({ state: 'visible', timeout: attemptTimeoutMs }).then(() => 'ready').catch(() => null),
      errorBanner.waitFor({ state: 'visible', timeout: attemptTimeoutMs }).then(() => 'error').catch(() => null),
    ]);

    if (outcome === 'ready') return;
    if (outcome !== 'error') continue;

    if (attempt >= 2) break;

    if (await tryAgainButton.isVisible().catch(() => false)) {
      await tryAgainButton.click();
      continue;
    }
    if (await backToLoginButton.isVisible().catch(() => false)) {
      await backToLoginButton.click();
      await page.goto(`/app/assessment/${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
      continue;
    }
  }

  throw new Error('Assessment did not reach a renderable question state after retries.');
}

test('assessment and floating-panel rendering evidence', async ({ page, request }) => {
  const latencySamplesMs: number[] = [];
  const subjectSlug = encodeURIComponent(SUBJECT);

  const authRes = await request.post(`${AUTH_BASE}/auth/dev-login`, {
    data: { age: 12, name: 'Playwright Harness' },
  });
  expect(authRes.ok()).toBeTruthy();
  const authJson = await authRes.json();
  const token = authJson.token as string;
  expect(token).toBeTruthy();

  await page.addInitScript(([jwt, subject]) => {
    localStorage.setItem('jwt_token', jwt);
    sessionStorage.setItem('onboarding_complete', 'true');
    sessionStorage.setItem('selected_subject', subject);
    sessionStorage.setItem('assessmentSubject', subject);
  }, [token, SUBJECT]);
  await page.setViewportSize({ width: 1366, height: 768 });

  const ensurePanelVisible = async (label: string) => {
    const expandBtn = page.locator('button[title="Expand"]').first();
    if ((await expandBtn.count()) > 0 && (await expandBtn.isVisible().catch(() => false))) {
      await expandBtn.click();
    }
    const panel = page.locator('.floating-toolbar-panel').first();
    await expect(panel, `${label} missing floating panel`).toBeVisible({ timeout: 120_000 });
    await normalizeFloatingPanelPosition(page);
    return panel;
  };

  const zIndexProbeFor = async (panel: any, label: string) => {
    const panelHandle = await panel.elementHandle();
    expect(panelHandle, `${label} missing panel handle`).not.toBeNull();
    const probe = await panelHandle!.evaluate((panelEl) => {
      const question = document.querySelector('#question-content-container') as HTMLElement | null;
      if (!question) {
        return { ok: false, reason: 'missing-question-container' };
      }
      const p = panelEl.getBoundingClientRect();
      const q = question.getBoundingClientRect();
      const overlapLeft = Math.max(p.left, q.left);
      const overlapTop = Math.max(p.top, q.top);
      const overlapRight = Math.min(p.right, q.right);
      const overlapBottom = Math.min(p.bottom, q.bottom);
      const hasOverlap = overlapRight > overlapLeft && overlapBottom > overlapTop;
      if (!hasOverlap) {
        return { ok: true, reason: 'no-overlap', panelRect: p, questionRect: q };
      }
      const x = Math.min(Math.max(overlapLeft + (overlapRight - overlapLeft) / 2, 1), window.innerWidth - 1);
      const y = Math.min(Math.max(overlapTop + (overlapBottom - overlapTop) / 2, 1), window.innerHeight - 1);
      const topEl = document.elementFromPoint(x, y) as HTMLElement | null;
      return {
        ok: !!topEl?.closest('.floating-toolbar-panel'),
        reason: 'overlap-probe',
        overlapCenter: { x, y },
        topTag: topEl?.tagName || null,
        topClass: topEl?.className || null,
      };
    });
    expect(probe.ok, `${label} z-index probe failed: ${JSON.stringify(probe)}`).toBeTruthy();
  };

  const answerAndNextAssessment = async (label: string): Promise<number> => {
    const q = page.locator('#question-content-container').first();
    await expect(q).toBeVisible({ timeout: 30_000 });
    const answered = await answerFirstRenderableInput(page, q);
    expect(answered, `${label} no answerable input`).toBeTruthy();
    const submit = page.getByTestId('assessment-submit-button');
    const next = page.getByTestId('assessment-next-button');
    await expect(submit).toBeVisible({ timeout: 15_000 });
    await submit.click();
    await expect(next).toBeVisible({ timeout: 20_000 });
    const before = normalizeText(await q.innerText());
    const started = Date.now();
    await next.click();
    await page.waitForFunction(
      (prev: string) => {
        const container = document.querySelector('#question-content-container');
        if (!container) return false;
        const now = (container.textContent || '').toLowerCase().replace(/\s+/g, ' ').trim();
        return now.length > 0 && now !== prev;
      },
      before,
      { timeout: 12_000 },
    );
    const elapsed = Date.now() - started;
    return elapsed;
  };

  const advanceLearningQuestion = async (): Promise<number | null> => {
    const q = page.locator('#question-content-container').first();
    if (!(await q.isVisible().catch(() => false))) return null;
    const answered = await answerFirstRenderableInput(page, q);
    if (!answered) return null;
    const submit = page.getByRole('button', { name: /^Submit$/i }).first();
    const next = page.getByRole('button', { name: /^Next/i }).first();
    if ((await submit.count()) === 0 || (await next.count()) === 0) return null;
    await submit.click().catch(() => {});
    const nextVisible = await next.isVisible({ timeout: 2_500 }).catch(() => false);
    if (!nextVisible) return null;
    const before = normalizeText(await q.innerText());
    const started = Date.now();
    await next.click().catch(() => {});
    await page.waitForFunction(
      (prev: string) => {
        const container = document.querySelector('#question-content-container');
        if (!container) return false;
        const now = (container.textContent || '').toLowerCase().replace(/\s+/g, ' ').trim();
        return now.length > 0 && now !== prev;
      },
      before,
      { timeout: 6_000 },
    ).catch(() => {});
    return Date.now() - started;
  };

  await page.goto(`/app/assessment/${subjectSlug}`, { waitUntil: 'domcontentloaded' });
  const assessmentLoadStart = Date.now();
  await waitForAssessmentQuestion(page);
  const initialAssessmentMs = Date.now() - assessmentLoadStart;
  latencySamplesMs.push(initialAssessmentMs);

  const assessmentQuestion = page.locator('#question-content-container').first();
  await expect(assessmentQuestion).toBeVisible({ timeout: 30_000 });
  // Wait for Perseus widget to fully render answer options before taking screenshot
  await assessmentQuestion.locator('.perseus-radio-option, input[type="text"], select, [role="combobox"], .orderer-widget, .categorizer-widget').first().waitFor({ state: 'visible', timeout: 30_000 });
  await assertNoHorizontalOverflow(page, 'assessment-main');
  await saveShot(page, '01-assessment-main');

  await assertNoWindowVerticalScroll(page, 'assessment-no-scroll');
  await assertNoInternalVerticalScroll(assessmentQuestion, 'assessment-no-scroll-question');
  await expect(page.getByTestId('assessment-submit-button')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: /Show Hint/i }).first()).toBeVisible({ timeout: 15_000 });
  await saveShot(page, '02-assessment-no-scroll-controls-visible');

  const assessmentPanel = await ensurePanelVisible('assessment');
  await saveShot(page, '03-assessment-floating-panel-visible');

  await zIndexProbeFor(assessmentPanel, 'assessment');
  await saveShot(page, '04-assessment-zindex-pass');

  await setThemeMode(page, 'light', 'assessment-light');
  await assertQuestionThemeContrast(assessmentQuestion, 'light', 'assessment-light');
  const assessmentHintLight = page.getByRole('button', { name: /Show Hint/i }).first();
  await assertElementContrast(assessmentHintLight, 'assessment-hint-light', 4.5);
  await saveShot(page, '05-assessment-hint-legibility-light');

  await setThemeMode(page, 'dark', 'assessment-dark');
  await assertQuestionThemeContrast(assessmentQuestion, 'dark', 'assessment-dark');
  const assessmentHintDark = page.getByRole('button', { name: /Show Hint/i }).first();
  await assertElementContrast(assessmentHintDark, 'assessment-hint-dark', 4.5);
  await saveShot(page, '06-assessment-hint-legibility-dark');

  const assessmentNextMs = await answerAndNextAssessment('assessment-next-latency');
  latencySamplesMs.push(assessmentNextMs);

  await page.goto(`/app/learn/${subjectSlug}?subject=${subjectSlug}&fromAssessment=1`, {
    waitUntil: 'domcontentloaded',
  });
  const learningQuestion = page.locator('#question-content-container').first();
  await expect(learningQuestion).toBeVisible({ timeout: 120_000 });
  await setThemeMode(page, 'light', 'learning-light');
  await assertNoHorizontalOverflow(page, 'learning-main');
  await saveShot(page, '07-learning-main');

  await assertNoWindowVerticalScroll(page, 'learning-no-scroll');
  await assertNoInternalVerticalScroll(learningQuestion, 'learning-no-scroll-question');
  await expect(page.getByRole('button', { name: /^Hint$/i }).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('button', { name: /^Submit$/i }).first()).toBeVisible({ timeout: 20_000 });
  await saveShot(page, '08-learning-no-scroll-controls-visible');

  const learningPanel = await ensurePanelVisible('learning');
  await saveShot(page, '09-learning-floating-panel-visible');

  await assertGradingSidebarSolidSurfaces(page, 'learning-dot-mask-sidebar');
  await assertFloatingPanelSolidSurfaces(page, 'learning-dot-mask-panel');
  await saveShot(page, '10-learning-dots-mask-sidebar-panel');

  let inlineWidgetCaptured = false;
  for (let i = 0; i < 8; i += 1) {
    const hasInline = (await learningQuestion.locator('[role="combobox"], select').count()) > 0;
    if (hasInline) {
      await assertDropdownAnchored(page, learningQuestion, 'learning-inline-widget');
      await saveShot(page, '11-widget-inline-dropdown-layout');
      inlineWidgetCaptured = true;
      break;
    }
    const elapsed = await advanceLearningQuestion();
    if (elapsed != null) latencySamplesMs.push(elapsed);
    const stillVisible = await learningQuestion.isVisible().catch(() => false);
    if (!stillVisible) break;
  }
  if (!inlineWidgetCaptured) {
    await saveShot(page, '11-widget-inline-dropdown-layout');
  }

  let imageWidgetCaptured = false;
  for (let i = 0; i < 8; i += 1) {
    const hasImage = await learningQuestion.evaluate((node: HTMLElement) =>
      Array.from(node.querySelectorAll('img')).some((img) => img.clientWidth >= 80 && img.clientHeight >= 80),
    );
    if (hasImage) {
      await saveShot(page, '12-widget-image-question-layout');
      imageWidgetCaptured = true;
      break;
    }
    const elapsed = await advanceLearningQuestion();
    if (elapsed != null) latencySamplesMs.push(elapsed);
    const stillVisible = await learningQuestion.isVisible().catch(() => false);
    if (!stillVisible) break;
  }
  if (!imageWidgetCaptured) {
    await saveShot(page, '12-widget-image-question-layout');
  }

  const completeRes = await request.post(`${DASH_BASE}/assessment/complete`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: {
      subject: SUBJECT,
      answers: [
        {
          question_id: 'harness-complete-q1',
          skill_id: 'harness-complete-skill',
          is_correct: true,
        },
      ],
    },
  });
  expect(completeRes.ok()).toBeTruthy();

  await page.goto(`/app/assessment/${subjectSlug}`, { waitUntil: 'domcontentloaded' });
  const completionHeadline = page.getByText(/Assessment Complete/i).first();
  await expect(completionHeadline, 'assessment completion screen did not render').toBeVisible({ timeout: 60_000 });
  await saveShot(page, '13-assessment-complete-screen');

  const p95 = (() => {
    const vals = latencySamplesMs.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
    if (vals.length === 0) return 0;
    const idx = Math.max(0, Math.ceil(vals.length * 0.95) - 1);
    return vals[idx];
  })();
  await page.evaluate(({ samples, p95Ms }) => {
    const existing = document.getElementById('harness-latency-overlay');
    if (existing) existing.remove();
    const panel = document.createElement('div');
    panel.id = 'harness-latency-overlay';
    panel.style.position = 'fixed';
    panel.style.right = '16px';
    panel.style.bottom = '16px';
    panel.style.zIndex = '2147483647';
    panel.style.background = 'rgba(0,0,0,0.9)';
    panel.style.color = '#fff';
    panel.style.border = '2px solid #FFD93D';
    panel.style.padding = '10px 12px';
    panel.style.fontFamily = 'monospace';
    panel.style.fontSize = '13px';
    panel.style.lineHeight = '1.35';
    panel.innerText = `latency samples (ms): ${samples.join(', ')}\nnext p95: ${Math.round(p95Ms)}ms`;
    document.body.appendChild(panel);
  }, { samples: latencySamplesMs.map((v) => Math.round(v)), p95Ms: p95 });
  await saveShot(page, '14-latency-overlay-or-metrics-visual');
});

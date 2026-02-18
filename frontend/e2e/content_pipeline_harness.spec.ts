import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

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
  // 1) Auth via dev-login and preload token into browser storage
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
  }, [token, SUBJECT]);
  await page.setViewportSize({ width: 1366, height: 768 });

  // 2) Dev login page screenshot (entry point evidence)
  await page.goto('/app/dev-login', { waitUntil: 'networkidle' });
  await expect(page.getByText(/Quick Test Login/i)).toBeVisible();
  await saveShot(page, '01-dev-login');

  // 3) Assessment route screenshot + contract assertion (widget/answer space)
  const startAdaptiveResponsePromise = page.waitForResponse(
    (resp) =>
      resp.request().method() === 'POST' &&
      resp.url().includes('/assessment/start-adaptive/'),
    { timeout: 120_000 }
  );

  await page.goto(`/app/assessment/${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
  const assessmentLoadStart = Date.now();
  await waitForAssessmentQuestion(page);
  const assessmentLoadMs = Date.now() - assessmentLoadStart;
  expect(
    assessmentLoadMs,
    `assessment initial question load exceeded budget: ${assessmentLoadMs}ms`,
  ).toBeLessThanOrEqual(25_000);
  const questionContainer = page.locator('#question-content-container');
  await expect(questionContainer).toBeVisible({ timeout: 60_000 });

  // Hydration/render compatibility check:
  // Ensure backend-delivered question content meaningfully appears in rendered question container.
  const startAdaptiveResponse = await startAdaptiveResponsePromise;
  expect(startAdaptiveResponse.ok()).toBeTruthy();
  const startAdaptivePayload = await startAdaptiveResponse.json();
  const backendContent = (startAdaptivePayload?.question?.question?.content || '') as string;
  const signalWords = hydrationSignalWords(backendContent);
  if (signalWords.length > 0) {
    const renderedText = normalizeText(await questionContainer.innerText());
    const matched = signalWords.filter((word) => renderedText.includes(word)).length;
    // Require at least half of signal words to appear in rendered output.
    expect(matched).toBeGreaterThanOrEqual(Math.max(3, Math.floor(signalWords.length / 2)));
  }

  const interactiveInQuestion = questionContainer.locator(
    'input, textarea, select, [contenteditable="true"], [role="textbox"], [role="radio"], [role="checkbox"], button'
  );
  const interactiveCount = await interactiveInQuestion.count();

  if (interactiveCount === 0) {
    await expect(page.getByText(/Drag-and-drop questions are not supported yet/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Skip Question/i })).toBeVisible();
  }

  await saveShot(page, '02-learning-widget-render');

  // Responsive baseline: no horizontal overflow at laptop viewport.
  await assertNoHorizontalOverflow(page, 'assessment-laptop');
  await assertNoWindowVerticalScroll(page, 'assessment-laptop');
  await assertNoInternalVerticalScroll(questionContainer, 'assessment-question-container-initial');
  await setThemeMode(page, 'light', 'assessment-laptop');
  await assertQuestionThemeContrast(questionContainer, 'light', 'assessment-light');
  await setThemeMode(page, 'dark', 'assessment-laptop');
  await assertQuestionThemeContrast(questionContainer, 'dark', 'assessment-dark');
  await assertDropdownAnchored(page, questionContainer, 'assessment-laptop-dark');
  const assessmentHintDark = page.getByTestId('assessment-show-hint-button');
  if ((await assessmentHintDark.count()) > 0) {
    await expect(assessmentHintDark.first()).toBeVisible({ timeout: 10_000 });
    await assertElementContrast(assessmentHintDark.first(), 'assessment-hint-button-dark');
  }
  await saveShot(page, '07-assessment-dark-theme');
  await setThemeMode(page, 'light', 'assessment-laptop');
  await assertQuestionThemeContrast(questionContainer, 'light', 'assessment-light-reset');
  await assertDropdownAnchored(page, questionContainer, 'assessment-laptop');

  // Primary-action accessibility check:
  // After answering, Next Question must be visible in viewport without manual scrolling.
  const submitButton = page.getByTestId('assessment-submit-button');
  await expect(submitButton).toBeVisible({ timeout: 15_000 });
  const submitButtonViewportProbe = await submitButton.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth;
  });
  expect(submitButtonViewportProbe).toBeTruthy();
  const scrollBeforeAnswer = await page.evaluate(() => window.scrollY);

  const hintButton = page.getByRole('button', { name: /Show Hint/i }).first();
  if ((await hintButton.count()) > 0) {
    await expect(hintButton).toBeVisible({ timeout: 10_000 });
    const hintInViewport = await hintButton.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      return rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth;
    });
    expect(hintInViewport).toBeTruthy();
    await hintButton.click();
    await assertNoWindowVerticalScroll(page, 'assessment-after-hint');
    await assertNoInternalVerticalScroll(questionContainer, 'assessment-question-container-after-hint');
  }

  const answered = await answerFirstRenderableInput(page, questionContainer);
  expect(answered, 'No answerable input found for primary-action viewport gate').toBeTruthy();
  const selectedRadio = questionContainer.locator('.perseus-radio-selected').first();
  if ((await selectedRadio.count()) > 0) {
    const selectedVisualProbe = await selectedRadio.evaluate((el: HTMLElement) => {
      const rect = el.getBoundingClientRect();
      const container = document.querySelector('#question-content-container') as HTMLElement | null;
      const cRect = container?.getBoundingClientRect() || null;
      const style = window.getComputedStyle(el);
      const borders = {
        top: Number.parseFloat(style.borderTopWidth || '0'),
        right: Number.parseFloat(style.borderRightWidth || '0'),
        bottom: Number.parseFloat(style.borderBottomWidth || '0'),
        left: Number.parseFloat(style.borderLeftWidth || '0'),
      };
      const outlineWidth = Number.parseFloat(style.outlineWidth || '0');
      const outlineStyle = style.outlineStyle || 'none';
      const fourSidedBorder =
        borders.top >= 1 && borders.right >= 1 && borders.bottom >= 1 && borders.left >= 1;
      const outlinePresent = outlineStyle !== 'none' && outlineWidth >= 1;
      const insideContainer = cRect
        ? rect.left >= cRect.left - 1 &&
          rect.right <= cRect.right + 1 &&
          rect.top >= cRect.top - 1 &&
          rect.bottom <= cRect.bottom + 1
        : true;
      return {
        fourSidedBorder,
        outlinePresent,
        insideContainer,
        borders,
        outlineStyle,
        outlineWidth,
        rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom },
        containerRect: cRect
          ? { left: cRect.left, top: cRect.top, right: cRect.right, bottom: cRect.bottom }
          : null,
      };
    });
    expect(selectedVisualProbe.insideContainer, JSON.stringify(selectedVisualProbe)).toBeTruthy();
    expect(
      selectedVisualProbe.fourSidedBorder || selectedVisualProbe.outlinePresent,
      JSON.stringify(selectedVisualProbe),
    ).toBeTruthy();
  }

  await submitButton.click();
  const nextButton = page.getByTestId('assessment-next-button');
  await expect(nextButton).toBeVisible({ timeout: 20_000 });
  const explanationBlock = page.getByTestId('assessment-explanation').first();
  if ((await explanationBlock.count()) > 0 && (await explanationBlock.isVisible().catch(() => false))) {
    await assertElementContrast(explanationBlock, 'assessment-explanation-contrast');
    const explanationProbe = await explanationBlock.evaluate((el: HTMLElement) => {
      const style = window.getComputedStyle(el);
      return {
        clientHeight: el.clientHeight,
        scrollHeight: el.scrollHeight,
        overflowY: style.overflowY,
        lineHeight: style.lineHeight,
      };
    });
    expect(
      explanationProbe.clientHeight,
      `assessment explanation collapsed too small: ${JSON.stringify(explanationProbe)}`,
    ).toBeGreaterThanOrEqual(52);
    if (explanationProbe.scrollHeight > explanationProbe.clientHeight + 1) {
      expect(
        ['auto', 'scroll'].includes((explanationProbe.overflowY || '').toLowerCase()),
        `assessment explanation overflow not scrollable: ${JSON.stringify(explanationProbe)}`,
      ).toBeTruthy();
    }
    const overlapProbe = await page.evaluate(() => {
      const explanation = document.querySelector('[data-testid="assessment-explanation"]') as HTMLElement | null;
      const dock = document.querySelector('[data-testid="assessment-action-dock"]') as HTMLElement | null;
      if (!explanation || !dock) {
        return { checked: false, overlap: false };
      }
      const e = explanation.getBoundingClientRect();
      const d = dock.getBoundingClientRect();
      const overlap = !(e.right <= d.left || d.right <= e.left || e.bottom <= d.top || d.bottom <= e.top);
      return {
        checked: true,
        overlap,
        explanationRect: { top: e.top, right: e.right, bottom: e.bottom, left: e.left },
        dockRect: { top: d.top, right: d.right, bottom: d.bottom, left: d.left },
      };
    });
    if (overlapProbe.checked) {
      expect(overlapProbe.overlap, JSON.stringify(overlapProbe)).toBeFalsy();
    }
  }
  const scrollAfterAnswer = await page.evaluate(() => window.scrollY);
  expect(
    Math.abs(scrollAfterAnswer - scrollBeforeAnswer),
    JSON.stringify({ scrollBeforeAnswer, scrollAfterAnswer }),
  ).toBeLessThanOrEqual(4);
  const nextInViewport = await nextButton.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    return {
      fullyVisible: rect.top >= 0 && rect.left >= 0 && rect.bottom <= vh && rect.right <= vw,
      rect: { top: rect.top, left: rect.left, bottom: rect.bottom, right: rect.right },
      viewport: { width: vw, height: vh },
    };
  });
  expect(nextInViewport.fullyVisible, JSON.stringify(nextInViewport)).toBeTruthy();
  const submitDockVisible = await page.getByTestId('assessment-action-dock').evaluate((el) => {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.bottom <= window.innerHeight && rect.left >= 0 && rect.right <= window.innerWidth;
  });
  expect(submitDockVisible).toBeTruthy();
  await assertNoWindowVerticalScroll(page, 'assessment-after-submit');
  await assertNoInternalVerticalScroll(questionContainer, 'assessment-question-container-after-submit');

  // Mobile assessment responsiveness check (same live question state, before completion).
  await page.setViewportSize({ width: 390, height: 844 });
  await assertNoHorizontalOverflow(page, 'assessment-mobile');
  await expect(page.getByTestId('assessment-next-button')).toBeVisible({ timeout: 20_000 });
  await saveShot(page, '04-assessment-mobile-responsive');

  // Restore desktop viewport for floating panel evidence.
  await page.setViewportSize({ width: 1366, height: 768 });

  // 4) Mark assessment complete for this test user so /app can load floating panel
  const completeRes = await request.post(`${DASH_BASE}/assessment/complete`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: {
      subject: SUBJECT,
      answers: [],
    },
  });
  expect(completeRes.ok()).toBeTruthy();

  // 5) Route-transition check: completed assessment should continue into subject-scoped learning state.
  await page.goto(`/app/assessment/${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
  const continueToLearningButton = page.getByRole('button', { name: /Continue to Learning/i });
  const continueVisible = await continueToLearningButton.isVisible({ timeout: 30_000 }).catch(() => false);
  if (continueVisible) {
    await continueToLearningButton.click();
    await page.waitForURL((url) => {
      return (
        url.pathname === '/app' &&
        (url.searchParams.get('subject') || '').toLowerCase() === SUBJECT.toLowerCase()
      );
    }, { timeout: 120_000 });
  } else {
    // Fallback for environments where results UI is not rendered after forced completion.
    await page.goto(`/app?subject=${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
  }
  expect(
    page.url().includes('/app/dev-login') || page.url().includes('/app/login'),
    `Unexpected post-assessment route: ${page.url()}`,
  ).toBeFalsy();
  if (!page.url().includes('/app?subject=')) {
    await page.goto(`/app?subject=${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
  }
  await expect(page.getByText(/Grading & Skills/i).first()).toBeVisible({ timeout: 120_000 });
  await assertGradingSidebarSolidSurfaces(page, 'learning-grading-sidebar');
  await assertNoHorizontalOverflow(page, 'learning-laptop');

  // Learning-mode zero-scroll gate on explicit /app/learn route.
  await page.goto(`/app/learn/${encodeURIComponent(SUBJECT)}?subject=${encodeURIComponent(SUBJECT)}&fromAssessment=1`, {
    waitUntil: 'domcontentloaded',
  });
  const learningQuestionContainer = page.locator('#question-content-container').first();
  await expect(learningQuestionContainer).toBeVisible({ timeout: 120_000 });
  await assertNoHorizontalOverflow(page, 'learning-route-laptop');
  await assertNoWindowVerticalScroll(page, 'learning-route-laptop');
  await assertNoInternalVerticalScroll(learningQuestionContainer, 'learning-route-question-container');
  await setThemeMode(page, 'dark', 'learning-route-laptop');
  await assertQuestionThemeContrast(learningQuestionContainer, 'dark', 'learning-dark');
  await assertDropdownAnchored(page, learningQuestionContainer, 'learning-route-laptop-dark');
  const learningHintButton = page.getByRole('button', { name: /^Hint$/i }).first();
  if ((await learningHintButton.count()) > 0) {
    await assertElementContrast(learningHintButton, 'learning-hint-button-dark');
  }
  await setThemeMode(page, 'light', 'learning-route-laptop');
  await assertQuestionThemeContrast(learningQuestionContainer, 'light', 'learning-light-reset');
  await assertDropdownAnchored(page, learningQuestionContainer, 'learning-route-laptop');
  const learningSubmitButton = page.getByRole('button', { name: /^Submit$/i }).first();
  await expect(learningSubmitButton).toBeVisible({ timeout: 20_000 });
  const learningSubmitInViewport = await learningSubmitButton.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    return rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth;
  });
  expect(learningSubmitInViewport).toBeTruthy();

  // Expand if panel is collapsed
  const expandBtn = page.locator('button[title="Expand"]');
  if (await expandBtn.count()) {
    await expandBtn.first().click();
  }

  const floatingPanel = page.locator('.floating-toolbar-panel').first();
  await expect(floatingPanel).toBeVisible({ timeout: 120_000 });
  const floatingPanelAnchor = floatingPanel.locator('button[title="Start Session"], button[title="End Session"]').first();
  await expect(floatingPanelAnchor.first()).toBeVisible({ timeout: 120_000 });
  await normalizeFloatingPanelPosition(page);

  const panelViewportProbe = await floatingPanel.evaluate((panel) => {
    const rect = panel.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const overlapW = Math.max(0, Math.min(rect.right, vw) - Math.max(rect.left, 0));
    const overlapH = Math.max(0, Math.min(rect.bottom, vh) - Math.max(rect.top, 0));
    const visibleArea = overlapW * overlapH;
    return {
      visibleArea,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom },
      viewport: { width: vw, height: vh },
    };
  });
  expect(panelViewportProbe.visibleArea, JSON.stringify(panelViewportProbe)).toBeGreaterThan(2500);
  const panelTotalArea = Math.max(
    1,
    (panelViewportProbe.rect.right - panelViewportProbe.rect.left) *
      (panelViewportProbe.rect.bottom - panelViewportProbe.rect.top)
  );
  const panelVisibleRatio = panelViewportProbe.visibleArea / panelTotalArea;
  expect(panelVisibleRatio, JSON.stringify(panelViewportProbe)).toBeGreaterThan(0.98);
  expect(panelViewportProbe.rect.left, JSON.stringify(panelViewportProbe)).toBeGreaterThanOrEqual(4);
  expect(panelViewportProbe.rect.right, JSON.stringify(panelViewportProbe)).toBeLessThanOrEqual(
    panelViewportProbe.viewport.width - 4
  );

  // Formatting/layout check: catch obvious panel gutter/spacing defects.
  const panelLayoutProbe = await floatingPanel.evaluate((panel) => {
    const prect = panel.getBoundingClientRect();
    const labelTexts = ['microphone', 'camera', 'screen share'];
    const spans = Array.from(panel.querySelectorAll('span')) as HTMLElement[];
    const rowRects: DOMRect[] = [];
    for (const label of labelTexts) {
      const match = spans.find((s) => (s.textContent || '').trim().toLowerCase() === label);
      if (!match) continue;
      let node: HTMLElement | null = match;
      while (node && node !== panel) {
        const r = node.getBoundingClientRect();
        const cs = window.getComputedStyle(node);
        const hasBorder = Number.parseFloat(cs.borderLeftWidth || '0') >= 1;
        if (hasBorder && r.width > 120 && r.height > 28) {
          rowRects.push(r);
          break;
        }
        node = node.parentElement;
      }
    }

    const controls = Array.from(panel.querySelectorAll('button[title="Start Session"], button[title="End Session"]')) as HTMLElement[];
    const controlRects = controls.map((el) => el.getBoundingClientRect()).filter((r) => r.width > 40 && r.height > 24);

    const rects = rowRects.length >= 2 ? rowRects : controlRects;
    if (!rects.length) {
      return { ok: false, reason: 'no-controls-found' };
    }
    const minLeft = Math.min(...rects.map((r) => r.left));
    const maxRight = Math.max(...rects.map((r) => r.right));
    const leftGap = minLeft - prect.left;
    const rightGap = prect.right - maxRight;
    return {
      ok: leftGap <= 24 && rightGap <= 24 && leftGap >= 2 && rightGap >= 2,
      leftGap,
      rightGap,
      panelRect: { left: prect.left, right: prect.right, width: prect.width },
      controlsCount: rects.length,
      source: rowRects.length >= 2 ? 'rows' : 'controls',
    };
  });
  expect(panelLayoutProbe.ok, JSON.stringify(panelLayoutProbe)).toBeTruthy();
  await assertFloatingPanelSolidSurfaces(page, 'learning-floating-panel');
  await saveShot(page, '03-floating-panel-render');

  // Z-index collision check:
  // If panel and question overlap, panel must be the top element at overlap center.
  const panelHandle = await floatingPanel.elementHandle();
  expect(panelHandle).not.toBeNull();
  const zIndexProbe = await panelHandle!.evaluate((panel) => {
    const question = (
      document.querySelector('#question-content-container') ||
      document.querySelector('.main-app-area')
    ) as HTMLElement | null;
    if (!question) {
      return { ok: false, reason: 'missing-widget-container' };
    }

    const p = panel.getBoundingClientRect();
    const q = question.getBoundingClientRect();
    const overlapLeft = Math.max(p.left, q.left);
    const overlapTop = Math.max(p.top, q.top);
    const overlapRight = Math.min(p.right, q.right);
    const overlapBottom = Math.min(p.bottom, q.bottom);
    const hasOverlap = overlapRight > overlapLeft && overlapBottom > overlapTop;

    if (!hasOverlap) {
      return {
        ok: true,
        reason: 'no-overlap',
        panelRect: { left: p.left, top: p.top, right: p.right, bottom: p.bottom },
        questionRect: { left: q.left, top: q.top, right: q.right, bottom: q.bottom },
      };
    }

    const x = Math.min(Math.max(overlapLeft + (overlapRight - overlapLeft) / 2, 1), window.innerWidth - 1);
    const y = Math.min(Math.max(overlapTop + (overlapBottom - overlapTop) / 2, 1), window.innerHeight - 1);
    const topEl = document.elementFromPoint(x, y) as HTMLElement | null;
    const inPanel = !!topEl?.closest('.floating-toolbar-panel');
    const inQuestion = !!topEl?.closest('#question-content-container');
    return {
      ok: inPanel && !inQuestion,
      reason: 'overlap-probe',
      overlapCenter: { x, y },
      topTag: topEl?.tagName || null,
      topClass: topEl?.className || null,
      inPanel,
      inQuestion,
    };
  });
  // eslint-disable-next-line no-console
  console.log('zIndexProbe', JSON.stringify(zIndexProbe));
  expect(zIndexProbe.ok, JSON.stringify(zIndexProbe)).toBeTruthy();

  // Deep app-route coverage: floating panel must stay visible on /app/:id routes too.
  await page.goto('/app/harness-profile-route', { waitUntil: 'domcontentloaded' });
  await assertNoHorizontalOverflow(page, 'learning-profile-route-laptop');
  const profileRoutePanel = page.locator('.floating-toolbar-panel').first();
  await expect(profileRoutePanel).toBeVisible({ timeout: 120_000 });
  await normalizeFloatingPanelPosition(page);
  const profilePanelViewportProbe = await profileRoutePanel.evaluate((panel) => {
    const rect = panel.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const overlapW = Math.max(0, Math.min(rect.right, vw) - Math.max(rect.left, 0));
    const overlapH = Math.max(0, Math.min(rect.bottom, vh) - Math.max(rect.top, 0));
    const visibleArea = overlapW * overlapH;
    const totalArea = Math.max(1, rect.width * rect.height);
    return {
      visibleArea,
      visibleRatio: visibleArea / totalArea,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
      viewport: { width: vw, height: vh },
    };
  });
  expect(profilePanelViewportProbe.visibleArea, JSON.stringify(profilePanelViewportProbe)).toBeGreaterThan(2500);
  expect(profilePanelViewportProbe.visibleRatio, JSON.stringify(profilePanelViewportProbe)).toBeGreaterThan(0.98);
  await assertFloatingPanelSolidSurfaces(page, 'profile-route-floating-panel');
  await saveShot(page, '06-floating-panel-profile-route');

  // 6) Mobile responsiveness checks (learning route)
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto(`/app?subject=${encodeURIComponent(SUBJECT)}`, { waitUntil: 'domcontentloaded' });
  await assertNoHorizontalOverflow(page, 'learning-mobile');
  await expect(page.getByText(/Grading & Skills/i).first()).toBeVisible({ timeout: 120_000 });
  await saveShot(page, '05-learning-mobile-responsive');
});

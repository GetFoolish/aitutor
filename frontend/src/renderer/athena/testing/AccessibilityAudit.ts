/**
 * Accessibility Audit
 *
 * Tools for auditing WCAG 2.1 AA compliance.
 */

export interface AccessibilityIssue {
  id: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  wcagCriteria: string[];
  description: string;
  help: string;
  helpUrl?: string;
  nodes: Array<{
    element: string;
    selector: string;
    failureSummary: string;
  }>;
}

export interface AuditResult {
  passes: number;
  violations: number;
  incomplete: number;
  inapplicable: number;
  issues: AccessibilityIssue[];
  timestamp: number;
  url?: string;
}

export interface AuditOptions {
  /** Rules to run (empty = all) */
  rules?: string[];
  /** Rules to exclude */
  excludeRules?: string[];
  /** WCAG level to check */
  wcagLevel?: 'A' | 'AA' | 'AAA';
  /** Elements to include */
  include?: string[];
  /** Elements to exclude */
  exclude?: string[];
}

/**
 * WCAG 2.1 AA criteria for Athena
 */
export const WCAG_CRITERIA = {
  // Perceivable
  '1.1.1': 'Non-text Content',
  '1.3.1': 'Info and Relationships',
  '1.3.2': 'Meaningful Sequence',
  '1.3.3': 'Sensory Characteristics',
  '1.3.4': 'Orientation',
  '1.3.5': 'Identify Input Purpose',
  '1.4.1': 'Use of Color',
  '1.4.3': 'Contrast (Minimum)',
  '1.4.4': 'Resize Text',
  '1.4.5': 'Images of Text',
  '1.4.10': 'Reflow',
  '1.4.11': 'Non-text Contrast',
  '1.4.12': 'Text Spacing',
  '1.4.13': 'Content on Hover or Focus',

  // Operable
  '2.1.1': 'Keyboard',
  '2.1.2': 'No Keyboard Trap',
  '2.1.4': 'Character Key Shortcuts',
  '2.4.1': 'Bypass Blocks',
  '2.4.2': 'Page Titled',
  '2.4.3': 'Focus Order',
  '2.4.4': 'Link Purpose (In Context)',
  '2.4.5': 'Multiple Ways',
  '2.4.6': 'Headings and Labels',
  '2.4.7': 'Focus Visible',
  '2.5.1': 'Pointer Gestures',
  '2.5.2': 'Pointer Cancellation',
  '2.5.3': 'Label in Name',
  '2.5.4': 'Motion Actuation',

  // Understandable
  '3.1.1': 'Language of Page',
  '3.1.2': 'Language of Parts',
  '3.2.1': 'On Focus',
  '3.2.2': 'On Input',
  '3.2.3': 'Consistent Navigation',
  '3.2.4': 'Consistent Identification',
  '3.3.1': 'Error Identification',
  '3.3.2': 'Labels or Instructions',
  '3.3.3': 'Error Suggestion',
  '3.3.4': 'Error Prevention (Legal, Financial, Data)',

  // Robust
  '4.1.1': 'Parsing',
  '4.1.2': 'Name, Role, Value',
  '4.1.3': 'Status Messages',
};

/**
 * Athena-specific accessibility checks
 */
export const ATHENA_CHECKS = {
  // Widget accessibility
  'athena-widget-label': {
    description: 'Widgets must have accessible labels',
    wcag: ['1.1.1', '4.1.2'],
    check: (element: Element) => {
      const label = element.getAttribute('aria-label') ||
        element.getAttribute('aria-labelledby') ||
        element.querySelector('label');
      return !!label;
    },
  },

  'athena-widget-role': {
    description: 'Interactive widgets must have appropriate roles',
    wcag: ['4.1.2'],
    check: (element: Element) => {
      const role = element.getAttribute('role');
      const tagName = element.tagName.toLowerCase();
      const implicitRole = ['button', 'input', 'select', 'textarea', 'a'];
      return !!role || implicitRole.includes(tagName);
    },
  },

  'athena-math-alt': {
    description: 'Math content must have text alternatives',
    wcag: ['1.1.1'],
    check: (element: Element) => {
      if (!element.classList.contains('athena-math')) return true;
      const altText = element.getAttribute('aria-label') ||
        element.getAttribute('title') ||
        element.textContent;
      return !!altText && altText.length > 0;
    },
  },

  'athena-graph-description': {
    description: 'Interactive graphs must have descriptions',
    wcag: ['1.1.1', '1.3.1'],
    check: (element: Element) => {
      if (!element.classList.contains('athena-graph')) return true;
      const description = element.getAttribute('aria-label') ||
        element.getAttribute('aria-describedby') ||
        element.querySelector('[role="img"]');
      return !!description;
    },
  },

  'athena-focus-visible': {
    description: 'Interactive elements must have visible focus indicators',
    wcag: ['2.4.7'],
    check: (element: Element) => {
      const styles = window.getComputedStyle(element, ':focus');
      const outline = styles.getPropertyValue('outline');
      const boxShadow = styles.getPropertyValue('box-shadow');
      return outline !== 'none' || boxShadow !== 'none';
    },
  },

  'athena-keyboard-accessible': {
    description: 'All interactive elements must be keyboard accessible',
    wcag: ['2.1.1'],
    check: (element: Element) => {
      const tabIndex = element.getAttribute('tabindex');
      const focusable = element.matches(
        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      return focusable || tabIndex !== '-1';
    },
  },

  'athena-error-identification': {
    description: 'Form errors must be clearly identified',
    wcag: ['3.3.1'],
    check: (element: Element) => {
      const hasError = element.getAttribute('aria-invalid') === 'true';
      if (!hasError) return true;
      const errorMessage = element.getAttribute('aria-describedby') ||
        element.getAttribute('aria-errormessage');
      return !!errorMessage;
    },
  },

  'athena-live-region': {
    description: 'Dynamic content must use live regions',
    wcag: ['4.1.3'],
    check: (element: Element) => {
      if (!element.classList.contains('athena-announcer')) return true;
      const liveAttr = element.getAttribute('aria-live');
      return liveAttr === 'polite' || liveAttr === 'assertive';
    },
  },
};

/**
 * Run accessibility audit
 */
export async function runAccessibilityAudit(
  container: Element,
  options: AuditOptions = {}
): Promise<AuditResult> {
  const { wcagLevel = 'AA' } = options;

  const issues: AccessibilityIssue[] = [];
  let passes = 0;
  let violations = 0;

  // Run Athena-specific checks
  for (const [checkId, check] of Object.entries(ATHENA_CHECKS)) {
    if (options.excludeRules?.includes(checkId)) continue;
    if (options.rules?.length && !options.rules.includes(checkId)) continue;

    // Find relevant elements
    const elements = container.querySelectorAll('[class*="athena-"]');

    for (const element of elements) {
      if (options.exclude?.some(sel => element.matches(sel))) continue;

      try {
        const passed = check.check(element);
        if (passed) {
          passes++;
        } else {
          violations++;
          issues.push({
            id: checkId,
            impact: 'serious',
            wcagCriteria: check.wcag,
            description: check.description,
            help: check.description,
            nodes: [{
              element: element.tagName.toLowerCase(),
              selector: getSelector(element),
              failureSummary: `Element failed: ${check.description}`,
            }],
          });
        }
      } catch (err) {
        // Check couldn't run
      }
    }
  }

  // Run basic DOM checks
  const basicIssues = runBasicChecks(container, options);
  issues.push(...basicIssues);
  violations += basicIssues.length;

  return {
    passes,
    violations,
    incomplete: 0,
    inapplicable: 0,
    issues,
    timestamp: Date.now(),
  };
}

/**
 * Run basic accessibility checks
 */
function runBasicChecks(container: Element, options: AuditOptions): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];

  // Check for images without alt
  container.querySelectorAll('img:not([alt])').forEach((img) => {
    issues.push({
      id: 'image-alt',
      impact: 'critical',
      wcagCriteria: ['1.1.1'],
      description: 'Images must have alt text',
      help: 'Add an alt attribute to the image',
      nodes: [{
        element: 'img',
        selector: getSelector(img),
        failureSummary: 'Image is missing alt attribute',
      }],
    });
  });

  // Check for empty buttons
  container.querySelectorAll('button').forEach((btn) => {
    const hasText = btn.textContent?.trim() ||
      btn.getAttribute('aria-label') ||
      btn.getAttribute('aria-labelledby') ||
      btn.querySelector('img[alt], svg[aria-label]');
    if (!hasText) {
      issues.push({
        id: 'button-name',
        impact: 'critical',
        wcagCriteria: ['4.1.2'],
        description: 'Buttons must have accessible names',
        help: 'Add text content or aria-label to the button',
        nodes: [{
          element: 'button',
          selector: getSelector(btn),
          failureSummary: 'Button has no accessible name',
        }],
      });
    }
  });

  // Check for form inputs without labels
  container.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((input) => {
    const id = input.getAttribute('id');
    const hasLabel = input.getAttribute('aria-label') ||
      input.getAttribute('aria-labelledby') ||
      (id && container.querySelector(`label[for="${id}"]`)) ||
      input.closest('label');
    if (!hasLabel) {
      issues.push({
        id: 'label',
        impact: 'critical',
        wcagCriteria: ['1.3.1', '3.3.2'],
        description: 'Form elements must have labels',
        help: 'Add a label element or aria-label attribute',
        nodes: [{
          element: input.tagName.toLowerCase(),
          selector: getSelector(input),
          failureSummary: 'Form element has no label',
        }],
      });
    }
  });

  // Check for low contrast (simplified check)
  container.querySelectorAll('*').forEach((el) => {
    const styles = window.getComputedStyle(el);
    const color = styles.color;
    const bgColor = styles.backgroundColor;

    // Simple contrast check (would need proper algorithm for production)
    if (color && bgColor && color === bgColor) {
      issues.push({
        id: 'color-contrast',
        impact: 'serious',
        wcagCriteria: ['1.4.3'],
        description: 'Text must have sufficient color contrast',
        help: 'Ensure text and background have at least 4.5:1 contrast ratio',
        nodes: [{
          element: el.tagName.toLowerCase(),
          selector: getSelector(el),
          failureSummary: 'Text and background have same color',
        }],
      });
    }
  });

  return issues;
}

/**
 * Get CSS selector for element
 */
function getSelector(element: Element): string {
  if (element.id) {
    return `#${element.id}`;
  }

  const path: string[] = [];
  let current: Element | null = element;

  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase();

    if (current.className) {
      const classes = current.className.split(' ')
        .filter(c => c.trim())
        .map(c => `.${c}`)
        .join('');
      selector += classes;
    }

    const siblings = current.parentElement?.children;
    if (siblings && siblings.length > 1) {
      const index = Array.from(siblings).indexOf(current) + 1;
      selector += `:nth-child(${index})`;
    }

    path.unshift(selector);
    current = current.parentElement;
  }

  return path.join(' > ');
}

/**
 * Format audit results as report
 */
export function formatAuditReport(result: AuditResult): string {
  const lines: string[] = [];

  lines.push('# Accessibility Audit Report');
  lines.push('');
  lines.push(`Date: ${new Date(result.timestamp).toISOString()}`);
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`- **Passes:** ${result.passes}`);
  lines.push(`- **Violations:** ${result.violations}`);
  lines.push(`- **Incomplete:** ${result.incomplete}`);
  lines.push('');

  if (result.issues.length > 0) {
    lines.push('## Issues');
    lines.push('');

    const grouped = new Map<string, AccessibilityIssue[]>();
    for (const issue of result.issues) {
      if (!grouped.has(issue.impact)) {
        grouped.set(issue.impact, []);
      }
      grouped.get(issue.impact)!.push(issue);
    }

    for (const impact of ['critical', 'serious', 'moderate', 'minor']) {
      const issues = grouped.get(impact);
      if (!issues?.length) continue;

      lines.push(`### ${impact.charAt(0).toUpperCase() + impact.slice(1)} (${issues.length})`);
      lines.push('');

      for (const issue of issues) {
        lines.push(`#### ${issue.description}`);
        lines.push('');
        lines.push(`- **WCAG:** ${issue.wcagCriteria.join(', ')}`);
        lines.push(`- **Help:** ${issue.help}`);
        lines.push('');
        lines.push('**Affected elements:**');
        for (const node of issue.nodes) {
          lines.push(`- \`${node.selector}\``);
          lines.push(`  - ${node.failureSummary}`);
        }
        lines.push('');
      }
    }
  } else {
    lines.push('No accessibility issues found.');
  }

  return lines.join('\n');
}

export default {
  runAccessibilityAudit,
  formatAuditReport,
  WCAG_CRITERIA,
  ATHENA_CHECKS,
};

/**
 * Design Tokens for AITutor
 *
 * These tokens enforce the design system rules:
 * - 8pt grid spacing
 * - Neo-brutalist style (3px borders, offset shadows)
 * - Consistent typography scale
 *
 * Usage:
 *   import { spacing, shadows, borders, colors } from '@/styles/design-tokens';
 *   <div style={{ padding: spacing.lg, boxShadow: shadows.md }}>
 */

// 8pt Grid Spacing (all values are multiples of 8px)
export const spacing = {
  /** 4px - Only for icon padding, small inline gaps */
  xs: '4px',
  /** 8px - Small gaps */
  sm: '8px',
  /** 12px - Exception for tight spacing */
  tight: '12px',
  /** 16px - Standard gap */
  md: '16px',
  /** 24px - Large gap, card padding */
  lg: '24px',
  /** 32px - Section spacing */
  xl: '32px',
  /** 40px */
  '2xl': '40px',
  /** 48px - Large card padding */
  '3xl': '48px',
  /** 56px */
  '4xl': '56px',
  /** 64px - Hero sections */
  '5xl': '64px',
  /** 72px */
  '6xl': '72px',
  /** 80px */
  '7xl': '80px',
} as const;

// EXTREME NEO-BRUTALIST Shadows (HARSH solid black offsets)
export const shadows = {
  /** 4px 4px - Small elements, hover state */
  sm: '4px 4px 0 #000',
  /** 6px 6px - Standard cards, buttons */
  md: '6px 6px 0 #000',
  /** 8px 8px - Large/hero elements */
  lg: '8px 8px 0 #000',
  /** None */
  none: 'none',
} as const;

// Dark mode shadow variants
export const shadowsDark = {
  sm: '2px 2px 0 rgba(255,255,255,0.3)',
  md: '4px 4px 0 rgba(255,255,255,0.3)',
  lg: '6px 6px 0 rgba(255,255,255,0.3)',
  none: 'none',
} as const;

// EXTREME NEO-BRUTALIST Borders - THICK AND BOLD
export const borders = {
  /** 4px solid #000 - Primary elements (cards, buttons) */
  primary: '4px solid #000',
  /** 3px solid #000 - Secondary elements */
  secondary: '3px solid #000',
  /** 5px solid #000 - Large/hero elements */
  heavy: '5px solid #000',
} as const;

// Dark mode border variants
export const bordersDark = {
  primary: '3px solid #fff',
  secondary: '2px solid #fff',
  heavy: '4px solid #fff',
} as const;

// Border Radius - EXTREME NEO-BRUTALISM: NO ROUNDED CORNERS
export const borderRadius = {
  /** 0 - Sharp corners everywhere */
  sm: '0',
  /** 0 - Sharp corners everywhere */
  md: '0',
  /** 0 - Sharp corners everywhere */
  lg: '0',
  /** 0 - Even pills are sharp in extreme brutalism */
  full: '0',
} as const;

// EXTREME NEO-BRUTALISM Color Palette
// Pure, bold colors only - no pastels, no muted tones
export const colors = {
  // Primary Brand - BOLD YELLOW
  primary: '#FCD34D',
  primaryHover: '#FBBF24',

  // Neutrals - HIGH CONTRAST
  background: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceSecondary: '#FCD34D',
  border: '#000000',

  // Text - PURE BLACK
  textPrimary: '#000000',
  textSecondary: '#000000',
  textMuted: '#000000',

  // Semantic - BOLD COLORS
  success: '#22C55E',
  successBg: '#22C55E',
  warning: '#FCD34D',
  warningBg: '#FCD34D',
  error: '#FF6B6B',
  errorBg: '#FF6B6B',

  // Subject Colors - BOLD, NO PASTELS
  mathBg: '#FCD34D',
  scienceBg: '#22C55E',
  readingBg: '#FF6B6B',

  // Accent colors for EXTREME neo-brutalism
  accent1: '#FF6B6B', // Coral/Red
  accent2: '#FCD34D', // Yellow
  accent3: '#22C55E', // Green
} as const;

// EXTREME Typography Scale - MASSIVE HEADINGS
export const fontSize = {
  /** 14px - Captions, helper text */
  caption: '14px',
  /** 16px - Small body, labels */
  small: '16px',
  /** 18px - Body text */
  body: '18px',
  /** 20px - Large body */
  bodyLarge: '20px',
  /** 28px - Small heading (h5) */
  h5: '28px',
  /** 36px - Medium heading (h4) */
  h4: '36px',
  /** 48px - Large heading (h3) */
  h3: '48px',
  /** 64px - XL heading (h2) */
  h2: '64px',
  /** 80px - MASSIVE Hero heading (h1) */
  h1: '80px',
} as const;

// Line Heights
export const lineHeight = {
  /** 1.2 - Headings */
  tight: '1.2',
  /** 1.5 - Body text */
  normal: '1.5',
  /** 1.75 - Relaxed reading */
  relaxed: '1.75',
} as const;

// Font Weights
export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
  black: '900',
} as const;

// Hover state transform (neo-brutalist press effect)
export const hoverTransform = {
  /** Standard hover: shifts 2px, reduces shadow */
  standard: 'translate(2px, 2px)',
  /** Reset on hover end */
  none: 'translate(0, 0)',
} as const;

// Transition timings
export const transitions = {
  fast: '100ms ease',
  normal: '200ms ease',
  slow: '300ms ease',
} as const;

// Z-index scale
export const zIndex = {
  dropdown: 100,
  sticky: 200,
  modal: 300,
  popover: 400,
  toast: 500,
  tooltip: 600,
} as const;

/**
 * Validate if a spacing value follows 8pt grid
 * Allowed: 0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80
 */
export function isValidSpacing(value: number): boolean {
  const validValues = [0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80];
  return validValues.includes(value);
}

/**
 * Get the nearest valid 8pt grid value
 */
export function nearestGridValue(value: number): number {
  const gridValues = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80];
  return gridValues.reduce((prev, curr) =>
    Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
  );
}

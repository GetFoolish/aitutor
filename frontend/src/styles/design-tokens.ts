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

// Neo-Brutalist Shadows (solid black offsets, NO blur)
export const shadows = {
  /** 2px 2px - Small elements, hover state */
  sm: '2px 2px 0 #000',
  /** 4px 4px - Standard cards, buttons */
  md: '4px 4px 0 #000',
  /** 6px 6px - Large/hero elements */
  lg: '6px 6px 0 #000',
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

// Neo-Brutalist Borders
export const borders = {
  /** 3px solid #000 - Primary elements (cards, buttons) */
  primary: '3px solid #000',
  /** 2px solid #000 - Secondary elements */
  secondary: '2px solid #000',
  /** 4px solid #000 - Large/hero elements */
  heavy: '4px solid #000',
} as const;

// Dark mode border variants
export const bordersDark = {
  primary: '3px solid #fff',
  secondary: '2px solid #fff',
  heavy: '4px solid #fff',
} as const;

// Border Radius
export const borderRadius = {
  /** 8px - Small elements */
  sm: '8px',
  /** 12px - Standard (cards, buttons) */
  md: '12px',
  /** 16px - Large cards */
  lg: '16px',
  /** 999px - Pills, badges */
  full: '999px',
} as const;

// Color Palette
export const colors = {
  // Primary Brand
  primary: '#6C63FF',
  primaryHover: '#5B52E0',

  // Neutrals
  background: '#FFFDF5',
  surface: '#FFFFFF',
  surfaceSecondary: '#F5F5F5',
  border: '#000000',

  // Text
  textPrimary: '#000000',
  textSecondary: '#666666',
  textMuted: '#888888',

  // Semantic
  success: '#4CAF50',
  successBg: '#ADFF2F',
  warning: '#FF9800',
  warningBg: '#FFD93D',
  error: '#F44336',
  errorBg: '#FF006E',

  // Subject Colors
  mathBg: '#E3F2FD',
  scienceBg: '#E8F5E9',
  readingBg: '#FFF3E0',

  // Accent colors for neo-brutalism
  accent1: '#C4B5FD', // Purple tint
  accent2: '#FFD93D', // Yellow
  accent3: '#4ADE80', // Green
} as const;

// Typography Scale
export const fontSize = {
  /** 12px - Captions, helper text */
  caption: '12px',
  /** 14px - Small body, labels */
  small: '14px',
  /** 16px - Body text (minimum for readability) */
  body: '16px',
  /** 18px - Large body */
  bodyLarge: '18px',
  /** 20px - Small heading (h5) */
  h5: '20px',
  /** 24px - Medium heading (h4) */
  h4: '24px',
  /** 32px - Large heading (h3) */
  h3: '32px',
  /** 40px - XL heading (h2) */
  h2: '40px',
  /** 48px - Hero heading (h1) */
  h1: '48px',
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

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Neo-Brutalism Box Shadows (hard offset, zero blur)
      boxShadow: {
        'neo-xs': '2px 2px 0 #000',
        'neo-sm': '3px 3px 0 #000',
        'neo': '4px 4px 0 #000',
        'neo-md': '6px 6px 0 #000',
        'neo-lg': '8px 8px 0 #000',
        'neo-xl': '12px 12px 0 #000',
        'neo-2xl': '16px 16px 0 #000',
        // Dark mode variants
        'neo-dark': '4px 4px 0 rgba(255,255,255,0.4)',
        'neo-md-dark': '6px 6px 0 rgba(255,255,255,0.4)',
        'neo-lg-dark': '8px 8px 0 rgba(255,255,255,0.4)',
      },

      // Neo-Brutalism Border Widths
      borderWidth: {
        'neo': '4px',
        'neo-thick': '5px',
      },

      // Neo-Brutalism Colors
      colors: {
        'neo': {
          'bg': '#FFFDF5',         // Cream background
          'black': '#000000',      // Pure black
          'white': '#FFFFFF',      // Pure white
          'red': '#FF6B6B',        // Hot Red
          'yellow': '#FFD93D',     // Vivid Yellow
          'violet': '#C4B5FD',     // Soft Violet
          'blue': '#60A5FA',       // Electric Blue
        },
      },

      // Typography
      fontFamily: {
        'sans': ['Space Grotesk', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        'mono': ['Space Mono', 'Courier New', 'monospace'], // Only for code blocks
      },

      // Font sizes (minimum 14px for body, 16px+ for interactive)
      fontSize: {
        'xs': ['14px', { lineHeight: '1.4', fontWeight: '700' }],
        'sm': ['16px', { lineHeight: '1.5', fontWeight: '700' }],
        'base': ['18px', { lineHeight: '1.6', fontWeight: '600' }],
        'lg': ['20px', { lineHeight: '1.6', fontWeight: '700' }],
        'xl': ['24px', { lineHeight: '1.4', fontWeight: '900' }],
        '2xl': ['30px', { lineHeight: '1.3', fontWeight: '900' }],
        '3xl': ['36px', { lineHeight: '1.2', fontWeight: '900' }],
        '4xl': ['48px', { lineHeight: '1.1', fontWeight: '900' }],
      },

      // Border radius (sharp corners only, except pills)
      borderRadius: {
        'none': '0',
        'full': '9999px', // Only for pills/badges
        // Remove all other radius values
        DEFAULT: '0',
      },

      // Animation for neo-brutalist press effect
      transitionProperty: {
        'neo': 'transform, box-shadow',
      },

      // Z-index scale
      zIndex: {
        'modal': '100',
        'overlay': '90',
        'dropdown': '80',
        'sticky': '70',
        'header': '60',
        'panel': '50',
      },
    },
  },
  plugins: [],
}

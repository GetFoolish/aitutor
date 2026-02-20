# Frontend UI Audit — Neo-Brutalism Violations

**Reference:** https://www.designprompts.dev/neo-brutalism
**Date:** February 20, 2026

---

## TL;DR — 5 Things Any Good Frontend Dev Would Have Caught

1. **Question content is literally invisible** — the question panel has `height: 0` + `overflow: hidden`, so students see a blank screen
2. **Buttons are comically small** — `h-8` (32px), `h-9` (36px) when neo-brutalism demands 48px+ minimum
3. **Rounded corners everywhere** — `rounded-md`, `rounded-lg`, `rounded-xl` used 40+ times when the spec says **0px sharp corners only**
4. **Soft blurry shadows** — every shadow has blur-radius values when the spec explicitly says **zero blur, hard offset only**
5. **Font sizes for ants** — `text-xs` (12px) on buttons and labels, `font-size: 11px` on body

---

## BLOCKING BUG: Question Content Invisible

The entire question panel renders with `height: 0px` and `overflow: hidden`. Students can't see any questions or answer choices. This is the #1 priority.

**Root cause:** Nested flex containers with `flex: 1 1 0%` and `min-height: 0px` collapse to zero. The `framework-perseus` container and two parent wrappers all have `overflow: hidden` with computed height 0.

**Fix:** The content wrapper between the header and submit button needs explicit `min-height` or `flex-shrink: 0` instead of relying on flex growth in a constrained parent.

---

## CATEGORY 1: Wrong Border Widths (40+ violations)

The spec says **`border-4` (4px) on ALL visual elements**. The codebase mixes 1px, 2px, 3px, and 4px randomly.

| Component | Current | Should Be | File |
|-----------|---------|-----------|------|
| Subject buttons (inactive) | `border: 3px` | `border: 4px` | DevLogin.tsx |
| Age buttons | `border: 3px` | `border: 4px` | DevLogin.tsx |
| Theme toggle | `border: 3px` | `border: 4px` | DevLogin.tsx |
| Exit button | `border: 3px` | `border: 4px` | AssessmentFlow.tsx |
| Try Again button | `border: 3px` | `border: 4px` | AssessmentFlow.tsx |
| Error banner | `border: 3px` | `border: 4px` | AssessmentFlow.tsx |
| Progress bar divider | `border-t-[3px]` | `border-t-[4px]` | AssessmentQuestion.tsx |
| Question container (mobile) | `border-[3px]` | `border-[4px]` | AssessmentQuestion.tsx |
| Hint display | `border-[3px]` | `border-[4px]` | AssessmentQuestion.tsx |
| Hint button | `border-[3px]` | `border-[4px]` | AssessmentQuestion.tsx |
| Skip question box | `border-[3px]` | `border-[4px]` | AssessmentQuestion.tsx |
| Perseus inputs | `border: 2px` | `border: 4px` | index.css |
| Dropdown triggers | `border: 2px` | `border: 4px` | index.css |
| All shadcn/ui components | `border` (1px) | `border-4` | button.tsx, card.tsx, input.tsx |

---

## CATEGORY 2: Forbidden Rounded Corners (40+ violations)

Neo-brutalism is **sharp corners (0px) or fully round (pills only)**. Never `rounded-md`, `rounded-lg`, `rounded-xl`.

| Component | Current | Should Be | File |
|-----------|---------|-----------|------|
| Button (base) | `rounded-md` | `rounded-none` | button.tsx |
| Button (sm) | `rounded-md` | `rounded-none` | button.tsx |
| Button (lg) | `rounded-md` | `rounded-none` | button.tsx |
| Card | `rounded-xl` | `rounded-none` | card.tsx |
| Input | `rounded-md` | `rounded-none` | input.tsx |
| Badge | `rounded-md` | `rounded-full` (exception for pills) | badge.tsx |
| Progress bar | `rounded-full` | `rounded-none` | progress.tsx |
| Slider track | `rounded-full` | `rounded-none` | slider.tsx |
| Tabs | `rounded-lg` | `rounded-none` | tabs.tsx |
| Alert dialog | `sm:rounded-lg` | `rounded-none` | alert-dialog.tsx |
| SignupForm | `rounded-xl` | `rounded-none` | SignupForm.tsx |
| Stream element | `border-radius: 32px` | `border-radius: 0` | App.scss line 414 |
| Scratchpad | `border-radius: 8px` | `border-radius: 0` | index.css line 76 |
| Perseus inputs | `border-radius: 6px` | `border-radius: 0` | index.css |
| Dropdown triggers | `border-radius: 6px` | `border-radius: 0` | index.css |
| Popper menus | `border-radius: 6px` | `border-radius: 0` | index.css |

---

## CATEGORY 3: Soft/Blurry Shadows (30+ violations)

Neo-brutalism shadows are **solid black, hard offset, ZERO blur**. Like `4px 4px 0 #000`. The codebase is full of gaussian blur shadows.

| Location | Current | Should Be |
|----------|---------|-----------|
| index.css `--shadow-2xs` | `0px 4px 8px -1px hsl(0 0% 0% / 0.05)` | `2px 2px 0 #000` |
| index.css `--shadow-xs` | `0px 4px 8px -1px hsl(0 0% 0% / 0.05)` | `3px 3px 0 #000` |
| index.css `--shadow-sm` | `0px 4px 8px -1px ... 0px 1px 2px -2px` | `4px 4px 0 #000` |
| Perseus inputs | `box-shadow: 0 4px 10px rgba(0,0,0,0.08)` | `box-shadow: 3px 3px 0 #000` |
| Dropdown triggers | `box-shadow: 0 4px 10px rgba(0,0,0,0.08)` | `box-shadow: 3px 3px 0 #000` |
| Popper menus | `box-shadow: 0 4px 10px rgba(0,0,0,0.08)` | `box-shadow: 4px 4px 0 #000` |
| SignupForm | `shadow-2xl backdrop-blur-xl` | `shadow-[8px_8px_0_#000]` no blur |
| AssessmentFlow overlay | `backdropFilter: 'blur(1px)'` | Remove entirely |
| Question container shadow | `shadow-[2px_2px_0_0_...]` | `shadow-[4px_4px_0_0_#000]` minimum |
| Hint display shadow | `shadow-[2px_2px_0_0...]` | `shadow-[4px_4px_0_0_#000]` |

---

## CATEGORY 4: Buttons Too Small (25+ violations)

Neo-brutalism buttons are **chunky, bold, prominent**. Minimum 48px height, 16px+ font, bold weight.

| Component | Height | Font | Weight | Issues |
|-----------|--------|------|--------|--------|
| Button (default) | `h-9` (36px) | `text-sm` (14px) | `font-medium` | Too short, too thin, too light |
| Button (sm) | `h-8` (32px) | `text-xs` (12px) | `font-medium` | Way too small |
| Button (lg) | `h-10` (40px) | — | `font-medium` | Still under 48px |
| Hint button | — | `text-[12px]` | `font-bold` | Text microscopic |
| Try Again | — | `14px` | `700` | Font too small |
| Error message text | — | `14px` | — | Below minimum |
| Mobile min-height | `44px` | — | — | Should be 48px |

**Fix:** Update button.tsx base variants:
```
default: "h-12 px-6 py-3 text-base font-bold border-4 border-black shadow-[4px_4px_0_#000]"
sm: "h-10 px-4 py-2 text-sm font-bold border-4 border-black shadow-[3px_3px_0_#000]"
lg: "h-14 px-8 py-4 text-lg font-black border-4 border-black shadow-[6px_6px_0_#000]"
```

---

## CATEGORY 5: Typography Violations (25+ violations)

| Issue | Current | Should Be | Locations |
|-------|---------|-----------|-----------|
| Wrong font | `Space Mono` | `Space Grotesk` | App.scss line 51 |
| Body font size | `11px` | `14px` minimum | App.scss line 106 |
| Button weight | `font-medium` (500) | `font-bold` (700) minimum | button.tsx |
| Badge text | `text-xs font-semibold` | `text-sm font-bold` | badge.tsx |
| Missing uppercase | Many buttons/labels | `uppercase` on all buttons, labels, headings | Throughout |
| Hint text | `text-[12px]` | `text-sm` (14px) minimum | AssessmentQuestion.tsx |

---

## CATEGORY 6: User Flow Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| Question content invisible | Students can't see questions | Fix flex container heights |
| Submit button ABOVE question content | Backwards flow — button before content | Fix element order in assessment layout |
| Exit button doesn't work | Users trapped in assessment | Fix click handler / z-index issues |
| No hover states on age buttons | Buttons feel dead, no feedback | Add `hover:-translate-y-1 hover:shadow-[5px_5px_0_#000]` |
| Subject buttons inconsistent borders | Active=4px, inactive=3px | All should be 4px, active gets different bg color |
| No press-down effect on most buttons | Doesn't feel neo-brutalist "mechanical" | Add `active:translate-x-[4px] active:translate-y-[4px] active:shadow-none` |
| Dark mode toggle tiny (36x36) | Hard to tap on mobile | Minimum 48x48 |
| Decorative shapes overlap content | Shapes positioned over interactive elements | Add `pointer-events-none` and ensure z-index ordering |

---

## CATEGORY 7: Missing Tailwind Config

`tailwind.config.js` has NO neo-brutalism theme overrides. All the design tokens should be centralized there:

```js
// Missing from tailwind.config.js:
theme: {
  extend: {
    boxShadow: {
      'neo-sm': '3px 3px 0 #000',
      'neo': '4px 4px 0 #000',
      'neo-md': '6px 6px 0 #000',
      'neo-lg': '8px 8px 0 #000',
      'neo-xl': '12px 12px 0 #000',
    },
    borderWidth: {
      'neo': '4px',
    },
    fontFamily: {
      'sans': ['Space Grotesk', 'system-ui', 'sans-serif'],
    },
    colors: {
      'neo-bg': '#FFFDF5',
      'neo-red': '#FF6B6B',
      'neo-yellow': '#FFD93D',
      'neo-violet': '#C4B5FD',
      'neo-blue': '#60A5FA',
    },
  },
}
```

---

## PRIORITY FIX ORDER

### P0 — Blocking (do these first)
1. Fix question content panel `height: 0` / `overflow: hidden` — students literally can't see questions
2. Fix element order — submit button should be BELOW question content, not above
3. Fix exit button click handler

### P1 — High (design system fundamentals)
4. Update `tailwind.config.js` with neo-brutalism theme tokens
5. Fix `button.tsx` — sharp corners, 4px borders, hard shadows, 48px+ height, bold font
6. Fix `card.tsx` — sharp corners, 4px borders, hard shadows
7. Fix `input.tsx` — sharp corners, 4px borders
8. Replace ALL shadow definitions in `index.css` with hard-offset shadows
9. Fix App.scss: change `Space Mono` to `Space Grotesk`, fix `11px` body font

### P2 — Medium (component consistency)
10. Update ALL `border-[3px]` to `border-[4px]` in AssessmentQuestion.tsx
11. Update ALL `border: 3px` to `border: 4px` in AssessmentFlow.tsx and DevLogin.tsx
12. Remove all `rounded-md/lg/xl` from UI components (tabs, alert-dialog, badge, progress, slider)
13. Remove `backdrop-blur` from SignupForm and overlay components
14. Add hover/active states with translate press-down effect to all interactive elements

### P3 — Low (polish)
15. Add `uppercase` to all button and label text
16. Increase all `text-xs` to `text-sm` minimum
17. Standardize shadow offsets (4px for buttons, 8px for cards, 12px for modals)
18. Add missing `pointer-events-none` to decorative shapes

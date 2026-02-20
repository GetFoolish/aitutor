# QA Bug Verification Report — Round 4

**Date:** February 20, 2026
**Tester:** Claude (automated browser + code review)
**Environment:** localhost:5173 (dev-login, Math, Age 10/Grade 5)
**Commits tested:** 90115db3 (backend), aa138a29 (schemas), e1ca060c (design v1), latest (P0 fixes + design v2)

---

## Bug Status Summary: 7 Fixed / 1 Improved / 1 Partial

| # | Bug | Status | Notes |
|---|-----|--------|-------|
| 1 | Generic meta-questions | **FIXED** | 4 consecutive real math questions across rounds 2-4. Validator working. |
| 2 | Responsive layout | **FIXED** | Tested at 375px and 428px. |
| 3 | "Continue to Learning" shows marketing | **FIXED** | Code verified: `fromAssessment=1` param check. |
| 4 | Fraction 4/100 marked wrong | **FIXED** | Code verified: `parseFractionOrDecimal()` handles "4/100" → 0.04. |
| 5 | Assessment state doesn't reset | **FIXED** | Code verified: exit handler clears all state. |
| 6 | MCQ pre-selected wrong answer | **FIXED** | Browser verified: 0 checked radios on load. |
| 7 | Perseus linter stack trace | **FIXED** | Browser verified: 0 lint elements in DOM. |
| 8 | Explanation panel truncated | **FIXED** | Browser verified: full explanation text visible. |
| 9 | Exit button non-functional | **PARTIAL** | Navigation works (no more tab freeze), but `/app` destination page hangs. |

---

## P0 Bug: CSS Collapse — IMPROVED but NOT FULLY FIXED

**Round 3 result:** Question content fully visible (2 sessions)
**Round 4 result:** Question content partially visible — text in DOM but clipped by collapsed parent containers

**What changed:** The fix changed `assessment-content-wrapper` to `flex: 1 1 auto` and `minHeight: auto`, which helped. The wrapper is now 126px (was 0px). But the nested containers BETWEEN the wrapper and the Perseus renderer still have collapse issues:

| Depth | Element | Height | Issue |
|-------|---------|--------|-------|
| 0 | perseus-renderer | 54px | Content exists ✅ |
| 3 | question card (border-[4px]) | 130px | Card rendered ✅ |
| 4 | unnamed flex wrapper | 32px | `flex: 1 1 0%`, `overflow: hidden auto` — crushes 130px card to 32px ❌ |
| 5 | unnamed flex wrapper | 25px | `flex: 1 1 auto` — even smaller ❌ |
| 6 | framework-perseus | 116px | `overflow: hidden` — content clipped ❌ |
| 8 | assessment-content-wrapper | 126px | Fixed ✅ |

**Root cause:** The fix addressed the outermost wrapper but didn't fix the inner containers at depths 4-7. These still have `flex: 1 1 0%` with `overflow: hidden`, creating a nested crush chain.

**Note:** This bug is intermittent — Round 3 showed the content fully visible on 2 test sessions, while Round 4 shows it clipped. Could be related to question content length, viewport size, or render timing.

**Fix needed:** Ensure containers at depths 4-7 use `flex: 0 0 auto` or `overflow: visible` so they don't crush their children. The key culprit is `flex: 1 1 0%` combined with `overflow: hidden` on parent flex containers.

---

## P0 Bug: Exit Button — PARTIAL FIX (Navigation works, destination hangs)

**Previous:** Clicking ✕ Exit froze the entire browser tab (history.block race condition)
**Current:** ✕ Exit successfully navigates from `/app/assessment/Math` → `/app?subject=Math` (confirmed via URL change). **No tab freeze.** The `unblockRef` fix resolved the `history.block()` race condition.

**Remaining issue:** The destination page `/app?subject=Math` becomes unresponsive after loading. Tab times out on all interactions (screenshots, JS execution). This is a separate issue — likely the learning page component encountering an error when loading after an abandoned assessment.

---

## Neo-Brutalism Design Compliance

### Tailwind Config — FULLY SET UP ✅

All tokens defined in `tailwind.config.js`:
- `shadow-neo` through `shadow-neo-2xl` (hard offset, zero blur)
- `border-neo` (4px), `border-neo-thick` (5px)
- Colors: `neo-bg` (#FFFDF5), `neo-red`, `neo-yellow`, `neo-violet`, `neo-blue`
- Font: Space Grotesk as default sans
- Font sizes: minimum 14px for `text-xs`, 16px for `text-sm`
- Border radius: DEFAULT 0px (sharp corners everywhere)

### shadcn/ui Components — FULLY COMPLIANT ✅

| Component | Key Properties | Status |
|-----------|---------------|--------|
| button.tsx | `rounded-none`, `border-neo`, `h-12` (48px), `font-bold uppercase`, `shadow-neo`, press effect | ✅ PASS |
| card.tsx | `rounded-none`, `border-neo`, `shadow-neo-md`, `font-black uppercase` title | ✅ PASS |
| input.tsx | `rounded-none`, `border-neo`, `h-12` (48px), `text-base font-bold`, `shadow-neo` | ✅ PASS |

### Dev-Login Page — MOSTLY COMPLIANT ✅

| Element | Spec | Actual | Status |
|---------|------|--------|--------|
| Font family | Space Grotesk | Space Grotesk | ✅ PASS |
| Background | #FFFDF5 | rgb(255,253,245) | ✅ PASS |
| Heading | 36px+ weight 900 | 36px, 900 | ✅ PASS |
| Subject buttons | 4px border, 0px radius, 48px+ | 4px, 0px, 72px | ✅ PASS |
| Subject shadows | hard offset | 6px 6px 0 #000 | ✅ PASS |
| Age buttons | 4px border, 56px+ | 4px, 129px | ✅ PASS |
| Input field | 4px border, 0px radius | 4px, 0px, shadow 4px 4px 0 | ✅ PASS |
| Theme toggle | 48px, 4px border | 48px, 4px | ✅ PASS |
| Body font size | 14px+ | **12px** | ❌ FAIL |
| Button label font size | 16px+ | **12px** | ❌ FAIL |

### Assessment Page — MOSTLY COMPLIANT ✅ (improved from last round)

| Element | Spec | Actual | Status |
|---------|------|--------|--------|
| Exit button border | 4px | 4px | ✅ PASS (was 3px) |
| Exit button shadow | 4px+ | 4px 4px 0 | ✅ PASS (was 2px) |
| Exit button height | 48px+ | 56px | ✅ PASS (was 37px) |
| Exit button font | 16px+ bold | 16px, 900 | ✅ PASS (was 13px) |
| Font family | Space Grotesk | Space Grotesk | ✅ PASS |
| ASSESSMENT MODE bar | 16px+ | 16px, 900 | ✅ PASS |
| Question header font | 14px+ | **12px** | ❌ FAIL |

---

## Assessment Performance Trend

| Metric | Target | Round 1 | Round 2 | Round 3 | Round 4 |
|--------|--------|---------|---------|---------|---------|
| First question load | <25s | ~60-76s | 40s | ~35s | ~35s |
| Meta-questions | 0% | 100% | 0% | 0% | 0% |
| Question visible | 100% | 0% | 0% | 100% | **Partial** |
| Exit button | Works | No | Freeze | Nav+hang | Nav+hang |

---

## Priority Fixes Still Needed

1. **CSS collapse (P0)** — Inner flex containers (depths 4-7 from Perseus) still crush content. Need to fix `flex: 1 1 0%` + `overflow: hidden` on the divs between `assessment-content-wrapper` and the question card. This is intermittent — sometimes renders, sometimes clips.

2. **Learning page hang** — `/app?subject=Math` crashes after exit navigation. This prevents the full exit flow from working. Separate from the exit button itself.

3. **Font sizes** — Body font 12px and button labels 12px need to be bumped. The tailwind config has correct minimums (14px for xs, 16px for sm) but the inline styles and inherited CSS override them.

4. **Question header** — "QUESTION 1 OF 10" renders at 12px. Should be at least 14px per the design system.

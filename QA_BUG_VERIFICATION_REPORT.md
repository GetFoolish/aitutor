# QA Bug Verification Report

**Date:** February 20, 2026 (Round 3 — post design-system commit e1ca060c)
**Tester:** Claude (automated browser + code review)
**Environment:** localhost:5173 (dev-login, Math, Age 10/Grade 5)
**Commits tested:** 90115db3 (backend fixes), aa138a29 (schemas/tests), e1ca060c (design system)

---

## Summary: 7 Fixed / 1 Improved / 1 Partial

| # | Bug | Status | Verification |
|---|-----|--------|-------------|
| 1 | Generic meta-questions | **IMPROVED** | Round 1: meta-question served. Rounds 2-3: real math questions ("In the number 4.72…", "Maya is thinking of a decimal…", "A scientist recorded the mass…"). 3 consecutive real questions = validator working. |
| 2 | Responsive layout | **FIXED** | Browser verified at 375px and 428px. |
| 3 | "Continue to Learning" shows marketing | **FIXED** (code) | `fromAssessment=1` URL param check in index.tsx. |
| 4 | Fraction 4/100 marked wrong | **FIXED** (code) | `parseFractionOrDecimal()` correctly handles "4/100" → 0.04. |
| 5 | Assessment state doesn't reset | **FIXED** (code) | Exit handler clears all state before navigate. |
| 6 | MCQ pre-selected wrong answer | **FIXED** | Browser: 0 checked radios on load. |
| 7 | Perseus linter stack trace | **FIXED** | Browser: 0 lint elements in DOM. |
| 8 | Explanation panel truncated | **FIXED** | Browser: full explanation text visible. |
| 9 | Exit button non-functional | **PARTIAL** | Navigation now fires (URL changes to `/app?subject=Math`) but destination page hangs. See details below. |

---

## FIXED: Question Content Invisible (CSS Collapse)

**Previous status:** Critical blocker — question text invisible (height: 0px + overflow: hidden)
**Current status:** **FIXED** as of commit e1ca060c

Tested 2 consecutive assessment sessions. Both times question text was fully visible:
- Session 1: "Maya is thinking of a decimal number. It has a 6 in the ones place…"
- Session 2: "A scientist recorded the mass of a small sample. The mass has 1 in the tens place…"

Both are real math questions with visible input fields and readable text. The CSS collapse that plagued all previous testing rounds is resolved.

---

## PARTIAL: Exit Button (Bug #9)

**Previous status:** Clicking ✕ Exit froze the entire browser tab
**Current status:** Navigation fires successfully (URL changes from `/app/assessment/Math` → `/app?subject=Math`) but the destination `/app` page hangs after loading.

The `history.block()` race condition appears to be fixed — the exit handler now successfully navigates away. However, the `/app?subject=Math` page itself becomes unresponsive after the navigation completes. This may be a separate issue with the learning page component rather than the exit button logic.

**Root cause of remaining issue:** Likely the learning page (`/app`) encountering an error when loading with a subject parameter after an assessment was abandoned (incomplete assessment state in backend?).

---

## Neo-Brutalism Design Compliance (commit e1ca060c)

### Dev-Login Page — MOSTLY COMPLIANT

| Element | Spec | Actual | Status |
|---------|------|--------|--------|
| Font family | Space Grotesk | Space Grotesk ✅ | PASS |
| Body background | #FFFDF5 | rgb(255,253,245) ✅ | PASS |
| Heading size | 36px+ | 36px, weight 900 ✅ | PASS |
| Subject buttons | border-4, 0px radius | 4px border, 0px radius ✅ | PASS |
| Subject button height | 48px+ | 72px ✅ | PASS |
| Subject button shadow | hard offset, 0 blur | 6px 6px 0 #000 ✅ | PASS |
| Age buttons | border-4, 0px radius | 4px border, 0px radius ✅ | PASS |
| Age button height | 56px+ | 129px ✅ | PASS |
| Input field | border-4, 0px radius | 4px border, 0px radius ✅ | PASS |
| Input shadow | hard offset | 4px 4px 0 #000 ✅ | PASS |
| Theme toggle | 48px, border-4 | 48px, 4px border ✅ | PASS |
| Body font size | 14px+ | 12px ❌ | FAIL — still too small |

### Assessment Page — PARTIALLY COMPLIANT

| Element | Spec | Actual | Status |
|---------|------|--------|--------|
| Exit button border | 4px | 3px ❌ | FAIL |
| Exit button shadow | 4px+ offset | 2px 2px 0 ❌ | FAIL |
| Exit button height | 48px+ | 37.5px ❌ | FAIL |
| Exit button font size | 16px+ | 13px ❌ | FAIL |
| Question header font | 14px+ bold | 12px, 700 ❌ | FAIL — too small |
| Submit button | not captured (inline styles) | Visually OK from screenshot | NEEDS VERIFY |
| Font family | Space Grotesk | Space Grotesk ✅ | PASS |

### Remaining Design Issues

1. **Body font size** still 12px (should be 14px minimum for readability)
2. **Exit button** doesn't meet any neo-brutalism specs — too small, thin border, tiny shadow
3. **Question header text** at 12px is too small for the QUESTION 1 OF 10 display
4. **Assessment page elements** use inline styles that weren't updated in the design pass (commit e1ca060c only touched DevLogin and AssessmentQuestion, not AssessmentFlow inline styles)

---

## Assessment Performance

| Metric | Target | Round 1 | Round 2 | Round 3 |
|--------|--------|---------|---------|---------|
| Time to first question | <25s | ~60-76s | 40.2s | ~35s |
| Meta-questions | 0% | 100% (Q1 meta) | 0% | 0% |
| Question visibility | 100% | 0% (collapsed) | 0% (collapsed) | **100%** ✅ |
| Exit button works | Yes | No | No (freezes tab) | Partial (navigates but dest hangs) |

---

## Priority Fixes Remaining

1. **Exit button destination hang** — `/app?subject=Math` page hangs after exit navigation. Investigate learning page component error handling for abandoned assessments.
2. **Assessment page design** — Exit button, question header, and other inline-styled elements in AssessmentFlow.tsx need neo-brutalism treatment (4px borders, larger sizes, hard shadows).
3. **Body font size** — Bump from 12px to 14px minimum.
4. **Global design audit** — Other pages (shadcn/ui components like button.tsx, card.tsx, input.tsx) still have rounded corners, blur shadows, thin borders from defaults. See FRONTEND_AUDIT.md for full list.

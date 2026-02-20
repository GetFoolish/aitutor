# QA Bug Verification Report

**Date:** February 20, 2026
**Tester:** Claude (automated browser + code review)
**Environment:** localhost:5173 (dev-login, Math, Age 10/Grade 5)

---

## Summary: 5 Fixed / 2 Not Fixed / 1 Partial / 1 New Bug Found

| # | Bug | Status | Verification Method |
|---|-----|--------|-------------------|
| 1 | Generic meta-questions (50% broken) | **NOT FIXED** | Browser: Q1 served "Which of the following is true about Decimal Place Value?" — exact pattern the validator should catch. Code review: `validate_not_meta_question()` exists with correct regex but is not blocking at runtime. |
| 2 | Responsive layout (only works at 328px) | **FIXED** | Browser: Tested at 375px (iPhone) and 428px (iPhone Plus). Content renders, wraps, and is readable at both widths. |
| 3 | "Continue to Learning" shows marketing page | **FIXED** (code) | Code review: `index.tsx` lines 152-173 correctly check `fromAssessment=1` URL param and skip auth guard. Could not verify in browser due to assessment trapping navigation (Bug #9). |
| 4 | Fraction 4/100 marked wrong | **FIXED** (code) | Code review: `parseFractionOrDecimal()` in `scoring-utils.ts` lines 65-79 correctly splits on `/`, parses numerator/denominator, returns `num/den`. "4/100" → 0.04. Used at line 236 in numeric-input scoring. |
| 5 | Assessment state doesn't reset | **FIXED** (code) | Code review: `AssessmentFlow.tsx` lines 635-641 clear `assessmentIdRef`, `assessmentId`, `currentQuestion`, `completed`, and sessionStorage keys BEFORE calling `history.replace()`. |
| 6 | MCQ pre-selected wrong answer | **FIXED** | Browser: Verified on Q1 and Q2 — all 4 radio buttons unselected on load. DOM confirmed 0 checked radios. |
| 7 | Perseus linter stack trace in DOM | **FIXED** | Browser: Zero lint-related elements in DOM. No `highlightLint` traces in Perseus renderer HTML. |
| 8 | Explanation panel truncated | **FIXED** | Browser: Wrong answer on Q2 showed full explanation text: "The digit 2 is the second digit after the decimal point, so it is in the hundredths place." — not truncated. |
| 9 | Exit button non-functional | **PARTIAL FIX** | Browser: Clicking "✕ Exit" button during assessment did nothing — URL stayed on `/app/assessment/Math`. Code review: Main exit handler (line 642) correctly uses `history.replace()`, BUT loading-phase cancel (line 482) still uses `window.location.replace()`. The exit button click handler may not be firing due to the forced CSS overrides or a z-index/event issue. |

---

## NEW BUG FOUND

### Question Content Panel Collapsed (BLOCKING)

**Severity:** Critical
**Description:** The question content area renders with `height: 0px` and `overflow: hidden`, making all question text and answer choices completely invisible to users.

**Root cause:** Multiple nested flex containers between the assessment-container and the Perseus renderer have `flex: 1 1 0%` with `min-height: 0px`, causing the content to collapse to zero height. Specifically:
- A wrapper div at depth 6 from the question text has `height: 0`, `overflow: hidden auto`
- Another at depth 7 has `height: 0`, `overflow: visible`
- The `framework-perseus` container has `overflow: hidden`, `height: 134px` (clipping)

**Repro:** Navigate to any assessment question. Content is in the DOM but visually invisible.

**Workaround:** Force `height: auto !important` and `overflow: visible !important` on affected containers.

**Files to investigate:**
- `AssessmentQuestion.tsx` — question panel container styles
- `App.scss` lines 174-430 — nested height/overflow declarations

---

## Notes

- Bug #1: The `validate_not_meta_question()` regex is correct in `pre_serve_validator.py`, but the meta-question still got served. Either the validator isn't running on this code path, or the question was pre-cached before the fix was deployed. Check if the validator runs on JIT-generated questions.
- Bug #9: The exit button's click handler may be blocked by the CSS overrides applied during testing (we had to force `overflow: visible` on ancestors). Should retest with clean CSS. The code itself has the correct `history.replace()` pattern on the main exit handler.
- Bugs #3, #4, #5 could only be verified via code review because the assessment UI issues prevented full browser testing of those flows.

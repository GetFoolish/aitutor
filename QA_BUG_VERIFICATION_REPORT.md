# QA Bug Verification Report

**Date:** February 20, 2026
**Tester:** Claude (automated browser + code review)
**Environment:** localhost:5173 (dev-login, Math, Age 10/Grade 5)

---

## Summary: 5 Fixed / 2 Not Fixed / 1 Still Broken / 1 New Bug

| # | Bug | Status | Verification Method |
|---|-----|--------|-------------------|
| 1 | Generic meta-questions (50% broken) | **IMPROVED** | Round 1: Q1 was a meta-question. Round 2 (post-fix): Q1 was a real math question ("In the number 4.72, which digit is in the tenths place?"). Validator may now be working, but needs more testing to confirm consistency. |
| 2 | Responsive layout (only works at 328px) | **FIXED** | Browser: Tested at 375px (iPhone) and 428px (iPhone Plus). Content renders, wraps, and is readable at both widths. |
| 3 | "Continue to Learning" shows marketing page | **FIXED** (code) | Code review: `index.tsx` lines 152-173 correctly check `fromAssessment=1` URL param and skip auth guard. Could not verify in browser due to exit button bug (#9). |
| 4 | Fraction 4/100 marked wrong | **FIXED** (code) | Code review: `parseFractionOrDecimal()` in `scoring-utils.ts` lines 65-79 correctly splits on `/`, parses numerator/denominator, returns `num/den`. "4/100" → 0.04. |
| 5 | Assessment state doesn't reset | **FIXED** (code) | Code review: `AssessmentFlow.tsx` lines 635-641 clear `assessmentIdRef`, `assessmentId`, `currentQuestion`, `completed`, and sessionStorage keys BEFORE calling `history.replace()`. |
| 6 | MCQ pre-selected wrong answer | **FIXED** | Browser: Verified on Q1 and Q2 — all 4 radio buttons unselected on load. DOM confirmed 0 checked radios. |
| 7 | Perseus linter stack trace in DOM | **FIXED** | Browser: Zero lint-related elements in DOM. No `highlightLint` traces in Perseus renderer HTML. |
| 8 | Explanation panel truncated | **FIXED** | Browser: Wrong answer on Q2 showed full explanation text — not truncated. |
| 9 | Exit button non-functional | **STILL BROKEN** | Browser (2 rounds): Clicking "✕ Exit" freezes the entire browser tab. Root cause identified — see below. |

---

## STILL BROKEN: Exit Button Freezes Tab

**Severity:** Critical
**Tested:** 2 separate sessions. Both times clicking ✕ Exit made the browser tab completely unresponsive (all JS execution times out at 30s).

**Root cause:** Race condition between `history.block()` and the exit handler.

1. `AssessmentFlow.tsx` line 104-109 sets up `history.block()` that prevents ALL in-app navigation while `assessmentId` is truthy and `completed` is false.
2. The exit button handler (line 633-644) calls `setAssessmentId(null)` — but this is an async React state update.
3. The handler then immediately calls `history.replace('/app?subject=...')` at line 644.
4. Since React hasn't flushed the state update yet, `history.block()` is still active and blocks the navigation with a confirmation prompt.
5. This confirmation prompt appears to hang the tab entirely (possibly because it's a `history.block` prompt that can't be dismissed programmatically).

**Fix:** The exit handler needs to call the `unblock` function BEFORE navigating. Either:
- Store the `unblock` return value in a ref and call it in the exit handler before `history.replace()`
- Or use `window.location.href` as a fallback (bypasses history.block)
- Or wrap `history.replace()` in a `setTimeout(() => ..., 0)` to let React flush the state update first

---

## STILL BROKEN: Question Content Invisible (CSS Collapse)

**Severity:** Critical
**Tested:** 3 separate assessment sessions across 2 rounds of fixes. All show the same issue.

**Description:** The question content area renders with `height: 0px` and `overflow: hidden`, making all question text and answer choices completely invisible to users. The header ("QUESTION 1 OF 10") and submit button are visible, but the actual question between them is collapsed to zero height.

**Root cause:** Multiple nested flex containers between the assessment-container and the Perseus renderer have `flex: 1 1 0%` with `min-height: 0px`, causing the content to collapse to zero height. Specifically:
- A wrapper div at depth 6 from the question text has `height: 0`, `overflow: hidden auto`
- Another at depth 7 has `height: 0`, `overflow: hidden`
- The `framework-perseus` container has `overflow: hidden`, `height: 134px` (clipping)

**Files to fix:**
- `AssessmentQuestion.tsx` — question panel container styles
- `App.scss` lines 174-430 — nested height/overflow declarations
- The content wrapper between the header and submit button (line 695-706 in AssessmentFlow.tsx) has `flex: 1, minHeight: 0` which contributes to the collapse

---

## Other Observations

- **Assessment load time:** 40.2 seconds from click to first question rendered. Better than the reported 60-76s, but still above the <25s target.
- **Meta-questions:** Improved after the compound fix (0 meta-questions found in DB cleanup, Q1 was a real math question), but needs more testing to confirm consistency.
- Bugs #3, #4, #5 could only be verified via code review because the assessment UI issues prevented full browser testing of those flows.

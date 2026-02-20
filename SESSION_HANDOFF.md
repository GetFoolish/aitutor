# Teachr.Live QA Session Handoff

**Date:** February 20, 2026
**Total commits so far:** 22 (19 original marathon + 3 quick wins)

---

## What is Teachr.Live?

Full-stack adaptive learning platform for K-12 students:
- **Frontend:** React/TypeScript (Vite), localhost:5173
- **Backend:** FastAPI, Gemini AI for question generation, Perseus renderer for math
- **Design system:** Neo-brutalism — #FFFDF5 bg, 4px borders, hard offset shadows `4px 4px 0 #000`, 0px border-radius, Space Grotesk font, 14px min font, 48px min button height
- **Assessment flow:** 10-question adaptive assessments, 3-hint system, correct/incorrect feedback with AI explanations
- **Dev access:** `/app/dev-login` → select subject + age → starts assessment

## What's Been Fixed (22 commits)

All original 20 layout/CSS bugs are resolved:
- Layout bleeding, CSS collapse, font sizes, border consistency, shadow consistency
- Exit button positioning, progress label sizing, submit button styling
- Biology 503 (now loads), floating panel text clearance (280px)
- Next button yellow, selection color vivid yellow

## What's Still Broken — 8 Remaining Issues

### P0 Critical
1. **Issue #3: Science 404 on next question** — After answering Q1 in Science, `/assessment/next` returns HTTP 404. Backend session gets lost. File: `dash_api.py` session persistence logic.

2. **Empty answer accepted as "CORRECT"** — Dropdown "select one" placeholder → Submit → "CORRECT!". Backend doesn't validate actual answer was selected. (This was found during testing but wasn't in the numbered list — may need to be added.)

3. **Exit button → broken loading state** — Click ✕ EXIT → `/app?subject=X` tries to auto-start a NEW assessment instead of showing a landing page. Shows "FAILED TO LOAD" dead-end. No exit confirmation dialog either.

### P1 High
4. **Issue #4: Duplicate questions** — Q1 and Q2 test same concept. Content hash not tracked in prefetch worker, only last 3 skills excluded. Pool/JIT don't filter by content hash.

5. **Issue #7: Progress bar doesn't update after submit** — Need to update progress state immediately in handleSubmit.

6. **Issue #8: No loading spinner on next question** — Need loading state + spinner in AssessmentFlow.

7. **Issue #6: Submit below fold after 3 hints** — After showing all 3 hints, Submit button scrolls off screen. Options: sticky submit, accordion hints, or limit to 2 hints.

### P2 Medium
8. **Issue #9: Hints give away answer** — Hint prompts too vague ("don't reveal" isn't specific enough). Need stricter prompt rules.

9. **Issue #10: Biology too easy for Grade 5** — Difficulty hardcoded to 0.5 for all grades. No grade→difficulty mapping exists.

10. **Issue #11: No back button** — Product decision needed: allow question navigation or not?

### Design System Gaps (not blocking but noted)
- FloatingControlPanel: 3px border (should be 4px), no hard shadow, 2px button borders, button sizes 24-40px, timer font 9px
- Perseus answer option buttons: 0px border, no shadow, 43px height
- Focus indicators nearly invisible for keyboard nav
- Tab order skips Hint and Submit buttons (accessibility)
- No session recovery on page refresh

## Key Files

- `frontend/src/components/assessment/AssessmentFlow.tsx` — main assessment flow, line 258 has the 404 error
- `frontend/src/components/assessment/AssessmentQuestion.tsx` — question rendering
- `frontend/src/components/assessment/FloatingControlPanel.tsx` — right-side panel
- `frontend/src/App.scss` / `frontend/src/index.css` — global styles
- `frontend/src/index.tsx` — routes (line 286: dev-login route)
- Backend: `dash_api.py` — session management, next-question endpoint
- Adaptive engine files — question selection, difficulty calibration, hint generation

## Test Results Summary

- **Math:** Works perfectly, instant load (pre-built question bank)
- **Science:** Loads Q1 fine, but Q2+ returns 404
- **Biology:** Now loads (was 503), but next-question can be slow (Gemini)
- **English:** Loads after 15-25s wait (Gemini generation), standard MC format
- **Dark mode:** Works, switches cleanly mid-assessment
- **Double-click protection:** Works, no duplicate submissions

## Full Test Report

See: `COMPREHENSIVE_USER_TESTING_REPORT.md` in the repo root — has all 16 issues with repro steps, screenshots context, and recommended priority fix order.

## What To Do Next

User said "fix them all" for the 8 remaining complex issues. Start with:
1. Science 404 (debug backend session in dash_api.py)
2. Empty answer validation (server-side check)
3. Exit flow (route to dashboard, add confirmation dialog)
4. Duplicate questions (content hash tracking)
5. Progress bar update
6. Loading spinner
7. Hint prompt strictness
8. Difficulty calibration

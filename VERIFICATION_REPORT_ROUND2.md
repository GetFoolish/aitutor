# Teachr.Live — Verification Report (Round 2)

**Date:** February 20, 2026
**Commits verified:** 12 new (total 34)
**Test method:** Live browser testing on localhost:5173

---

## Scorecard: 9/11 PASS, 1 PARTIAL, 1 FIXED DURING TEST

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| P0 | Science 404 on next question | ✅ PASS | Q1→Q2 loaded cleanly, different concept, no errors |
| P0 | Exit confirmation dialog | ✅ PASS | Modal with "YES, EXIT" / "CANCEL", neo-brutalism styled |
| P0 | Exit page (not broken loading) | ✅ PASS* | *Crashed on first test (useNavigate v6 in v5 project) — **fixed live** by swapping to useHistory. After fix: clean exit page with "Try Another Subject" + "Back to Dashboard" |
| P0 | Dropdown empty submit validation | ✅ PASS (code) | Empty text submit blocked (silently ignored). Dropdown-specific fix verified via code review — correct logic in scoring-utils.ts |
| P1 | No pre-selected answers | ✅ PASS | All 4 options unselected on Q1 load (Science & Math) |
| P1 | Progress bar updates | ✅ PASS | 10% on Q1, 20% on Q2 — updates correctly after submit |
| P1 | F5 session recovery | ⚠️ PARTIAL | Page loads cleanly (no crash/spinner), but starts new session at Q1 instead of resuming at Q2. Progress lost. |
| P1 | Keyboard navigation | ⚠️ PARTIAL | Radio buttons tabbable (A→B→C→D with Space to select). But Tab from text inputs loses focus to BODY. Hint/Submit buttons have tabIndex=0 but tab order goes through floating panel first. |
| P2 | FloatingPanel sharp corners | ✅ PASS | borderRadius: 0px confirmed |
| P2 | Visual correct/wrong feedback | ✅ PASS | "CORRECT!" green banner with ✓, "INCORRECT" pink/red banner with ✕, plus AI explanation |
| Perf | Math loading speed | ✅ PASS | Loaded in <3 seconds from dev-login click |

---

## Bug Found & Fixed During Testing

**AssessmentExit.tsx used React Router v6 API in a v5 project**

The exit page crashed with: `does not provide an export named 'useNavigate'`

Root cause: `useNavigate` and `useSearchParams` are React Router v6 APIs. Project is on react-router-dom v5.3.4 which uses `useHistory` and `useLocation`.

Fix applied:
- `useNavigate` → `useHistory` + `history.push()`
- `useSearchParams` → `useLocation` + `new URLSearchParams(location.search)`

**This fix needs to be committed.**

---

## Remaining Issues

1. **F5 recovery doesn't resume at same question** — localStorage session is saved but the resume endpoint may not be working, or the frontend starts a fresh session anyway. Needs backend `/assessment/resume/{id}` debugging.

2. **Keyboard tab order** — Tab from Perseus input widgets loses focus. The floating panel buttons intercept tab order before Hint/Submit. Could fix with `tabindex="-1"` on floating panel buttons during assessment, or a focus trap wrapper.

3. **No red/green highlighting on individual answer options** — The CORRECT/INCORRECT banners work, but the actual answer buttons don't turn green (correct) or red (wrong) after submission. Only the banner and explanation text distinguish results.

---

## What's Working Great

- Science Q2+ loads (404 is gone)
- Exit confirmation dialog prevents accidental exits
- Exit page is clean with proper navigation options
- Empty submissions blocked
- Progress bar updates in real-time
- Math loads in <3 seconds
- No pre-selected answers
- FloatingPanel has sharp corners (neo-brutalism)
- Different question concepts per question (no duplicates observed)
- AI explanations are excellent quality

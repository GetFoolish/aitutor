# Teachr.Live — Comprehensive User Testing Report

**Date:** February 20, 2026
**Tested by:** Automated QA (Claude) acting as a Grade 5 student
**Environment:** localhost:5173, dev-login, multiple subjects
**Subjects tested:** Biology, Science, English, Math (exit flow)

---

## Executive Summary

After the marathon 19-commit, 30+ bug fix session, the platform is **significantly improved** — layout issues are fixed, fonts are correct, borders and shadows are consistent on main elements, and the core assessment flow works. However, real-user testing uncovered **16 new issues** that technical pixel-auditing missed. Several are critical enough to impact assessment integrity.

---

## P0 — Critical (Breaks Core Functionality)

### 1. Empty answer accepted as "CORRECT"
- **Where:** Dropdown-type questions (Perseus "select one" widget)
- **Steps:** Load question → Don't select any answer → Click Submit
- **Result:** Backend returns `"CORRECT!"` for a blank answer
- **Impact:** Assessment scores are meaningless. A student could click Submit 10 times without answering and potentially score 100%.
- **Root cause:** Frontend sends the placeholder value and backend doesn't validate that an actual selection was made.

### 2. "Next Question" fails with HTTP 404 (Science)
- **Where:** Science assessment, after answering Q1
- **Steps:** Start Science → Answer Q1 → Click "Next Question"
- **Result:** "FAILED TO LOAD NEXT QUESTION" → "NETWORK ISSUE" on retry
- **Console:** `Assessment next failed: Error: HTTP 404` at AssessmentFlow.tsx:258
- **Impact:** Science assessments are completely broken beyond Q1.

### 3. Exit button leads to broken loading state
- **Where:** Any assessment → Click ✕ EXIT
- **Steps:** Start Biology assessment → Answer Q1 → Click ✕ EXIT
- **Result:** Navigates to `/app?subject=Biology` which shows "STILL WORKING ON IT..." → Cancel → "FAILED TO LOAD ASSESSMENT" with only "Try Again" or "Back to Dev Login"
- **Impact:** Students can't cleanly exit an assessment. The exit route tries to auto-start a NEW assessment instead of showing a landing page. There's no way back to subject selection without going to dev-login.

---

## P1 — High (Significant UX Problems)

### 4. No exit confirmation dialog
- **Where:** ✕ EXIT button during assessment
- **Steps:** Mid-question or mid-feedback → Click ✕ EXIT
- **Result:** Immediately navigates away. No "Are you sure?" prompt.
- **Impact:** A student could accidentally tap Exit and lose all progress. Especially dangerous on touch devices. Every assessment platform has this safeguard.

### 5. Session not recovered on page refresh
- **Where:** Any assessment, browser refresh (F5/Cmd+R)
- **Steps:** Mid-assessment → Refresh page
- **Result:** Shows "STILL WORKING ON IT..." → starts a brand new session with Q1. All previous progress lost.
- **Impact:** Any accidental refresh, browser crash, or tab close destroys the assessment. No session persistence.

### 6. First answer option auto-selected on page load
- **Where:** Multiple choice questions (Perseus radio buttons)
- **Steps:** Load any question → observe option A
- **Result:** Option A appears pre-selected (blue highlight) before the student touches anything
- **Impact:** Biases students toward A. If combined with the empty-submit bug, students might submit A without realizing it was pre-selected.

### 7. Keyboard navigation can't reach Submit button
- **Where:** Assessment question area
- **Steps:** Tab through answer options (A→B→C→D) → keep tabbing
- **Result:** Focus cycles back to option A. Tab never reaches Hint or Submit buttons.
- **Impact:** Keyboard-only users (accessibility) cannot submit answers. Violates WCAG 2.1 requirements.

### 8. AI-generated subjects are very slow to load (15-25+ seconds)
- **Where:** English, Biology, and other Gemini-generated subjects
- **Steps:** Select English or Biology from dev-login
- **Result:** "PREPARING YOUR ENGLISH ASSESSMENT" spinner for 15-25+ seconds. First attempt often fails, showing "STILL WORKING ON IT..." with Cancel/Try Again.
- **Impact:** A 10-year-old will give up and leave. The loading message says "only take a few seconds" which sets wrong expectations.

---

## P2 — Medium (Polish / UX Improvements)

### 9. No visual distinction between correct/wrong answers after feedback
- **Where:** Post-submission feedback state
- **Steps:** Submit wrong answer → View feedback
- **Result:** The wrong answer stays blue-selected. The correct answer isn't highlighted green. Only the INCORRECT/CORRECT banner and text explanation distinguish the result.
- **Impact:** Students don't learn which answer was right at a glance. Most assessment tools highlight correct=green, wrong=red.

### 10. Answer selection visual feedback is too subtle
- **Where:** Multiple choice answer options
- **Steps:** Click an answer option
- **Result:** Very faint blue tint on the selected option. On a slightly dim screen, barely distinguishable from unselected.
- **Impact:** Students may not be confident which answer they selected before submitting.

### 11. Floating control panel obscures content
- **Where:** Right side of assessment screen
- **Steps:** Panel auto-expands, covering the right edge of question text
- **Result:** Panel overlaps content area. On narrower screens, it covers answer text.
- **Impact:** Students have to manually collapse it every time. Panel also re-expands after page refresh.

### 12. Floating panel doesn't match design system
- **Where:** FloatingControlPanel (collapsed and expanded)
- **Details:** Border is 3px (should be 4px), no hard shadow, buttons have 2px borders (should be 4px), button sizes 24-40px (should be 48px minimum), timer font 9px (should be 14px minimum)
- **Impact:** Inconsistent with neo-brutalism design language used everywhere else.

### 13. Answer option buttons don't match design system
- **Where:** Perseus-rendered answer options (A/B/C/D)
- **Details:** Border 0px (should be 4px), no hard shadow, height 43px (should be 48px)
- **Impact:** Answer buttons are the most-clicked element in the entire app and they don't match the design system.

### 14. Duplicate/repeated questions
- **Where:** Biology assessment, observed after Q1 correct answer
- **Steps:** Answer Q1 correctly → Click Next Question → Q2 appears
- **Result:** Q2 tests the exact same concept as Q1 (both about "basic need of all living things")
- **Impact:** Feels broken to students. Adaptive system should vary concepts.

### 15. Focus indicators nearly invisible
- **Where:** Radio button answer options during Tab navigation
- **Steps:** Tab through options
- **Result:** Extremely faint focus ring, barely visible on the light background
- **Impact:** Keyboard users can't tell which option has focus. Accessibility issue.

### 16. Dark mode has minor contrast concerns
- **Where:** Dark mode toggle (moon icon in header)
- **Details:** Dark mode works and looks intentional (black bg with dotted pattern, dark gray question card, white answer options). However, the question card background (#333-ish) against the black body creates a low-contrast boundary. Answer options remain white which is fine.
- **Impact:** Minor — dark mode is functional but could use more contrast differentiation between card and background.

---

## What's Working Well

These are genuine positives observed during user testing:

- **Layout is solid** — 1180px max width, no content bleeding, proper spacing
- **Font sizes are correct** — 14px body, 18px question text, Space Grotesk throughout
- **Borders and shadows are consistent** on main elements (exit button, banners, question cards, hint button, submit button)
- **Hint system works great** — 3 hints stacking UI, progressive reveal, good pedagogy
- **Feedback quality is excellent** — AI-generated explanations are age-appropriate and educational
- **Double-click protection works** — rapid Submit clicks don't cause duplicate submissions
- **Dark mode toggle works** — theme switches cleanly mid-assessment
- **Subject theming is nice** — colors change per subject (red=Math, yellow=English, etc.)
- **Biology now loads** — was permanently 503, now works
- **Dev-login page is clean** — subject selection + age grid is intuitive
- **Math loads instantly** — pre-built question banks make Math snappy
- **Neo-brutalism design is visually distinctive** — the brand identity is strong

---

## Priority Fix Order (Recommended)

1. **Empty answer validation** (P0 #1) — Server-side check, 30 min fix, protects assessment integrity
2. **Exit flow → proper landing page** (P0 #3) — Route `/app?subject=X` to a dashboard, not auto-start
3. **Science next-question 404** (P0 #2) — Backend session management bug
4. **Exit confirmation dialog** (P1 #4) — Simple modal, 1 hour
5. **Answer option styling** (P2 #13) — Match neo-brutalism, 1 hour
6. **Post-feedback answer highlighting** (P2 #9) — Green/red on correct/wrong, 1 hour
7. **Keyboard accessibility** (P1 #7) — Tab order through Hint → Submit, 2 hours
8. **Session recovery** (P1 #5) — localStorage session persistence, 4+ hours

---

*Report generated from live browser testing across 4 subjects, 8 assessment sessions, and 20+ individual interactions.*

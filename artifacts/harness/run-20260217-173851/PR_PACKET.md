# PR: Content Pipeline Harness Report

Generated: 2026-02-17T17:39:30.529880+00:00
Harness overall status: FAIL

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.12 |
| smoke | FAIL | yes | 2.36 |
| pretest_checklist | PASS | yes | 14.85 |
| content_v1_battletest | FAIL | yes | 4.06 |
| playwright | FAIL | yes | 17.42 |
| greptile | SKIPPED | no | 0.12 |

## Acceptance Criteria

- [ ] No duplicate questions by ID/content fingerprint
- [ ] Subject correctness (no cross-subject contamination)
- [ ] Assessment does not stop after 1-2 questions
- [x] Adaptive assessment remains stable through at least 8 consecutive next-question transitions (no break around Q4/Q5)
- [ ] Questions have answer area and renderable widget config
- [x] Next-question latency within budget
- [ ] Grading/skill-path metadata integrity checks passed
- [x] Grading correctness parity holds for rendered options (radio selectedChoiceIds map correctly to answer key)
- [ ] No leaked quoted choice text or duplicate 'Choose 1 answer' prompt labels in served/rendered content
- [ ] DASH system works end-to-end (health + auth + subject start + question fetch)
- [ ] Adaptive assessment start works across all available subjects (no terminal 400/invalid payload)
- [ ] Learning mode path stays subject-correct and content-valid (recommend-next has no cross-subject contamination)
- [x] Question loading times are optimized for max speed (initial load + learning recommend-next + adaptive start + repeated next-question transitions within budget)
- [ ] Websocket ping/pong smoke check passed
- [ ] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [ ] Primary assessment actions are visible/reachable without manual scrolling
- [ ] Assessment question view has zero browser-level vertical scroll while keeping question, hints, and actions usable
- [ ] Assessment question view has zero internal question-container scroll while keeping question/options/hints/actions usable
- [ ] Assessment question container overflow contract holds (`#question-content-container` does not compute to overflow-y:auto)
- [ ] Visual-heavy prompts stay viewport-fit and do not push Submit/Next below fold
- [ ] Assessment remains zero-window-scroll after opening at least one hint
- [ ] Learning mode route (`/app/learn/:subject`) maintains zero browser-level vertical scroll with question/actions visible
- [ ] Widget-family render integrity holds (radio/dropdown/text-numeric render inside container without detached overlays/stray text)
- [ ] Dropdown anchor integrity holds (opened listbox stays near combobox trigger and inside viewport on assessment + learning routes)
- [ ] Theme integrity holds in both modes (light/dark toggles render correct question surfaces/text without mixed-mode artifacts)
- [ ] Question content contrast passes in both light and dark themes on assessment + learning routes
- [ ] Hint control legibility passes in both themes (`Show Hint`/`Hint` stays readable on assessment + learning routes)
- [ ] Selected radio option highlight renders as complete 4-sided outline (no clipped/incomplete blue border)
- [ ] Assessment completion routes into subject-scoped learning state (not generic homepage fallback)
- [ ] Adaptive assessment reaches completed=true within 10 answered questions without manual retry loops
- [ ] Synthetic fallback question IDs resolve to source payloads so adaptive continuity cannot dead-end
- [ ] Responsive layout has no blocking overflow/clipping on tested viewports
- [ ] Playwright screenshots captured for assessment + floating panel
- [ ] Floating panel not obscured by widget container (Z-index check)
- [ ] Floating panel is fully visible on /app and /app/:id routes (not clipped/off-screen/sliver)
- [ ] AI payload matches browser-rendered content (hydration/render check)
- [ ] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- `artifacts/harness/run-20260217-173851/screenshots/01-dev-login.png`
- `artifacts/harness/run-20260217-173851/screenshots/02-learning-widget-render.png`
- `artifacts/harness/run-20260217-173851/screenshots/04-assessment-mobile-responsive.png`
- `artifacts/harness/run-20260217-173851/screenshots/07-assessment-dark-theme.png`

## Merge Policy

1. All required harness gates must pass on the PR head SHA.
2. No required gate may be skipped.
3. This report must be attached to the PR description or comment.
4. Smoke and Playwright evidence must be from the same run.
5. Greptile override requires explicit reviewer approval note.

## Reviewer Checklist

- [ ] Verified gate table and artifacts
- [ ] Reviewed screenshots for widget/floating-panel correctness
- [ ] Confirmed no skipped required gates
- [ ] Confirmed acceptance criteria checkboxes

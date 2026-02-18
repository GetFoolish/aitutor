# PR: Content Pipeline Harness Report

Generated: 2026-02-15T18:46:23.921461+00:00
Harness overall status: PASS

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.17 |
| smoke | PASS | yes | 156.97 |
| pretest_checklist | PASS | yes | 180.98 |
| content_v1_battletest | PASS | yes | 65.6 |
| playwright | PASS | yes | 19.23 |
| greptile | PASS | yes | 0.4 |

## Acceptance Criteria

- [x] No duplicate questions by ID/content fingerprint
- [x] Subject correctness (no cross-subject contamination)
- [x] Assessment does not stop after 1-2 questions
- [x] Adaptive assessment remains stable through at least 8 consecutive next-question transitions (no break around Q4/Q5)
- [x] Questions have answer area and renderable widget config
- [x] Next-question latency within budget
- [x] Grading/skill-path metadata integrity checks passed
- [x] Grading correctness parity holds for rendered options (radio selectedChoiceIds map correctly to answer key)
- [x] No leaked quoted choice text or duplicate 'Choose 1 answer' prompt labels in served/rendered content
- [x] DASH system works end-to-end (health + auth + subject start + question fetch)
- [x] Adaptive assessment start works across all available subjects (no terminal 400/invalid payload)
- [x] Learning mode path stays subject-correct and content-valid (recommend-next has no cross-subject contamination)
- [x] Question loading times are optimized for max speed (initial load + learning recommend-next + adaptive start + repeated next-question transitions within budget)
- [x] Websocket ping/pong smoke check passed
- [x] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [x] Primary assessment actions are visible/reachable without manual scrolling
- [x] Responsive layout has no blocking overflow/clipping on tested viewports
- [x] Playwright screenshots captured for assessment + floating panel
- [x] Floating panel not obscured by widget container (Z-index check)
- [x] AI payload matches browser-rendered content (hydration/render check)
- [x] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- `artifacts/harness/feature-allgreen-responsiveness-final-20260215-133920/screenshots/01-dev-login.png`
- `artifacts/harness/feature-allgreen-responsiveness-final-20260215-133920/screenshots/02-learning-widget-render.png`
- `artifacts/harness/feature-allgreen-responsiveness-final-20260215-133920/screenshots/03-floating-panel-render.png`
- `artifacts/harness/feature-allgreen-responsiveness-final-20260215-133920/screenshots/04-assessment-mobile-responsive.png`
- `artifacts/harness/feature-allgreen-responsiveness-final-20260215-133920/screenshots/05-learning-mobile-responsive.png`

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

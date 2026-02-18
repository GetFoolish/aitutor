# PR: Content Pipeline Harness Report

Generated: 2026-02-15T20:19:16.658848+00:00
Harness overall status: PASS

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.12 |
| smoke | PASS | yes | 178.07 |
| pretest_checklist | PASS | yes | 180.04 |
| content_v1_battletest | PASS | yes | 52.96 |
| playwright | PASS | yes | 18.97 |
| greptile | PASS | no | 0.02 |

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
- [x] Assessment question view has zero browser-level vertical scroll while keeping question, hints, and actions usable
- [x] Assessment question view has zero internal question-container scroll while keeping question/options/hints/actions usable
- [x] Selected radio option highlight renders as complete 4-sided outline (no clipped/incomplete blue border)
- [x] Assessment completion routes into subject-scoped learning state (not generic homepage fallback)
- [x] Responsive layout has no blocking overflow/clipping on tested viewports
- [x] Playwright screenshots captured for assessment + floating panel
- [x] Floating panel not obscured by widget container (Z-index check)
- [x] Floating panel is fully visible on /app and /app/:id routes (not clipped/off-screen/sliver)
- [x] AI payload matches browser-rendered content (hydration/render check)
- [x] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- `artifacts/harness/run-20260215-201206/screenshots/01-dev-login.png`
- `artifacts/harness/run-20260215-201206/screenshots/02-learning-widget-render.png`
- `artifacts/harness/run-20260215-201206/screenshots/03-floating-panel-render.png`
- `artifacts/harness/run-20260215-201206/screenshots/04-assessment-mobile-responsive.png`
- `artifacts/harness/run-20260215-201206/screenshots/05-learning-mobile-responsive.png`
- `artifacts/harness/run-20260215-201206/screenshots/06-floating-panel-profile-route.png`

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

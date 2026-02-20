# PR: Content Pipeline Harness Report

Generated: 2026-02-19T22:37:38.690652+00:00
Harness overall status: FAIL

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.08 |
| smoke | PASS | yes | 2.81 |
| pretest_checklist | PASS | yes | 15.92 |
| content_v1_battletest | PASS | yes | 3.24 |
| playwright | PASS | yes | 13.53 |
| greptile | SKIPPED | yes | 0.02 |

## Acceptance Criteria

- [x] No duplicate questions by ID/content fingerprint
- [x] Subject correctness (assessment + learning, no cross-subject contamination)
- [x] Assessment does not stop after 1-2 questions and reaches completion
- [x] Questions have answer area and renderable widget config
- [x] Grading/skill-path metadata integrity checks passed
- [x] Websocket ping/pong smoke check passed
- [x] No page scroll on assessment + learning desktop baseline
- [x] Floating panel present/usable in assessment
- [x] Floating panel present/usable in learning
- [x] Dot-mask isolation for sidebar cards + floating panel
- [x] Hint legibility passes in light and dark modes
- [x] Hydration/render content match passed
- [x] No leaked secrets/API keys in changed files
- [ ] Greptile review gate passed
- [ ] Strict no-skip policy enforced
- [x] Required screenshot manifest is complete
- [x] Latency budget hard gate (next-question P95 <= 2.5s, hard timeout <= 6s with retry UI)

## Metrics

- `initial_p95_ms`: 330.48
- `next_p95_ms`: 640.77
- `strict_no_skip`: True
- `required_screenshots_present`: True
- `floating_panel_assessment_pass`: True
- `floating_panel_learning_pass`: True
- `dot_mask_pass`: True

## QA Evidence

- `artifacts/harness/run-20260219-223703/screenshots/01-assessment-main.png`
- `artifacts/harness/run-20260219-223703/screenshots/02-assessment-no-scroll-controls-visible.png`
- `artifacts/harness/run-20260219-223703/screenshots/03-assessment-floating-panel-visible.png`
- `artifacts/harness/run-20260219-223703/screenshots/04-assessment-zindex-pass.png`
- `artifacts/harness/run-20260219-223703/screenshots/05-assessment-hint-legibility-light.png`
- `artifacts/harness/run-20260219-223703/screenshots/06-assessment-hint-legibility-dark.png`
- `artifacts/harness/run-20260219-223703/screenshots/07-learning-main.png`
- `artifacts/harness/run-20260219-223703/screenshots/08-learning-no-scroll-controls-visible.png`
- `artifacts/harness/run-20260219-223703/screenshots/09-learning-floating-panel-visible.png`
- `artifacts/harness/run-20260219-223703/screenshots/10-learning-dots-mask-sidebar-panel.png`
- `artifacts/harness/run-20260219-223703/screenshots/11-widget-inline-dropdown-layout.png`
- `artifacts/harness/run-20260219-223703/screenshots/12-widget-image-question-layout.png`
- `artifacts/harness/run-20260219-223703/screenshots/13-assessment-complete-screen.png`
- `artifacts/harness/run-20260219-223703/screenshots/14-latency-overlay-or-metrics-visual.png`

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

# PR: Content Pipeline Harness Report

Generated: 2026-02-15T15:50:42.496158+00:00
Harness overall status: FAIL

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.13 |
| smoke | PASS | yes | 8.15 |
| pretest_checklist | FAIL | yes | 223.56 |
| content_v1_battletest | PASS | yes | 66.75 |
| playwright | PASS | yes | 16.44 |
| greptile | PASS | yes | 0.43 |

## Acceptance Criteria

- [ ] No duplicate questions by ID/content fingerprint
- [ ] Subject correctness (no cross-subject contamination)
- [ ] Assessment does not stop after 1-2 questions
- [ ] Questions have answer area and renderable widget config
- [x] Next-question latency within budget
- [ ] Grading/skill-path metadata integrity checks passed
- [x] DASH system works end-to-end (health + auth + subject start + question fetch)
- [x] Websocket ping/pong smoke check passed
- [x] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [x] Playwright screenshots captured for assessment + floating panel
- [x] Floating panel not obscured by widget container (Z-index check)
- [x] AI payload matches browser-rendered content (hydration/render check)
- [x] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- `artifacts/harness/feature-allgreen-formatfix-20260215-104526/screenshots/01-dev-login.png`
- `artifacts/harness/feature-allgreen-formatfix-20260215-104526/screenshots/02-learning-widget-render.png`
- `artifacts/harness/feature-allgreen-formatfix-20260215-104526/screenshots/03-floating-panel-render.png`

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

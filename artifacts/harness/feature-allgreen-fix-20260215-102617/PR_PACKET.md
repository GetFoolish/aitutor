# PR: Content Pipeline Harness Report

Generated: 2026-02-15T15:33:36.451119+00:00
Harness overall status: PASS

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.12 |
| smoke | PASS | yes | 12.08 |
| pretest_checklist | PASS | yes | 273.5 |
| content_v1_battletest | PASS | yes | 58.68 |
| playwright | PASS | yes | 17.06 |
| greptile | PASS | yes | 0.45 |

## Acceptance Criteria

- [x] No duplicate questions by ID/content fingerprint
- [x] Subject correctness (no cross-subject contamination)
- [x] Assessment does not stop after 1-2 questions
- [x] Questions have answer area and renderable widget config
- [x] Next-question latency within budget
- [x] Grading/skill-path metadata integrity checks passed
- [x] DASH system works end-to-end (health + auth + subject start + question fetch)
- [x] Websocket ping/pong smoke check passed
- [x] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [x] Playwright screenshots captured for assessment + floating panel
- [x] Floating panel not obscured by widget container (Z-index check)
- [x] AI payload matches browser-rendered content (hydration/render check)
- [x] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- `artifacts/harness/feature-allgreen-fix-20260215-102617/screenshots/01-dev-login.png`
- `artifacts/harness/feature-allgreen-fix-20260215-102617/screenshots/02-learning-widget-render.png`
- `artifacts/harness/feature-allgreen-fix-20260215-102617/screenshots/03-floating-panel-render.png`

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

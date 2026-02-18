# PR: Content Pipeline Harness Report

Generated: 2026-02-15T14:10:19.161756+00:00
Harness overall status: FAIL

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.13 |
| smoke | PASS | yes | 4.39 |
| pretest_checklist | SKIPPED | yes | - |
| content_v1_battletest | SKIPPED | yes | - |
| playwright | FAIL | yes | 15.19 |
| greptile | SKIPPED | no | - |

## Acceptance Criteria

- [x] No duplicate questions by ID/content fingerprint
- [x] Subject correctness (no cross-subject contamination)
- [x] Assessment does not stop after 1-2 questions
- [ ] Questions have answer area and renderable widget config
- [x] Next-question latency within budget
- [x] Grading/skill-path metadata integrity checks passed
- [x] Websocket ping/pong smoke check passed
- [ ] Playwright screenshots captured for assessment + floating panel
- [ ] Floating panel not obscured by widget container (Z-index check)
- [ ] AI payload matches browser-rendered content (hydration/render check)
- [x] Greptile review gate passed
- [x] No leaked secrets/API keys in changed files

## QA Evidence

- No screenshots found

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

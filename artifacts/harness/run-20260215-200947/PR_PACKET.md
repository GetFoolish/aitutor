# PR: Content Pipeline Harness Report

Generated: 2026-02-15T20:11:28.809398+00:00
Harness overall status: FAIL

## Gate Results

| Gate | Status | Required | Duration (s) |
| --- | --- | --- | --- |
| secret_scan | PASS | yes | 0.18 |
| smoke | FAIL | yes | 93.29 |
| pretest_checklist | FAIL | yes | 1.24 |
| content_v1_battletest | FAIL | yes | 0.13 |
| playwright | FAIL | yes | 6.14 |
| greptile | PASS | no | 0.02 |

## Acceptance Criteria

- [ ] No duplicate questions by ID/content fingerprint
- [ ] Subject correctness (no cross-subject contamination)
- [ ] Assessment does not stop after 1-2 questions
- [ ] Adaptive assessment remains stable through at least 8 consecutive next-question transitions (no break around Q4/Q5)
- [ ] Questions have answer area and renderable widget config
- [ ] Next-question latency within budget
- [ ] Grading/skill-path metadata integrity checks passed
- [ ] Grading correctness parity holds for rendered options (radio selectedChoiceIds map correctly to answer key)
- [ ] No leaked quoted choice text or duplicate 'Choose 1 answer' prompt labels in served/rendered content
- [ ] DASH system works end-to-end (health + auth + subject start + question fetch)
- [ ] Adaptive assessment start works across all available subjects (no terminal 400/invalid payload)
- [ ] Learning mode path stays subject-correct and content-valid (recommend-next has no cross-subject contamination)
- [ ] Question loading times are optimized for max speed (initial load + learning recommend-next + adaptive start + repeated next-question transitions within budget)
- [ ] Websocket ping/pong smoke check passed
- [ ] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [ ] Primary assessment actions are visible/reachable without manual scrolling
- [ ] Assessment question view has zero browser-level vertical scroll while keeping question, hints, and actions usable
- [ ] Assessment question view has zero internal question-container scroll while keeping question/options/hints/actions usable
- [ ] Selected radio option highlight renders as complete 4-sided outline (no clipped/incomplete blue border)
- [ ] Assessment completion routes into subject-scoped learning state (not generic homepage fallback)
- [ ] Responsive layout has no blocking overflow/clipping on tested viewports
- [ ] Playwright screenshots captured for assessment + floating panel
- [ ] Floating panel not obscured by widget container (Z-index check)
- [ ] Floating panel is fully visible on /app and /app/:id routes (not clipped/off-screen/sliver)
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

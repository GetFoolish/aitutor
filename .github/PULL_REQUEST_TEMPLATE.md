## Summary

- What changed:
- Why it changed:
- Risk level:

## Harness Evidence

- Harness run directory: `artifacts/harness/...`
- PR packet: `artifacts/harness/.../PR_PACKET.md`
- Screenshots:
  - `artifacts/harness/.../screenshots/01-dev-login.png`
  - `artifacts/harness/.../screenshots/02-learning-widget-render.png`
  - `artifacts/harness/.../screenshots/03-floating-panel-render.png`
  - `artifacts/harness/.../screenshots/06-floating-panel-profile-route.png`

## Acceptance Criteria

- [ ] No duplicate questions by ID/content fingerprint
- [ ] Subject correctness validated (no cross-subject contamination)
- [ ] Assessment progression validated (not 1-2 question stall)
- [ ] Adaptive assessment stability validated across at least 8 consecutive next-question transitions (no break around Q4/Q5)
- [ ] Widget rendering + answer area contract validated
- [ ] Next-question latency budget passed
- [ ] Grading + skill-path integrity checks passed
- [ ] Grading correctness parity holds for rendered options (radio selectedChoiceIds map correctly to answer key)
- [ ] No leaked quoted choice text or duplicate "Choose 1 answer" prompt labels in served/rendered content
- [ ] DASH system works end-to-end (health + auth + subject start + question fetch)
- [ ] Adaptive assessment start works across all available subjects (no terminal 400/invalid payload)
- [ ] Learning mode path stays subject-correct and content-valid (recommend-next has no cross-subject contamination)
- [ ] Question loading times are optimized for max speed (initial load + learning recommend-next + adaptive start + next-question within budget)
- [ ] Loading latency checks include sustained flow in both modes (learning recommend-next + repeated adaptive next transitions)
- [ ] Websocket smoke check passed
- [ ] Frontend UI/UX stability checks passed (widget + floating panel visible and usable)
- [ ] Primary assessment actions remain visible/reachable without manual scrolling
- [ ] Assessment question view has zero browser-level vertical scroll at desktop baseline; question, hints, and actions remain simultaneously usable
- [ ] Responsive layout checks passed (no horizontal overflow/clipping on desktop + mobile)
- [ ] Pretest checklist passed
- [ ] Content v1 battletest passed
- [ ] Playwright evidence attached
- [ ] Floating panel Z-index collision check passed (not obscured by widget container)
- [ ] Floating panel is fully visible on both `/app` and `/app/:id` routes (not clipped/off-screen/sliver)
- [ ] Hydration/render compatibility check passed (AI payload maps to browser rendering)
- [ ] Greptile gate passed or reviewer-approved override noted
- [ ] Secret scan passed (no leaked API keys/secrets in changed files)

## Merge Policy Confirmation

- [ ] All required gates are PASS in `summary.json`
- [ ] No required gate skipped
- [ ] Evidence generated from the same commit SHA as this PR
- [ ] QA reviewed screenshots and gate output

## Reviewer Notes

- Known limitations:
- Follow-up tasks:

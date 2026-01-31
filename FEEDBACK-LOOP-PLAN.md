# Consolidated Feedback Loop Plan for AITutor

Based on research from the Moltbot community, Claude Code best practices, and real-world implementations.

---

## Executive Summary

**Current Problem:** Claude/Codex iterate without catching obvious UI bugs because:
1. Browser tool is flaky (Chrome extension disconnects)
2. Validation happens during iteration, not at commit
3. No visual verification requirement
4. No structured success criteria

**Solution:** Implement a 3-layer feedback system with visual verification gates.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  CODEX   │───▶│  CLAUDE  │───▶│  VISUAL  │───▶│  COMMIT  │  │
│  │  (Coder) │    │(Reviewer)│    │   GATE   │    │   GATE   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  Writes code    Reviews code    Screenshots     Tests pass      │
│  with tests     for quality     + ClaudeWatch   + No errors     │
│                                                                 │
│  ◀──────────────── LOOP UNTIL SUCCESS ─────────────────────▶   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Pre-Flight Gate (BLOCKING)

Before ANY feedback loop iteration starts, these must pass:

```typescript
// scripts/preflight-check.ts (ALREADY CREATED)
✓ Backend health (localhost:8000/health)
✓ Frontend loads (localhost:3000)
✓ Screenshot capability works
✓ No console errors on load
✓ Dynamic assessment route accessible
```

**If preflight fails → STOP. Don't waste tokens.**

---

## Phase 2: Visual Verification Gate (NEW)

### Option A: ClaudeWatch Integration (Recommended)

Install and configure [ClaudeWatch](https://github.com/PolarOrchid/ClaudeWatch):

```bash
npm install claudewatch --save-dev
```

Create `.claudewatch/config.js`:
```javascript
module.exports = {
  baseUrl: 'http://localhost:3000',
  pages: [
    {
      path: '/app/assessment/dynamic',
      name: 'Dynamic Assessment',
      requiredElements: [
        { selector: 'button:has-text("math")', description: 'Subject picker' },
        { selector: '.perseus-widget-radio, input[type="radio"]', description: 'Answer choices' },
        { selector: 'button:has-text("submit")', description: 'Submit button' }
      ],
      forbiddenText: [
        'No answer choices available',
        'question data is incomplete',
        'ERR_CONNECTION_REFUSED'
      ]
    }
  ],
  viewports: ['desktop', 'mobile'],
  validation: {
    visual: true,
    accessibility: true,
    console: true
  }
};
```

### Option B: Screenshot Tester (Simpler)

Use [claude-code-app-screenshot-tester](https://github.com/nathanwjclark/claude-code-app-screenshot-tester):

```bash
# Add to CLAUDE.md so Claude knows about it
npm run capture -- http://localhost:3000/app/assessment/dynamic --duration 5000
npm run analyze -- ./.claude-screenshots/aitutor/latest
```

---

## Phase 3: Block-at-Commit Hook (CRITICAL CHANGE)

**Current (wrong):** Validate during iteration
**Correct:** Let Claude finish, validate at commit time

Update `~/.clawdbot/moltbot.json`:

```json
{
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "block-at-commit": {
          "enabled": true,
          "trigger": "PreToolUse",
          "pattern": "git commit",
          "command": "cd /Users/gaganarora/clawd/aitutor-homework && npm run validate:all",
          "blockOnFailure": true,
          "message": "Commit blocked: validation failed. Fix issues and retry."
        }
      }
    }
  }
}
```

Add to `frontend/package.json`:
```json
{
  "scripts": {
    "validate:all": "npm run validate:preflight && npm run validate:visual && npm run test:e2e",
    "validate:preflight": "npx tsx ../scripts/preflight-check.ts",
    "validate:visual": "npx tsx ../scripts/visual-review.ts",
    "test:e2e": "npx playwright test"
  }
}
```

---

## Phase 4: Success Markers (Ralph Wiggum Pattern)

Use explicit completion markers in prompts:

```markdown
## Task
Fix the dynamic assessment to show answer choices.

## Success Criteria
When complete, the following must be true:
1. Preflight check passes
2. Visual review shows no critical errors
3. E2E tests pass
4. No "No answer choices available" in UI

## Completion Marker
When ALL criteria pass, output: <promise>ASSESSMENT_FIXED</promise>

Do not output the marker until you have VERIFIED all criteria.
```

The feedback loop continues until the marker appears.

---

## Phase 5: Parallel Agent Setup

### Coder-Reviewer Split

```
┌─────────────────┐     ┌─────────────────┐
│     CODEX       │     │     CLAUDE      │
│  (GPT-5 Codex)  │     │  (Sonnet 4.5)   │
├─────────────────┤     ├─────────────────┤
│ Focus: Writing  │     │ Focus: Review   │
│ - Implementation│────▶│ - Code quality  │
│ - Tests         │     │ - Visual verify │
│ - Bug fixes     │     │ - Design system │
└─────────────────┘     └─────────────────┘
         ▲                      │
         │                      │
         └──── Feedback ────────┘
```

### Swarm Pattern for Complex Tasks

For large refactors, spawn specialist agents:

```
Leader (You/Main Claude)
    │
    ├── Spawn: Security Reviewer
    ├── Spawn: Performance Reviewer
    ├── Spawn: UI/UX Reviewer (with screenshots)
    └── Spawn: Test Coverage Reviewer

All report back via inbox → Leader synthesizes
```

---

## Phase 6: Design System Enforcement

### Install UI Audit Skill

```bash
moltbot skill install ui-audit
```

### Add Design Rules to CLAUDE.md

```markdown
## Design System Rules (MANDATORY)

Before approving ANY UI change, verify:

### Spacing (8pt Grid)
- Valid: 0, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64px
- REJECT: 10px, 15px, 20px, 30px

### Neo-Brutalism
- Borders: 3px solid #000
- Shadows: 4px 4px 0 #000 (NO blur)
- Border-radius: 8px, 12px, or 999px only

### Critical Errors (INSTANT REJECT)
- "No answer choices available"
- "question data is incomplete"
- Any ERR_CONNECTION errors
```

---

## Implementation Checklist

### Immediate (Today)

- [ ] Update `moltbot.json` with block-at-commit hook
- [ ] Add `validate:all` script to package.json
- [ ] Install `moltbot skill install ui-audit`
- [ ] Update CLAUDE.md with design rules
- [ ] Test the complete flow manually

### This Week

- [ ] Set up ClaudeWatch with config
- [ ] Create baseline screenshots for regression
- [ ] Add success markers to feedback loop prompts
- [ ] Test parallel coder-reviewer setup

### Next Week

- [ ] Implement swarm pattern for complex tasks
- [ ] Add Claude Vision for design scoring
- [ ] Set up CI integration for design linting
- [ ] Document the complete workflow

---

## Updated moltbot.json Configuration

```json
{
  "agents": {
    "defaults": {
      "feedbackLoop": {
        "enabled": true,
        "coder": "openai-codex/gpt-5.2",
        "reviewer": "anthropic/claude-sonnet-4-5",
        "maxIterations": 10,

        "preflight": {
          "enabled": true,
          "script": "npx tsx scripts/preflight-check.ts",
          "blockOnFailure": true
        },

        "validation": {
          "visual": {
            "enabled": true,
            "tool": "claudewatch",
            "screenshotOnError": true
          },
          "tests": {
            "enabled": true,
            "command": "npx playwright test"
          },
          "designLint": {
            "enabled": true,
            "command": "npx tsx scripts/lint-design-tokens.ts"
          }
        },

        "blockAtCommit": {
          "enabled": true,
          "script": "npm run validate:all",
          "blockOnFailure": true
        },

        "successMarker": {
          "enabled": true,
          "pattern": "<promise>([A-Z_]+)</promise>",
          "requiredForApproval": true
        },

        "memory": {
          "enabled": true,
          "feedbackHistoryPath": "memory/FEEDBACK-HISTORY.md",
          "searchBeforeReview": true,
          "saveAfterReview": true
        }
      }
    }
  }
}
```

---

## Key Differences from Current Setup

| Aspect | Current (Broken) | New (Fixed) |
|--------|------------------|-------------|
| When to validate | During iteration | At commit time |
| Browser tool | Chrome extension (flaky) | Playwright (reliable) |
| Success criteria | Implicit | Explicit markers |
| Visual check | Optional | Mandatory gate |
| Feedback format | Free text | Structured JSON |
| Design rules | In checklist | Enforced by lint |
| Parallel agents | Sequential | True parallel |

---

## Sources

- [Ralph Wiggum Technique](https://www.atcyrus.com/stories/ralph-wiggum-technique-claude-code-autonomous-loops)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [ClaudeWatch](https://github.com/PolarOrchid/ClaudeWatch)
- [Screenshot Tester](https://github.com/nathanwjclark/claude-code-app-screenshot-tester)
- [Parallel Subagents](https://zachwills.net/how-to-use-claude-code-subagents-to-parallelize-development/)
- [Swarm Orchestration](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [Addy Osmani Workflow](https://addyosmani.com/blog/ai-coding-workflow/)
- [Awesome Moltbot Skills](https://github.com/VoltAgent/awesome-moltbot-skills)

---

## Next Steps

1. **Apply this plan** - Update moltbot.json with new config
2. **Test the flow** - Run a complete feedback loop cycle
3. **Iterate** - Adjust based on what works

The key insight: **Don't validate during iteration. Gate at commit.**

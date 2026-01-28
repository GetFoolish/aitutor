# CLAUDE.md - AI Coding Guidelines for AITutor

## Hard Rules

### Two-Strike Rule
If your approach fails twice, **STOP**. Do not try a third time.
Instead:
1. Explain why it failed
2. Propose 3 alternative approaches
3. Wait for approval before proceeding

### Verify Before Moving On
After every change:
- Run the relevant test/check
- Confirm it actually works (screenshot, output, or logs)
- Do NOT proceed until verified

**"It should work" is not verification.**

### Time-Box Explorations
- Max 15 minutes on any single approach
- If stuck, escalate with options — don't keep spinning

### Check Before You Code
Before touching any code:
- [ ] Verify which variables/state actually exist in the component
- [ ] Confirm imports and dependencies are installed
- [ ] Check if the service is running and responsive
- [ ] Test the simplest possible version first

## Anti-Patterns (DO NOT)

- ❌ Try the same failing approach more than twice
- ❌ Use complex CSS hacks (clipPath, negative margins) when simpler solutions exist
- ❌ Assume variables exist — verify them first
- ❌ Continue coding if service is unresponsive — fix that first
- ❌ Build UI for data you haven't inspected ("show me what OCR actually outputs" first)
- ❌ Over-engineer when text display would work fine
- ❌ Use nested ternaries — prefer if/else or switch statements

## Required Workflow

### Before Any Change
1. Read the relevant code and understand existing state/props
2. Check that dependencies are installed (`pip list`, `npm list`)
3. Verify services are running (`curl health endpoints`)

### After Any Change
1. Run locally and verify it works
2. If UI change: describe what you see or take screenshot
3. If API change: show the actual response
4. Only then say "done"

### When Debugging
1. First: check logs (`docker logs`, service output)
2. Second: verify the data (what does the API actually return?)
3. Third: check the simplest case (does it work with hardcoded values?)
4. Only then: try fixes

## Project-Specific Notes

### Services & Ports
- Teaching Assistant: 8002
- Homework Service: 8004
- Frontend: 3000

### Common Issues
- PyMuPDF needs to be installed for PDF processing
- MongoDB must be running for any backend work
- Kill orphan processes before restarting: `lsof -i :PORT | grep LISTEN`

### Image/OCR Approach
- OCR extracts text, not visual elements
- For image content (cookies, shapes, etc.): display the actual image, don't rely on OCR
- Always inspect OCR output before building UI around it

## When Things Go Wrong

If you've spent 30+ minutes on something and it's still broken:
1. Stop coding
2. Summarize what you tried and why it failed
3. Ask: "Should I continue, try a different approach, or pause for help?"

**Don't waste hours on a broken approach.**

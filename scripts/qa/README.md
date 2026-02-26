# Pre-Flight QA System

Fast automated QA checks using cmux browser automation to catch regressions before manual testing.

## Overview

This system runs 5 critical checks in < 30 seconds:

1. **Empty Answer Validation** - Verifies empty answers are rejected
2. **Layout Crush Detection** - Checks mobile viewport rendering
3. **MongoDB Health** - Ensures database connection is responsive
4. **State Management** - Validates session isolation
5. **Visual Regression** - Compares screenshots against baselines

## Quick Start

### Prerequisites

- Services running: frontend (localhost:5173), backend (localhost:8000)
- cmux browser installed and available in PATH
- Python 3.8+ with venv activated

### Run Pre-Flight Check

```bash
# From project root
./scripts/qa/preflight.sh
```

### Auto-Run with run_tutor.sh

```bash
# Run QA check after services start
RUN_PREFLIGHT_QA=1 ./run_tutor.sh
```

## Usage

### Manual Check Execution

```bash
# Run all checks
python3 scripts/qa/qa_runner.py

# Run with custom artifacts directory
python3 scripts/qa/qa_runner.py --artifacts-dir /path/to/artifacts

# Run specific check module
python3 scripts/qa/checks/empty_validation.py
```

### Interpreting Results

**Terminal Output:**
```
🔍 Pre-Flight QA Check - 2026-02-26 14:30:00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ [1/5] Empty validation       (2.3s)
✅ [2/5] Layout crush (mobile)  (1.8s)
❌ [3/5] MongoDB timeout         (5.1s)
   └─ Health check took 4.8s (budget: 3s)
✅ [4/5] State management        (3.2s)
⚠️  [5/5] Visual regression      (4.1s)
   └─ 7.2% diff on assessment-question.png

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary: 3 passed, 1 failed, 1 warning (16.5s)
```

**Exit Codes:**
- `0` - All checks passed
- `1` - One or more checks failed

**Artifacts:**
- Located in `artifacts/qa/run-TIMESTAMP/`
- Screenshots: `screenshots/`
- DOM snapshots: `dom-snapshots/`
- Logs: `logs/`
- Summary JSON: `summary.json`

## Check Details

### 1. Empty Answer Validation

**Purpose:** Catch the recurring bug where empty dropdown/radio answers are accepted as "CORRECT"

**Test Flow:**
1. Navigate to dev-login
2. Select subject
3. Start assessment
4. Click submit without selecting answer
5. Verify error message or disabled button

**Pass Criteria:** Error message appears OR submit stays disabled

### 2. Layout Crush Detection

**Purpose:** Catch mobile viewport layout collapse (height: 0px bug)

**Test Flow:**
1. Set viewport to 375x667 (iPhone SE)
2. Navigate to assessment
3. Verify content height > 100px
4. Check `.perseus-renderer` is visible
5. Capture screenshot

**Pass Criteria:** Content height > 100px AND no overflow crush

### 3. MongoDB Health

**Purpose:** Catch Atlas connection timeouts that cascade to UI hangs

**Test Flow:**
1. Call `/api/health` endpoint
2. Verify response time < 3s
3. Check `ready: true` in response
4. Verify not falling back to localhost

**Pass Criteria:** Health responds < 3s with `ready: true`

### 4. State Management

**Purpose:** Catch question state leaking between assessment sessions

**Test Flow:**
1. Start assessment, get Q1 content
2. Submit answer
3. Exit assessment
4. Start NEW assessment
5. Verify Q1 content differs

**Pass Criteria:** Question content differs between sessions

### 5. Visual Regression

**Purpose:** Flag design system violations and layout changes

**Test Flow:**
1. Screenshot assessment landing
2. Screenshot first question
3. Screenshot feedback panel
4. Compare against baselines (5% pixel diff tolerance)

**Pass Criteria:** < 5% visual diff from baseline (or no baseline exists)

**Baseline Management:**
- Baselines stored in `scripts/qa/baselines/screenshots/`
- First run creates baselines
- Subsequent runs compare against baselines
- Commit baselines to git for team consistency

## Architecture

### Directory Structure

```
scripts/qa/
├── cmux_browser.py          # cmux CLI wrapper
├── qa_runner.py             # Orchestrator
├── preflight.sh             # Shell entry point
├── README.md                # This file
├── checks/                  # Check modules
│   ├── empty_validation.py
│   ├── layout_crush.py
│   ├── mongodb_health.py
│   ├── state_management.py
│   └── visual_regression.py
└── baselines/               # Visual regression baselines
    └── screenshots/
        └── .gitkeep
```

### Check Module Interface

Each check module exports a `run_check()` function:

```python
def run_check() -> Tuple[bool, str, float]:
    """Run the check.

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()
    try:
        # Check logic here
        passed = True
        details = "Check details"
    except Exception as e:
        passed = False
        details = f"Error: {e}"

    elapsed = time.time() - start
    return passed, details, elapsed
```

### cmux Browser API

See `cmux_browser.py` for full API. Key methods:

```python
from scripts.qa.cmux_browser import CmuxBrowser

browser = CmuxBrowser()
browser.navigate("http://localhost:5173")
browser.wait_for_element(".assessment-question", timeout_ms=5000)
browser.click('[data-testid="submit-button"]')
browser.fill('[data-subject="Science"]', "Science")
snapshot = browser.snapshot(".content-wrapper")
```

## Environment Variables

```bash
# Frontend URL (default: http://localhost:5173)
export FRONTEND_URL=http://localhost:5173

# Backend API URL (default: http://localhost:8000)
export DASH_API_URL=http://localhost:8000

# MongoDB URI (from .env, no default)
export MONGODB_URI=mongodb+srv://...

# Enable auto-run with run_tutor.sh
export RUN_PREFLIGHT_QA=1
```

## Troubleshooting

### "cmux browser not available"

Install cmux or ensure it's in PATH:
```bash
which cmux
cmux browser --help
```

### "Services not ready"

Ensure services are running:
```bash
# Check frontend
curl http://localhost:5173

# Check backend health
curl http://localhost:8000/health
```

### "Element not found" errors

Check that:
- Frontend is actually loaded (not 404)
- Selectors match current HTML structure
- Timeouts are sufficient for slow responses

### Screenshots not matching

- First run creates baselines (expected)
- Legitimate UI changes require baseline updates
- Delete old baselines to regenerate

## Integration with Existing Tests

### Relation to Other Test Layers

**Layer 1: Pre-Flight (This System)** - Fast smoke test before manual testing
**Layer 2: Watch Mode (Future)** - Real-time feedback during development
**Layer 3: Playwright E2E** - Comprehensive harness for PR workflow

### When to Use Which

- **Pre-Flight:** Before manual localhost testing, fast feedback
- **Playwright:** Before PR submission, comprehensive coverage
- **Watch Mode:** During active development, continuous feedback

### No Conflicts

- Pre-Flight uses cmux browser (terminal-based)
- Playwright uses Chromium (separate browser instance)
- Can run concurrently without conflicts

## Future Enhancements

- Watch mode: Auto-run on file changes
- Continuous monitoring: Background polling
- Performance profiling: Track page load times
- Accessibility checks: WCAG validation
- Cross-browser testing: Multiple cmux modes

## Support

For issues or questions:
1. Check logs in `artifacts/qa/run-TIMESTAMP/logs/`
2. Review `summary.json` for structured output
3. Verify cmux browser version: `cmux --version`
4. Check service logs: `backend.log`, browser console

## Contributing

When adding new checks:

1. Create module in `scripts/qa/checks/`
2. Implement `run_check() -> Tuple[bool, str, float]`
3. Add check to `qa_runner.py` orchestrator
4. Update this README with check details
5. Add baseline files if needed
6. Test standalone: `python3 scripts/qa/checks/new_check.py`

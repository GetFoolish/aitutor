# QA System Quick Start

## Usage

### Run Pre-Flight Check

```bash
# From project root
./scripts/qa/preflight.sh
```

### Auto-Run with Services

```bash
RUN_PREFLIGHT_QA=1 ./run_tutor.sh
```

## Expected Output

```
🔍 Pre-Flight QA Check - 2026-02-26 15:42:19
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ [1/5] Empty validation               (2.3s)
✅ [2/5] Layout crush (mobile)          (1.8s)
✅ [3/5] MongoDB health                 (0.8s)
✅ [4/5] State management               (3.2s)
✅ [5/5] Visual regression              (4.1s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary: 5 passed (12.2s)

📁 Artifacts: artifacts/qa/run-20260226-154219
```

## What It Checks

1. **Empty validation** - Verifies empty answers are rejected
2. **Layout crush** - Detects mobile viewport layout collapse
3. **MongoDB health** - Checks database connection < 3s
4. **State management** - Validates session isolation
5. **Visual regression** - Compares DOM against baselines

## Files Created

```
artifacts/qa/run-TIMESTAMP/
├── summary.json          # JSON report
├── screenshots/          # Visual evidence
├── dom-snapshots/        # Page snapshots
└── logs/                 # Check logs
```

## Troubleshooting

### "Services not responding"

Start services first:
```bash
./run_tutor.sh
```

### "cmux browser not found"

Install or add to PATH:
```bash
which cmux
cmux browser --help
```

### Visual regression fails after UI changes

Update baselines:
```bash
python3 scripts/qa/checks/visual_regression.py --update-baseline
```

## More Info

- Full documentation: `scripts/qa/README.md`
- Implementation details: `scripts/qa/IMPLEMENTATION_COMPLETE.md`

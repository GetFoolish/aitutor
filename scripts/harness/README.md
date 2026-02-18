# Harness Scripts

- `run_pipeline_harness.py`: orchestrates all gates and writes `summary.json`.
- `smoke_test.py`: API and websocket smoke validations.
- `secret_scan.sh`: scans changed files for accidental secret/API key leaks.
- `run_playwright_capture.sh`: executes Playwright CLI test and captures screenshots.
- `greptile_gate.sh`: runs configured Greptile review command.
- `generate_pr_packet.py`: builds `PR_PACKET.md` from harness outputs.
- `create_pr.sh`: optional helper to branch, commit harness files, push, and open PR.
- `post_pr_comment.sh`: posts a generated markdown body to a PR.

## Typical local run

```bash
python3 scripts/harness/run_pipeline_harness.py --mode local
```

## Typical CI run

```bash
python3 scripts/harness/run_pipeline_harness.py --mode ci --output-dir artifacts/harness/ci-run
```

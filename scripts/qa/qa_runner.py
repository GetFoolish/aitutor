#!/usr/bin/env python3
"""QA runner orchestrator - executes all pre-flight checks and generates reports.

This script runs all QA check modules, manages timeouts, and generates
terminal output and JSON summaries.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class CheckResult:
    """Result from running a single check."""
    name: str
    passed: bool
    details: str
    elapsed_s: float
    error: Optional[str] = None
    warning: bool = False


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _now_stamp() -> str:
    """Get current timestamp for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _load_check_module(check_path: Path) -> Any:
    """Dynamically load a check module.

    Args:
        check_path: Path to check module .py file

    Returns:
        Loaded module
    """
    spec = importlib.util.spec_from_file_location(check_path.stem, check_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {check_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_check(
    check_name: str,
    check_path: Path,
    timeout_s: int = 30,
    artifacts_dir: Optional[Path] = None,
) -> CheckResult:
    """Run a single check module.

    Args:
        check_name: Human-readable check name
        check_path: Path to check module
        timeout_s: Timeout in seconds
        artifacts_dir: Artifacts directory to pass to check

    Returns:
        CheckResult
    """
    start = time.time()

    try:
        # Load check module
        module = _load_check_module(check_path)

        if not hasattr(module, "run_check"):
            return CheckResult(
                name=check_name,
                passed=False,
                details="Check module missing run_check() function",
                elapsed_s=time.time() - start,
                error="Missing run_check() function",
            )

        # Run check function with timeout
        # Note: Python doesn't have easy per-function timeouts
        # For now, rely on check modules to handle their own timeouts
        passed, details, check_elapsed = module.run_check()

        elapsed = time.time() - start

        # Check if this is a warning (passed but with notes)
        warning = passed and ("warning" in details.lower() or "%" in details)

        return CheckResult(
            name=check_name,
            passed=passed,
            details=details,
            elapsed_s=elapsed,
            warning=warning,
        )

    except Exception as e:
        elapsed = time.time() - start
        return CheckResult(
            name=check_name,
            passed=False,
            details=f"Check failed with exception: {e}",
            elapsed_s=elapsed,
            error=str(e),
        )


def run_all_checks(artifacts_dir: Path) -> List[CheckResult]:
    """Run all QA checks.

    Args:
        artifacts_dir: Directory for artifacts

    Returns:
        List of CheckResults
    """
    checks_dir = PROJECT_ROOT / "scripts" / "qa" / "checks"

    # Define check modules in execution order
    check_modules = [
        ("Empty validation", checks_dir / "empty_validation.py"),
        ("Layout crush (mobile)", checks_dir / "layout_crush.py"),
        ("MongoDB health", checks_dir / "mongodb_health.py"),
        ("State management", checks_dir / "state_management.py"),
        ("Visual regression", checks_dir / "visual_regression.py"),
    ]

    results: List[CheckResult] = []

    for check_name, check_path in check_modules:
        if not check_path.exists():
            results.append(
                CheckResult(
                    name=check_name,
                    passed=False,
                    details=f"Check module not found: {check_path}",
                    elapsed_s=0.0,
                    error=f"Module not found: {check_path}",
                )
            )
            continue

        result = run_check(check_name, check_path, artifacts_dir=artifacts_dir)
        results.append(result)

    return results


def generate_terminal_report(results: List[CheckResult]) -> None:
    """Generate and print terminal report.

    Args:
        results: List of check results
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    print()
    print(f"🔍 Pre-Flight QA Check - {timestamp}")
    print("━" * 80)

    total_elapsed = sum(r.elapsed_s for r in results)

    for idx, result in enumerate(results, 1):
        # Status icon
        if result.passed and not result.warning:
            icon = "✅"
        elif result.warning:
            icon = "⚠️ "
        else:
            icon = "❌"

        # Print check summary
        print(f"{icon} [{idx}/{len(results)}] {result.name:<30} ({result.elapsed_s:.1f}s)")

        # Print details if failed or warning
        if not result.passed or result.warning:
            # Indent details
            detail_lines = result.details.split("\n")
            for line in detail_lines:
                if line.strip():
                    print(f"   └─ {line}")

    print("━" * 80)

    # Summary
    passed_count = sum(1 for r in results if r.passed and not r.warning)
    failed_count = sum(1 for r in results if not r.passed)
    warning_count = sum(1 for r in results if r.warning)

    summary_parts = []
    if passed_count:
        summary_parts.append(f"{passed_count} passed")
    if failed_count:
        summary_parts.append(f"{failed_count} failed")
    if warning_count:
        summary_parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")

    print(f"📊 Summary: {', '.join(summary_parts)} ({total_elapsed:.1f}s)")

    # Print failures and warnings
    if failed_count > 0:
        print()
        for result in results:
            if not result.passed:
                print(f"❌ {result.name}: {result.details.split(chr(10))[0]}")

    if warning_count > 0:
        print()
        for result in results:
            if result.warning:
                print(f"⚠️  {result.name}: {result.details.split(chr(10))[0]}")

    print()


def generate_json_report(
    results: List[CheckResult],
    artifacts_dir: Path,
) -> Dict[str, Any]:
    """Generate JSON report.

    Args:
        results: List of check results
        artifacts_dir: Artifacts directory

    Returns:
        Report dict
    """
    report = {
        "created_at": _now_iso(),
        "artifacts_dir": str(artifacts_dir),
        "checks": [],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed and not r.warning),
            "failed": sum(1 for r in results if not r.passed),
            "warnings": sum(1 for r in results if r.warning),
            "total_elapsed_s": round(sum(r.elapsed_s for r in results), 2),
        },
        "ok": all(r.passed for r in results),
    }

    for result in results:
        report["checks"].append({
            "name": result.name,
            "passed": result.passed,
            "warning": result.warning,
            "details": result.details,
            "elapsed_s": round(result.elapsed_s, 2),
            "error": result.error,
        })

    return report


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run pre-flight QA checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Directory for artifacts (default: artifacts/qa/run-TIMESTAMP)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only JSON report (no terminal formatting)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Set up artifacts directory
    if args.artifacts_dir:
        artifacts_dir = args.artifacts_dir
    else:
        artifacts_dir = PROJECT_ROOT / "artifacts" / "qa" / f"run-{_now_stamp()}"

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (artifacts_dir / "screenshots").mkdir(exist_ok=True)
    (artifacts_dir / "dom-snapshots").mkdir(exist_ok=True)
    (artifacts_dir / "logs").mkdir(exist_ok=True)

    # Set environment variables for checks
    os.environ["QA_ARTIFACTS_DIR"] = str(artifacts_dir)
    os.environ["FRONTEND_URL"] = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    os.environ["DASH_API_URL"] = os.environ.get("DASH_API_URL", "http://localhost:8000")

    # Run checks
    results = run_all_checks(artifacts_dir)

    # Generate reports
    if not args.json_only:
        generate_terminal_report(results)

    json_report = generate_json_report(results, artifacts_dir)

    # Write JSON report
    summary_path = artifacts_dir / "summary.json"
    summary_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")

    if not args.json_only:
        print(f"📁 Artifacts: {artifacts_dir}")
        print()

    # Exit with appropriate code
    exit_code = 0 if json_report["ok"] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

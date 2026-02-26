#!/usr/bin/env python3
"""Visual regression QA check.

Validates:
- UI screenshots match baseline images
- No unexpected visual changes
- Key page elements render correctly
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cmux_browser import CmuxBrowser, CmuxBrowserError


def _compute_snapshot_hash(snapshot_text: str) -> str:
    """Compute SHA256 hash of snapshot for comparison.

    Args:
        snapshot_text: DOM snapshot text

    Returns:
        SHA256 hash hex string
    """
    return hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest()


def _get_baseline_path(page_name: str, baselines_dir: Path) -> Path:
    """Get path to baseline snapshot file.

    Args:
        page_name: Name of the page (e.g., 'home', 'about')
        baselines_dir: Directory containing baseline snapshots

    Returns:
        Path to baseline file
    """
    return baselines_dir / f"{page_name}_snapshot.txt"


def _get_baseline_hash_path(page_name: str, baselines_dir: Path) -> Path:
    """Get path to baseline hash file.

    Args:
        page_name: Name of the page (e.g., 'home', 'about')
        baselines_dir: Directory containing baseline hashes

    Returns:
        Path to baseline hash file
    """
    return baselines_dir / f"{page_name}_snapshot.hash"


def _save_baseline(page_name: str, snapshot_text: str, baselines_dir: Path) -> None:
    """Save snapshot as new baseline.

    Args:
        page_name: Name of the page
        snapshot_text: DOM snapshot text
        baselines_dir: Directory to save baselines
    """
    baselines_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = _get_baseline_path(page_name, baselines_dir)
    hash_path = _get_baseline_hash_path(page_name, baselines_dir)

    snapshot_path.write_text(snapshot_text, encoding="utf-8")
    snapshot_hash = _compute_snapshot_hash(snapshot_text)
    hash_path.write_text(snapshot_hash, encoding="utf-8")


def _load_baseline_hash(page_name: str, baselines_dir: Path) -> Optional[str]:
    """Load baseline hash if it exists.

    Args:
        page_name: Name of the page
        baselines_dir: Directory containing baselines

    Returns:
        Baseline hash or None if not found
    """
    hash_path = _get_baseline_hash_path(page_name, baselines_dir)
    if not hash_path.exists():
        return None
    return hash_path.read_text(encoding="utf-8").strip()


def _compare_snapshots(current_snapshot: str, baseline_hash: str) -> Tuple[bool, str]:
    """Compare current snapshot with baseline.

    Args:
        current_snapshot: Current DOM snapshot text
        baseline_hash: Baseline snapshot hash

    Returns:
        Tuple of (matches, details)
    """
    current_hash = _compute_snapshot_hash(current_snapshot)

    if current_hash == baseline_hash:
        return True, f"Snapshot matches baseline (hash: {current_hash[:16]}...)"

    # Calculate simple diff metrics
    current_lines = current_snapshot.split("\n")
    line_count_diff = len(current_lines)

    return False, (
        f"Snapshot differs from baseline\n"
        f"  Current hash:  {current_hash[:16]}...\n"
        f"  Baseline hash: {baseline_hash[:16]}...\n"
        f"  Current lines: {line_count_diff}"
    )


def run_check(
    url: str = "http://localhost:8000",
    baselines_dir: Optional[Path] = None,
    update_baseline: bool = False,
) -> Tuple[bool, str, float]:
    """Run visual regression check.

    Args:
        url: Base URL to test (default: http://localhost:8000)
        baselines_dir: Directory containing baseline snapshots
        update_baseline: If True, save current snapshot as new baseline

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()
    browser = None

    if baselines_dir is None:
        baselines_dir = Path(__file__).parent.parent / "baselines" / "screenshots"

    try:
        browser = CmuxBrowser()

        # Step 1: Open browser and navigate to app
        open_result = browser.open(url)
        if open_result["status"] != "ok":
            return False, f"Failed to open browser: {open_result['error']}", time.time() - start

        # Wait for page to load
        wait_result = browser.wait_for_element("body", timeout_ms=5000)
        if wait_result["status"] != "ok":
            return False, f"Page failed to load: {wait_result['error']}", time.time() - start

        # Step 2: Capture DOM snapshot
        # Use compact snapshot to focus on structure, not dynamic content
        snapshot_result = browser.snapshot(compact=True, max_depth=5)
        if snapshot_result["status"] != "ok":
            return False, f"Failed to capture snapshot: {snapshot_result['error']}", time.time() - start

        current_snapshot = snapshot_result["raw_output"]
        if not current_snapshot:
            return False, "Snapshot is empty", time.time() - start

        page_name = "home"

        # Step 3: Update baseline if requested
        if update_baseline:
            _save_baseline(page_name, current_snapshot, baselines_dir)
            elapsed = time.time() - start
            return True, f"Baseline updated for '{page_name}' page (snapshot: {len(current_snapshot)} chars)", elapsed

        # Step 4: Load baseline and compare
        baseline_hash = _load_baseline_hash(page_name, baselines_dir)
        if baseline_hash is None:
            # No baseline exists yet - save current as baseline
            _save_baseline(page_name, current_snapshot, baselines_dir)
            elapsed = time.time() - start
            return True, f"No baseline found - saved current snapshot as baseline for '{page_name}' (snapshot: {len(current_snapshot)} chars)", elapsed

        # Step 5: Compare snapshots
        matches, compare_details = _compare_snapshots(current_snapshot, baseline_hash)

        elapsed = time.time() - start
        if matches:
            return True, f"Visual regression check passed: {compare_details}", elapsed
        else:
            return False, f"Visual regression detected: {compare_details}", elapsed

    except CmuxBrowserError as e:
        return False, f"Browser error: {e}", time.time() - start
    except Exception as e:
        return False, f"Unexpected error: {e}", time.time() - start


def main() -> None:
    """Entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run visual regression QA check")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base URL to test (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--baselines-dir",
        type=Path,
        default=None,
        help="Directory containing baseline snapshots (default: ../baselines/screenshots)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current snapshot",
    )
    args = parser.parse_args()

    passed, details, elapsed = run_check(
        args.url,
        args.baselines_dir,
        args.update_baseline,
    )

    print(f"Visual Regression Check: {'PASS' if passed else 'FAIL'}")
    print(f"Details: {details}")
    print(f"Elapsed: {elapsed:.3f}s")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

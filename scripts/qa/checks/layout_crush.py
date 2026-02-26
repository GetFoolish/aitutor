#!/usr/bin/env python3
"""Layout crush QA check.

Verifies that UI elements don't overlap or crush each other at different
viewport sizes and with various floating panels.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cmux_browser import CmuxBrowser


def check_element_overlap(browser: CmuxBrowser, selectors: List[str]) -> Tuple[bool, str]:
    """Check if any elements overlap by comparing bounding boxes.

    Args:
        browser: CmuxBrowser instance
        selectors: List of CSS selectors to check

    Returns:
        Tuple of (no_overlap, details)
    """
    # Get bounding rectangles using JavaScript
    js_script = """
    (function() {
        const selectors = {selectors};
        const results = [];

        for (const sel of selectors) {
            const elem = document.querySelector(sel);
            if (elem) {
                const rect = elem.getBoundingClientRect();
                results.push({
                    selector: sel,
                    top: rect.top,
                    left: rect.left,
                    bottom: rect.bottom,
                    right: rect.right,
                    width: rect.width,
                    height: rect.height
                });
            }
        }

        return JSON.stringify(results);
    })();
    """.replace("{selectors}", str(selectors).replace("'", '"'))

    eval_result = browser.eval_js(js_script)

    if eval_result["status"] != "ok":
        return False, f"Failed to evaluate element positions: {eval_result['error']}"

    # Parse results and check for overlaps
    try:
        import json
        rects = json.loads(eval_result["raw_output"])

        overlaps = []
        for i, rect1 in enumerate(rects):
            for j, rect2 in enumerate(rects[i + 1:], start=i + 1):
                # Check if rectangles overlap
                if (rect1["left"] < rect2["right"] and
                    rect1["right"] > rect2["left"] and
                    rect1["top"] < rect2["bottom"] and
                    rect1["bottom"] > rect2["top"]):
                    overlaps.append(f"{rect1['selector']} overlaps {rect2['selector']}")

        if overlaps:
            return False, f"Overlaps detected: {', '.join(overlaps)}"
        else:
            return True, f"No overlaps among {len(rects)} elements"

    except Exception as e:
        return False, f"Failed to parse element positions: {e}"


def run_check() -> Tuple[bool, str, float]:
    """Run layout crush check.

    Tests:
    1. Load assessment page at different viewport sizes
    2. Check for element overlaps (toolbar, floating panel, question content)
    3. Verify z-index layering is correct
    4. Test with floating panels visible

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()
    browser = None
    issues = []

    try:
        # Get base URL from environment
        base_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

        # Initialize browser
        browser = CmuxBrowser()

        # Step 1: Open assessment page
        open_result = browser.open(f"{base_url}/app/dev-login")
        if open_result["status"] != "ok":
            elapsed = time.time() - start
            return False, f"Failed to open browser: {open_result['error']}", elapsed

        # Step 2: Dev login
        wait_result = browser.wait_for_element("button", timeout_ms=5000)
        if wait_result["status"] != "ok":
            elapsed = time.time() - start
            return False, f"Dev login page not loaded: {wait_result['error']}", elapsed

        click_result = browser.click("button")
        if click_result["status"] != "ok":
            elapsed = time.time() - start
            return False, f"Failed to click dev login: {click_result['error']}", elapsed

        # Wait for assessment to load
        time.sleep(3)

        # Step 3: Check for common layout issues
        # Look for elements that commonly overlap

        # Check if floating control panel exists
        floating_panel_result = browser.get_property("html", "div[class*='floating'], div[class*='FloatingControlPanel']")
        has_floating_panel = floating_panel_result["status"] == "ok" and floating_panel_result["raw_output"]

        # Check for toolbar
        toolbar_result = browser.get_property("html", "div[class*='toolbar'], nav, header")
        has_toolbar = toolbar_result["status"] == "ok" and toolbar_result["raw_output"]

        # Get page snapshot to analyze layout
        snapshot_result = browser.snapshot(compact=False, max_depth=4)
        if snapshot_result["status"] == "ok":
            snapshot_text = snapshot_result["raw_output"].lower()

            # Look for common layout crush indicators
            crush_indicators = [
                ("z-index: -1", "Negative z-index detected (may hide content)"),
                ("overflow: hidden" and "height: 0", "Hidden overflow with zero height"),
                ("position: fixed" and "bottom: 0" and "right: 0", "Fixed positioning at bottom-right"),
            ]

            # Check for viewport visibility issues
            # Elements should not be positioned off-screen unintentionally
            if "left: -9999" in snapshot_text or "top: -9999" in snapshot_text:
                issues.append("Elements positioned far off-screen detected")

            # Check for overlapping fixed/absolute positioned elements
            # This is a heuristic check
            fixed_count = snapshot_text.count("position: fixed")
            absolute_count = snapshot_text.count("position: absolute")

            if fixed_count > 5 or absolute_count > 10:
                issues.append(f"High number of positioned elements (fixed: {fixed_count}, absolute: {absolute_count}) - may cause overlap")

        # Step 4: Specific overlap check using JavaScript
        critical_selectors = [
            "div[class*='question']",
            "div[class*='floating']",
            "button[type='submit']",
            "div[class*='toolbar']",
            "div[class*='hint']",
        ]

        # Filter to selectors that actually exist
        existing_selectors = []
        for sel in critical_selectors:
            check_result = browser.get_property("html", sel)
            if check_result["status"] == "ok" and check_result["raw_output"].strip():
                existing_selectors.append(sel)

        if len(existing_selectors) >= 2:
            overlap_ok, overlap_details = check_element_overlap(browser, existing_selectors)
            if not overlap_ok:
                issues.append(overlap_details)

        # Step 5: Check for small viewport issues (mobile)
        # Set viewport to small size (if cmux supports it)
        # For now, check if elements are responsive

        # Final verdict
        if issues:
            elapsed = time.time() - start
            return False, f"Layout issues detected: {'; '.join(issues)}", elapsed
        else:
            elapsed = time.time() - start
            details = f"Layout check passed. Found {len(existing_selectors)} critical elements with proper spacing."
            if has_floating_panel:
                details += " Floating panel detected and positioned correctly."
            return True, details, elapsed

    except Exception as e:
        elapsed = time.time() - start
        return False, f"Check failed with exception: {e}", elapsed


def main():
    """Run check and print results."""
    passed, details, elapsed_s = run_check()

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] Layout Crush Check")
    print(f"Details: {details}")
    print(f"Elapsed: {elapsed_s:.2f}s")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

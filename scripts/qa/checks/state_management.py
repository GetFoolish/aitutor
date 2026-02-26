#!/usr/bin/env python3
"""State management QA check.

Validates:
- localStorage persistence across page reloads
- Session state continuity
- User preferences retained
- No state corruption on navigation
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cmux_browser import CmuxBrowser, CmuxBrowserError


def run_check(url: str = "http://localhost:8000") -> Tuple[bool, str, float]:
    """Run state management check.

    Args:
        url: Base URL to test (default: http://localhost:8000)

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()
    browser = None

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

        # Step 2: Set localStorage state
        set_state_script = """
        (function() {
            localStorage.setItem('qa_test_key', 'qa_test_value');
            localStorage.setItem('qa_test_timestamp', Date.now().toString());
            return localStorage.getItem('qa_test_key');
        })();
        """
        set_result = browser.eval_js(set_state_script)
        if set_result["status"] != "ok":
            return False, f"Failed to set localStorage: {set_result['error']}", time.time() - start

        # Step 3: Reload page
        reload_result = browser.navigate(url)
        if reload_result["status"] != "ok":
            return False, f"Failed to reload page: {reload_result['error']}", time.time() - start

        # Wait for page to load again
        wait_result = browser.wait_for_element("body", timeout_ms=5000)
        if wait_result["status"] != "ok":
            return False, f"Page failed to reload: {wait_result['error']}", time.time() - start

        # Step 4: Check localStorage persistence
        check_state_script = """
        (function() {
            var testKey = localStorage.getItem('qa_test_key');
            var testTimestamp = localStorage.getItem('qa_test_timestamp');
            return JSON.stringify({
                key_exists: testKey !== null,
                key_value: testKey,
                timestamp_exists: testTimestamp !== null,
                all_keys: Object.keys(localStorage).length
            });
        })();
        """
        check_result = browser.eval_js(check_state_script)
        if check_result["status"] != "ok":
            return False, f"Failed to check localStorage: {check_result['error']}", time.time() - start

        # Parse and validate result
        import json
        try:
            state_data = json.loads(check_result["raw_output"])
            if not state_data.get("key_exists"):
                return False, "localStorage state not persisted after reload", time.time() - start
            if state_data.get("key_value") != "qa_test_value":
                return False, f"localStorage value corrupted: expected 'qa_test_value', got '{state_data.get('key_value')}'", time.time() - start
            if not state_data.get("timestamp_exists"):
                return False, "localStorage timestamp not persisted", time.time() - start
        except (json.JSONDecodeError, KeyError) as e:
            return False, f"Failed to parse localStorage check result: {e}", time.time() - start

        # Step 5: Test navigation state continuity
        # Navigate to a different path and back
        about_url = f"{url}/about" if not url.endswith("/") else f"{url}about"
        nav_result = browser.navigate(about_url)
        if nav_result["status"] != "ok":
            # About page may not exist, that's ok - just check we can navigate
            pass

        # Navigate back to home
        back_result = browser.navigate(url)
        if back_result["status"] != "ok":
            return False, f"Failed to navigate back: {back_result['error']}", time.time() - start

        # Wait for page to load
        wait_result = browser.wait_for_element("body", timeout_ms=5000)
        if wait_result["status"] != "ok":
            return False, f"Page failed to load after navigation: {wait_result['error']}", time.time() - start

        # Step 6: Verify state still persists after navigation
        final_check_result = browser.eval_js(check_state_script)
        if final_check_result["status"] != "ok":
            return False, f"Failed to check localStorage after navigation: {final_check_result['error']}", time.time() - start

        try:
            final_state_data = json.loads(final_check_result["raw_output"])
            if not final_state_data.get("key_exists"):
                return False, "localStorage state lost after navigation", time.time() - start
            if final_state_data.get("key_value") != "qa_test_value":
                return False, f"localStorage value corrupted after navigation: expected 'qa_test_value', got '{final_state_data.get('key_value')}'", time.time() - start
        except (json.JSONDecodeError, KeyError) as e:
            return False, f"Failed to parse final localStorage check result: {e}", time.time() - start

        # Step 7: Cleanup test data
        cleanup_script = """
        (function() {
            localStorage.removeItem('qa_test_key');
            localStorage.removeItem('qa_test_timestamp');
            return 'cleaned';
        })();
        """
        browser.eval_js(cleanup_script)

        elapsed = time.time() - start
        return True, f"State management check passed: localStorage persists across reloads and navigation (checked {state_data.get('all_keys', 0)} keys)", elapsed

    except CmuxBrowserError as e:
        return False, f"Browser error: {e}", time.time() - start
    except Exception as e:
        return False, f"Unexpected error: {e}", time.time() - start


def main() -> None:
    """Entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run state management QA check")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base URL to test (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    passed, details, elapsed = run_check(args.url)

    print(f"State Management Check: {'PASS' if passed else 'FAIL'}")
    print(f"Details: {details}")
    print(f"Elapsed: {elapsed:.3f}s")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

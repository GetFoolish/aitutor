#!/usr/bin/env python3
"""cmux browser automation wrapper for QA checks.

Provides Python interface to cmux browser CLI commands with structured error handling.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CmuxBrowserError(Exception):
    """Raised when cmux browser command fails."""
    pass


class CmuxBrowser:
    """Wrapper for cmux browser CLI automation."""

    def __init__(self, surface_id: Optional[str] = None):
        """Initialize browser wrapper.

        Args:
            surface_id: Optional surface identifier (e.g., 'surface:1')
        """
        self.surface_id = surface_id
        self._check_cmux_available()

    def _check_cmux_available(self) -> None:
        """Verify cmux browser is installed and accessible."""
        try:
            result = subprocess.run(
                ["cmux", "browser", "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise CmuxBrowserError("cmux browser not available")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise CmuxBrowserError(f"cmux browser not available: {e}")

    def _run_command(
        self,
        args: List[str],
        timeout: float = 30,
        parse_json: bool = False,
    ) -> Dict[str, Any]:
        """Execute cmux browser command.

        Args:
            args: Command arguments (excluding 'cmux browser')
            timeout: Command timeout in seconds
            parse_json: Whether to parse stdout as JSON

        Returns:
            Dict with status, output, error, elapsed_s
        """
        cmd = ["cmux", "browser"]
        if self.surface_id:
            cmd.extend(["--surface", self.surface_id])
        cmd.extend(args)

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed = time.time() - start

            output = result.stdout.strip()
            error = result.stderr.strip()

            # Try to parse JSON output if requested
            parsed_output = None
            if parse_json and output:
                try:
                    parsed_output = json.loads(output)
                except json.JSONDecodeError:
                    pass

            return {
                "status": "ok" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "output": parsed_output if parsed_output is not None else output,
                "raw_output": output,
                "error": error,
                "elapsed_s": elapsed,
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            return {
                "status": "timeout",
                "returncode": -1,
                "output": None,
                "raw_output": "",
                "error": f"Command timed out after {timeout}s",
                "elapsed_s": elapsed,
                "command": " ".join(cmd),
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "status": "error",
                "returncode": -1,
                "output": None,
                "raw_output": "",
                "error": str(e),
                "elapsed_s": elapsed,
                "command": " ".join(cmd),
            }

    def open(self, url: str, split: bool = False) -> Dict[str, Any]:
        """Open browser to URL.

        Args:
            url: URL to navigate to
            split: Whether to open in new split

        Returns:
            Command result dict
        """
        cmd = ["open-split" if split else "open", url]
        result = self._run_command(cmd)

        # Extract surface ID from output if we just created a browser
        if result["status"] == "ok" and not self.surface_id:
            # Output format: "OK surface=surface:N pane=pane:M placement=..."
            output = result["raw_output"]
            if "surface=" in output:
                # Extract surface:N from "surface=surface:N"
                for part in output.split():
                    if part.startswith("surface="):
                        self.surface_id = part.split("=", 1)[1]
                        break
            elif output.startswith("surface:"):
                # Fallback: direct surface:N format
                self.surface_id = output.split()[0]

        return result

    def navigate(self, url: str, snapshot_after: bool = False) -> Dict[str, Any]:
        """Navigate to URL.

        Args:
            url: URL to navigate to
            snapshot_after: Whether to capture snapshot after navigation

        Returns:
            Command result dict
        """
        cmd = ["navigate", url]
        if snapshot_after:
            cmd.append("--snapshot-after")
        return self._run_command(cmd)

    def wait_for_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        url_contains: Optional[str] = None,
        timeout_ms: int = 5000,
    ) -> Dict[str, Any]:
        """Wait for element or condition.

        Args:
            selector: CSS selector to wait for
            text: Text content to wait for
            url_contains: URL substring to wait for
            timeout_ms: Timeout in milliseconds

        Returns:
            Command result dict
        """
        cmd = ["wait", "--timeout-ms", str(timeout_ms)]
        if selector:
            cmd.extend(["--selector", selector])
        if text:
            cmd.extend(["--text", text])
        if url_contains:
            cmd.extend(["--url-contains", url_contains])
        return self._run_command(cmd, timeout=timeout_ms / 1000 + 5)

    def click(self, selector: str, snapshot_after: bool = False) -> Dict[str, Any]:
        """Click element.

        Args:
            selector: CSS selector to click
            snapshot_after: Whether to capture snapshot after click

        Returns:
            Command result dict
        """
        cmd = ["click", selector]
        if snapshot_after:
            cmd.append("--snapshot-after")
        return self._run_command(cmd)

    def fill(self, selector: str, text: str, snapshot_after: bool = False) -> Dict[str, Any]:
        """Fill input element.

        Args:
            selector: CSS selector of input
            text: Text to fill
            snapshot_after: Whether to capture snapshot after fill

        Returns:
            Command result dict
        """
        cmd = ["fill", selector, text]
        if snapshot_after:
            cmd.append("--snapshot-after")
        return self._run_command(cmd)

    def type_text(self, selector: str, text: str, snapshot_after: bool = False) -> Dict[str, Any]:
        """Type text into element.

        Args:
            selector: CSS selector to type into
            text: Text to type
            snapshot_after: Whether to capture snapshot after typing

        Returns:
            Command result dict
        """
        cmd = ["type", selector, text]
        if snapshot_after:
            cmd.append("--snapshot-after")
        return self._run_command(cmd)

    def snapshot(
        self,
        selector: Optional[str] = None,
        interactive: bool = False,
        compact: bool = False,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get DOM snapshot.

        Args:
            selector: CSS selector to snapshot (default: entire page)
            interactive: Include interactive elements
            compact: Compact output
            max_depth: Maximum tree depth

        Returns:
            Command result dict with parsed snapshot
        """
        cmd = ["snapshot"]
        if selector:
            cmd.extend(["--selector", selector])
        if interactive:
            cmd.append("--interactive")
        if compact:
            cmd.append("--compact")
        if max_depth is not None:
            cmd.extend(["--max-depth", str(max_depth)])

        # Snapshot output is typically plain text, not JSON
        return self._run_command(cmd, parse_json=False)

    def eval_js(self, script: str) -> Dict[str, Any]:
        """Evaluate JavaScript in browser.

        Args:
            script: JavaScript code to execute

        Returns:
            Command result dict
        """
        return self._run_command(["eval", script])

    def get_property(
        self,
        property_name: str,
        selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get page or element property.

        Args:
            property_name: Property to get (url, title, text, html, value, etc.)
            selector: Optional CSS selector for element properties

        Returns:
            Command result dict
        """
        cmd = ["get", property_name]
        if selector:
            cmd.append(selector)
        return self._run_command(cmd)

    def get_url(self) -> str:
        """Get current URL.

        Returns:
            Current page URL
        """
        result = self._run_command(["get-url"])
        if result["status"] == "ok":
            return result["raw_output"]
        return ""

    def screenshot(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Capture screenshot.

        Note: cmux browser screenshot functionality depends on version.
        This method uses eval to trigger screenshot via JS if direct command unavailable.

        Args:
            output_path: Path to save screenshot (if None, returns data)

        Returns:
            Command result dict
        """
        # Try direct screenshot command first
        # If not available, would need to use alternative method
        # For now, document that screenshot should be handled at check level
        return {
            "status": "error",
            "error": "Screenshot support requires implementation at check level",
            "output": None,
            "raw_output": "",
            "elapsed_s": 0.0,
            "command": "screenshot (not implemented)",
        }


def create_browser(url: Optional[str] = None) -> CmuxBrowser:
    """Create and optionally open a browser instance.

    Args:
        url: Optional URL to navigate to immediately

    Returns:
        CmuxBrowser instance
    """
    browser = CmuxBrowser()
    if url:
        browser.open(url)
    return browser


def quick_check(
    url: str,
    selector: str,
    wait_timeout_ms: int = 5000,
) -> Tuple[bool, str, float]:
    """Quick helper for checking if element exists at URL.

    Args:
        url: URL to navigate to
        selector: CSS selector to check for
        wait_timeout_ms: Wait timeout in milliseconds

    Returns:
        Tuple of (success, details, elapsed_s)
    """
    start = time.time()
    try:
        browser = create_browser(url)
        result = browser.wait_for_element(selector, timeout_ms=wait_timeout_ms)
        elapsed = time.time() - start

        if result["status"] == "ok":
            return True, f"Element {selector} found", elapsed
        else:
            return False, f"Element {selector} not found: {result['error']}", elapsed

    except Exception as e:
        elapsed = time.time() - start
        return False, f"Browser check failed: {e}", elapsed

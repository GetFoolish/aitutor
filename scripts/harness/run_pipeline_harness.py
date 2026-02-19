#!/usr/bin/env python3
"""Run the full content pipeline harness.

This script orchestrates all gates, writes artifacts, and generates a PR packet.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Gate:
    name: str
    command: List[str]
    timeout_s: int
    required: bool = True
    env: Optional[Dict[str, str]] = None
    skip_when_env: Optional[str] = None


REQUIRED_SCREENSHOT_FILES = [
    "01-assessment-main.png",
    "02-assessment-no-scroll-controls-visible.png",
    "03-assessment-floating-panel-visible.png",
    "04-assessment-zindex-pass.png",
    "05-assessment-hint-legibility-light.png",
    "06-assessment-hint-legibility-dark.png",
    "07-learning-main.png",
    "08-learning-no-scroll-controls-visible.png",
    "09-learning-floating-panel-visible.png",
    "10-learning-dots-mask-sidebar-panel.png",
    "11-widget-inline-dropdown-layout.png",
    "12-widget-image-question-layout.png",
    "13-assessment-complete-screen.png",
    "14-latency-overlay-or-metrics-visual.png",
]


def _is_truthy(raw: Optional[str]) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _active_skip_env() -> List[str]:
    active: List[str] = []
    for name, value in os.environ.items():
        if name.startswith("HARNESS_SKIP_") and _is_truthy(value):
            active.append(name)
    return sorted(active)


def _p95(values: List[float]) -> Optional[float]:
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return None
    vals.sort()
    idx = max(0, math.ceil(0.95 * len(vals)) - 1)
    return vals[idx]


def _derive_metrics(output_dir: Path) -> Dict:
    smoke_path = output_dir / "smoke.json"
    checks = {}
    if smoke_path.exists():
        try:
            smoke_payload = json.loads(smoke_path.read_text(encoding="utf-8"))
            checks = (smoke_payload.get("checks") or {})
        except Exception:
            checks = {}

    loading = checks.get("loading_latency") or {}
    adaptive = checks.get("adaptive_start_all_subjects") or {}
    adaptive_payload = adaptive.get("payload") or {}
    adaptive_rows = adaptive_payload.get("start_results") or []
    start_latencies = [
        float(r.get("elapsed_s"))
        for r in adaptive_rows
        if isinstance(r, dict) and isinstance(r.get("elapsed_s"), (int, float))
    ]
    if isinstance(loading.get("initial_question_fetch_elapsed_s"), (int, float)):
        start_latencies.append(float(loading.get("initial_question_fetch_elapsed_s")))

    next_latencies = loading.get("adaptive_next_transition_elapsed_s") or []
    next_latencies = [float(v) for v in next_latencies if isinstance(v, (int, float))]
    if isinstance(loading.get("next_question_elapsed_s"), (int, float)):
        next_latencies.append(float(loading.get("next_question_elapsed_s")))

    screenshots_dir = output_dir / "screenshots"
    present = {p.name for p in screenshots_dir.glob("*.png")} if screenshots_dir.exists() else set()
    missing_required = [name for name in REQUIRED_SCREENSHOT_FILES if name not in present]

    floating_assessment_pass = all(
        name in present
        for name in ("03-assessment-floating-panel-visible.png", "04-assessment-zindex-pass.png")
    )
    floating_learning_pass = "09-learning-floating-panel-visible.png" in present
    dot_mask_pass = "10-learning-dots-mask-sidebar-panel.png" in present

    return {
        "required_screenshots_present": len(missing_required) == 0,
        "missing_required_screenshots": missing_required,
        "initial_p95_ms": (
            round(_p95(start_latencies) * 1000, 2)
            if _p95(start_latencies) is not None
            else None
        ),
        "next_p95_ms": (
            round(_p95(next_latencies) * 1000, 2)
            if _p95(next_latencies) is not None
            else None
        ),
        "floating_panel_assessment_pass": floating_assessment_pass,
        "floating_panel_learning_pass": floating_learning_pass,
        "dot_mask_pass": dot_mask_pass,
    }


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _run_gate(gate: Gate, output_dir: Path) -> Dict:
    if gate.skip_when_env and os.environ.get(gate.skip_when_env, "").lower() in {"1", "true", "yes"}:
        return {
            "name": gate.name,
            "ok": True,
            "required": gate.required,
            "skipped": True,
            "skip_reason": f"{gate.skip_when_env}=true",
            "command": " ".join(shlex.quote(x) for x in gate.command),
        }

    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = logs_dir / f"{gate.name}.stdout.log"
    stderr_path = logs_dir / f"{gate.name}.stderr.log"

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    if gate.env:
        env.update(gate.env)

    started = time.time()
    with stdout_path.open("w", encoding="utf-8") as out_f, stderr_path.open("w", encoding="utf-8") as err_f:
        try:
            proc = subprocess.run(
                gate.command,
                cwd=str(ROOT),
                env=env,
                stdout=out_f,
                stderr=err_f,
                timeout=gate.timeout_s,
                check=False,
            )
            rc = int(proc.returncode)
            timed_out = False
        except subprocess.TimeoutExpired:
            rc = 124
            timed_out = True

    elapsed = time.time() - started
    ok = rc == 0

    return {
        "name": gate.name,
        "ok": ok,
        "required": gate.required,
        "skipped": False,
        "timed_out": timed_out,
        "returncode": rc,
        "elapsed_s": round(elapsed, 2),
        "command": " ".join(shlex.quote(x) for x in gate.command),
        "stdout": str(stdout_path.relative_to(ROOT)),
        "stderr": str(stderr_path.relative_to(ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run content pipeline harness")
    parser.add_argument(
        "--mode",
        choices=["local", "ci"],
        default="local",
        help="Harness mode (controls defaults like greptile requirement)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "harness" / f"run-{_now_stamp()}",
        help="Directory for harness artifacts",
    )
    parser.add_argument(
        "--require-greptile",
        action="store_true",
        help="Force Greptile gate to be required",
    )
    return parser.parse_args()


def _env_bool(name: str) -> Optional[bool]:
    raw = os.environ.get(name)
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return None


def _resolve_python_bin() -> str:
    configured = os.environ.get("HARNESS_PYTHON_BIN")
    if configured:
        return configured

    candidates = [
        ROOT / "venv" / "bin" / "python3",
        ROOT / "venv" / "bin" / "python",
        ROOT / ".venv" / "bin" / "python3",
        ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "python3"


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    python_bin = _resolve_python_bin()

    env_require_greptile = _env_bool("HARNESS_REQUIRE_GREPTILE")
    strict_no_skip = True

    if args.require_greptile:
        require_greptile = True
    elif env_require_greptile is not None:
        require_greptile = env_require_greptile
    else:
        require_greptile = args.mode == "ci"

    if strict_no_skip:
        require_greptile = True

    active_skip_env = _active_skip_env()
    if strict_no_skip and active_skip_env:
        summary = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": args.mode,
            "require_greptile": require_greptile,
            "strict_no_skip": True,
            "ok": False,
            "duration_s": 0.0,
            "output_dir": str(output_dir.resolve()),
            "gates": [],
            "error": "strict_no_skip_violation",
            "active_skip_env": active_skip_env,
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(summary_path)
        print(json.dumps({"ok": False, "reason": "skip env vars are not allowed in strict mode"}, indent=2))
        raise SystemExit(1)

    gates = [
        Gate(
            name="secret_scan",
            command=[
                "bash",
                "scripts/harness/secret_scan.sh",
                str((output_dir / "secret_scan.json").relative_to(ROOT)),
            ],
            timeout_s=180,
            required=True,
            skip_when_env="HARNESS_SKIP_SECRET_SCAN",
        ),
        Gate(
            name="smoke",
            command=[
                python_bin,
                "scripts/harness/smoke_test.py",
                "--output",
                str((output_dir / "smoke.json").relative_to(ROOT)),
            ],
            timeout_s=420,
            required=True,
        ),
        Gate(
            name="pretest_checklist",
            command=[python_bin, "scripts/pretest_checklist.py"],
            timeout_s=1800,
            required=True,
            env={
                "PRETEST_INCLUDE_CONTENT_V1": "false",
            },
            skip_when_env="HARNESS_SKIP_PRETEST",
        ),
        Gate(
            name="content_v1_battletest",
            command=[python_bin, "scripts/content_v1_battletest.py"],
            timeout_s=1800,
            required=True,
            env={
                "CONTENT_V1_USE_DEV_LOGIN": os.environ.get("CONTENT_V1_USE_DEV_LOGIN", "true"),
            },
            skip_when_env="HARNESS_SKIP_CONTENT_V1",
        ),
        Gate(
            name="playwright",
            command=[
                "bash",
                "scripts/harness/run_playwright_capture.sh",
                str((output_dir / "screenshots").relative_to(ROOT)),
            ],
            timeout_s=1800,
            required=True,
            env={
                "HARNESS_SCREENSHOT_DIR": str((output_dir / "screenshots").resolve()),
                "PLAYWRIGHT_JSON_REPORT": str((output_dir / "playwright-report.json").resolve()),
            },
            skip_when_env="HARNESS_SKIP_PLAYWRIGHT",
        ),
        Gate(
            name="greptile",
            command=[
                "bash",
                "scripts/harness/greptile_gate.sh",
                str((output_dir / "greptile.json").relative_to(ROOT)),
            ],
            timeout_s=900,
            required=require_greptile,
            env={
                "HARNESS_REQUIRE_GREPTILE": "1" if require_greptile else "0",
            },
            skip_when_env="HARNESS_SKIP_GREPTILE",
        ),
    ]

    started = time.time()
    gate_results = []
    for gate in gates:
        print(f"[HARNESS] Running gate: {gate.name}")
        gate_result = _run_gate(gate, output_dir)

        # Normalize gate status from artifact payloads when the gate script
        # returns 0 but reports an internal skip (e.g., optional greptile).
        if gate.name == "greptile":
            greptile_path = output_dir / "greptile.json"
            if greptile_path.exists():
                try:
                    greptile_payload = json.loads(greptile_path.read_text(encoding="utf-8"))
                    gate_result["artifact"] = str(greptile_path.relative_to(ROOT))
                    if bool(greptile_payload.get("skipped")):
                        gate_result["skipped"] = True
                        gate_result["ok"] = False
                        gate_result["skip_reason"] = greptile_payload.get("reason") or "greptile skipped"
                    elif "ok" in greptile_payload:
                        gate_result["ok"] = bool(greptile_payload.get("ok"))
                except Exception:
                    gate_result["artifact_parse_error"] = str(greptile_path.relative_to(ROOT))

        gate_results.append(gate_result)
        status = "PASS" if gate_result.get("ok") else "FAIL"
        if gate_result.get("skipped"):
            status = "SKIP"
        print(f"[HARNESS] {gate.name}: {status}")

    has_required_skip = any(g.get("required", True) and g.get("skipped") for g in gate_results)
    ok = all(g.get("ok") for g in gate_results if g.get("required", True)) and not has_required_skip

    derived_metrics = _derive_metrics(output_dir)
    if strict_no_skip and not derived_metrics.get("required_screenshots_present", False):
        ok = False

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "require_greptile": require_greptile,
        "strict_no_skip": strict_no_skip,
        "ok": ok,
        "duration_s": round(time.time() - started, 2),
        "output_dir": str(output_dir.resolve()),
        "gates": gate_results,
        **derived_metrics,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    pr_packet_cmd = [
        python_bin,
        "scripts/harness/generate_pr_packet.py",
        "--summary",
        str(summary_path.relative_to(ROOT)),
        "--output",
        str((output_dir / "PR_PACKET.md").relative_to(ROOT)),
        "--screenshots-dir",
        str((output_dir / "screenshots").relative_to(ROOT)),
    ]

    print("[HARNESS] Generating PR packet")
    pr_packet_rc = subprocess.run(pr_packet_cmd, cwd=str(ROOT), env=os.environ.copy(), check=False).returncode
    if pr_packet_rc != 0:
        ok = False
        summary["ok"] = False
        summary["pr_packet_error"] = f"generate_pr_packet.py exited {pr_packet_rc}"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(summary_path)
    print(json.dumps({"ok": summary["ok"], "mode": args.mode}, indent=2))
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()

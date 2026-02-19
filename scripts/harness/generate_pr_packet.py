#!/usr/bin/env python3
"""Generate a PR-ready markdown packet from harness artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def _gate_row(gate: Dict) -> str:
    if gate.get("skipped"):
        status = "SKIPPED"
    else:
        status = "PASS" if gate.get("ok") else "FAIL"
    required = "yes" if gate.get("required", True) else "no"
    elapsed = gate.get("elapsed_s", "-")
    return f"| {gate.get('name')} | {status} | {required} | {elapsed} |"


def _criterion_line(title: str, passed: bool) -> str:
    return f"- [{'x' if passed else ' '}] {title}"


def _gate_effective_ok(gate_map: Dict[str, Dict], name: str) -> bool:
    gate = gate_map.get(name, {})
    return bool(gate.get("ok")) and not bool(gate.get("skipped"))


def build_packet(summary: Dict, screenshots_dir: Path) -> str:
    gates = summary.get("gates", [])
    gate_map = {g.get("name"): g for g in gates}

    secret_scan_ok = _gate_effective_ok(gate_map, "secret_scan")
    smoke_ok = _gate_effective_ok(gate_map, "smoke")
    pretest_ok = _gate_effective_ok(gate_map, "pretest_checklist")
    c1_ok = _gate_effective_ok(gate_map, "content_v1_battletest")
    pw_ok = _gate_effective_ok(gate_map, "playwright")
    greptile_ok = _gate_effective_ok(gate_map, "greptile")

    smoke_payload: Dict = {}
    output_dir = summary.get("output_dir")
    if output_dir:
        smoke_path = Path(output_dir) / "smoke.json"
        try:
            smoke_payload = json.loads(smoke_path.read_text(encoding="utf-8"))
        except Exception:
            smoke_payload = {}
        greptile_path = Path(output_dir) / "greptile.json"
        if greptile_path.exists():
            try:
                greptile_payload = json.loads(greptile_path.read_text(encoding="utf-8"))
                if bool(greptile_payload.get("skipped")):
                    greptile_ok = False
                elif "ok" in greptile_payload:
                    greptile_ok = bool(greptile_payload.get("ok"))
            except Exception:
                greptile_ok = False
    websocket_check = (smoke_payload.get("checks") or {}).get("websocket", {})
    websocket_ok = bool(websocket_check.get("ok")) and not bool(websocket_check.get("skipped"))
    adaptive_all_subjects_check = (smoke_payload.get("checks") or {}).get("adaptive_start_all_subjects", {})
    adaptive_all_subjects_ok = bool(adaptive_all_subjects_check.get("ok")) and not bool(adaptive_all_subjects_check.get("skipped"))
    learning_path_scope_check = (smoke_payload.get("checks") or {}).get("learning_path_subject_validity", {})
    learning_path_scope_ok = bool(learning_path_scope_check.get("ok")) and not bool(learning_path_scope_check.get("skipped"))
    loading_latency_check = (smoke_payload.get("checks") or {}).get("loading_latency", {})
    loading_latency_ok = bool(loading_latency_check.get("ok")) and not bool(loading_latency_check.get("skipped"))
    question_fetch_check = (smoke_payload.get("checks") or {}).get("question_fetch", {})
    question_fetch_ok = bool(question_fetch_check.get("ok"))
    dash_service_ok = bool(((smoke_payload.get("services") or {}).get("dash") or {}).get("ok"))
    dash_dev_login_ok = bool(((smoke_payload.get("checks") or {}).get("dev_login") or {}).get("ok"))
    dash_question_flow_ok = bool(((smoke_payload.get("checks") or {}).get("question_fetch") or {}).get("ok"))
    dash_end_to_end_ok = smoke_ok and dash_service_ok and dash_dev_login_ok and dash_question_flow_ok

    shot_paths: List[Path] = []
    if screenshots_dir.exists():
        shot_paths = sorted(p for p in screenshots_dir.glob("*.png"))
    present_screens = {p.name for p in shot_paths}
    missing_required_screens = [name for name in REQUIRED_SCREENSHOT_FILES if name not in present_screens]
    strict_no_skip = bool(summary.get("strict_no_skip", True))
    required_screenshots_present = bool(summary.get("required_screenshots_present", len(missing_required_screens) == 0))
    if not required_screenshots_present and summary.get("missing_required_screenshots"):
        missing_required_screens = list(summary.get("missing_required_screenshots") or missing_required_screens)
    initial_p95_ms = summary.get("initial_p95_ms")
    next_p95_ms = summary.get("next_p95_ms")
    next_latency_budget_ok = isinstance(next_p95_ms, (int, float)) and float(next_p95_ms) <= 2500.0
    floating_panel_assessment_pass = bool(summary.get("floating_panel_assessment_pass", False))
    floating_panel_learning_pass = bool(summary.get("floating_panel_learning_pass", False))
    dot_mask_pass = bool(summary.get("dot_mask_pass", False))
    no_skipped_required = all(
        not (bool(g.get("required", True)) and bool(g.get("skipped")))
        for g in gates
    )

    lines: List[str] = []
    lines.append("# PR: Content Pipeline Harness Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Harness overall status: {'PASS' if summary.get('ok') else 'FAIL'}")
    lines.append("")
    lines.append("## Gate Results")
    lines.append("")
    lines.append("| Gate | Status | Required | Duration (s) |")
    lines.append("| --- | --- | --- | --- |")
    for gate in gates:
        lines.append(_gate_row(gate))
    lines.append("")

    lines.append("## Acceptance Criteria")
    lines.append("")
    lines.append(_criterion_line("No duplicate questions by ID/content fingerprint", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Subject correctness (assessment + learning, no cross-subject contamination)", smoke_ok and pretest_ok and learning_path_scope_ok))
    lines.append(_criterion_line("Assessment does not stop after 1-2 questions and reaches completion", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Questions have answer area and renderable widget config", smoke_ok and pretest_ok and pw_ok and question_fetch_ok))
    lines.append(_criterion_line("Grading/skill-path metadata integrity checks passed", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Websocket ping/pong smoke check passed", websocket_ok))
    lines.append(_criterion_line("No page scroll on assessment + learning desktop baseline", pw_ok))
    lines.append(_criterion_line("Floating panel present/usable in assessment", floating_panel_assessment_pass and pw_ok))
    lines.append(_criterion_line("Floating panel present/usable in learning", floating_panel_learning_pass and pw_ok))
    lines.append(_criterion_line("Dot-mask isolation for sidebar cards + floating panel", dot_mask_pass and pw_ok))
    lines.append(_criterion_line("Hint legibility passes in light and dark modes", pw_ok))
    lines.append(_criterion_line("Hydration/render content match passed", pw_ok))
    lines.append(_criterion_line("No leaked secrets/API keys in changed files", secret_scan_ok))
    lines.append(_criterion_line("Greptile review gate passed", greptile_ok))
    lines.append(_criterion_line("Strict no-skip policy enforced", strict_no_skip and no_skipped_required))
    lines.append(_criterion_line("Required screenshot manifest is complete", required_screenshots_present))
    lines.append(_criterion_line("Latency budget hard gate (next-question P95 <= 2.5s, hard timeout <= 6s with retry UI)", loading_latency_ok and next_latency_budget_ok))
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- `initial_p95_ms`: {initial_p95_ms if initial_p95_ms is not None else 'n/a'}")
    lines.append(f"- `next_p95_ms`: {next_p95_ms if next_p95_ms is not None else 'n/a'}")
    lines.append(f"- `strict_no_skip`: {strict_no_skip}")
    lines.append(f"- `required_screenshots_present`: {required_screenshots_present}")
    lines.append(f"- `floating_panel_assessment_pass`: {floating_panel_assessment_pass}")
    lines.append(f"- `floating_panel_learning_pass`: {floating_panel_learning_pass}")
    lines.append(f"- `dot_mask_pass`: {dot_mask_pass}")
    lines.append("")

    lines.append("## QA Evidence")
    lines.append("")
    if shot_paths:
        for shot in shot_paths:
            lines.append(f"- `{_rel(shot)}`")
    else:
        lines.append("- No screenshots found")
    if missing_required_screens:
        lines.append("")
        lines.append("### Missing Required Screenshots")
        for name in missing_required_screens:
            lines.append(f"- `{name}`")
    lines.append("")

    lines.append("## Merge Policy")
    lines.append("")
    lines.append("1. All required harness gates must pass on the PR head SHA.")
    lines.append("2. No required gate may be skipped.")
    lines.append("3. This report must be attached to the PR description or comment.")
    lines.append("4. Smoke and Playwright evidence must be from the same run.")
    lines.append("5. Greptile override requires explicit reviewer approval note.")
    lines.append("")

    lines.append("## Reviewer Checklist")
    lines.append("")
    lines.append("- [ ] Verified gate table and artifacts")
    lines.append("- [ ] Reviewed screenshots for widget/floating-panel correctness")
    lines.append("- [ ] Confirmed no skipped required gates")
    lines.append("- [ ] Confirmed acceptance criteria checkboxes")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PR packet from harness outputs")
    parser.add_argument("--summary", type=Path, required=True, help="Path to harness summary.json")
    parser.add_argument("--output", type=Path, required=True, help="Output markdown path")
    parser.add_argument("--screenshots-dir", type=Path, required=True, help="Directory containing screenshots")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    summary_path = args.summary if args.summary.is_absolute() else (ROOT / args.summary)
    output_path = args.output if args.output.is_absolute() else (ROOT / args.output)
    screenshots_dir = args.screenshots_dir if args.screenshots_dir.is_absolute() else (ROOT / args.screenshots_dir)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    missing_required = []
    if screenshots_dir.exists():
        present = {p.name for p in screenshots_dir.glob("*.png")}
        missing_required = [name for name in REQUIRED_SCREENSHOT_FILES if name not in present]
    else:
        missing_required = REQUIRED_SCREENSHOT_FILES.copy()

    if missing_required:
        raise SystemExit(
            "Required screenshot manifest missing entries: "
            + ", ".join(missing_required)
        )

    packet = build_packet(summary, screenshots_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packet, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()

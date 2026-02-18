#!/usr/bin/env python3
"""Generate a PR-ready markdown packet from harness artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]


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
    lines.append(_criterion_line("Subject correctness (no cross-subject contamination)", smoke_ok and pretest_ok and c1_ok))
    lines.append(_criterion_line("Assessment does not stop after 1-2 questions", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Adaptive assessment remains stable through at least 8 consecutive next-question transitions (no break around Q4/Q5)", pretest_ok))
    lines.append(_criterion_line("Questions have answer area and renderable widget config", smoke_ok and pretest_ok and pw_ok))
    # Keep latency criteria tied to the dedicated latency check, not whole-smoke status.
    lines.append(_criterion_line("Next-question latency within budget", loading_latency_ok))
    lines.append(_criterion_line("Grading/skill-path metadata integrity checks passed", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Grading correctness parity holds for rendered options (radio selectedChoiceIds map correctly to answer key)", pretest_ok))
    lines.append(_criterion_line("No leaked quoted choice text or duplicate 'Choose 1 answer' prompt labels in served/rendered content", smoke_ok and question_fetch_ok and pw_ok))
    lines.append(_criterion_line("DASH system works end-to-end (health + auth + subject start + question fetch)", dash_end_to_end_ok))
    lines.append(_criterion_line("Adaptive assessment start works across all available subjects (no terminal 400/invalid payload)", smoke_ok and adaptive_all_subjects_ok))
    lines.append(_criterion_line("Learning mode path stays subject-correct and content-valid (recommend-next has no cross-subject contamination)", smoke_ok and learning_path_scope_ok))
    lines.append(_criterion_line("Question loading times are optimized for max speed (initial load + learning recommend-next + adaptive start + repeated next-question transitions within budget)", loading_latency_ok))
    lines.append(_criterion_line("Websocket ping/pong smoke check passed", websocket_ok))
    lines.append(_criterion_line("Frontend UI/UX stability checks passed (widget + floating panel visible and usable)", pw_ok and len(shot_paths) >= 3))
    lines.append(_criterion_line("Primary assessment actions are visible/reachable without manual scrolling", pw_ok))
    lines.append(_criterion_line("Assessment question view has zero browser-level vertical scroll while keeping question, hints, and actions usable", pw_ok))
    lines.append(_criterion_line("Assessment question view has zero internal question-container scroll while keeping question/options/hints/actions usable", pw_ok))
    lines.append(_criterion_line("Assessment question container overflow contract holds (`#question-content-container` does not compute to overflow-y:auto)", pw_ok))
    lines.append(_criterion_line("Visual-heavy prompts stay viewport-fit and do not push Submit/Next below fold", pw_ok))
    lines.append(_criterion_line("Assessment remains zero-window-scroll after opening at least one hint", pw_ok))
    lines.append(_criterion_line("Learning mode route (`/app/learn/:subject`) maintains zero browser-level vertical scroll with question/actions visible", pw_ok))
    lines.append(_criterion_line("Widget-family render integrity holds (radio/dropdown/text-numeric render inside container without detached overlays/stray text)", pw_ok))
    lines.append(_criterion_line("Dropdown anchor integrity holds (opened listbox stays near combobox trigger and inside viewport on assessment + learning routes)", pw_ok))
    lines.append(_criterion_line("Theme integrity holds in both modes (light/dark toggles render correct question surfaces/text without mixed-mode artifacts)", pw_ok))
    lines.append(_criterion_line("Question content contrast passes in both light and dark themes on assessment + learning routes", pw_ok))
    lines.append(_criterion_line("Hint control legibility passes in both themes (`Show Hint`/`Hint` stays readable on assessment + learning routes)", pw_ok))
    lines.append(_criterion_line("Selected radio option highlight renders as complete 4-sided outline (no clipped/incomplete blue border)", pw_ok))
    lines.append(_criterion_line("Assessment completion routes into subject-scoped learning state (not generic homepage fallback)", pw_ok and smoke_ok))
    lines.append(_criterion_line("Adaptive assessment reaches completed=true within 10 answered questions without manual retry loops", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Synthetic fallback question IDs resolve to source payloads so adaptive continuity cannot dead-end", smoke_ok and pretest_ok))
    lines.append(_criterion_line("Responsive layout has no blocking overflow/clipping on tested viewports", pw_ok))
    lines.append(_criterion_line("Playwright screenshots captured for assessment + floating panel", pw_ok and len(shot_paths) >= 4))
    lines.append(_criterion_line("Floating panel not obscured by widget container (Z-index check)", pw_ok))
    lines.append(_criterion_line("Floating panel is fully visible on /app and /app/:id routes (not clipped/off-screen/sliver)", pw_ok))
    lines.append(_criterion_line("AI payload matches browser-rendered content (hydration/render check)", pw_ok))
    lines.append(_criterion_line("Greptile review gate passed", greptile_ok))
    lines.append(_criterion_line("No leaked secrets/API keys in changed files", secret_scan_ok))
    lines.append("")

    lines.append("## QA Evidence")
    lines.append("")
    if shot_paths:
        for shot in shot_paths:
            lines.append(f"- `{_rel(shot)}`")
    else:
        lines.append("- No screenshots found")
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
    packet = build_packet(summary, screenshots_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packet, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()

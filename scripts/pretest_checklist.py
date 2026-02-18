#!/usr/bin/env python3
"""
Pre-test checklist runner for local QA.

Runs:
1) Frontend scoring tests (vitest)
2) Full subject sweep (/api/start-subject + /api/questions/5)
3) Strict question checks (pre-serve validator + render contract)
4) Adaptive assessment probe (must not complete after one answer)
5) Cold-subject non-crash probe (must not return 500)
6) Optional Content V1 battletest

Usage:
  python3 scripts/pretest_checklist.py

Optional env:
  AUTH_BASE=http://localhost:8003
  DASH_BASE=http://localhost:8000
  SUBJECTS_FILE=artifacts/pretest/all_subjects.txt
  PRETEST_INCLUDE_CONTENT_V1=true|false   (default: true)
  CONTENT_V1_USE_DEV_LOGIN=true|false     (used by battletest, default: true)
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
AUTH_BASE = os.environ.get("AUTH_BASE", "http://localhost:8003")
DASH_BASE = os.environ.get("DASH_BASE", "http://localhost:8000")
SUBJECTS_FILE = Path(os.environ.get("SUBJECTS_FILE", str(ROOT / "artifacts" / "pretest" / "all_subjects.txt")))
INCLUDE_CONTENT_V1 = os.environ.get("PRETEST_INCLUDE_CONTENT_V1", "true").lower() in {"1", "true", "yes"}
MIN_STABLE_ADAPTIVE_TRANSITIONS = max(
    5,
    int(os.environ.get("PRETEST_MIN_STABLE_ADAPTIVE_TRANSITIONS", "8")),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _req_json(
    method: str,
    url: str,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 45,
    retries: int = 2,
) -> Tuple[int, Any]:
    data = None
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    last_err: Optional[str] = None
    for i in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = raw
                return res.status, parsed
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return e.code, parsed
        except Exception as e:  # connection errors/timeouts
            last_err = str(e)
            if i < retries:
                time.sleep(1 + i)
                continue
            return 0, {"error": last_err}

    return 0, {"error": last_err or "unknown error"}


def _get_dev_token() -> str:
    code, body = _req_json(
        "POST",
        f"{AUTH_BASE}/auth/dev-login",
        payload={"age": 12, "name": "Pretest Runner"},
        timeout=20,
        retries=2,
    )
    if code != 200 or not isinstance(body, dict) or "token" not in body:
        raise RuntimeError(f"dev-login failed: code={code} body={body}")
    return str(body["token"])


def _run_scoring_tests() -> Dict[str, Any]:
    cmd = ["npm", "--prefix", "frontend", "exec", "vitest", "run", "src/lib/scoring-utils.test.ts"]
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    passed = p.returncode == 0
    return {
        "ok": passed,
        "command": " ".join(cmd),
        "returncode": p.returncode,
        "stdout_tail": "\n".join(p.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(p.stderr.splitlines()[-20:]),
    }


def _load_subjects() -> List[str]:
    if SUBJECTS_FILE.exists():
        subjects = [line.strip() for line in SUBJECTS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
        if subjects:
            return subjects
    # Fallback: small core set if subject list file is missing
    return ["Science", "History", "English", "Geography", "python", "world war 1", "Physics", "Geometry"]


def _render_contract_failures(q: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    question = q.get("question")
    if not isinstance(question, dict):
        return ["missing question dict"]

    widgets = question.get("widgets")
    if not isinstance(widgets, dict) or len(widgets) == 0:
        failures.append("missing widgets dict")
    if not isinstance(q.get("answerArea"), dict):
        failures.append("missing answerArea dict")

    for wid, wdef in (widgets or {}).items():
        if not isinstance(wdef, dict):
            failures.append(f"{wid}: widget is not dict")
            continue
        wtype = wdef.get("type")
        if not isinstance(wtype, str) or not wtype:
            failures.append(f"{wid}: missing widget type")
    return failures


_RE_SPACE = re.compile(r"\s+")
_RE_WIDGET_MARK = re.compile(r"\[\[☃[^\]]+\]\]")


def _content_fingerprint(q: Dict[str, Any]) -> str:
    """Fingerprint normalized prompt+answerArea for duplicate-content detection."""
    content = ((q.get("question") or {}).get("content") or "")
    content = _RE_WIDGET_MARK.sub(" ", str(content))
    content = _RE_SPACE.sub(" ", content).strip().lower()
    answer_area = json.dumps(q.get("answerArea") or {}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{content}|{answer_area}".encode("utf-8")).hexdigest()


def _load_pre_serve_validator():
    path = ROOT / "services" / "DashSystem" / "pre_serve_validator.py"
    spec = importlib.util.spec_from_file_location("pre_serve_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load pre_serve_validator")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_pre_serve


def _run_subject_sweep(token: str) -> Dict[str, Any]:
    subjects = _load_subjects()
    validate_pre_serve = _load_pre_serve_validator()

    widget_counts: Counter[str] = Counter()
    rows: List[Dict[str, Any]] = []
    pre_serve_failed = 0
    render_failed = 0
    questions_checked = 0
    duplicate_id_total = 0
    duplicate_content_total = 0

    for subject in subjects:
        t0 = time.time()
        sc, sp = _req_json(
            "POST",
            f"{DASH_BASE}/api/start-subject",
            token=token,
            payload={"subject": subject, "region": "US"},
            timeout=45,
            retries=2,
        )
        t1 = time.time()
        qc, qp = _req_json(
            "GET",
            f"{DASH_BASE}/api/questions/5",
            token=token,
            timeout=120,
            retries=2,
        )
        t2 = time.time()

        q_list = qp if isinstance(qp, list) else []
        status = sp.get("status", "unknown") if isinstance(sp, dict) else "unknown"
        skills_count = int(sp.get("skills_count", 0)) if isinstance(sp, dict) and str(sp.get("skills_count", "0")).isdigit() else 0
        q_count = len(q_list)

        transport_ok = (sc == 200 and qc == 200 and q_count > 0)
        pre_fails = 0
        render_fails = 0
        ids: List[str] = []
        fps: List[str] = []

        for q in q_list:
            questions_checked += 1
            dm_q = q.get("dash_metadata", {}) if isinstance(q, dict) else {}
            qid = ""
            if isinstance(dm_q, dict):
                qid = str(dm_q.get("dash_question_id") or "")
            ids.append(qid)
            fps.append(_content_fingerprint(q))

            widgets = ((q.get("question") or {}).get("widgets") or {})
            if isinstance(widgets, dict):
                for w in widgets.values():
                    if isinstance(w, dict):
                        wt = w.get("type")
                        if isinstance(wt, str) and wt:
                            widget_counts[wt] += 1

            dm = q.get("dash_metadata", {}) if isinstance(q, dict) else {}
            skill_ids = dm.get("skill_ids") if isinstance(dm, dict) else []
            skill_id = skill_ids[0] if isinstance(skill_ids, list) and skill_ids else ""

            vr = validate_pre_serve(q, skill_id=skill_id, subject=subject)
            if not vr.passed:
                pre_fails += 1
                pre_serve_failed += 1

            rc_fails = _render_contract_failures(q)
            if rc_fails:
                render_fails += 1
                render_failed += 1

        duplicate_id_count = max(0, len([x for x in ids if x]) - len(set([x for x in ids if x])))
        duplicate_content_count = max(0, len(fps) - len(set(fps)))
        duplicate_id_total += duplicate_id_count
        duplicate_content_total += duplicate_content_count

        strict_ok = (
            transport_ok
            and pre_fails == 0
            and render_fails == 0
            and duplicate_id_count == 0
            and duplicate_content_count == 0
        )
        rows.append(
            {
                "subject": subject,
                "status": status,
                "start_code": sc,
                "questions_code": qc,
                "skills_count": skills_count,
                "questions_count": q_count,
                "start_seconds": round(t1 - t0, 2),
                "questions_seconds": round(t2 - t1, 2),
                "transport_ok": transport_ok,
                "strict_ok": strict_ok,
                "checked_questions": q_count,
                "pre_serve_failures": pre_fails,
                "render_contract_failures": render_fails,
                "duplicate_id_count": duplicate_id_count,
                "duplicate_content_count": duplicate_content_count,
            }
        )

    transport_pass = sum(1 for r in rows if r["transport_ok"])
    strict_pass = sum(1 for r in rows if r["strict_ok"])
    return {
        "ok": strict_pass == len(rows),
        "subjects": rows,
        "totals": {
            "subjects": len(rows),
            "transport_pass": transport_pass,
            "transport_fail": len(rows) - transport_pass,
            "strict_pass": strict_pass,
            "strict_fail": len(rows) - strict_pass,
            "questions_checked": questions_checked,
            "pre_serve_failed": pre_serve_failed,
            "render_contract_failed": render_failed,
            "duplicate_id_total": duplicate_id_total,
            "duplicate_content_total": duplicate_content_total,
        },
        "widget_types": dict(widget_counts),
    }


def _run_cold_subject_probe(token: str) -> Dict[str, Any]:
    subject = f"zzzz pretest probe {int(time.time())}"
    sc, sp = _req_json(
        "POST",
        f"{DASH_BASE}/api/start-subject",
        token=token,
        payload={"subject": subject, "region": "US"},
        timeout=45,
        retries=2,
    )
    qc, qp = _req_json(
        "GET",
        f"{DASH_BASE}/api/questions/3",
        token=token,
        timeout=60,
        retries=2,
    )
    status = sp.get("status", "unknown") if isinstance(sp, dict) else "unknown"
    # Gate: must not 500; both 200 and 503 are acceptable for brand-new subjects.
    ok = (sc == 200 and qc != 500)
    return {
        "ok": ok,
        "subject": subject,
        "start_code": sc,
        "start_status": status,
        "questions_code": qc,
        "questions_body_type": type(qp).__name__,
    }


def _run_adaptive_flow_probe(token: str) -> Dict[str, Any]:
    """
    Ensure adaptive assessment remains stable over multiple consecutive answers.
    Gate per subject:
    - start-adaptive returns first question
    - repeated /assessment/next calls return completed=False with valid question payload
      for sustained transitions (default: 8) to catch "breaks after Q4" regressions
    """
    subjects = ["Science", "Math"]
    rows: List[Dict[str, Any]] = []
    min_stable_transitions = MIN_STABLE_ADAPTIVE_TRANSITIONS

    for subject in subjects:
        # Pin subject first
        _req_json(
            "POST",
            f"{DASH_BASE}/api/start-subject",
            token=token,
            payload={"subject": subject, "region": "US"},
            timeout=45,
            retries=2,
        )

        # Start adaptive (retry once for transient generator stalls)
        start_code, start_body = 0, {}
        for attempt in range(2):
            start_code, start_body = _req_json(
                "POST",
                f"{DASH_BASE}/assessment/start-adaptive/{urllib.parse.quote(subject)}",
                token=token,
                payload={},
                timeout=120,
                retries=1,
            )
            if start_code == 200 and isinstance(start_body, dict) and not start_body.get("error"):
                break
            if attempt == 0:
                time.sleep(1.5)

        start_ok = (
            start_code == 200
            and isinstance(start_body, dict)
            and not start_body.get("error")
            and isinstance(start_body.get("question"), dict)
        )

        next_code = 0
        next_body: Any = {}
        transitions_ok = 0
        progression: List[Dict[str, Any]] = []
        completed_early = False

        if start_ok:
            assessment_id = start_body.get("assessment_id")
            current_question = start_body.get("question") or {}
            current_difficulty = float(start_body.get("current_difficulty") or 0.5)

            for step in range(1, min_stable_transitions + 1):
                dm = current_question.get("dash_metadata") if isinstance(current_question, dict) else {}
                if not isinstance(dm, dict):
                    dm = {}
                payload = {
                    "assessment_id": assessment_id,
                    "question_id": dm.get("dash_question_id") or f"q_{step}",
                    "skill_id": (dm.get("skill_ids") or [""])[0] if isinstance(dm.get("skill_ids"), list) else "",
                    "is_correct": True,
                }

                step_ok = False
                for attempt in range(8):
                    # Mirror frontend behavior: prefetch next branch before requesting /assessment/next.
                    _req_json(
                        "POST",
                        f"{DASH_BASE}/assessment/prefetch",
                        token=token,
                        payload={
                            "assessment_id": assessment_id,
                            "current_difficulty": current_difficulty,
                        },
                        timeout=30,
                        retries=1,
                    )
                    next_code, next_body = _req_json(
                        "POST",
                        f"{DASH_BASE}/assessment/next",
                        token=token,
                        payload=payload,
                        timeout=120,
                        retries=1,
                    )
                    completed_early = bool(next_body.get("completed")) if isinstance(next_body, dict) else False
                    step_ok = (
                        next_code == 200
                        and isinstance(next_body, dict)
                        and next_body.get("completed") is False
                        and isinstance(next_body.get("question"), dict)
                    )
                    if step_ok:
                        break
                    if next_code == 503 and attempt < 7:
                        time.sleep(1.2 * (attempt + 1))
                        continue
                    break

                progression.append(
                    {
                        "step": step,
                        "next_code": next_code,
                        "step_ok": step_ok,
                        "completed_early": completed_early,
                    }
                )

                if not step_ok or completed_early:
                    break
                transitions_ok += 1
                current_question = (next_body or {}).get("question") or {}
                next_difficulty = (next_body or {}).get("current_difficulty") if isinstance(next_body, dict) else None
                if isinstance(next_difficulty, (int, float)):
                    current_difficulty = float(next_difficulty)

        rows.append(
            {
                "subject": subject,
                "start_code": start_code,
                "next_code": next_code,
                "start_ok": start_ok,
                "stable_transitions_ok": transitions_ok,
                "min_required_transitions": min_stable_transitions,
                "completed_early": completed_early,
                "progression": progression,
            }
        )

    ok = all(
        r["start_ok"]
        and r["stable_transitions_ok"] >= min_stable_transitions
        and not r["completed_early"]
        for r in rows
    )
    return {"ok": ok, "subjects": rows}


def _run_content_v1_battletest() -> Dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("CONTENT_V1_USE_DEV_LOGIN", "true")
    cmd = ["python3", "scripts/content_v1_battletest.py"]
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=1200,
        env=env,
    )
    lines = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
    artifact_path = None
    for ln in lines:
        if "artifacts/proof/content-v1-battletest-" in ln and ln.endswith(".json"):
            artifact_path = ln
    ok = p.returncode == 0
    return {
        "ok": ok,
        "command": " ".join(cmd),
        "returncode": p.returncode,
        "artifact": artifact_path,
        "stdout_tail": "\n".join(p.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(p.stderr.splitlines()[-20:]),
    }


def main() -> int:
    out_dir = ROOT / "artifacts" / "pretest"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"checklist-{stamp}.json"

    result: Dict[str, Any] = {
        "created_at": _now_iso(),
        "dash_base": DASH_BASE,
        "auth_base": AUTH_BASE,
        "steps": {},
    }

    # Step 0: health and auth token
    health_code, health_body = _req_json("GET", f"{DASH_BASE}/health", timeout=10, retries=1)
    result["steps"]["health"] = {"ok": health_code == 200, "code": health_code, "body": health_body}
    if health_code != 200:
        result["ok"] = False
        result["error"] = "DASH API health check failed"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(out_path)
        print(json.dumps({"ok": False, "reason": "health_failed"}, indent=2))
        return 1

    try:
        token = _get_dev_token()
        result["steps"]["auth"] = {"ok": True}
    except Exception as e:
        result["steps"]["auth"] = {"ok": False, "error": str(e)}
        result["ok"] = False
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(out_path)
        print(json.dumps({"ok": False, "reason": "auth_failed"}, indent=2))
        return 1

    # Step 1: scoring tests
    result["steps"]["scoring_tests"] = _run_scoring_tests()

    # Step 2: full subject sweep + strict checks
    result["steps"]["subject_sweep"] = _run_subject_sweep(token)

    # Step 3: adaptive assessment should not complete after one question
    result["steps"]["adaptive_flow_probe"] = _run_adaptive_flow_probe(token)

    # Step 4: cold subject should not crash with 500
    result["steps"]["cold_subject_probe"] = _run_cold_subject_probe(token)

    # Step 5: optional content v1 battletest
    if INCLUDE_CONTENT_V1:
        result["steps"]["content_v1_battletest"] = _run_content_v1_battletest()
    else:
        result["steps"]["content_v1_battletest"] = {"ok": True, "skipped": True}

    step_oks = [bool(v.get("ok")) for v in result["steps"].values()]
    result["ok"] = all(step_oks)

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(out_path)
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "health": result["steps"]["health"]["ok"],
                "scoring_tests": result["steps"]["scoring_tests"]["ok"],
                "subject_sweep": result["steps"]["subject_sweep"]["ok"],
                "adaptive_flow_probe": result["steps"]["adaptive_flow_probe"]["ok"],
                "cold_subject_probe": result["steps"]["cold_subject_probe"]["ok"],
                "content_v1_battletest": result["steps"]["content_v1_battletest"]["ok"],
                "totals": result["steps"]["subject_sweep"].get("totals", {}),
            },
            indent=2,
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

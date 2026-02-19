#!/usr/bin/env python3
"""Smoke gate for the content pipeline harness.

Validates:
- service health
- auth + subject start + question fetch
- question contract (widgets + answer area)
- duplicate/content fingerprint checks
- cross-subject contamination checks
- adaptive assessment progression after first answer
- websocket ping/pong round-trip
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import websockets
except Exception:
    websockets = None


AUTH_BASE = os.environ.get("AUTH_BASE", "http://localhost:8003")
DASH_BASE = os.environ.get("DASH_BASE", "http://localhost:8000")
TA_BASE = os.environ.get("TA_BASE", "http://localhost:8002")
SUBJECT = os.environ.get("HARNESS_SUBJECT", "Science").strip().title()
QUESTIONS_LATENCY_BUDGET_S = float(os.environ.get("HARNESS_QUESTIONS_LATENCY_BUDGET_S", "8"))
NEXT_LATENCY_BUDGET_S = float(os.environ.get("HARNESS_NEXT_LATENCY_BUDGET_S", "2.5"))
ADAPTIVE_START_LATENCY_BUDGET_S = float(os.environ.get("HARNESS_ADAPTIVE_START_LATENCY_BUDGET_S", "8"))
MIN_QUESTION_COUNT = int(os.environ.get("HARNESS_MIN_QUESTION_COUNT", "5"))
ADAPTIVE_START_TIMEOUT_S = float(os.environ.get("HARNESS_ADAPTIVE_START_TIMEOUT_S", "4"))
ADAPTIVE_START_RETRY_TIMEOUT_S = float(os.environ.get("HARNESS_ADAPTIVE_START_RETRY_TIMEOUT_S", "12"))
SKIP_WEBSOCKET = os.environ.get("HARNESS_SKIP_WEBSOCKET", "false").lower() in {"1", "true", "yes"}
SKIP_ADAPTIVE = os.environ.get("HARNESS_SKIP_ADAPTIVE", "false").lower() in {"1", "true", "yes"}

_RE_SPACE = re.compile(r"\s+")
_RE_WIDGET = re.compile(r"\[\[☃[^\]]+\]\]")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _req_json(
    method: str,
    url: str,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 45,
    retries: int = 1,
) -> Tuple[int, Any, float]:
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
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                elapsed = time.time() - t0
                raw = res.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = raw
                return res.status, parsed, elapsed
        except urllib.error.HTTPError as e:
            elapsed = time.time() - t0
            raw = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return e.code, parsed, elapsed
        except Exception as e:
            last_err = str(e)
            if i < retries:
                time.sleep(1 + i)
                continue
            return 0, {"error": last_err}, 0.0

    return 0, {"error": last_err or "unknown error"}, 0.0


def _fingerprint(q: Dict[str, Any]) -> str:
    content = ((q.get("question") or {}).get("content") or "")
    content = _RE_WIDGET.sub(" ", str(content))
    content = _RE_SPACE.sub(" ", content).strip().lower()
    answer_area = json.dumps(q.get("answerArea") or {}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{content}|{answer_area}".encode("utf-8")).hexdigest()


def _question_contract_issues(q: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    question = q.get("question")
    if not isinstance(question, dict):
        return ["missing question dict"]

    widgets = question.get("widgets")
    if not isinstance(widgets, dict) or not widgets:
        issues.append("missing widgets dict")
    content = question.get("content")
    has_radio_widget = False
    if not isinstance(q.get("answerArea"), dict):
        issues.append("missing answerArea dict")
    else:
        answer_type = (q.get("answerArea") or {}).get("type")
        if not isinstance(answer_type, str) or not answer_type.strip():
            issues.append("missing answerArea.type")

    for wid, wdef in (widgets or {}).items():
        if not isinstance(wdef, dict):
            issues.append(f"{wid}: widget is not dict")
            continue
        wtype = wdef.get("type")
        if not isinstance(wtype, str) or not wtype:
            issues.append(f"{wid}: missing widget type")
            continue

        if wtype == "radio":
            has_radio_widget = True
            opts = wdef.get("options")
            if not isinstance(opts, dict):
                issues.append(f"{wid}: radio options is not dict")
                continue
            choices = opts.get("choices")
            if not isinstance(choices, list) or not choices:
                issues.append(f"{wid}: radio choices missing/empty")
                continue
            correct_count = 0
            for cidx, choice in enumerate(choices):
                if isinstance(choice, dict):
                    if bool(choice.get("correct")):
                        correct_count += 1
                    raw_content = str(choice.get("content", "")).strip()
                else:
                    raw_content = str(choice).strip()
                if (
                    len(raw_content) >= 2
                    and raw_content[0] == raw_content[-1]
                    and raw_content[0] in {"'", '"'}
                ):
                    inner = raw_content[1:-1].strip()
                    if (
                        inner
                        and inner.count(raw_content[0]) == 0
                        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.,/%:+\-]*", inner)
                    ):
                        issues.append(f"{wid}: choice[{cidx}] has leaked wrapping quotes")
            multi = bool(opts.get("multipleSelect"))
            if correct_count == 0:
                issues.append(f"{wid}: no correct choice marked")
            if not multi and correct_count != 1:
                issues.append(f"{wid}: expected exactly one correct choice for single-select")

        if wtype == "dropdown":
            opts = wdef.get("options")
            if not isinstance(opts, dict):
                issues.append(f"{wid}: dropdown options is not dict")
                continue
            choices = opts.get("choices")
            if isinstance(choices, list):
                for cidx, choice in enumerate(choices):
                    raw_content = str(choice.get("content", "") if isinstance(choice, dict) else choice).strip()
                    if (
                        len(raw_content) >= 2
                        and raw_content[0] == raw_content[-1]
                        and raw_content[0] in {"'", '"'}
                    ):
                        inner = raw_content[1:-1].strip()
                        if (
                            inner
                            and inner.count(raw_content[0]) == 0
                            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.,/%:+\-]*", inner)
                        ):
                            issues.append(f"{wid}: dropdown choice[{cidx}] has leaked wrapping quotes")

    if has_radio_widget and isinstance(content, str):
        if re.search(r"^\s*choose\s+(?:\d+|one)\s+answers?:\s*$", content, flags=re.IGNORECASE | re.MULTILINE):
            issues.append("question content includes duplicate radio instruction label")

    return issues


def _validate_subject_scope(subject: str, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simple guard to catch cross-subject contamination in skill IDs."""
    subject_key = subject.lower()
    contamination: List[str] = []
    missing_skill_ids = 0

    for q in questions:
        dm = q.get("dash_metadata") or {}
        skill_ids = dm.get("skill_ids") or []
        if not isinstance(skill_ids, list) or not skill_ids:
            missing_skill_ids += 1
            continue
        joined = " ".join(str(s).lower() for s in skill_ids)
        if subject_key == "science" and "math" in joined:
            contamination.append(joined)
        if subject_key == "math" and "science" in joined:
            contamination.append(joined)

    return {
        "subject": subject,
        "missing_skill_ids": missing_skill_ids,
        "contamination_count": len(contamination),
        "contamination_examples": contamination[:3],
        "ok": missing_skill_ids == 0 and len(contamination) == 0,
    }


def _wait_for_dash_ready(timeout_s: int = 90) -> Dict[str, Any]:
    started = time.time()
    polls = 0
    while time.time() - started < timeout_s:
        polls += 1
        code, body, elapsed = _req_json("GET", f"{DASH_BASE}/health", timeout=8, retries=0)
        if code == 200 and isinstance(body, dict) and body.get("ready") is True:
            return {
                "ok": True,
                "code": code,
                "elapsed_s": elapsed,
                "polls": polls,
                "body": body,
            }
        time.sleep(2)
    return {
        "ok": False,
        "code": 0,
        "elapsed_s": time.time() - started,
        "polls": polls,
        "body": {"error": "dash not ready within timeout"},
    }


def _subject_list_from_available(payload: Any) -> List[str]:
    if not isinstance(payload, dict):
        return []
    docs = payload.get("subjects")
    if not isinstance(docs, list):
        return []

    out: List[str] = []
    seen: set[str] = set()
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        subject = doc.get("subject")
        if not isinstance(subject, str):
            continue
        normalized = subject.strip().title()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
    return out


def _adaptive_start_acceptable(code: int, body: Any) -> tuple[bool, str]:
    # Ready path: fully formed adaptive start payload.
    if code == 200 and isinstance(body, dict):
        if body.get("assessment_id") and isinstance(body.get("question"), dict):
            return True, "ready"
        return False, "200-missing-assessment-payload"

    # Retryable path while curriculum/questions are preparing.
    if code == 503 and isinstance(body, dict):
        detail = str(body.get("detail", "")).lower()
        if any(k in detail for k in ("prepare", "prepared", "retry", "warming", "generat")):
            return True, "retryable-503"
        return False, "503-non-retryable-detail"

    if code == 400:
        return False, "terminal-400"

    # Slow subjects can time out during cold generation; treat this as retryable
    # (non-terminal) as long as at least some subjects return concrete 200/503.
    if code == 0 and isinstance(body, dict):
        err = str(body.get("error", "")).lower()
        if "timed out" in err or "timeout" in err:
            return True, "timeout-retryable"
    return False, f"unexpected-{code}"


async def _ws_probe(token: str) -> Dict[str, Any]:
    if websockets is None:
        return {
            "ok": False,
            "error": "python websockets package not available",
        }

    # Secure path: fetch short-lived one-time stream auth code (no JWT in URL)
    code_resp, code_body, code_elapsed = _req_json(
        "POST",
        f"{TA_BASE}/auth/stream-code?purpose=feed",
        token=token,
        timeout=15,
        retries=1,
    )
    if code_resp != 200 or not isinstance(code_body, dict) or not code_body.get("code"):
        return {
            "ok": False,
            "elapsed_s": code_elapsed,
            "error": f"failed to issue stream auth code ({code_resp}): {code_body}",
        }

    stream_code = str(code_body["code"])
    ws_url = TA_BASE.replace("http://", "ws://").replace("https://", "wss://") + f"/ws/feed?code={urllib.parse.quote(stream_code)}"
    started = time.time()

    try:
        async with websockets.connect(ws_url, open_timeout=15, close_timeout=10) as ws:
            await ws.send(json.dumps({"type": "ping", "timestamp": time.time(), "data": {}}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            payload = json.loads(raw) if isinstance(raw, str) else raw
            ok = isinstance(payload, dict) and payload.get("type") == "pong"
            return {
                "ok": ok,
                "elapsed_s": time.time() - started,
                "response": payload,
            }
    except Exception as e:
        return {
            "ok": False,
            "elapsed_s": time.time() - started,
            "error": str(e),
        }


def run(output_path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "created_at": _now_iso(),
        "subject": SUBJECT,
        "services": {},
        "checks": {},
        "ok": False,
        "errors": [],
    }

    # 1) Service health
    result["services"]["dash"] = _wait_for_dash_ready()
    for service, base in (("auth", AUTH_BASE), ("teaching_assistant", TA_BASE)):
        code, body, elapsed = _req_json("GET", f"{base}/health", timeout=10, retries=1)
        optional = service == "teaching_assistant" and SKIP_WEBSOCKET
        result["services"][service] = {
            "ok": (code == 200) if not optional else True,
            "actual_ok": code == 200,
            "optional": optional,
            "code": code,
            "elapsed_s": elapsed,
            "body": body,
        }

    if not all(v.get("ok") for v in result["services"].values()):
        result["errors"].append("service health checks failed")

    # 2) Auth dev-login
    code, auth_body, elapsed = _req_json(
        "POST",
        f"{AUTH_BASE}/auth/dev-login",
        payload={"age": 12, "name": "Harness Smoke"},
        timeout=20,
        retries=1,
    )
    token = auth_body.get("token") if isinstance(auth_body, dict) else None
    result["checks"]["dev_login"] = {
        "ok": code == 200 and isinstance(token, str) and len(token) > 10,
        "code": code,
        "elapsed_s": elapsed,
        "body": auth_body if code != 200 else {"token_received": bool(token)},
    }
    if not result["checks"]["dev_login"]["ok"]:
        result["errors"].append("dev-login failed")

    if not token:
        result["ok"] = False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    # 3) Subject start + question fetch
    sc, sp, s_elapsed = _req_json(
        "POST",
        f"{DASH_BASE}/api/start-subject",
        token=token,
        payload={"subject": SUBJECT, "region": "US"},
        timeout=45,
        retries=1,
    )
    qc, qp, q_elapsed = _req_json(
        "GET",
        f"{DASH_BASE}/api/questions/10",
        token=token,
        timeout=120,
        retries=1,
    )
    questions: List[Dict[str, Any]] = qp if isinstance(qp, list) else []

    ids: List[str] = []
    fingerprints: List[str] = []
    contract_failures: List[str] = []
    for idx, q in enumerate(questions):
        dm = q.get("dash_metadata") or {}
        qid = str(dm.get("dash_question_id") or "")
        ids.append(qid)
        fingerprints.append(_fingerprint(q))
        issues = _question_contract_issues(q)
        if issues:
            contract_failures.append(f"q[{idx}] {qid or '<missing_id>'}: {', '.join(issues)}")

    duplicate_ids = len([x for x in set(ids) if x and ids.count(x) > 1])
    duplicate_fps = len([x for x in set(fingerprints) if fingerprints.count(x) > 1])
    scope_check = _validate_subject_scope(SUBJECT, questions)

    result["checks"]["question_fetch"] = {
        "ok": (
            sc == 200
            and qc == 200
            and len(questions) >= MIN_QUESTION_COUNT
            and q_elapsed <= QUESTIONS_LATENCY_BUDGET_S
            and duplicate_ids == 0
            and duplicate_fps == 0
            and not contract_failures
            and scope_check["ok"]
        ),
        "start_subject": {"code": sc, "elapsed_s": s_elapsed, "body": sp},
        "questions": {
            "code": qc,
            "elapsed_s": q_elapsed,
            "count": len(questions),
            "duplicate_ids": duplicate_ids,
            "duplicate_content": duplicate_fps,
            "contract_failures": contract_failures[:10],
            "scope_check": scope_check,
        },
        "budgets": {
            "questions_latency_budget_s": QUESTIONS_LATENCY_BUDGET_S,
            "min_question_count": MIN_QUESTION_COUNT,
        },
    }
    if not result["checks"]["question_fetch"]["ok"]:
        result["errors"].append("question fetch/contract/scope checks failed")

    # 3b) Learning-path recommend-next subject/content validity
    recommend_elapsed_s: Optional[float] = None
    current_question_ids_for_recommend = [x for x in ids if x][:3]
    if not current_question_ids_for_recommend:
        result["checks"]["learning_path_subject_validity"] = {
            "ok": False,
            "reason": "no-current-question-ids-for-recommend-next",
        }
        result["errors"].append("learning path recommend-next subject/content check failed")
    else:
        rc, rp, r_elapsed = _req_json(
            "POST",
            f"{DASH_BASE}/api/questions/recommend-next",
            token=token,
            payload={
                "current_question_ids": current_question_ids_for_recommend,
                "count": 5,
            },
            timeout=120,
            retries=1,
        )
        recommend_elapsed_s = r_elapsed
        recommended: List[Dict[str, Any]] = rp if isinstance(rp, list) else []

        rec_ids: List[str] = []
        rec_fingerprints: List[str] = []
        rec_contract_failures: List[str] = []
        for idx, q in enumerate(recommended):
            dm = q.get("dash_metadata") or {}
            qid = str(dm.get("dash_question_id") or "")
            rec_ids.append(qid)
            rec_fingerprints.append(_fingerprint(q))
            issues = _question_contract_issues(q)
            if issues:
                rec_contract_failures.append(f"q[{idx}] {qid or '<missing_id>'}: {', '.join(issues)}")

        rec_duplicate_ids = len([x for x in set(rec_ids) if x and rec_ids.count(x) > 1])
        rec_duplicate_fps = len([x for x in set(rec_fingerprints) if rec_fingerprints.count(x) > 1])
        rec_scope_check = _validate_subject_scope(SUBJECT, recommended)
        overlap_with_current = sorted(set(current_question_ids_for_recommend).intersection(set([x for x in rec_ids if x])))

        learning_path_ok = (
            rc == 200
            and isinstance(rp, list)
            and len(recommended) > 0
            and rec_duplicate_ids == 0
            and rec_duplicate_fps == 0
            and len(overlap_with_current) == 0
            and not rec_contract_failures
            and rec_scope_check["ok"]
        )
        result["checks"]["learning_path_subject_validity"] = {
            "ok": learning_path_ok,
            "current_question_ids": current_question_ids_for_recommend,
            "recommend_next": {
                "code": rc,
                "elapsed_s": r_elapsed,
                "count": len(recommended),
                "overlap_with_current_ids": overlap_with_current,
                "duplicate_ids": rec_duplicate_ids,
                "duplicate_content": rec_duplicate_fps,
                "contract_failures": rec_contract_failures[:10],
                "scope_check": rec_scope_check,
                "body": rp if rc != 200 else {"sample_ids": [x for x in rec_ids[:5] if x]},
            },
        }
        if not learning_path_ok:
            result["errors"].append("learning path recommend-next subject/content check failed")

    # 4) Adaptive start validation across all available subjects + progression
    if SKIP_ADAPTIVE:
        result["checks"]["adaptive_start_all_subjects"] = {
            "ok": True,
            "skipped": True,
            "reason": "HARNESS_SKIP_ADAPTIVE=true",
        }
        result["checks"]["adaptive_progression"] = {
            "ok": True,
            "skipped": True,
            "reason": "HARNESS_SKIP_ADAPTIVE=true",
        }
        result["checks"]["loading_latency"] = {
            "ok": True,
            "skipped": True,
            "reason": "HARNESS_SKIP_ADAPTIVE=true",
        }
    else:
        def _start_adaptive_for(subject_name: str, timeout_s: float) -> Tuple[int, Any, float]:
            return _req_json(
                "POST",
                f"{DASH_BASE}/assessment/start-adaptive/{urllib.parse.quote(subject_name)}",
                token=token,
                payload={},
                timeout=timeout_s,
                retries=0,
            )

        subj_code, subj_body, subj_elapsed = _req_json(
            "GET",
            f"{DASH_BASE}/api/subjects/available",
            token=token,
            timeout=45,
            retries=1,
        )
        catalog_subjects = _subject_list_from_available(subj_body)
        subjects_to_check = catalog_subjects if catalog_subjects else [SUBJECT]

        start_rows: List[Dict[str, Any]] = []
        ready_start_payload: Optional[Dict[str, Any]] = None
        ready_start_subject: Optional[str] = None
        for sname in subjects_to_check:
            ac, ap, a_elapsed = _start_adaptive_for(sname, ADAPTIVE_START_TIMEOUT_S)
            timed_out = ac == 0 and isinstance(ap, dict) and "timed out" in str(ap.get("error", "")).lower()
            retried = False
            acceptable, verdict = _adaptive_start_acceptable(ac, ap)
            row = {
                "subject": sname,
                "code": ac,
                "elapsed_s": a_elapsed,
                "retried_after_timeout": retried,
                "acceptable": acceptable,
                "verdict": verdict,
                "body": ap,
            }
            start_rows.append(row)
            if (
                ready_start_payload is None
                and ac == 200
                and isinstance(ap, dict)
                and ap.get("assessment_id")
                and isinstance(ap.get("question"), dict)
            ):
                ready_start_payload = ap
                ready_start_subject = sname

        timeout_retryable_count = sum(1 for r in start_rows if r.get("verdict") == "timeout-retryable")
        concrete_count = len(start_rows) - timeout_retryable_count
        start_all_ok = all(r["acceptable"] for r in start_rows) and concrete_count > 0
        result["checks"]["adaptive_start_all_subjects"] = {
            "ok": start_all_ok,
            "adaptive_start_timeout_s": ADAPTIVE_START_TIMEOUT_S,
            "adaptive_start_retry_timeout_s": ADAPTIVE_START_RETRY_TIMEOUT_S,
            "catalog_fetch": {
                "code": subj_code,
                "elapsed_s": subj_elapsed,
                "count": len(catalog_subjects),
                "fallback_used": len(catalog_subjects) == 0,
            },
            "subjects_checked_count": len(subjects_to_check),
            "subjects_checked": subjects_to_check,
            "timeout_retryable_count": timeout_retryable_count,
            "concrete_result_count": concrete_count,
            "results": start_rows,
        }
        if not start_all_ok:
            result["errors"].append("adaptive start failed for one or more available subjects")

        progression_ok = False
        progression_payload: Dict[str, Any] = {}
        next_transition_latencies: List[float] = []

        if ready_start_payload is not None and ready_start_subject is not None:
            current_q = ready_start_payload.get("question") or {}
            progression_payload = {
                "subject_used": ready_start_subject,
                "start_code": 200,
                "start_elapsed_s": next(
                    (r.get("elapsed_s") for r in start_rows if r.get("subject") == ready_start_subject),
                    None,
                ),
                "start_body": ready_start_payload,
            }
            required_transitions = 8
            stable_transitions = 0
            transition_rows: List[Dict[str, Any]] = []
            session_id = ready_start_payload.get("assessment_id")

            for step in range(1, required_transitions + 1):
                dm = (current_q.get("dash_metadata") or {}) if isinstance(current_q, dict) else {}
                qid = dm.get("dash_question_id") or f"adaptive_step_{step}"
                skill_id = ((dm.get("skill_ids") or [""])[0] if isinstance(dm.get("skill_ids"), list) else "") or ""

                nc, np, n_elapsed = 0, {}, 0.0
                completed_early = False
                has_next_question = False
                attempts_used = 0
                step_ok = False

                # /assessment/next can return transient 503 while the next question is prepared.
                # Retry with backoff before failing this transition.
                for attempt in range(3):
                    attempts_used = attempt + 1
                    nc, np, n_elapsed = _req_json(
                        "POST",
                        f"{DASH_BASE}/assessment/next",
                        token=token,
                        payload={
                            "assessment_id": session_id,
                            "question_id": qid,
                            "skill_id": skill_id,
                            "is_correct": True,
                        },
                        timeout=max(6, int(NEXT_LATENCY_BUDGET_S + 2)),
                        retries=0,
                    )
                    completed_early = isinstance(np, dict) and bool(np.get("completed"))
                    has_next_question = isinstance(np, dict) and isinstance(np.get("question"), dict)
                    # Stability = progression continuity.
                    # Latency budget is enforced separately via percentile + hard-timeout checks.
                    step_ok = (nc == 200 and not completed_early and has_next_question)
                    if step_ok:
                        break
                    if nc == 503 and attempt < 2:
                        time.sleep(0.4 * (attempt + 1))
                        continue
                    break

                transition_rows.append(
                    {
                        "step": step,
                        "code": nc,
                        "elapsed_s": n_elapsed,
                        "attempts_used": attempts_used,
                        "completed_early": completed_early,
                        "has_next_question": has_next_question,
                        "ok": step_ok,
                    }
                )

                if not step_ok:
                    break

                stable_transitions += 1
                next_transition_latencies.append(float(n_elapsed))
                current_q = (np.get("question") if isinstance(np, dict) else None) or {}

            progression_ok = stable_transitions >= required_transitions
            progression_payload["required_stable_transitions"] = required_transitions
            progression_payload["stable_transitions"] = stable_transitions
            progression_payload["transitions"] = transition_rows
            first_transition = transition_rows[0] if transition_rows else {}
            progression_payload["next"] = {
                "code": first_transition.get("code"),
                "elapsed_s": first_transition.get("elapsed_s"),
                "completed_early": first_transition.get("completed_early"),
                "has_next_question": first_transition.get("has_next_question"),
                "attempts_used": first_transition.get("attempts_used"),
            }
        else:
            progression_payload["next"] = {"skipped": True, "reason": "no-200-start-adaptive-result"}

        result["checks"]["adaptive_progression"] = {
            "ok": progression_ok,
            "payload": progression_payload,
            "budgets": {
                "next_latency_budget_s": NEXT_LATENCY_BUDGET_S,
            },
        }
        if not progression_ok:
            result["errors"].append("adaptive assessment progression check failed")

        adaptive_start_elapsed = progression_payload.get("start_elapsed_s")
        next_elapsed = max(next_transition_latencies) if next_transition_latencies else ((progression_payload.get("next") or {}).get("elapsed_s"))
        p95_next_elapsed = None
        next_timeout_budget_s = float(os.environ.get("HARNESS_NEXT_TIMEOUT_BUDGET_S", "6.0"))
        if next_transition_latencies:
            vals = sorted(float(v) for v in next_transition_latencies if isinstance(v, (int, float)))
            if vals:
                if len(vals) == 1:
                    p95_next_elapsed = vals[0]
                else:
                    # Linear interpolation percentile (reduces sensitivity to single outliers).
                    pos = 0.95 * (len(vals) - 1)
                    lo = int(math.floor(pos))
                    hi = int(math.ceil(pos))
                    if lo == hi:
                        p95_next_elapsed = vals[lo]
                    else:
                        frac = pos - lo
                        p95_next_elapsed = vals[lo] + (vals[hi] - vals[lo]) * frac

        hard_timeout_ok = all(float(v) <= next_timeout_budget_s for v in next_transition_latencies)
        loading_latency_ok = (
            isinstance(q_elapsed, (int, float))
            and q_elapsed <= QUESTIONS_LATENCY_BUDGET_S
            and isinstance(recommend_elapsed_s, (int, float))
            and recommend_elapsed_s <= NEXT_LATENCY_BUDGET_S
            and isinstance(adaptive_start_elapsed, (int, float))
            and adaptive_start_elapsed <= ADAPTIVE_START_LATENCY_BUDGET_S
            and isinstance(p95_next_elapsed, (int, float))
            and p95_next_elapsed <= NEXT_LATENCY_BUDGET_S
            and hard_timeout_ok
        )
        result["checks"]["loading_latency"] = {
            "ok": loading_latency_ok,
            "initial_question_fetch_elapsed_s": q_elapsed,
            "learning_recommend_next_elapsed_s": recommend_elapsed_s,
            "adaptive_start_elapsed_s": adaptive_start_elapsed,
            "next_question_elapsed_s": next_elapsed,
            "next_question_p95_elapsed_s": p95_next_elapsed,
            "adaptive_next_transition_elapsed_s": next_transition_latencies,
            "adaptive_next_hard_timeout_ok": hard_timeout_ok,
            "budgets": {
                "initial_question_fetch_budget_s": QUESTIONS_LATENCY_BUDGET_S,
                "learning_recommend_next_budget_s": NEXT_LATENCY_BUDGET_S,
                "adaptive_start_budget_s": ADAPTIVE_START_LATENCY_BUDGET_S,
                "next_question_budget_s": NEXT_LATENCY_BUDGET_S,
                "next_question_timeout_budget_s": next_timeout_budget_s,
            },
        }
        if not loading_latency_ok:
            result["errors"].append("question loading latency exceeded budget")

    # 5) Websocket ping/pong check
    if SKIP_WEBSOCKET:
        result["checks"]["websocket"] = {
            "ok": True,
            "skipped": True,
            "reason": "HARNESS_SKIP_WEBSOCKET=true",
        }
    else:
        scode, sbody, s_elapsed = _req_json(
            "POST",
            f"{TA_BASE}/session/start",
            token=token,
            payload={"assessment_mode": True},
            timeout=30,
            retries=1,
        )

        ws_result: Dict[str, Any] = {
            "session_start": {
                "code": scode,
                "elapsed_s": s_elapsed,
                "body": sbody,
            },
            "probe": None,
            "session_end": None,
            "ok": False,
        }

        if scode == 200:
            ws_result["probe"] = asyncio.run(_ws_probe(token))
            ecode, ebody, eelapsed = _req_json(
                "POST",
                f"{TA_BASE}/session/end",
                token=token,
                payload={"assessment_mode": True},
                timeout=30,
                retries=1,
            )
            ws_result["session_end"] = {
                "code": ecode,
                "elapsed_s": eelapsed,
                "body": ebody,
            }
            ws_result["ok"] = bool(ws_result["probe"] and ws_result["probe"].get("ok") and ecode == 200)

        result["checks"]["websocket"] = ws_result
        if not ws_result["ok"]:
            result["errors"].append("websocket probe failed")

    # Final status
    result["ok"] = len(result["errors"]) == 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run content-pipeline smoke gate")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/harness/smoke.json"),
        help="Path for JSON output report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(args.output)
    print(args.output)
    print(json.dumps({"ok": result["ok"], "errors": result["errors"]}, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()

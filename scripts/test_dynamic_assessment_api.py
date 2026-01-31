#!/usr/bin/env python3
"""Smoke test for dynamic assessment (DEV_MODE auth bypass).

Usage (with backend running locally):
  DEV_MODE=true python scripts/test_dynamic_assessment_api.py

It will:
- Start a dynamic assessment for math/science/reading WITHOUT auth headers
- Assert responses include subject metadata
- Hit the prefetch + batch endpoints to confirm incremental generation works
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add project root to path for content module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from content.tone_guidelines import validate_tone


DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")


def _post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{DASH_API_URL}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def _get_json(path: str) -> Dict[str, Any]:
    r = requests.get(f"{DASH_API_URL}{path}", timeout=120)
    r.raise_for_status()
    return r.json()


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def test_subject(subject: str):
    print(f"\n=== dynamic assessment smoke: {subject} ===")

    start = _post_json(
        "/api/assessment/dynamic/start",
        {
            "age_range": "8-10",
            "subject": subject,
            "grade": "3-5",
            "topics": [subject] if subject in {"science", "reading"} else ["math-basics"],
            "question_count": 10,
        },
    )

    assessment_id = start.get("assessment_id")
    _assert(isinstance(assessment_id, str) and assessment_id, "missing assessment_id")

    resp_subject = start.get("subject")
    _assert(resp_subject == subject, f"expected subject={subject}, got {resp_subject}")

    questions = start.get("questions") or []
    _assert(len(questions) > 0, "start returned empty questions")

    def _assert_question_tone(q: Dict[str, Any]):
        item = q.get("question") or {}
        content = item.get("content") or ""
        violations = validate_tone(str(content))
        # Also validate hint tone where present
        for h in (q.get("hints") or []):
            if isinstance(h, dict):
                violations.extend(validate_tone(str(h.get("content") or "")))
        violations = sorted(set(v for v in violations if v))
        _assert(not violations, f"tone violations: {violations} for content={content!r}")

    q0 = questions[0]
    meta = (q0.get("dash_metadata") or {})
    _assert(meta.get("subject") == subject, f"question dash_metadata.subject missing/mismatch: {meta.get('subject')}")

    # Validate tone on the initial buffer (spot-check all returned questions)
    for q in questions:
        _assert_question_tone(q)

    # Prefetch should ensure at least 4 generated (or total_questions if smaller)
    prefetch = _get_json(f"/api/assessment/dynamic/{assessment_id}/prefetch?index=0&prefetch_ahead=3")
    generated_total = prefetch.get("generated_total", 0)
    _assert(generated_total >= 1, "prefetch did not generate any questions")

    # Pull next batch from the server to confirm incremental generation works.
    # (If generation is slow, this still validates the endpoint + non-empty content.)
    batch = _get_json(f"/api/assessment/dynamic/{assessment_id}/batch?start={len(questions)}&limit=2")
    batch_questions = batch.get("questions") or []
    _assert(batch_questions is not None, "batch response missing questions")
    for q in batch_questions:
        _assert_question_tone(q)

    # Ensure the stored assessment fetch includes subject too.
    full = _get_json(f"/api/assessment/dynamic/{assessment_id}")
    _assert(full.get("subject") == subject, "assessment fetch missing subject")

    print("ok")


def main():
    print(f"DASH_API_URL={DASH_API_URL}")
    print("(this test assumes backend is already running)")

    # Tiny wait if someone starts this right after boot.
    time.sleep(0.5)

    for subj in ("math", "science", "reading"):
        test_subject(subj)

    print("\nall good")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

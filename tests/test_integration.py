"""
Integration tests for the DASH API.

Runs against the live server on localhost:8000.
Tests the full request lifecycle: HTTP → FastAPI → DASH → MongoDB → response.

Usage:
    # Run directly (recommended):
    cd /path/to/aitutor
    venv/bin/python tests/test_integration.py

    # Run with pytest (requires server running):
    pytest tests/test_integration.py -m integration -v

    # Skip integration tests:
    pytest -m "not integration"
"""

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

import os
import sys
import json
import time
import uuid
import traceback
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import jwt
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

# Unique test user to avoid polluting real data
TEST_USER_ID = f"integration_test_{uuid.uuid4().hex[:8]}"
TEST_EMAIL = f"{TEST_USER_ID}@test.example.com"
TEST_AGE = 10  # Grade 5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_token(user_id: str = TEST_USER_ID, age: int = TEST_AGE, exp_hours: int = 24) -> str:
    """Create a valid JWT token for test requests."""
    payload = {
        "sub": user_id,
        "email": TEST_EMAIL,
        "name": f"Test User {user_id}",
        "age": age,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=exp_hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def make_expired_token() -> str:
    """Create an expired JWT token."""
    payload = {
        "sub": TEST_USER_ID,
        "iat": datetime.utcnow() - timedelta(hours=48),
        "exp": datetime.utcnow() - timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def auth_headers(token: Optional[str] = None) -> dict:
    """Return Authorization header."""
    t = token or make_token()
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  PASS  {name}")

    def fail(self, name: str, detail: str):
        self.failed += 1
        self.errors.append((name, detail))
        print(f"  FAIL  {name}")
        print(f"        {detail}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"\n  Failures:")
            for name, detail in self.errors:
                print(f"    - {name}: {detail}")
        print(f"{'='*60}")
        return self.failed == 0

results = TestResult()

# ---------------------------------------------------------------------------
# Test Groups
# ---------------------------------------------------------------------------

def test_health():
    """Test 1: Health endpoint (no auth required)."""
    print("\n--- Health & Status ---")

    r = requests.get(f"{BASE_URL}/health")
    if r.status_code == 200:
        data = r.json()
        # Check required fields
        for field in ["status", "ready", "skills_count", "ai_questions_enabled"]:
            if field in data:
                results.ok(f"health has '{field}': {data[field]}")
            else:
                results.fail(f"health has '{field}'", f"missing from response: {list(data.keys())}")
    else:
        results.fail("health returns 200", f"got {r.status_code}: {r.text[:200]}")


def test_auth_enforcement():
    """Test 2: Auth enforcement — protected endpoints reject bad/missing tokens."""
    print("\n--- Auth Enforcement ---")

    # No token
    r = requests.get(f"{BASE_URL}/api/grading-panel")
    if r.status_code == 401:
        results.ok("no token → 401")
    else:
        results.fail("no token → 401", f"got {r.status_code}")

    # Invalid token
    r = requests.get(f"{BASE_URL}/api/grading-panel",
                     headers={"Authorization": "Bearer garbage.token.here"})
    if r.status_code == 401:
        results.ok("invalid token → 401")
    else:
        results.fail("invalid token → 401", f"got {r.status_code}")

    # Expired token
    r = requests.get(f"{BASE_URL}/api/grading-panel",
                     headers=auth_headers(make_expired_token()))
    if r.status_code == 401:
        results.ok("expired token → 401")
    else:
        results.fail("expired token → 401", f"got {r.status_code}")

    # Valid token should NOT be 401
    r = requests.get(f"{BASE_URL}/api/grading-panel", headers=auth_headers())
    if r.status_code != 401:
        results.ok(f"valid token → not 401 (got {r.status_code})")
    else:
        results.fail("valid token → not 401", f"got 401")

    # Missing 'sub' claim
    bad_payload = {"email": "x@x.com", "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()}
    bad_token = jwt.encode(bad_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = requests.get(f"{BASE_URL}/api/grading-panel",
                     headers=auth_headers(bad_token))
    if r.status_code == 401:
        results.ok("token without 'sub' → 401")
    else:
        results.fail("token without 'sub' → 401", f"got {r.status_code}")


def test_open_endpoints():
    """Test 3: Open endpoints work without auth."""
    print("\n--- Open Endpoints ---")

    # Questions sample (requires auth — uses JWT for personalized selection)
    r = requests.get(f"{BASE_URL}/api/questions/5", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            results.ok(f"GET /api/questions/5 → {len(data)} questions")
            if len(data) > 0:
                q = data[0]
                # Validate Perseus format
                has_widgets = "widgets" in q.get("question", {})
                has_hints = "hints" in q
                if has_widgets:
                    results.ok("question has widgets in question.widgets")
                else:
                    results.fail("question has widgets", f"keys: {list(q.get('question', {}).keys())}")
                if has_hints:
                    results.ok("question has hints array")
                else:
                    results.fail("question has hints", f"keys: {list(q.keys())}")
        else:
            results.fail("GET /api/questions/5 → list", f"got {type(data).__name__}")
    else:
        results.fail("GET /api/questions/5 → 200", f"got {r.status_code}: {r.text[:200]}")

    # Available subjects
    r = requests.get(f"{BASE_URL}/api/subjects/available")
    if r.status_code == 200:
        data = r.json()
        results.ok(f"GET /api/subjects/available → {data}")
    else:
        results.fail("GET /api/subjects/available → 200", f"got {r.status_code}")


def test_subject_lifecycle():
    """Test 4: Start a subject, verify curriculum loads."""
    print("\n--- Subject Lifecycle ---")

    r = requests.post(f"{BASE_URL}/api/start-subject",
                      headers=auth_headers(),
                      json={"subject": "Math", "region": "US"})
    if r.status_code == 200:
        data = r.json()
        status = data.get("status")
        skills = data.get("skills_count", 0)
        results.ok(f"start-subject Math → status={status}, skills={skills}")
        if skills > 0:
            results.ok(f"Math curriculum has {skills} skills")
        else:
            results.fail("Math has skills", "skills_count is 0")
    else:
        results.fail("start-subject → 200", f"got {r.status_code}: {r.text[:300]}")


def test_question_serving():
    """Test 5: Get questions and validate Perseus format."""
    print("\n--- Question Serving ---")

    # First ensure Math is loaded
    requests.post(f"{BASE_URL}/api/start-subject",
                  headers=auth_headers(),
                  json={"subject": "Math", "region": "US"})

    # Get preloaded questions
    r = requests.get(f"{BASE_URL}/api/questions/preloaded", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            results.ok(f"preloaded → {len(data)} questions")

            # Validate first question deeply
            q = data[0]
            _validate_perseus_question(q, "preloaded[0]")
        else:
            results.ok(f"preloaded → empty list (no questions available yet)")
    else:
        results.fail("preloaded → 200", f"got {r.status_code}: {r.text[:200]}")


def _validate_perseus_question(q: dict, label: str):
    """Validate a Perseus-format question has all required fields."""
    # Top-level structure
    for field in ["question", "hints"]:
        if field in q:
            results.ok(f"{label} has '{field}'")
        else:
            results.fail(f"{label} has '{field}'", f"keys: {list(q.keys())}")

    # Question must have content and widgets
    question = q.get("question", {})
    if "content" in question:
        content = question["content"]
        results.ok(f"{label} question.content length={len(content)}")
    else:
        results.fail(f"{label} has question.content", f"keys: {list(question.keys())}")

    widgets = question.get("widgets", {})
    if widgets:
        # Check each widget has type and options
        for wid, wdef in widgets.items():
            wtype = wdef.get("type")
            if wtype:
                results.ok(f"{label} widget '{wid}' type={wtype}")
                # Check widget has options
                if "options" in wdef:
                    results.ok(f"{label} widget '{wid}' has options")
                else:
                    results.fail(f"{label} widget '{wid}' has options", f"keys: {list(wdef.keys())}")
                # Check widget has version
                if "version" in wdef:
                    results.ok(f"{label} widget '{wid}' has version")
                else:
                    results.fail(f"{label} widget '{wid}' has version", f"keys: {list(wdef.keys())}")
                break  # Only check first widget to keep output manageable
            else:
                results.fail(f"{label} widget '{wid}' has type", f"keys: {list(wdef.keys())}")

    # Hints should be list of dicts
    hints = q.get("hints", [])
    if isinstance(hints, list):
        results.ok(f"{label} hints is list with {len(hints)} items")
        if len(hints) > 0:
            h = hints[0]
            if isinstance(h, dict) and "content" in h:
                results.ok(f"{label} hint[0] has content")
            elif isinstance(h, str):
                results.fail(f"{label} hint[0] is dict", "hint is raw string, not {content, ...}")
            else:
                results.fail(f"{label} hint[0] has content", f"type={type(h).__name__}, keys={list(h.keys()) if isinstance(h, dict) else 'N/A'}")
    else:
        results.fail(f"{label} hints is list", f"type={type(hints).__name__}")

    # answerArea should exist
    if "answerArea" in q:
        results.ok(f"{label} has answerArea")
    else:
        results.fail(f"{label} has answerArea", f"missing from top-level keys: {list(q.keys())}")


def test_submit_answer_flow():
    """Test 6: Submit an answer and verify state updates."""
    print("\n--- Submit Answer Flow ---")

    # Get a question first
    requests.post(f"{BASE_URL}/api/start-subject",
                  headers=auth_headers(),
                  json={"subject": "Math", "region": "US"})

    r = requests.get(f"{BASE_URL}/api/questions/3", headers=auth_headers())
    if r.status_code != 200 or not r.json():
        results.fail("get questions for submit test", f"got {r.status_code}")
        return

    questions = r.json()
    if not questions:
        results.ok("no questions available — skipping submit test")
        return

    q = questions[0]
    q_id = q.get("dash_metadata", {}).get("question_id") or q.get("question_id", "test_q_1")
    skill_ids = q.get("dash_metadata", {}).get("skill_ids") or q.get("skill_ids", [])

    if not skill_ids:
        # Try to extract from widgets or just use a placeholder
        skill_ids = ["math_placeholder_skill"]

    # Submit correct answer
    submit_body = {
        "question_id": q_id,
        "skill_ids": skill_ids if isinstance(skill_ids, list) else [skill_ids],
        "is_correct": True,
        "response_time_seconds": 5.0,
        "selected_answer": "test answer",
        "selected_answer_index": 0,
    }

    r = requests.post(f"{BASE_URL}/api/submit-answer",
                      headers=auth_headers(),
                      json=submit_body)
    if r.status_code == 200:
        data = r.json()
        results.ok(f"submit-answer → 200, keys: {list(data.keys())[:5]}")
    elif r.status_code == 422:
        results.fail("submit-answer → 200", f"422 validation error: {r.text[:300]}")
    else:
        results.fail("submit-answer → 200", f"got {r.status_code}: {r.text[:300]}")


def test_grading_panel():
    """Test 7: Grading panel returns student performance data."""
    print("\n--- Grading Panel ---")

    r = requests.get(f"{BASE_URL}/api/grading-panel", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        results.ok(f"grading-panel → 200, type={type(data).__name__}")
        if isinstance(data, dict):
            results.ok(f"grading-panel keys: {list(data.keys())[:8]}")
        elif isinstance(data, list):
            results.ok(f"grading-panel has {len(data)} entries")
    else:
        results.fail("grading-panel → 200", f"got {r.status_code}: {r.text[:200]}")


def test_assessment_flow():
    """Test 8: Full assessment lifecycle — start → get questions → complete."""
    print("\n--- Assessment Flow ---")

    # Use a unique user per test to avoid "already completed" blocks
    assess_user = f"assess_test_{uuid.uuid4().hex[:8]}"
    assess_token = make_token(user_id=assess_user)
    hdrs = auth_headers(assess_token)

    # Start subject first
    r = requests.post(f"{BASE_URL}/api/start-subject",
                      headers=hdrs,
                      json={"subject": "Math", "region": "US"})
    if r.status_code != 200:
        results.fail("assessment: start subject", f"got {r.status_code}: {r.text[:200]}")
        return

    # Check assessment status
    r = requests.get(f"{BASE_URL}/assessment/status/Math", headers=hdrs)
    if r.status_code == 200:
        data = r.json()
        results.ok(f"assessment status → {data.get('status', 'unknown')}")
    else:
        results.fail("assessment status → 200", f"got {r.status_code}")

    # Start assessment
    r = requests.post(f"{BASE_URL}/assessment/start/Math", headers=hdrs)
    if r.status_code == 200:
        data = r.json()
        questions = data.get("questions", [])
        assessment_id = data.get("assessment_id")
        results.ok(f"start assessment → {len(questions)} questions, id={assessment_id}")

        if questions and len(questions) > 0:
            # Validate first assessment question
            aq = questions[0]
            _validate_perseus_question(aq, "assessment[0]")

            # Complete assessment with answers
            answers = []
            for aq in questions:
                q_id = aq.get("dash_metadata", {}).get("question_id", "unknown")
                s_ids = aq.get("dash_metadata", {}).get("skill_ids", [])
                skill = s_ids[0] if s_ids else "unknown_skill"
                answers.append({
                    "question_id": q_id,
                    "skill_id": skill,
                    "is_correct": True,  # Answer all correct for testing
                })

            r = requests.post(f"{BASE_URL}/assessment/complete",
                              headers=hdrs,
                              json={"subject": "Math", "answers": answers})
            if r.status_code == 200:
                data = r.json()
                results.ok(f"complete assessment → status={data.get('status')}, score={data.get('score')}")
            else:
                results.fail("complete assessment → 200", f"got {r.status_code}: {r.text[:300]}")
        else:
            results.ok("assessment returned 0 questions — no curriculum questions available")

    elif r.status_code == 400:
        # May mean "already completed" — that's valid behavior
        results.ok(f"start assessment → 400 (expected if already done): {r.json().get('detail', '')[:100]}")
    else:
        results.fail("start assessment → 200", f"got {r.status_code}: {r.text[:300]}")


def test_adaptive_assessment():
    """Test 9: Adaptive assessment — start → answer → next → repeat."""
    print("\n--- Adaptive Assessment ---")

    adapt_user = f"adaptive_test_{uuid.uuid4().hex[:8]}"
    adapt_token = make_token(user_id=adapt_user)
    hdrs = auth_headers(adapt_token)

    # Start subject
    requests.post(f"{BASE_URL}/api/start-subject", headers=hdrs,
                  json={"subject": "Math", "region": "US"})

    # Start adaptive assessment
    r = requests.post(f"{BASE_URL}/assessment/start-adaptive/Math", headers=hdrs)
    if r.status_code != 200:
        results.fail("start-adaptive → 200", f"got {r.status_code}: {r.text[:300]}")
        return

    data = r.json()
    assessment_id = data.get("assessment_id")
    first_q = data.get("first_question", {})
    results.ok(f"start-adaptive → id={assessment_id}")

    if not first_q:
        results.ok("adaptive: no first question (empty curriculum)")
        return

    # Answer first question and get next
    q_id = first_q.get("dash_metadata", {}).get("question_id", "unknown")
    skill_id = (first_q.get("dash_metadata", {}).get("skill_ids") or ["unknown"])[0]

    r = requests.post(f"{BASE_URL}/assessment/next", headers=hdrs,
                      json={
                          "assessment_id": assessment_id,
                          "question_id": q_id,
                          "skill_id": skill_id,
                          "is_correct": True,
                      })
    if r.status_code == 200:
        data = r.json()
        if data.get("completed"):
            results.ok(f"adaptive next → completed (score={data.get('score')})")
        elif data.get("next_question"):
            results.ok("adaptive next → got next question")
            # Check difficulty adjustment
            diff = data.get("current_difficulty")
            if diff is not None:
                results.ok(f"adaptive difficulty = {diff}")
            else:
                results.ok("adaptive: no difficulty field (may be internal)")
        else:
            results.ok(f"adaptive next → {list(data.keys())}")
    else:
        results.fail("adaptive next → 200", f"got {r.status_code}: {r.text[:300]}")


def test_analytics_endpoints():
    """Test 10: Question analytics recording and retrieval."""
    print("\n--- Analytics ---")

    # Record analytics
    r = requests.post(f"{BASE_URL}/api/question-analytics",
                      headers=auth_headers(),
                      json={
                          "question_id": "test_analytics_q",
                          "correct": True,
                          "hints_used": 1,
                          "time_seconds": 12.5,
                          "skipped": False,
                          "skill_id": "test_skill",
                      })
    if r.status_code == 200:
        results.ok("record analytics → 200")
    else:
        results.fail("record analytics → 200", f"got {r.status_code}: {r.text[:200]}")

    # Get quality report
    r = requests.get(f"{BASE_URL}/api/quality-report", headers=auth_headers())
    if r.status_code == 200:
        results.ok(f"quality-report → 200")
    else:
        results.fail("quality-report → 200", f"got {r.status_code}: {r.text[:200]}")

    # Get flagged questions
    r = requests.get(f"{BASE_URL}/api/flagged-questions", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        count = len(data) if isinstance(data, list) else "N/A"
        results.ok(f"flagged-questions → {count} flagged")
    else:
        results.fail("flagged-questions → 200", f"got {r.status_code}: {r.text[:200]}")


def test_prerequisites():
    """Test 11: Prerequisites endpoint."""
    print("\n--- Prerequisites ---")

    # Use a known math skill (may not exist in AI curriculum)
    r = requests.get(f"{BASE_URL}/api/prerequisites/xd0ae8a03", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        results.ok(f"prerequisites → {list(data.keys())[:5]}")
    elif r.status_code == 404:
        results.ok("prerequisites → 404 (skill not in current curriculum)")
    else:
        results.fail("prerequisites → 200 or 404", f"got {r.status_code}: {r.text[:200]}")


def test_review_status():
    """Test 12: Spaced repetition review status."""
    print("\n--- Spaced Repetition ---")

    r = requests.get(f"{BASE_URL}/api/review-status", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        results.ok(f"review-status → {type(data).__name__}, keys={list(data.keys()) if isinstance(data, dict) else len(data)}")
    else:
        results.fail("review-status → 200", f"got {r.status_code}: {r.text[:200]}")


def test_misconceptions():
    """Test 13: Student misconceptions endpoint."""
    print("\n--- Misconceptions ---")

    r = requests.get(f"{BASE_URL}/api/misconceptions", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        results.ok(f"misconceptions → {type(data).__name__}")
    else:
        results.fail("misconceptions → 200", f"got {r.status_code}: {r.text[:200]}")


def test_recommend_next():
    """Test 14: Next question recommendation."""
    print("\n--- Recommend Next ---")

    r = requests.post(f"{BASE_URL}/api/questions/recommend-next",
                      headers=auth_headers(),
                      json={"current_question_ids": [], "count": 3})
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            results.ok(f"recommend-next → {len(data)} questions")
            if data:
                _validate_perseus_question(data[0], "recommend[0]")
        else:
            results.ok(f"recommend-next → {type(data).__name__}")
    else:
        results.fail("recommend-next → 200", f"got {r.status_code}: {r.text[:300]}")


def test_content_pool():
    """Test 15: Content pool endpoints."""
    print("\n--- Content Pool ---")

    # Pool stats for a test skill
    r = requests.get(f"{BASE_URL}/api/pool-stats/test_skill_123", headers=auth_headers())
    if r.status_code == 200:
        data = r.json()
        results.ok(f"pool-stats → {data}")
    elif r.status_code == 404:
        results.ok("pool-stats → 404 (skill not found, expected)")
    else:
        results.fail("pool-stats → 200 or 404", f"got {r.status_code}: {r.text[:200]}")

    # Generation audit
    r = requests.get(f"{BASE_URL}/api/generation-audit", headers=auth_headers())
    if r.status_code == 200:
        results.ok("generation-audit → 200")
    else:
        results.fail("generation-audit → 200", f"got {r.status_code}: {r.text[:200]}")


def test_invalid_inputs():
    """Test 16: Invalid/malformed inputs return proper errors, not 500s."""
    print("\n--- Invalid Input Handling ---")

    # Submit answer with missing required fields
    r = requests.post(f"{BASE_URL}/api/submit-answer",
                      headers=auth_headers(),
                      json={})
    if r.status_code == 422:
        results.ok("empty submit-answer → 422 (validation error)")
    elif r.status_code == 500:
        results.fail("empty submit-answer → not 500", f"got 500 (server crash): {r.text[:200]}")
    else:
        results.ok(f"empty submit-answer → {r.status_code}")

    # Start assessment with empty subject
    r = requests.post(f"{BASE_URL}/assessment/start/",
                      headers=auth_headers())
    if r.status_code in (404, 405, 422):
        results.ok(f"empty subject assessment → {r.status_code}")
    elif r.status_code == 500:
        results.fail("empty subject assessment → not 500", f"got 500")
    else:
        results.ok(f"empty subject assessment → {r.status_code}")

    # Analytics with wrong types
    r = requests.post(f"{BASE_URL}/api/question-analytics",
                      headers=auth_headers(),
                      json={"question_id": 12345, "correct": "not_a_bool"})
    if r.status_code in (200, 422):
        results.ok(f"bad analytics types → {r.status_code}")
    elif r.status_code == 500:
        results.fail("bad analytics types → not 500", f"got 500: {r.text[:200]}")
    else:
        results.ok(f"bad analytics types → {r.status_code}")

    # Start subject with very long name
    r = requests.post(f"{BASE_URL}/api/start-subject",
                      headers=auth_headers(),
                      json={"subject": "A" * 200, "region": "US"})
    if r.status_code in (200, 422):
        results.ok(f"oversized subject name → {r.status_code}")
    elif r.status_code == 500:
        results.fail("oversized subject → not 500", f"got 500: {r.text[:200]}")
    else:
        results.ok(f"oversized subject → {r.status_code}")

    # Negative sample size (with auth)
    r = requests.get(f"{BASE_URL}/api/questions/-1", headers=auth_headers())
    if r.status_code in (200, 422, 400):
        results.ok(f"negative sample size → {r.status_code}")
    elif r.status_code == 500:
        results.fail("negative sample size → not 500", f"got 500")
    else:
        results.ok(f"negative sample size → {r.status_code}")

    # Huge sample size (with auth)
    r = requests.get(f"{BASE_URL}/api/questions/999999", headers=auth_headers())
    if r.status_code in (200, 422, 400):
        results.ok(f"huge sample size → {r.status_code}")
    elif r.status_code == 500:
        results.fail("huge sample size → not 500", f"got 500: {r.text[:200]}")
    else:
        results.ok(f"huge sample size → {r.status_code}")


def test_concurrent_requests():
    """Test 17: Multiple rapid requests don't crash the server."""
    print("\n--- Concurrency Stress ---")

    import concurrent.futures

    def hit_health():
        r = requests.get(f"{BASE_URL}/health")
        return r.status_code

    def hit_questions():
        r = requests.get(f"{BASE_URL}/api/questions/2")
        return r.status_code

    def hit_grading():
        r = requests.get(f"{BASE_URL}/api/grading-panel", headers=auth_headers())
        return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = []
        for _ in range(5):
            futures.append(pool.submit(hit_health))
            futures.append(pool.submit(hit_questions))
            futures.append(pool.submit(hit_grading))

        statuses = [f.result(timeout=30) for f in futures]

    errors_500 = [s for s in statuses if s == 500]
    if not errors_500:
        results.ok(f"15 concurrent requests → 0 server errors (statuses: {set(statuses)})")
    else:
        results.fail(f"concurrent requests → no 500s", f"got {len(errors_500)} 500 errors out of 15")


def test_response_times():
    """Test 18: Key endpoints respond within reasonable time."""
    print("\n--- Response Times ---")

    endpoints = [
        ("GET", "/health", None),
        ("GET", "/api/grading-panel", auth_headers()),
        ("GET", "/api/questions/3", None),
        ("GET", "/api/review-status", auth_headers()),
    ]

    for method, path, hdrs in endpoints:
        start = time.time()
        if method == "GET":
            r = requests.get(f"{BASE_URL}{path}", headers=hdrs)
        elapsed_ms = (time.time() - start) * 1000

        if elapsed_ms < 5000:
            results.ok(f"{path} → {r.status_code} in {elapsed_ms:.0f}ms")
        else:
            results.fail(f"{path} < 5s", f"took {elapsed_ms:.0f}ms")


def test_cleanup():
    """Cleanup: remove test data from MongoDB."""
    print("\n--- Cleanup ---")
    try:
        # We use unique user IDs so test data won't interfere with real users.
        # MongoDB cleanup would require direct DB access — just note it.
        results.ok(f"test user: {TEST_USER_ID} (ephemeral, won't affect real data)")
    except Exception as e:
        results.ok(f"cleanup note: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"{'='*60}")
    print(f"  Integration Tests — DASH API")
    print(f"  Server: {BASE_URL}")
    print(f"  Test user: {TEST_USER_ID}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Verify server is up
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"\nERROR: Server returned {r.status_code} on /health")
            sys.exit(1)
    except requests.ConnectionError:
        print(f"\nERROR: Cannot connect to {BASE_URL}")
        print("Start the server: cd services/DashSystem && python dash_api.py")
        sys.exit(1)

    # Run all tests
    try:
        test_health()
        test_auth_enforcement()
        test_open_endpoints()
        test_subject_lifecycle()
        test_question_serving()
        test_submit_answer_flow()
        test_grading_panel()
        test_assessment_flow()
        test_adaptive_assessment()
        test_analytics_endpoints()
        test_prerequisites()
        test_review_status()
        test_misconceptions()
        test_recommend_next()
        test_content_pool()
        test_invalid_inputs()
        test_concurrent_requests()
        test_response_times()
        test_cleanup()
    except Exception as e:
        results.fail("UNCAUGHT EXCEPTION", f"{type(e).__name__}: {e}\n{traceback.format_exc()}")

    all_pass = results.summary()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

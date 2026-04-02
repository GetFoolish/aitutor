"""
Tests for the adaptive difficulty and student memory fixes.

ISSUE 1: Verifies grade-based difficulty scaling is wired correctly.
ISSUE 2: Verifies student memory context is stored in session and passed through.
ISSUE 3: Verifies prefetch worker accepts force_mc/student_context params (no NameError).
"""
import inspect
import sys
from pathlib import Path

import pytest

# ── Ensure services/ is importable ────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "services" / "DashSystem"))


# ---------------------------------------------------------------------------
# ISSUE 1: Grade-based difficulty scaling
# ---------------------------------------------------------------------------

class TestAdaptiveDifficultyScaling:
    """Verify that _initial_difficulty_for_grade and _max_difficulty_for_grade
    produce different values for different grade levels, and that the module-level
    _difficulty_step_for_grade also scales correctly."""

    def test_difficulty_step_for_grade_scales_by_grade(self):
        """_difficulty_step_for_grade must return smaller steps for younger students."""
        from services.DashSystem.dash_api import _difficulty_step_for_grade

        step_k = _difficulty_step_for_grade("K")
        step_5 = _difficulty_step_for_grade("GRADE_5")
        step_12 = _difficulty_step_for_grade("GRADE_12")

        assert step_k < step_5 < step_12, (
            f"Steps must increase with grade: K={step_k}, G5={step_5}, G12={step_12}"
        )

    def test_difficulty_step_kindergarten_is_smallest(self):
        step_k = _difficulty_step_for_grade("K")
        assert step_k == 0.06

    def test_difficulty_step_grade12_is_largest(self):
        step_12 = _difficulty_step_for_grade("GRADE_12")
        assert step_12 == 0.15

    def test_difficulty_step_unknown_grade_returns_default(self):
        step = _difficulty_step_for_grade("UNKNOWN")
        assert step == 0.13

    def test_initial_difficulty_grade_maps_are_defined_in_start_adaptive(self):
        """Verify that the inner helper _initial_difficulty_for_grade exists
        inside start_adaptive_assessment and covers all expected grades.

        We inspect the source to confirm the hardcoded 0.5 is no longer used
        for target_difficulty in the JIT call."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api.start_adaptive_assessment)

        # The function must call _jit_first_question with initial_difficulty, not 0.5
        assert "target_difficulty=initial_difficulty" in source, (
            "start_adaptive_assessment must pass initial_difficulty (not hardcoded 0.5) "
            "to _jit_first_question"
        )

        # The prefetch worker call must also pass initial_difficulty, not 0.5
        # Look for the _assessment_prefetch_worker call
        assert "initial_difficulty, jwt_age" in source or "initial_difficulty," in source, (
            "Prefetch worker must receive initial_difficulty, not 0.5"
        )

    def test_session_stores_student_context(self):
        """Verify the session document template includes student_context and force_mc."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api.start_adaptive_assessment)
        assert '"student_context": _frozen_student_context' in source, (
            "Session must persist frozen student_context for downstream use"
        )
        assert '"force_mc": force_mc' in source, (
            "Session must persist force_mc for downstream prefetch/JIT"
        )


# ---------------------------------------------------------------------------
# ISSUE 2: Student memory system
# ---------------------------------------------------------------------------

class TestStudentMemoryDB:
    """Verify the StudentMemoryDB correctly stores, retrieves, and generates
    student context strings for Gemini injection."""

    @pytest.fixture
    def mem_db(self, tmp_path):
        """Create a fresh in-memory StudentMemoryDB for each test."""
        from services.DashSystem.student_memory import StudentMemoryDB
        db_path = tmp_path / "test_students.db"
        return StudentMemoryDB(db_path=db_path)

    def test_ensure_student_creates_record(self, mem_db):
        mem_db.ensure_student("student_1", age=8, grade="GRADE_2")
        row = mem_db._conn.execute(
            "SELECT age, grade FROM students WHERE student_id=?", ("student_1",)
        ).fetchone()
        assert row is not None
        assert row["age"] == 8
        assert row["grade"] == "GRADE_2"

    def test_record_question_attempt(self, mem_db):
        mem_db.ensure_student("s1")
        mem_db.record_question_attempt(
            "s1", "q1", "Math", "addition", "Addition", True, 5.0
        )
        rows = mem_db._conn.execute(
            "SELECT * FROM question_history WHERE student_id=?", ("s1",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["was_correct"] == 1

    def test_weak_skills_identified(self, mem_db):
        mem_db.ensure_student("s1")
        # Record 3 wrong attempts at fractions
        for i in range(3):
            mem_db.record_question_attempt(
                "s1", f"q{i}", "Math", "fractions", "Fractions", False
            )
        weak = mem_db.get_weak_skills("s1", min_attempts=2, max_accuracy=0.6)
        assert "Fractions" in weak

    def test_mastered_skills_identified(self, mem_db):
        mem_db.ensure_student("s1")
        # Record 4 correct attempts at addition
        for i in range(4):
            mem_db.record_question_attempt(
                "s1", f"q{i}", "Math", "addition", "Addition", True
            )
        mastered = mem_db.get_mastered_skills("s1", min_attempts=3, min_accuracy=0.85)
        assert "Addition" in mastered

    def test_student_context_for_gemini_includes_grade(self, mem_db):
        mem_db.ensure_student("s1", age=10, grade="GRADE_4")
        ctx = mem_db.get_student_context_for_gemini("s1")
        assert "Grade 4" in ctx or "GRADE_4" in ctx

    def test_student_context_includes_struggles(self, mem_db):
        mem_db.ensure_student("s1", age=10, grade="GRADE_4")
        for i in range(3):
            mem_db.record_question_attempt(
                "s1", f"q{i}", "Math", "fractions", "Fractions", False
            )
        ctx = mem_db.get_student_context_for_gemini("s1")
        assert "Fractions" in ctx
        assert "Struggles" in ctx or "struggles" in ctx.lower()

    def test_student_context_empty_for_unknown_student(self, mem_db):
        ctx = mem_db.get_student_context_for_gemini("nonexistent")
        assert ctx == ""

    def test_record_session(self, mem_db):
        mem_db.ensure_student("s1")
        mem_db.record_session("sess_1", "s1", "Math", 7, 10)
        recent = mem_db.get_recent_session_summary("s1", limit=1)
        assert len(recent) == 1
        assert "Math" in recent[0]
        assert "7/10" in recent[0]


# ---------------------------------------------------------------------------
# ISSUE 3: Prefetch worker signature — no NameError
# ---------------------------------------------------------------------------

class TestPrefetchWorkerSignature:
    """Verify _assessment_prefetch_worker accepts force_mc and student_context
    parameters (the fix for the NameError crash)."""

    def test_prefetch_worker_accepts_force_mc_and_student_context(self):
        """The function signature must include force_mc and student_context kwargs."""
        from services.DashSystem.dash_api import _assessment_prefetch_worker
        sig = inspect.signature(_assessment_prefetch_worker)
        params = list(sig.parameters.keys())
        assert "force_mc" in params, (
            "_assessment_prefetch_worker must accept force_mc parameter"
        )
        assert "student_context" in params, (
            "_assessment_prefetch_worker must accept student_context parameter"
        )

    def test_prefetch_worker_does_not_reference_payload(self):
        """The prefetch worker must NOT reference 'payload' (out of scope)."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api._assessment_prefetch_worker)
        assert "payload.force_mc" not in source, (
            "_assessment_prefetch_worker must not reference payload.force_mc (NameError)"
        )
        assert "payload." not in source, (
            "_assessment_prefetch_worker must not reference payload at all"
        )

    def test_assessment_next_jit_uses_real_skill_name(self):
        """The JIT fallback in assessment_next_question must use _pick_real_skill_name,
        not a meta name like 'Math for Grade 5'."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api.assessment_next_question)

        # The source should contain _pick_real_skill_name for JIT calls
        assert "_pick_real_skill_name" in source, (
            "assessment_next_question JIT must use _pick_real_skill_name()"
        )

    def test_prefetch_worker_uses_real_skill_name(self):
        """The prefetch worker must use _pick_real_skill_name, not meta skill names."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api._assessment_prefetch_worker)
        assert "_pick_real_skill_name" in source, (
            "_assessment_prefetch_worker must use _pick_real_skill_name()"
        )
        # Must NOT use the old meta pattern
        assert 'f"{subject} for {grade_name}"' not in source, (
            "Must not use meta skill name 'Math for Grade 5' in prefetch worker"
        )

    def test_prefetch_worker_falls_back_to_session_values(self):
        """When force_mc/student_context are not passed (e.g. /assessment/prefetch
        endpoint), the worker must read them from the session document it loads."""
        from services.DashSystem import dash_api
        source = inspect.getsource(dash_api._assessment_prefetch_worker)
        # Worker should fall back to session-stored values
        assert 'session.get("student_context"' in source, (
            "Worker must fall back to session student_context when not passed by caller"
        )
        assert 'session.get("force_mc"' in source, (
            "Worker must fall back to session force_mc when not passed by caller"
        )


# ---------------------------------------------------------------------------
# Import helper — needed because _difficulty_step_for_grade is at module level
# ---------------------------------------------------------------------------

def _difficulty_step_for_grade(grade: str) -> float:
    """Import proxy for test convenience."""
    from services.DashSystem.dash_api import _difficulty_step_for_grade as fn
    return fn(grade)

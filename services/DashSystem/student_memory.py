"""
Student Memory System for Teachr.Live

SQLite-backed persistent memory per student. Captures skill struggles,
learning patterns, and session history so Gemini generates personalized
questions. Frozen at assessment-start (never changes mid-session).

Patterns from hermes_state.py:
- WAL journal mode
- BEGIN IMMEDIATE transactions
- Random jitter retry (20-150ms) on lock contention
- FTS5 on question_history for searchability
"""

import json
import logging
import os
import random
import sqlite3
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(os.path.expanduser("~/.hermes/aitutor_students.db"))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    student_id  TEXT PRIMARY KEY,
    name        TEXT,
    age         INTEGER,
    grade       TEXT,
    created_at  REAL NOT NULL,
    last_seen   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS memory (
    student_id  TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (student_id, key),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,
    student_id          TEXT NOT NULL,
    subject             TEXT NOT NULL,
    score               INTEGER DEFAULT 0,
    questions_correct   INTEGER DEFAULT 0,
    questions_total     INTEGER DEFAULT 0,
    started_at          REAL NOT NULL,
    ended_at            REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS question_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id          TEXT NOT NULL,
    question_id         TEXT NOT NULL,
    subject             TEXT NOT NULL,
    skill               TEXT NOT NULL,
    skill_name          TEXT,
    was_correct         INTEGER NOT NULL,
    response_time_sec   REAL,
    timestamp           REAL NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_student ON memory(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_qh_student ON question_history(student_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_qh_skill ON question_history(student_id, skill, was_correct);

CREATE VIRTUAL TABLE IF NOT EXISTS qh_fts USING fts5(
    skill_name,
    subject,
    content=question_history,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS qh_fts_insert AFTER INSERT ON question_history BEGIN
    INSERT INTO qh_fts(rowid, skill_name, subject) VALUES (new.id, new.skill_name, new.subject);
END;

CREATE TRIGGER IF NOT EXISTS qh_fts_delete AFTER DELETE ON question_history BEGIN
    INSERT INTO qh_fts(qh_fts, rowid, skill_name, subject) VALUES('delete', old.id, old.skill_name, old.subject);
END;
"""

_WRITE_MAX_RETRIES = 15
_WRITE_RETRY_MIN_S = 0.020
_WRITE_RETRY_MAX_S = 0.150
_CHECKPOINT_EVERY_N_WRITES = 50


class StudentMemoryDB:
    """SQLite-backed student memory store. Thread-safe via WAL + jitter retry."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._write_count = 0
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=1.0,
            isolation_level=None,  # manual transaction management
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(SCHEMA_SQL)

    def _execute_write(self, fn):
        """BEGIN IMMEDIATE + jitter retry — same pattern as hermes_state.py."""
        last_err = None
        for attempt in range(_WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    try:
                        result = fn(self._conn)
                        self._conn.commit()
                    except BaseException:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                        raise
                self._write_count += 1
                if self._write_count % _CHECKPOINT_EVERY_N_WRITES == 0:
                    try:
                        self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except Exception:
                        pass
                return result
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                last_err = exc
                sleep_s = random.uniform(_WRITE_RETRY_MIN_S, _WRITE_RETRY_MAX_S)
                time.sleep(sleep_s)
        raise last_err

    # ── Student upsert ────────────────────────────────────────────────────────

    def ensure_student(self, student_id: str, age: int = None, grade: str = None, name: str = None):
        now = time.time()
        def _write(conn):
            conn.execute(
                """INSERT INTO students (student_id, name, age, grade, created_at, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(student_id) DO UPDATE SET
                     last_seen = excluded.last_seen,
                     age = COALESCE(excluded.age, age),
                     grade = COALESCE(excluded.grade, grade),
                     name = COALESCE(excluded.name, name)""",
                (student_id, name, age, grade, now, now),
            )
        self._execute_write(_write)

    # ── Memory keys ──────────────────────────────────────────────────────────

    def set_memory(self, student_id: str, key: str, value: str):
        now = time.time()
        def _write(conn):
            conn.execute(
                """INSERT INTO memory (student_id, key, value, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(student_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (student_id, key, value, now),
            )
        self._execute_write(_write)

    def get_memory(self, student_id: str) -> Dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value FROM memory WHERE student_id = ?", (student_id,)
        ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ── Question attempts ─────────────────────────────────────────────────────

    def record_question_attempt(
        self,
        student_id: str,
        question_id: str,
        subject: str,
        skill: str,
        skill_name: str,
        was_correct: bool,
        response_time_sec: float = None,
    ):
        now = time.time()
        def _write(conn):
            conn.execute(
                """INSERT INTO question_history
                   (student_id, question_id, subject, skill, skill_name, was_correct, response_time_sec, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, question_id, subject, skill, skill_name or skill,
                 1 if was_correct else 0, response_time_sec, now),
            )
        self._execute_write(_write)

    # ── Session record ────────────────────────────────────────────────────────

    def record_session(
        self,
        session_id: str,
        student_id: str,
        subject: str,
        questions_correct: int,
        questions_total: int,
        started_at: float = None,
    ):
        now = time.time()
        score = round(questions_correct / questions_total * 100) if questions_total else 0
        def _write(conn):
            conn.execute(
                """INSERT INTO sessions
                   (session_id, student_id, subject, score, questions_correct, questions_total, started_at, ended_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                     ended_at=excluded.ended_at, score=excluded.score,
                     questions_correct=excluded.questions_correct, questions_total=excluded.questions_total""",
                (session_id, student_id, subject, score, questions_correct, questions_total,
                 started_at or now, now),
            )
        self._execute_write(_write)

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_weak_skills(self, student_id: str, min_attempts: int = 2, max_accuracy: float = 0.6) -> List[str]:
        """Skills where accuracy < max_accuracy across at least min_attempts questions."""
        rows = self._conn.execute(
            """SELECT skill, skill_name,
                      COUNT(*) as attempts,
                      SUM(was_correct) as correct
               FROM question_history
               WHERE student_id = ?
               GROUP BY skill
               HAVING attempts >= ?
               ORDER BY (CAST(correct AS REAL) / attempts) ASC""",
            (student_id, min_attempts),
        ).fetchall()
        return [
            r["skill_name"] or r["skill"]
            for r in rows
            if r["attempts"] > 0 and (r["correct"] / r["attempts"]) < max_accuracy
        ]

    def get_mastered_skills(self, student_id: str, min_attempts: int = 3, min_accuracy: float = 0.85) -> List[str]:
        rows = self._conn.execute(
            """SELECT skill_name, skill,
                      COUNT(*) as attempts,
                      SUM(was_correct) as correct
               FROM question_history
               WHERE student_id = ?
               GROUP BY skill
               HAVING attempts >= ? AND (CAST(correct AS REAL) / attempts) >= ?""",
            (student_id, min_attempts, min_accuracy),
        ).fetchall()
        return [r["skill_name"] or r["skill"] for r in rows]

    def get_recent_session_summary(self, student_id: str, limit: int = 5) -> List[str]:
        """Last N sessions as compact strings like 'Math 3/5'."""
        rows = self._conn.execute(
            """SELECT subject, questions_correct, questions_total
               FROM sessions WHERE student_id = ? AND ended_at IS NOT NULL
               ORDER BY ended_at DESC LIMIT ?""",
            (student_id, limit),
        ).fetchall()
        return [f"{r['subject']} {r['questions_correct']}/{r['questions_total']}" for r in rows]

    # ── Memory snapshot for Gemini ────────────────────────────────────────────

    def get_student_memory_snapshot(self, student_id: str) -> str:
        """Compact text snapshot frozen at session start for Gemini injection."""
        student = self._conn.execute(
            "SELECT grade, age FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        if not student:
            return ""

        parts = []
        if student["grade"]:
            grade = student["grade"].replace("GRADE_", "Grade ").replace("_", " ").title()
            parts.append(grade)
        elif student["age"]:
            parts.append(f"Age {student['age']}")

        weak = self.get_weak_skills(student_id, min_attempts=2)
        if weak:
            parts.append(f"Struggles: {', '.join(weak[:4])}")

        mastered = self.get_mastered_skills(student_id)
        if mastered:
            parts.append(f"Mastered: {', '.join(mastered[:3])}")

        mem = self.get_memory(student_id)
        if mem.get("learning_style"):
            parts.append(f"Works well: {mem['learning_style']}")
        if mem.get("misconceptions"):
            parts.append(f"Common errors: {mem['misconceptions']}")

        recent = self.get_recent_session_summary(student_id, limit=3)
        if recent:
            parts.append(f"Recent: {', '.join(recent)}")

        return " | ".join(parts) if parts else ""

    def get_student_context_for_gemini(self, student_id: str) -> str:
        """Full prompt addition for Gemini question generation."""
        snapshot = self.get_student_memory_snapshot(student_id)
        if not snapshot:
            return ""

        student = self._conn.execute(
            "SELECT grade, age FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        weak = self.get_weak_skills(student_id, min_attempts=2)
        mastered = self.get_mastered_skills(student_id)
        mem = self.get_memory(student_id)

        lines = ["STUDENT CONTEXT:"]

        grade_str = ""
        if student:
            if student["grade"]:
                grade_str = student["grade"].replace("GRADE_", "Grade ").replace("_", " ").title()
            elif student["age"]:
                grade_str = f"Age {student['age']}"
        if grade_str:
            lines.append(f"  Student is in {grade_str}.")

        if weak:
            lines.append(f"  Struggles with: {', '.join(weak[:5])}. Focus on these but keep difficulty achievable.")

        if mastered:
            lines.append(f"  Has mastered: {', '.join(mastered[:4])}. Avoid trivially easy questions on these.")

        if mem.get("learning_style"):
            lines.append(f"  Learns best with: {mem['learning_style']}.")

        if mem.get("misconceptions"):
            lines.append(f"  Common mistake: {mem['misconceptions']}. Design a distractor that targets this.")

        return "\n".join(lines) if len(lines) > 1 else ""

    # ── Post-assessment memory update ─────────────────────────────────────────

    def update_memory_after_assessment(
        self,
        student_id: str,
        subject: str,
        skill_results: List[Dict],  # [{"skill": ..., "skill_name": ..., "is_correct": bool}]
    ):
        """Analyze patterns and update persistent memory keys."""
        if not skill_results:
            return

        wrong_skills = [r["skill_name"] or r["skill"] for r in skill_results if not r["is_correct"]]
        skill_counts = Counter(wrong_skills)
        repeated_struggles = [s for s, c in skill_counts.items() if c >= 1]

        # Update struggles_with
        if repeated_struggles:
            existing = self.get_memory(student_id).get("struggles_with", "")
            existing_list = [s.strip() for s in existing.split(",") if s.strip()] if existing else []
            combined = list(dict.fromkeys(repeated_struggles[:3] + existing_list))[:6]
            self.set_memory(student_id, "struggles_with", ", ".join(combined))

        # Update last_subject_score
        correct = sum(1 for r in skill_results if r["is_correct"])
        total = len(skill_results)
        self.set_memory(student_id, f"last_{subject.lower()}_score", f"{correct}/{total}")


# ── Module-level singleton ────────────────────────────────────────────────────

_db: Optional[StudentMemoryDB] = None
_db_lock = threading.Lock()


def get_student_memory() -> StudentMemoryDB:
    """Return the module-level singleton DB instance (lazy init)."""
    global _db
    if _db is None:
        with _db_lock:
            if _db is None:
                try:
                    _db = StudentMemoryDB()
                    logger.info(f"[STUDENT_MEMORY] Initialized at {_db.db_path}")
                except Exception as e:
                    logger.warning(f"[STUDENT_MEMORY] Init failed: {e} — memory disabled")
                    return None
    return _db


# ── Convenience API (module-level) ────────────────────────────────────────────

def record_question_attempt(
    student_id: str,
    question_id: str,
    subject: str,
    skill: str,
    skill_name: str,
    was_correct: bool,
    response_time_sec: float = None,
):
    db = get_student_memory()
    if db:
        try:
            db.ensure_student(student_id)
            db.record_question_attempt(
                student_id, question_id, subject, skill, skill_name,
                was_correct, response_time_sec
            )
        except Exception as e:
            logger.warning(f"[STUDENT_MEMORY] record_question_attempt failed: {e}")


def record_session(
    session_id: str,
    student_id: str,
    subject: str,
    questions_correct: int,
    questions_total: int,
    started_at: float = None,
):
    db = get_student_memory()
    if db:
        try:
            db.ensure_student(student_id)
            db.record_session(session_id, student_id, subject, questions_correct, questions_total, started_at)
        except Exception as e:
            logger.warning(f"[STUDENT_MEMORY] record_session failed: {e}")


def get_student_context_for_gemini(student_id: str) -> str:
    db = get_student_memory()
    if not db:
        return ""
    try:
        return db.get_student_context_for_gemini(student_id)
    except Exception as e:
        logger.warning(f"[STUDENT_MEMORY] get_student_context_for_gemini failed: {e}")
        return ""


def update_memory_after_assessment(
    student_id: str,
    subject: str,
    skill_results: List[Dict],
):
    db = get_student_memory()
    if db:
        try:
            db.ensure_student(student_id)
            db.update_memory_after_assessment(student_id, subject, skill_results)
        except Exception as e:
            logger.warning(f"[STUDENT_MEMORY] update_memory_after_assessment failed: {e}")

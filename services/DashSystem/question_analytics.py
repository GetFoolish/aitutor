"""
Question Analytics & Quality Scoring System

Tracks per-question performance metrics (correctness rate, hint usage,
skip rate, time-to-solve) and auto-flags low-quality questions.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pymongo import ASCENDING
from pymongo.database import Database

from shared.logging_config import get_logger

logger = get_logger(__name__)


class QuestionAnalytics:
    """Tracks per-question performance and computes quality scores."""

    def __init__(self, db: Database):
        self.collection = db["question_analytics"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for fast lookups."""
        try:
            self.collection.create_index([("question_id", ASCENDING)], unique=True)
            self.collection.create_index([("skill_id", ASCENDING)])
            self.collection.create_index([("flagged", ASCENDING)])
            logger.info("[QUESTION_ANALYTICS] Indexes ensured on question_analytics collection")
        except Exception as e:
            logger.warning(f"[QUESTION_ANALYTICS] Index creation warning: {e}")

    def record_attempt(
        self,
        question_id: str,
        student_id: str,
        correct: bool,
        hints_used: int,
        time_seconds: float,
        skipped: bool,
        skill_id: Optional[str] = None,
    ) -> None:
        """Record an attempt on a question using atomic $inc updates."""
        inc_fields: Dict = {
            "attempt_count": 1,
            "hint_usage_total": hints_used,
            "total_time_seconds": time_seconds,
        }
        if correct:
            inc_fields["correct_count"] = 1
        if skipped:
            inc_fields["skip_count"] = 1

        update: Dict = {
            "$inc": inc_fields,
            "$set": {"updated_at": datetime.utcnow()},
            "$setOnInsert": {
                "question_id": question_id,
                "created_at": datetime.utcnow(),
            },
        }

        if skill_id:
            update["$setOnInsert"]["skill_id"] = skill_id

        update["$addToSet"] = {"student_ids": student_id}

        self.collection.update_one(
            {"question_id": question_id},
            update,
            upsert=True,
        )

        self._update_flagged_status(question_id)

        logger.info(
            f"[QUESTION_ANALYTICS] Recorded attempt: q={question_id} "
            f"correct={correct} hints={hints_used} time={time_seconds:.1f}s skipped={skipped}"
        )

    def _update_flagged_status(self, question_id: str) -> None:
        """Recompute and store the flagged status for a question."""
        doc = self.collection.find_one({"question_id": question_id})
        if not doc:
            return

        attempt_count = doc.get("attempt_count", 0)
        if attempt_count < 3:
            return

        metrics = self._compute_metrics(doc)
        flagged = self._is_flagged(metrics)

        self.collection.update_one(
            {"question_id": question_id},
            {"$set": {"flagged": flagged, "quality_score": metrics.get("quality_score", 0)}},
        )

    def _compute_metrics(self, doc: Dict) -> Dict:
        """Compute quality metrics from a raw analytics document."""
        attempt_count = doc.get("attempt_count", 0)
        if attempt_count == 0:
            return {
                "attempt_count": 0,
                "correctness_rate": 0,
                "skip_rate": 0,
                "avg_time_seconds": 0,
                "avg_hints": 0,
                "unique_students": 0,
                "quality_score": 0,
            }

        correct_count = doc.get("correct_count", 0)
        skip_count = doc.get("skip_count", 0)
        hint_usage_total = doc.get("hint_usage_total", 0)
        total_time = doc.get("total_time_seconds", 0)
        student_ids = doc.get("student_ids", [])

        correctness_rate = correct_count / attempt_count
        skip_rate = skip_count / attempt_count
        avg_time = total_time / attempt_count
        avg_hints = hint_usage_total / attempt_count
        unique_students = len(student_ids) if isinstance(student_ids, list) else 0

        # Quality score: weighted combination
        # Ideal correctness is 0.3-0.8 (not too easy, not too hard)
        if 0.3 <= correctness_rate <= 0.8:
            correctness_score = 1.0
        elif correctness_rate < 0.3:
            correctness_score = correctness_rate / 0.3
        else:
            correctness_score = max(0, (1.0 - correctness_rate) / 0.2)

        skip_score = max(0, 1.0 - (skip_rate / 0.5))
        hint_score = max(0, 1.0 - (avg_hints / 3.0))

        if 5 <= avg_time <= 120:
            time_score = 1.0
        elif avg_time < 5:
            time_score = avg_time / 5.0
        else:
            time_score = max(0, 1.0 - (avg_time - 120) / 180)

        quality_score = (
            correctness_score * 0.35
            + skip_score * 0.25
            + hint_score * 0.20
            + time_score * 0.20
        )

        return {
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "skip_count": skip_count,
            "correctness_rate": round(correctness_rate, 4),
            "skip_rate": round(skip_rate, 4),
            "avg_time_seconds": round(avg_time, 2),
            "avg_hints": round(avg_hints, 2),
            "unique_students": unique_students,
            "quality_score": round(quality_score, 4),
        }

    def _is_flagged(self, metrics: Dict) -> bool:
        """Determine if a question should be flagged as low quality."""
        cr = metrics.get("correctness_rate")
        qs = metrics.get("quality_score")
        return (
            metrics.get("skip_rate", 0) > 0.5
            or (cr is not None and cr < 0.1)
            or (cr is not None and cr > 0.95)
            or (qs is not None and qs < 0.3)
        )

    def get_quality_score(self, question_id: str) -> Dict:
        """Compute quality score and metrics for a specific question."""
        doc = self.collection.find_one({"question_id": question_id})
        if not doc:
            return {
                "question_id": question_id,
                "quality_score": None,
                "flagged": False,
                "metrics": None,
                "message": "No analytics data for this question",
            }

        metrics = self._compute_metrics(doc)
        flagged = self._is_flagged(metrics)

        return {
            "question_id": question_id,
            "quality_score": metrics["quality_score"],
            "flagged": flagged,
            "metrics": metrics,
        }

    def get_flagged_questions(self, min_attempts: int = 5) -> List[Dict]:
        """Return questions flagged as low quality with enough data."""
        docs = list(
            self.collection.find(
                {
                    "flagged": True,
                    "attempt_count": {"$gte": min_attempts},
                },
                {"_id": 0, "student_ids": 0},
            ).sort("quality_score", ASCENDING)
        )

        results = []
        for doc in docs:
            metrics = self._compute_metrics(doc)
            results.append(
                {
                    "question_id": doc["question_id"],
                    "skill_id": doc.get("skill_id"),
                    "quality_score": metrics["quality_score"],
                    "flagged": True,
                    "metrics": metrics,
                }
            )

        return results

    def get_skill_analytics(self, skill_id: str) -> Dict:
        """Aggregate analytics across all questions for a skill."""
        docs = list(self.collection.find({"skill_id": skill_id}))

        if not docs:
            return {
                "skill_id": skill_id,
                "question_count": 0,
                "total_attempts": 0,
                "avg_quality_score": None,
                "flagged_count": 0,
                "metrics": None,
                "message": "No analytics data for this skill",
            }

        total_attempts = 0
        total_correct = 0
        total_skips = 0
        total_hints = 0
        total_time = 0.0
        flagged_count = 0
        quality_scores = []

        for doc in docs:
            metrics = self._compute_metrics(doc)
            total_attempts += metrics["attempt_count"]
            total_correct += metrics.get("correct_count", 0)
            total_skips += metrics.get("skip_count", 0)
            total_hints += doc.get("hint_usage_total", 0)
            total_time += doc.get("total_time_seconds", 0)
            quality_scores.append(metrics["quality_score"])
            if self._is_flagged(metrics):
                flagged_count += 1

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        return {
            "skill_id": skill_id,
            "question_count": len(docs),
            "total_attempts": total_attempts,
            "avg_quality_score": round(avg_quality, 4),
            "flagged_count": flagged_count,
            "metrics": {
                "overall_correctness_rate": round(total_correct / total_attempts, 4) if total_attempts else 0,
                "overall_skip_rate": round(total_skips / total_attempts, 4) if total_attempts else 0,
                "overall_avg_time_seconds": round(total_time / total_attempts, 2) if total_attempts else 0,
                "overall_avg_hints": round(total_hints / total_attempts, 2) if total_attempts else 0,
            },
        }

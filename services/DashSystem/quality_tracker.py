"""
Production feedback loop for question quality.

Reads analytics data from ai_tutor.question_analytics, computes quality
scores, and manages question lifecycle (retire, demote, boost) across both
queue systems:

  - ai_tutor.ai_question_queue   (DASH AI provider queue)
  - ai_tutor.content_v1_queue    (Content V1 queue)

Quality score range: 0.0 (terrible) to 1.0 (excellent).

Actions taken based on aggregated student performance:

  - quality < 0.25   -> RETIRE  (remove from queue, flag in questions collection)
  - quality 0.25-0.40 -> DEMOTE  (lower priority via quality_score field)
  - quality 0.40-0.70 -> NEUTRAL (no change)
  - quality > 0.70   -> BOOST   (higher priority via quality_score field)

All actions are logged to ai_tutor.quality_actions_log for auditability.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QualityTracker:
    """Monitors question quality using aggregated analytics and manages question lifecycle."""

    # Score thresholds for quality actions
    RETIRE_THRESHOLD = 0.25
    DEMOTE_THRESHOLD = 0.40
    BOOST_THRESHOLD = 0.70

    def __init__(self, db_ai_tutor, db_questions, content_service=None) -> None:
        """
        Initialize QualityTracker with database references.

        Args:
            db_ai_tutor: The ai_tutor database (pymongo Database object).
            db_questions: The questions_db database (pymongo Database object).
            content_service: Optional ContentGenerationService for pool regeneration after retirement.
        """
        self.analytics_col = db_ai_tutor["question_analytics"]
        self.questions_col = db_questions["ai_generated_questions"]
        self.queue_col = db_ai_tutor["ai_question_queue"]
        self.quality_log_col = db_ai_tutor["quality_actions_log"]

        # Also reference content_v1 collections for completeness
        self.content_v1_questions_col = db_ai_tutor["content_v1_questions"]
        self.content_v1_queue_col = db_ai_tutor["content_v1_queue"]

        # Content pool (primary serving pool) — retirement must also remove from here
        self.content_pool_col = db_ai_tutor["content_pool"]

        # ContentGenerationService for triggering pool regeneration after retirement
        self.content_service = content_service

        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient quality sweep queries."""
        try:
            self.analytics_col.create_index(
                [("attempt_count", -1)],
                background=True,
            )
            self.quality_log_col.create_index(
                [("action", 1), ("created_at", -1)],
                background=True,
            )
            self.quality_log_col.create_index(
                [("question_id", 1)],
                background=True,
            )
            self.content_pool_col.create_index(
                [("question_id", 1)],
                background=True,
            )
        except Exception as e:
            logger.warning(f"[QUALITY_TRACKER] Index creation warning (non-fatal): {e}")

    # ------------------------------------------------------------------
    # Quality Score Computation
    # ------------------------------------------------------------------

    def compute_quality_score(self, analytics: dict) -> float:
        """
        Compute quality score from analytics data.

        Ideal question characteristics:
          - 40-70% correctness rate (not too easy, not too hard)
          - <20% skip rate (students engage with the question)
          - <2 average hints used (question is clear enough)
          - 30-120s average time (appropriate complexity)

        Args:
            analytics: Dict with keys: attempt_count, correct_count, skip_count,
                       hint_usage_total, total_time_seconds.

        Returns:
            Float between 0.0 (terrible) and 1.0 (excellent).
            Returns 0.5 (neutral) if insufficient data (< 3 attempts).
        """
        if not analytics or analytics.get("attempt_count", 0) < 3:
            return 0.5  # Not enough data, neutral score

        attempts = analytics["attempt_count"]
        correct_rate = (analytics.get("correct_count") or 0) / attempts
        skip_rate = (analytics.get("skip_count") or 0) / attempts
        avg_hints = (analytics.get("hint_usage_total") or 0) / attempts
        avg_time = (analytics.get("total_time_seconds") or 0) / attempts

        # --- Correctness score ---
        # Peak at 0.55, drops off at extremes.
        # Too easy (>0.85) or too hard (<0.15) = bad question.
        if correct_rate < 0.15:
            correctness_score = 0.1
        elif correct_rate > 0.85:
            correctness_score = 0.3  # Too easy, not terrible
        elif 0.35 <= correct_rate <= 0.75:
            correctness_score = 1.0  # Sweet spot
        else:
            correctness_score = 0.6  # Acceptable

        # --- Skip score ---
        # Lower skip rate = better. 50%+ skip rate = 0 score.
        skip_score = max(0.0, 1.0 - (skip_rate * 2))

        # --- Hint score ---
        # 0-1 hints = great, 2 = ok, 3+ = question might be unclear.
        hint_score = max(0.0, 1.0 - (avg_hints * 0.3))

        # --- Time score ---
        # 15-120s is ideal. Too fast (<10s) = too easy. Too slow (>180s) = confusing.
        if avg_time < 10:
            time_score = 0.4
        elif avg_time > 180:
            time_score = 0.3
        elif 15 <= avg_time <= 120:
            time_score = 1.0
        else:
            time_score = 0.7

        # --- Weighted combination ---
        quality = (
            correctness_score * 0.35
            + skip_score * 0.30
            + hint_score * 0.20
            + time_score * 0.15
        )

        return round(quality, 3)

    # ------------------------------------------------------------------
    # Quality Sweep
    # ------------------------------------------------------------------

    async def run_quality_sweep(self, min_attempts: int = 5) -> dict:
        """
        Sweep all questions with enough analytics data and take quality actions.

        Actions by quality score:
          - quality < 0.25  -> RETIRE  (remove from queue, mark as retired)
          - quality 0.25-0.40 -> DEMOTE  (set low quality_score on queue entry)
          - quality 0.40-0.70 -> NEUTRAL (no queue change)
          - quality > 0.70  -> BOOST   (set high quality_score on queue entry)

        Args:
            min_attempts: Minimum number of student attempts before taking action.

        Returns:
            Dict with keys: retired, demoted, boosted, neutral, total_reviewed, errors.
        """
        results = {
            "retired": 0,
            "demoted": 0,
            "boosted": 0,
            "neutral": 0,
            "total_reviewed": 0,
            "errors": 0,
        }

        try:
            # Find all analytics records with enough data
            cursor = self.analytics_col.find(
                {"attempt_count": {"$gte": min_attempts}}
            )

            for analytics_doc in cursor:
                question_id = analytics_doc.get("question_id")
                if not question_id:
                    continue

                results["total_reviewed"] += 1
                quality_score = self.compute_quality_score(analytics_doc)

                try:
                    if quality_score < self.RETIRE_THRESHOLD:
                        await self.retire_question(
                            question_id,
                            reason=(
                                f"Quality score {quality_score:.3f} below "
                                f"retire threshold {self.RETIRE_THRESHOLD}"
                            ),
                            quality_score=quality_score,
                            analytics=analytics_doc,
                        )
                        results["retired"] += 1

                    elif quality_score < self.DEMOTE_THRESHOLD:
                        await self.adjust_queue_priority(question_id, quality_score)
                        self._log_action(
                            question_id, "demoted", quality_score, analytics_doc
                        )
                        results["demoted"] += 1

                    elif quality_score > self.BOOST_THRESHOLD:
                        await self.adjust_queue_priority(question_id, quality_score)
                        self._log_action(
                            question_id, "boosted", quality_score, analytics_doc
                        )
                        results["boosted"] += 1

                    else:
                        # Neutral -- still set quality_score for sorting consistency
                        await self.adjust_queue_priority(question_id, quality_score)
                        results["neutral"] += 1

                except Exception as e:
                    logger.warning(
                        f"[QUALITY_TRACKER] Error processing question {question_id}: {e}"
                    )
                    results["errors"] += 1

        except Exception as e:
            logger.error(f"[QUALITY_TRACKER] Quality sweep failed: {e}")
            results["errors"] += 1

        logger.info(
            f"[QUALITY_TRACKER] Sweep complete: "
            f"reviewed={results['total_reviewed']}, retired={results['retired']}, "
            f"demoted={results['demoted']}, boosted={results['boosted']}, "
            f"neutral={results['neutral']}, errors={results['errors']}"
        )
        return results

    # ------------------------------------------------------------------
    # Question Lifecycle Actions
    # ------------------------------------------------------------------

    async def retire_question(
        self,
        question_id: str,
        reason: str,
        quality_score: float = 0.0,
        analytics: Optional[dict] = None,
    ) -> None:
        """
        Mark a question as retired: remove from queue, flag in questions collection.

        Args:
            question_id: The question_id to retire.
            reason: Human-readable reason for retirement.
            quality_score: The computed quality score that triggered retirement.
            analytics: The analytics data at time of retirement (for logging).
        """
        # Remove from ai_question_queue (DASH AI provider)
        removed_ai = self.queue_col.delete_many({"question_id": question_id})

        # Remove from content_v1_queue (only ready entries, not served)
        removed_v1 = self.content_v1_queue_col.delete_many(
            {"question_id": question_id, "status": "ready"}
        )

        # Flag in ai_generated_questions collection
        self.questions_col.update_one(
            {"question_id": question_id},
            {
                "$set": {
                    "quality.retired": True,
                    "quality.retired_reason": reason,
                    "quality.retired_at": datetime.utcnow(),
                    "quality.quality_score": quality_score,
                }
            },
        )

        # Also flag in content_v1_questions if present
        self.content_v1_questions_col.update_one(
            {"question_id": question_id},
            {
                "$set": {
                    "quality.retired": True,
                    "quality.retired_reason": reason,
                    "quality.retired_at": datetime.utcnow(),
                    "quality.quality_score": quality_score,
                }
            },
        )

        # Remove from content_pool (the primary serving pool) — this was previously
        # missing, causing retired questions to keep being served via pop_question()
        retired_pool_doc = self.content_pool_col.find_one_and_delete(
            {"question_id": question_id}
        )
        pool_skill_id = retired_pool_doc.get("skill_id") if retired_pool_doc else None

        total_removed = (removed_ai.deleted_count if removed_ai else 0) + (
            removed_v1.deleted_count if removed_v1 else 0
        ) + (1 if retired_pool_doc else 0)
        logger.info(
            f"[QUALITY_TRACKER] RETIRED question {question_id}: "
            f"score={quality_score:.3f}, removed {total_removed} queue/pool entries. "
            f"Reason: {reason}"
        )

        # Log the action
        self._log_action(question_id, "retired", quality_score, analytics, reason)

        # Trigger pool regeneration for the affected skill so the pool doesn't shrink
        if pool_skill_id and self.content_service:
            import threading

            def _backfill():
                try:
                    self.content_service.ensure_pool(pool_skill_id)
                    logger.info(
                        f"[QUALITY_TRACKER] Pool backfill triggered for skill {pool_skill_id} "
                        f"after retiring {question_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[QUALITY_TRACKER] Pool backfill failed for {pool_skill_id}: {e}"
                    )

            threading.Thread(target=_backfill, daemon=True).start()

    async def adjust_queue_priority(
        self, question_id: str, quality_score: float
    ) -> None:
        """
        Adjust queue priority based on quality score.

        Sets the quality_score field on queue entries. The queue pop logic
        sorts by quality_score descending, so higher scores are served first.

        Args:
            question_id: The question_id to adjust.
            quality_score: The computed quality score (0.0-1.0).
        """
        # Update ai_question_queue entries
        self.queue_col.update_many(
            {"question_id": question_id, "status": "ready"},
            {"$set": {"quality_score": quality_score}},
        )

        # Update content_v1_queue entries
        self.content_v1_queue_col.update_many(
            {"question_id": question_id, "status": "ready"},
            {"$set": {"quality_score": quality_score}},
        )

        # Also store quality_score on the question document itself
        self.questions_col.update_one(
            {"question_id": question_id},
            {"$set": {"quality.quality_score": quality_score}},
        )
        self.content_v1_questions_col.update_one(
            {"question_id": question_id},
            {"$set": {"quality.quality_score": quality_score}},
        )

    # ------------------------------------------------------------------
    # Quality Report
    # ------------------------------------------------------------------

    async def get_quality_report(self) -> dict:
        """
        Generate a summary report of question quality across the system.

        Returns:
            Dict with total_questions, avg_quality, score_distribution,
            top_10_best, bottom_10_worst, recently_retired, action_summary.
        """
        report: Dict[str, Any] = {}

        try:
            # Total questions with analytics
            total_with_analytics = self.analytics_col.count_documents({})
            total_with_min_data = self.analytics_col.count_documents(
                {"attempt_count": {"$gte": 3}}
            )
            report["total_questions_with_analytics"] = total_with_analytics
            report["total_questions_with_sufficient_data"] = total_with_min_data

            # Compute quality scores for all questions with sufficient data
            scored_questions: List[Dict[str, Any]] = []
            cursor = self.analytics_col.find({"attempt_count": {"$gte": 3}})
            for doc in cursor:
                qid = doc.get("question_id", "unknown")
                score = self.compute_quality_score(doc)
                scored_questions.append({
                    "question_id": qid,
                    "quality_score": score,
                    "attempt_count": doc.get("attempt_count", 0),
                    "correct_rate": round(
                        doc.get("correct_count", 0)
                        / max(doc.get("attempt_count", 1), 1),
                        3,
                    ),
                    "skip_rate": round(
                        doc.get("skip_count", 0)
                        / max(doc.get("attempt_count", 1), 1),
                        3,
                    ),
                })

            # Average quality
            if scored_questions:
                avg_quality = round(
                    sum(q["quality_score"] for q in scored_questions)
                    / len(scored_questions),
                    3,
                )
            else:
                avg_quality = 0.5
            report["average_quality_score"] = avg_quality

            # Score distribution by band
            distribution = {
                "retire_zone_0_to_25": 0,
                "demote_zone_25_to_40": 0,
                "neutral_zone_40_to_70": 0,
                "boost_zone_70_to_100": 0,
            }
            for q in scored_questions:
                s = q["quality_score"]
                if s < self.RETIRE_THRESHOLD:
                    distribution["retire_zone_0_to_25"] += 1
                elif s < self.DEMOTE_THRESHOLD:
                    distribution["demote_zone_25_to_40"] += 1
                elif s <= self.BOOST_THRESHOLD:
                    distribution["neutral_zone_40_to_70"] += 1
                else:
                    distribution["boost_zone_70_to_100"] += 1
            report["score_distribution"] = distribution

            # Top 10 best and bottom 10 worst
            sorted_asc = sorted(
                scored_questions, key=lambda x: x["quality_score"]
            )
            report["bottom_10_worst"] = sorted_asc[:10]
            report["top_10_best"] = sorted_asc[-10:][::-1]

            # Recently retired questions (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recently_retired = list(
                self.quality_log_col.find(
                    {
                        "action": "retired",
                        "created_at": {"$gte": seven_days_ago},
                    },
                    {"_id": 0},
                )
                .sort("created_at", -1)
                .limit(20)
            )
            report["recently_retired"] = recently_retired

            # Action summary (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            action_pipeline = [
                {"$match": {"created_at": {"$gte": thirty_days_ago}}},
                {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            ]
            action_counts = {}
            for doc in self.quality_log_col.aggregate(action_pipeline):
                action_counts[doc["_id"]] = doc["count"]
            report["action_summary_last_30_days"] = action_counts

        except Exception as e:
            logger.error(
                f"[QUALITY_TRACKER] Error generating quality report: {e}"
            )
            report["error"] = str(e)

        return report

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_action(
        self,
        question_id: str,
        action: str,
        quality_score: float,
        analytics: Optional[dict] = None,
        reason: str = "",
    ) -> None:
        """Log a quality action to the audit trail collection."""
        try:
            log_entry = {
                "question_id": question_id,
                "action": action,
                "quality_score": quality_score,
                "reason": reason,
                "created_at": datetime.utcnow(),
            }
            if analytics:
                log_entry["analytics_snapshot"] = {
                    "attempt_count": analytics.get("attempt_count", 0),
                    "correct_count": analytics.get("correct_count", 0),
                    "skip_count": analytics.get("skip_count", 0),
                    "hint_usage_total": analytics.get("hint_usage_total", 0),
                    "total_time_seconds": analytics.get("total_time_seconds", 0),
                }
            self.quality_log_col.insert_one(log_entry)
        except Exception as e:
            logger.warning(
                f"[QUALITY_TRACKER] Failed to log action for {question_id}: {e}"
            )

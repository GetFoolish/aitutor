#!/usr/bin/env python3
"""content.dynamic_assessment

Dynamic assessment sessions that generate questions incrementally.

Key behavior:
- Start creates an assessment session document (no need to pre-generate all questions).
- When fetching question N, we *also* ensure N+1..N+3 exist (prefetch) so the next step is fast.
- Supports multiple subjects (at minimum: math, science, reading).

This module is called from services/DashSystem/dash_api.py.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv

from content.question_generator import QuestionGenerator

# Load environment variables (supports running without run_tutor.sh)
load_dotenv()

# MongoDB
mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")
client = MongoClient(mongodb_uri)
db = client[db_name]


def get_grade_from_age_range(age_range: str) -> str:
    """Map age range to grade level."""
    mapping = {
        "5-7": "K-2",
        "8-10": "3-5",
        "11-13": "6-8",
        "14-17": "9-12",
        "18+": "9-12",  # Adult uses high school level
    }
    return mapping.get(age_range, "3-5")


def _normalize_subject(subject: str) -> str:
    """Normalize incoming subject values to our supported set."""
    s = (subject or "").strip().lower()
    if s in {"math", "mathematics"}:
        return "math"
    if s in {"science"}:
        return "science"
    if s in {"reading", "english", "ela", "language-arts"}:
        return "reading"
    # default
    return "math"


def _default_topics_for_subject(subject: str) -> List[str]:
    s = _normalize_subject(subject)
    if s == "science":
        return ["science"]
    if s == "reading":
        return ["reading"]
    return ["math-basics"]


def _plan_difficulties(question_count: int) -> List[str]:
    """Create a shuffled list of difficulties with a simple distribution."""
    easy_count = int(question_count * 0.4)
    medium_count = int(question_count * 0.4)
    hard_count = max(0, question_count - easy_count - medium_count)
    difficulties = ["easy"] * easy_count + ["medium"] * medium_count + ["hard"] * hard_count

    # Shuffle to mix difficulties
    import random

    random.shuffle(difficulties)
    # Edge case: question_count small
    if not difficulties:
        difficulties = ["medium"]
    return difficulties[:question_count]


def _topic_to_subject(topic: str, explicit_subject: str) -> str:
    """Pick generator subject string.

    We keep explicit_subject as the main selector (math/science/reading).
    Some topic ids from the older UI map to legacy subjects.
    """
    s = _normalize_subject(explicit_subject)

    # Keep old topic mapping for backwards compatibility.
    topic_to_subject = {
        "math-basics": "math",
        "algebra": "math",
        "geometry": "math",
        "fractions": "math",
        "word-problems": "math",
        "statistics": "math",
        "reading": "reading",
        "writing": "reading",
        "science": "science",
        "coding": "computer_science",
    }

    if topic:
        mapped = topic_to_subject.get(topic)
        if mapped:
            # Prefer keeping reading as "reading" (not "english")
            if mapped == "english":
                return "reading"
            return mapped

    return s


def _difficulty_topics(difficulty: str, topic: str) -> List[str]:
    """Difficulty-appropriate topic mappings (mostly for math)."""
    mapping = {
        "easy": {
            "math-basics": ["counting", "addition", "subtraction"],
            "algebra": ["simple_equations"],
            "geometry": ["basic_shapes"],
            "fractions": ["simple_fractions"],
            "word-problems": ["simple_word_problems"],
            "statistics": ["simple_probability"],
            "reading": ["reading_comprehension"],
            "writing": ["grammar_basics"],
            "science": ["life_science"],
        },
        "medium": {
            "math-basics": ["multiplication", "division"],
            "algebra": ["linear_equations"],
            "geometry": ["area_perimeter"],
            "fractions": ["fraction_operations"],
            "word-problems": ["multi_step_problems"],
            "statistics": ["data_interpretation"],
            "reading": ["main_idea"],
            "writing": ["sentence_structure"],
            "science": ["physical_science"],
        },
        "hard": {
            "math-basics": ["order_of_operations"],
            "algebra": ["systems_of_equations"],
            "geometry": ["volume_surface_area"],
            "fractions": ["mixed_numbers"],
            "word-problems": ["complex_word_problems"],
            "statistics": ["probability"],
            "reading": ["inference"],
            "writing": ["editing_revision"],
            "science": ["earth_space_science"],
        },
    }
    return mapping.get(difficulty, {}).get(topic, [topic])


def _difficulty_widgets(difficulty: str, subject: str) -> List[str]:
    """Widget types to use.

    For now we keep it fairly generic so it works across subjects.
    """
    # Many non-math topics still work fine with radio/numeric-input.
    widgets = {
        "easy": ["radio", "numeric-input"],
        "medium": ["numeric-input", "dropdown"],
        "hard": ["numeric-input", "orderer"],
    }
    return widgets.get(difficulty, ["numeric-input"])


def _build_generation_plan(
    topics: List[str],
    subject: str,
    question_count: int,
) -> List[Dict[str, Any]]:
    """Create a per-question plan so generation can be incremental and deterministic."""
    topics = [t for t in (topics or []) if isinstance(t, str) and t.strip()]
    if not topics:
        topics = _default_topics_for_subject(subject)

    difficulties = _plan_difficulties(question_count)

    plan: List[Dict[str, Any]] = []
    for i in range(question_count):
        difficulty = difficulties[i]
        original_topic = topics[i % len(topics)]
        gen_subject = _topic_to_subject(original_topic, subject)
        sub_topics = _difficulty_topics(difficulty, original_topic)
        # Simple: rotate through subtopics
        sub_topic = sub_topics[i % len(sub_topics)] if sub_topics else original_topic
        widgets = _difficulty_widgets(difficulty, gen_subject)
        widget_type = widgets[i % len(widgets)] if widgets else "numeric-input"

        plan.append(
            {
                "index": i,
                "difficulty": difficulty,
                "original_topic": original_topic,
                "sub_topic": sub_topic,
                "widget_type": widget_type,
                "subject": gen_subject,
            }
        )

    return plan


def _to_perseus_item(
    *,
    assessment_id: str,
    grade: str,
    subject: str,
    planned: Dict[str, Any],
    generated: Any,
    order: int,
) -> Dict[str, Any]:
    # generated may be a dataclass (GeneratedQuestion) or plain dict
    if hasattr(generated, "__dict__"):
        question_id = generated.question_id
        question = generated.question
        answer_area = generated.answer_area
        hints = generated.hints
        topic = getattr(generated, "topic", planned.get("sub_topic"))
    else:
        question_id = generated.get("question_id")
        question = generated.get("question", {})
        answer_area = generated.get("answer_area", {})
        hints = generated.get("hints", [])
        topic = generated.get("topic") or planned.get("sub_topic")

    return {
        "question": question,
        "answerArea": answer_area,
        "hints": hints,
        "itemDataVersion": {"major": 0, "minor": 1},
        "dash_metadata": {
            "dash_question_id": question_id,
            "assessment_id": assessment_id,
            "difficulty": planned.get("difficulty"),
            "topic": planned.get("original_topic"),
            "planned_sub_topic": planned.get("sub_topic"),
            "subject": _normalize_subject(subject),
            "skill_ids": [f"assess_{topic or 'unknown'}"],
            "skill_names": [str(topic or "Assessment")],
            "grade": grade,
            "source": "dynamic_assessment",
            "order": order,
        },
    }


def create_assessment_session(
    *,
    user_id: str,
    age_range: str,
    grade: str,
    subject: str,
    topics: List[str],
    question_count: int,
    user_memories: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create an empty assessment session with a stored generation plan."""
    assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
    subject = _normalize_subject(subject)

    plan = _build_generation_plan(topics, subject, question_count)

    assessment_doc = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "age_range": age_range,
        "grade": grade,
        "subject": subject,
        "topics": topics,
        "question_count": int(question_count),
        "plan": plan,
        "questions": [],
        "generated_question_ids": [],
        "status": "in_progress",
        "created_at": datetime.utcnow(),
        "results": None,
        "user_memories": user_memories,
    }
    db.assessments.insert_one(assessment_doc)

    return {
        "assessment_id": assessment_id,
        "subject": subject,
        "grade": grade,
        "topics": topics,
        "total_questions": int(question_count),
    }


def _generate_one_for_index(
    *,
    generator: QuestionGenerator,
    assessment: Dict[str, Any],
    planned: Dict[str, Any],
    used_openers: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Optional[Any]]:
    """Generate a single question (Perseus item) for the plan entry."""
    grade = assessment.get("grade")
    assessment_id = assessment.get("assessment_id")
    explicit_subject = assessment.get("subject")

    user_memories = assessment.get("user_memories")

    q = None
    last_err: Optional[Exception] = None

    # Retry at the assessment layer if tone validation fails inside QuestionGenerator.
    # QuestionGenerator itself retries 3 times internally before raising ValueError.
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            print(f"[DYNAMIC_ASSESSMENT] Generating question (attempt {attempt+1}/{max_attempts}) "
                  f"topic={planned.get('sub_topic')} subject={planned.get('subject')}")
            
            q = generator.generate_question(
                topic=planned.get("sub_topic") or planned.get("original_topic"),
                widget_type=planned.get("widget_type") or "numeric-input",
                grade=grade,
                subject=planned.get("subject") or explicit_subject,
                user_memories=str(user_memories) if user_memories else None,
                used_openers=used_openers,
            )
            if q:
                content_preview = q.question.get("content", "")[:60]
                print(f"[DYNAMIC_ASSESSMENT] Generated successfully: {content_preview}...")
                break
        except ValueError as e:
            # Tone validation failure - log and retry with new generation
            print(f"[DYNAMIC_ASSESSMENT] Tone validation FAILED (attempt {attempt+1}): {e}")
            last_err = e
            q = None
        except Exception as e:
            print(f"[DYNAMIC_ASSESSMENT] Generation error (attempt {attempt+1}): {e}")
            last_err = e
            q = None

    if not q:
        err_msg = f"QuestionGenerator failed after {max_attempts} attempts"
        if last_err:
            err_msg += f": {last_err}"
        print(f"[DYNAMIC_ASSESSMENT] CRITICAL: {err_msg}")
        raise RuntimeError(err_msg)

    perseus_item = _to_perseus_item(
        assessment_id=assessment_id,
        grade=grade,
        subject=explicit_subject,
        planned=planned,
        generated=q,
        order=int(planned.get("index", 0)),
    )

    return perseus_item, q


def ensure_prefetched(
    *,
    assessment_id: str,
    target_index: int,
    prefetch_ahead: int = 3,
) -> Dict[str, Any]:
    """Ensure questions exist for target_index and (target_index+1..+prefetch_ahead).

    Returns stats about how many were generated.
    """
    assessment = db.assessments.find_one({"assessment_id": assessment_id})
    if not assessment:
        raise ValueError("Assessment not found")

    question_count = int(assessment.get("question_count", 0))
    if question_count <= 0:
        raise ValueError("Invalid assessment question_count")

    existing_questions: List[Dict[str, Any]] = assessment.get("questions", []) or []
    existing_ids = set(assessment.get("generated_question_ids", []) or [])

    want_upto = min(question_count - 1, int(target_index) + int(prefetch_ahead))

    generated_now = 0

    # Only instantiate generator if we actually need to generate.
    if len(existing_questions) <= want_upto:
        generator = QuestionGenerator()
        used_openers: List[str] = []

        while len(existing_questions) <= want_upto and len(existing_questions) < question_count:
            next_index = len(existing_questions)
            plan = assessment.get("plan") or []
            if next_index >= len(plan):
                break
            planned = plan[next_index]

            perseus_item, raw_obj = _generate_one_for_index(
                generator=generator,
                assessment=assessment,
                planned=planned,
                used_openers=used_openers,
            )

            qid = perseus_item.get("dash_metadata", {}).get("dash_question_id")
            if not qid:
                # Extremely unlikely; skip and try again.
                continue
            if qid in existing_ids:
                # Avoid duplicates (shouldn't happen with uuid ids, but still).
                continue

            existing_questions.append(perseus_item)
            existing_ids.add(qid)
            used_openers.append(
                (perseus_item.get("question", {}) or {}).get("content", "")[:60]
            )
            generated_now += 1

            # Store generated question in the reusable library too (best-effort)
            try:
                if raw_obj is not None:
                    generator.save_to_mongodb([raw_obj])
            except Exception:
                pass

        db.assessments.update_one(
            {"assessment_id": assessment_id},
            {
                "$set": {
                    "questions": existing_questions,
                    "generated_question_ids": list(existing_ids),
                }
            },
        )

    if generated_now:
        # Simple visibility in local dev logs.
        print(
            f"[DYNAMIC_ASSESSMENT] prefetch generated_now={generated_now} "
            f"generated_total={len(existing_questions)} target_index={target_index} ahead={prefetch_ahead}"
        )

    return {
        "assessment_id": assessment_id,
        "total_questions": question_count,
        "generated_now": generated_now,
        "generated_total": len(existing_questions),
        "prefetch_ahead": prefetch_ahead,
        "target_index": int(target_index),
    }


def get_question(
    *,
    assessment_id: str,
    index: int,
    prefetch_ahead: int = 3,
) -> Dict[str, Any]:
    """Fetch question at index, ensuring prefetch ahead."""
    stats = ensure_prefetched(
        assessment_id=assessment_id,
        target_index=index,
        prefetch_ahead=prefetch_ahead,
    )

    assessment = db.assessments.find_one({"assessment_id": assessment_id})
    if not assessment:
        raise ValueError("Assessment not found")

    questions: List[Dict[str, Any]] = assessment.get("questions", []) or []
    if index < 0 or index >= len(questions):
        raise IndexError("Question index out of range")

    return {
        "assessment_id": assessment_id,
        "subject": assessment.get("subject"),
        "grade": assessment.get("grade"),
        "topics": assessment.get("topics", []),
        "total_questions": int(assessment.get("question_count", len(questions))),
        "question_index": int(index),
        "question": questions[index],
        "prefetch": stats,
    }


def get_batch(
    *,
    assessment_id: str,
    start_index: int,
    limit: int = 4,
    prefetch_ahead: int = 3,
) -> Dict[str, Any]:
    """Return a batch of questions starting at start_index.

    This is used by the frontend to pull newly-generated questions into its local buffer.
    """
    if limit <= 0:
        limit = 1

    # Ensure prefetch relative to the last question in this batch.
    last_needed = start_index + limit - 1
    stats = ensure_prefetched(
        assessment_id=assessment_id,
        target_index=last_needed,
        prefetch_ahead=prefetch_ahead,
    )

    assessment = db.assessments.find_one({"assessment_id": assessment_id})
    if not assessment:
        raise ValueError("Assessment not found")

    questions: List[Dict[str, Any]] = assessment.get("questions", []) or []
    batch = questions[start_index : start_index + limit]

    return {
        "assessment_id": assessment_id,
        "subject": assessment.get("subject"),
        "grade": assessment.get("grade"),
        "topics": assessment.get("topics", []),
        "total_questions": int(assessment.get("question_count", len(questions))),
        "start_index": int(start_index),
        "count": len(batch),
        "questions": batch,
        "prefetch": stats,
    }


# -----------------------------
# Completion (unchanged)
# -----------------------------

def complete_assessment(assessment_id: str, answers: List[Dict]) -> Dict:
    """Complete an assessment and generate learning path."""
    # Calculate scores by topic and difficulty
    topic_scores: Dict[str, Dict[str, int]] = {}
    difficulty_scores = {
        "easy": {"correct": 0, "total": 0},
        "medium": {"correct": 0, "total": 0},
        "hard": {"correct": 0, "total": 0},
    }

    for answer in answers:
        topic = answer.get("topic", "unknown")
        difficulty = answer.get("difficulty", "medium")
        is_correct = bool(answer.get("is_correct", False))

        if topic not in topic_scores:
            topic_scores[topic] = {"correct": 0, "total": 0}

        topic_scores[topic]["total"] += 1
        if difficulty not in difficulty_scores:
            difficulty_scores[difficulty] = {"correct": 0, "total": 0}
        difficulty_scores[difficulty]["total"] += 1

        if is_correct:
            topic_scores[topic]["correct"] += 1
            difficulty_scores[difficulty]["correct"] += 1

    total_correct = sum(d["correct"] for d in difficulty_scores.values())
    total_questions = sum(d["total"] for d in difficulty_scores.values())
    overall_score = total_correct / total_questions if total_questions > 0 else 0

    easy_pct = difficulty_scores["easy"]["correct"] / max(1, difficulty_scores["easy"]["total"])
    medium_pct = difficulty_scores["medium"]["correct"] / max(1, difficulty_scores["medium"]["total"])
    hard_pct = difficulty_scores["hard"]["correct"] / max(1, difficulty_scores["hard"]["total"])

    if hard_pct >= 0.7:
        skill_level = "advanced"
        start_difficulty = "medium"
    elif medium_pct >= 0.7:
        skill_level = "intermediate"
        start_difficulty = "easy-medium"
    elif easy_pct >= 0.7:
        skill_level = "beginner"
        start_difficulty = "easy"
    else:
        skill_level = "foundations"
        start_difficulty = "easy"

    weak_topics = [
        topic
        for topic, scores in topic_scores.items()
        if scores["correct"] / max(1, scores["total"]) < 0.6
    ]

    strong_topics = [
        topic
        for topic, scores in topic_scores.items()
        if scores["correct"] / max(1, scores["total"]) >= 0.8
    ]

    learning_path = {
        "skill_level": skill_level,
        "recommended_start_difficulty": start_difficulty,
        "focus_topics": weak_topics,
        "strong_topics": strong_topics,
        "suggested_daily_questions": 10 if skill_level == "foundations" else 15,
        "estimated_sessions_to_mastery": {
            topic: max(1, 5 - int(scores["correct"] / max(1, scores["total"]) * 5))
            for topic, scores in topic_scores.items()
        },
    }

    results = {
        "overall_score": overall_score,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "topic_scores": topic_scores,
        "difficulty_scores": difficulty_scores,
        "skill_level": skill_level,
        "learning_path": learning_path,
        "completed_at": datetime.utcnow(),
    }

    db.assessments.update_one(
        {"assessment_id": assessment_id},
        {"$set": {"status": "completed", "results": results}},
    )

    return results


# -----------------------------
# API endpoint functions (called from dash_api.py)
# -----------------------------

def create_dynamic_assessment_endpoint(user_id: str, data: Dict) -> Dict:
    """API handler for creating a dynamic assessment session.

    Start creates a session and generates the initial buffer (0..3).
    """
    age_range = data.get("age_range", "8-10")
    grade = data.get("grade") or get_grade_from_age_range(age_range)
    subject = _normalize_subject(data.get("subject", "math"))
    topics = data.get("topics") or _default_topics_for_subject(subject)
    question_count = int(data.get("question_count", 10))

    session = create_assessment_session(
        user_id=user_id,
        age_range=age_range,
        grade=grade,
        subject=subject,
        topics=topics,
        question_count=question_count,
        user_memories=data.get("user_memories"),
    )

    # Generate an initial buffer so the UI can start instantly.
    ensure_prefetched(
        assessment_id=session["assessment_id"],
        target_index=0,
        prefetch_ahead=3,
    )

    # Return the initial batch (first 4, or fewer if question_count < 4)
    initial_limit = min(4, question_count)
    batch = get_batch(
        assessment_id=session["assessment_id"],
        start_index=0,
        limit=initial_limit,
        prefetch_ahead=3,
    )

    return {
        "assessment_id": session["assessment_id"],
        "subject": session["subject"],
        "questions": batch.get("questions", []),
        "total_questions": session["total_questions"],
        "grade": session["grade"],
        "topics": session["topics"],
        "prefetch": batch.get("prefetch"),
    }


def complete_assessment_endpoint(assessment_id: str, answers: List[Dict]) -> Dict:
    """API endpoint handler for completing assessment."""
    return complete_assessment(assessment_id, answers)

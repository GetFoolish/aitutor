"""
Create dummy practice history data in MongoDB for testing Spec 001 - Practice History Dashboard.
"""

import sys
import os
import random
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def create_practice_history_data(user_id: str = "mongodb_test_user"):
    """
    Create varied practice history data for testing Practice History Dashboard.

    Creates data spanning multiple sessions (30+ min gaps create new sessions):
    - Session 1: 3 days ago - Basic counting/shapes (mostly correct)
    - Session 2: 2 days ago - Addition practice (mixed results)
    - Session 3: Yesterday - Subtraction focus (struggled)
    - Session 4: Today - Review session (improved)
    """

    # Define skill IDs available for the test user
    skills = [
        "counting_1_10",
        "number_recognition",
        "basic_shapes",
        "addition_basic",
        "subtraction_basic",
        "counting_100"
    ]

    # Generate question IDs
    def make_question_id(skill: str, num: int) -> str:
        return f"{skill}_q{num}"

    current_time = time.time()
    day_seconds = 86400  # 24 hours in seconds

    question_history = []

    # ============================================================
    # SESSION 1: 3 days ago - Basic counting/shapes (strong performance)
    # ============================================================
    session_1_start = current_time - (3 * day_seconds) + 36000  # 10am
    session_1_questions = [
        {"skill": "counting_1_10", "correct": True, "response_time": 12.5},
        {"skill": "counting_1_10", "correct": True, "response_time": 8.3},
        {"skill": "number_recognition", "correct": True, "response_time": 15.2},
        {"skill": "basic_shapes", "correct": True, "response_time": 20.1},
        {"skill": "basic_shapes", "correct": False, "response_time": 45.0},
        {"skill": "number_recognition", "correct": True, "response_time": 11.8},
    ]

    for i, q in enumerate(session_1_questions):
        question_history.append({
            "question_id": make_question_id(q["skill"], i + 1),
            "skill_ids": [q["skill"]],
            "is_correct": q["correct"],
            "response_time_seconds": q["response_time"],
            "timestamp": session_1_start + (i * 180),  # 3 min apart
            "time_penalty_applied": False
        })

    # ============================================================
    # SESSION 2: 2 days ago - Addition practice (mixed results)
    # ============================================================
    session_2_start = current_time - (2 * day_seconds) + 54000  # 3pm
    session_2_questions = [
        {"skill": "addition_basic", "correct": True, "response_time": 25.0},
        {"skill": "addition_basic", "correct": False, "response_time": 60.0},
        {"skill": "addition_basic", "correct": False, "response_time": 55.0},
        {"skill": "counting_100", "correct": True, "response_time": 30.0},
        {"skill": "addition_basic", "correct": True, "response_time": 35.0},
        {"skill": "addition_basic", "correct": True, "response_time": 28.0},
        {"skill": "counting_100", "correct": False, "response_time": 70.0},
        {"skill": "addition_basic", "correct": True, "response_time": 22.0},
    ]

    for i, q in enumerate(session_2_questions):
        question_history.append({
            "question_id": make_question_id(q["skill"], 10 + i),
            "skill_ids": [q["skill"]],
            "is_correct": q["correct"],
            "response_time_seconds": q["response_time"],
            "timestamp": session_2_start + (i * 150),  # 2.5 min apart
            "time_penalty_applied": q["response_time"] > 50
        })

    # ============================================================
    # SESSION 3: Yesterday - Subtraction focus (struggled)
    # ============================================================
    session_3_start = current_time - day_seconds + 43200  # 12pm yesterday
    session_3_questions = [
        {"skill": "subtraction_basic", "correct": False, "response_time": 55.0},
        {"skill": "subtraction_basic", "correct": False, "response_time": 65.0},
        {"skill": "subtraction_basic", "correct": True, "response_time": 48.0},
        {"skill": "subtraction_basic", "correct": False, "response_time": 72.0},
        {"skill": "counting_1_10", "correct": True, "response_time": 10.0},  # Review
        {"skill": "subtraction_basic", "correct": True, "response_time": 40.0},
        {"skill": "subtraction_basic", "correct": False, "response_time": 80.0},
    ]

    for i, q in enumerate(session_3_questions):
        question_history.append({
            "question_id": make_question_id(q["skill"], 20 + i),
            "skill_ids": [q["skill"]],
            "is_correct": q["correct"],
            "response_time_seconds": q["response_time"],
            "timestamp": session_3_start + (i * 200),  # 3+ min apart
            "time_penalty_applied": q["response_time"] > 50
        })

    # ============================================================
    # SESSION 4: Today - Review session (showing improvement!)
    # ============================================================
    session_4_start = current_time - 7200  # 2 hours ago
    session_4_questions = [
        {"skill": "subtraction_basic", "correct": True, "response_time": 32.0},
        {"skill": "subtraction_basic", "correct": True, "response_time": 28.0},
        {"skill": "addition_basic", "correct": True, "response_time": 18.0},
        {"skill": "subtraction_basic", "correct": False, "response_time": 45.0},
        {"skill": "subtraction_basic", "correct": True, "response_time": 25.0},
        {"skill": "basic_shapes", "correct": True, "response_time": 15.0},
        {"skill": "counting_100", "correct": True, "response_time": 22.0},
        {"skill": "addition_basic", "correct": True, "response_time": 16.0},
        {"skill": "subtraction_basic", "correct": True, "response_time": 20.0},
    ]

    for i, q in enumerate(session_4_questions):
        question_history.append({
            "question_id": make_question_id(q["skill"], 30 + i),
            "skill_ids": [q["skill"]],
            "is_correct": q["correct"],
            "response_time_seconds": q["response_time"],
            "timestamp": session_4_start + (i * 120),  # 2 min apart
            "time_penalty_applied": False
        })

    # Update skill states based on practice history
    skill_stats = {}
    for attempt in question_history:
        skill = attempt["skill_ids"][0]
        if skill not in skill_stats:
            skill_stats[skill] = {
                "practice_count": 0,
                "correct_count": 0,
                "last_practice_time": 0
            }
        skill_stats[skill]["practice_count"] += 1
        if attempt["is_correct"]:
            skill_stats[skill]["correct_count"] += 1
        skill_stats[skill]["last_practice_time"] = max(
            skill_stats[skill]["last_practice_time"],
            attempt["timestamp"]
        )

    # Check if user exists
    existing = mongo_db.users.find_one({"user_id": user_id})
    if not existing:
        print(f"\n❌ User '{user_id}' not found in MongoDB!")
        print("   Run create_test_user_mongodb.py first to create the test user.")
        return

    # Build skill_states update
    skill_states_update = {}
    for skill_id, stats in skill_stats.items():
        skill_states_update[f"skill_states.{skill_id}.practice_count"] = stats["practice_count"]
        skill_states_update[f"skill_states.{skill_id}.correct_count"] = stats["correct_count"]
        skill_states_update[f"skill_states.{skill_id}.last_practice_time"] = stats["last_practice_time"]

    # Update user with practice history
    result = mongo_db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "question_history": question_history,
                "last_updated": time.time(),
                **skill_states_update
            }
        }
    )

    # Print summary
    print("\n" + "=" * 60)
    print("  Practice History Data Created!")
    print("=" * 60)
    print(f"  User ID: {user_id}")
    print(f"  Total Questions: {len(question_history)}")
    print(f"  Sessions Created: 4")
    print()

    # Session breakdown
    total_correct = sum(1 for q in question_history if q["is_correct"])
    print("  Session Breakdown:")
    print("  ─────────────────────────────────────────────────")
    print("  Session 1 (3 days ago): 6 questions - Counting/Shapes (strong)")
    print("  Session 2 (2 days ago): 8 questions - Addition (mixed)")
    print("  Session 3 (yesterday):  7 questions - Subtraction (struggled)")
    print("  Session 4 (today):      9 questions - Review (improved!)")
    print("  ─────────────────────────────────────────────────")
    print(f"  Overall Accuracy: {total_correct}/{len(question_history)} ({100*total_correct/len(question_history):.1f}%)")
    print()

    # Skill breakdown
    print("  Skill Practice Summary:")
    for skill, stats in sorted(skill_stats.items()):
        acc = 100 * stats["correct_count"] / stats["practice_count"]
        print(f"    {skill}: {stats['practice_count']} attempts, {acc:.0f}% accuracy")

    print("=" * 60)
    print("\n📝 Next Steps:")
    print("   1. Start the frontend: cd frontend && npm run dev")
    print("   2. Start dash_api: python services/DashSystem/dash_api.py")
    print("   3. Log in as the test user")
    print("   4. Navigate to Practice History Dashboard")
    print("   5. Verify data displays correctly across sessions")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create practice history data for testing")
    parser.add_argument("--user", default="mongodb_test_user", help="User ID to add data to")
    args = parser.parse_args()

    try:
        create_practice_history_data(args.user)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

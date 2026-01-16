#!/usr/bin/env python3
"""Create dummy practice history data for testing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from datetime import datetime, timedelta
from managers.mongodb_manager import mongo_db

def create_practice_history_data(user_id="mongodb_test_user"):
    mongo_db.question_attempts.delete_many({"user_id": user_id})
    print(f"Cleared existing attempts for user: {user_id}")
    
    now = datetime.now()
    attempts = []
    
    # Session 1: 3 days ago - counting/shapes (strong)
    s1 = now - timedelta(days=3, hours=2)
    for i, (skill, correct, t) in enumerate([
        ("counting-objects", True, 15), ("counting-objects", True, 12),
        ("counting-objects", True, 10), ("basic-shapes", True, 20),
        ("basic-shapes", True, 18), ("basic-shapes", False, 25), ("basic-shapes", True, 15)
    ]):
        attempts.append({"user_id": user_id, "question_id": f"q_count_{i+1}",
            "is_correct": correct, "skill_ids": [skill], "response_time_seconds": t,
            "timestamp": s1 + timedelta(minutes=i*3), "session_id": "session_001"})
    
    # Session 2: 2 days ago - addition (mixed)
    s2 = now - timedelta(days=2, hours=4)
    for i, (skill, correct, t) in enumerate([
        ("addition-within-10", True, 20), ("addition-within-10", True, 18),
        ("addition-within-10", False, 30), ("addition-within-10", False, 35),
        ("addition-within-10", True, 22), ("addition-within-20", False, 40),
        ("addition-within-20", True, 25), ("addition-within-20", False, 45)
    ]):
        attempts.append({"user_id": user_id, "question_id": f"q_add_{i+1}",
            "is_correct": correct, "skill_ids": [skill], "response_time_seconds": t,
            "timestamp": s2 + timedelta(minutes=i*4), "session_id": "session_002"})
    
    # Session 3: Yesterday - subtraction (struggled)
    s3 = now - timedelta(days=1, hours=3)
    for i, (skill, correct, t) in enumerate([
        ("subtraction-within-10", False, 35), ("subtraction-within-10", False, 40),
        ("subtraction-within-10", True, 28), ("subtraction-within-10", False, 38),
        ("subtraction-within-10", True, 25), ("subtraction-within-10", True, 22)
    ]):
        attempts.append({"user_id": user_id, "question_id": f"q_sub_{i+1}",
            "is_correct": correct, "skill_ids": [skill], "response_time_seconds": t,
            "timestamp": s3 + timedelta(minutes=i*5), "session_id": "session_003"})
    
    # Session 4: Today - review (improved)
    s4 = now - timedelta(hours=1)
    for i, (skill, correct, t) in enumerate([
        ("counting-objects", True, 8), ("basic-shapes", True, 12),
        ("addition-within-10", True, 15), ("addition-within-20", True, 20),
        ("subtraction-within-10", True, 18), ("subtraction-within-10", True, 16),
        ("addition-within-10", True, 12), ("basic-shapes", True, 10), ("counting-objects", True, 7)
    ]):
        attempts.append({"user_id": user_id, "question_id": f"q_review_{i+1}",
            "is_correct": correct, "skill_ids": [skill], "response_time_seconds": t,
            "timestamp": s4 + timedelta(minutes=i*2), "session_id": "session_004"})
    
    result = mongo_db.question_attempts.insert_many(attempts)
    print(f"Created {len(result.inserted_ids)} practice history records (4 sessions, 3 days)")
    return len(result.inserted_ids)

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "mongodb_test_user"
    create_practice_history_data(user_id)

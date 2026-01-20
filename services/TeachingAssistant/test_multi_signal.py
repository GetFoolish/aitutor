"""
Test script for multi-signal struggle detection.
Simulates audio + visual signals from Vision Agents combined with interaction signals.
"""

import requests
import time
import sys
sys.path.append('../..')

from managers.mongodb_manager import mongo_db
from datetime import datetime
import uuid

BASE_URL = "http://localhost:8002"

def create_test_session():
    """Create a test session directly in MongoDB."""
    session_id = f"test_multi_signal_{uuid.uuid4().hex[:8]}"
    user_id = "test_user_multisignal"

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.utcnow(),
        "active": True,
        "consecutive_errors": 0,
        "hint_requests": 0,
        "questions_answered_this_session": 0,
        "last_activity": datetime.utcnow(),
    }

    mongo_db.sessions.insert_one(session)
    print(f"\n{'='*60}")
    print(f"✅ Created test session: {session_id}")
    print(f"{'='*60}\n")
    return session_id

def send_signals(session_id: str, audio: dict, visual: dict, description: str):
    """Send audio/visual signals to TeachingAssistant."""
    print(f"\n{'─'*60}")
    print(f"📡 SENDING SIGNALS: {description}")
    print(f"   Audio: {audio}")
    print(f"   Visual: {visual}")

    response = requests.post(
        f"{BASE_URL}/signals/update",
        json={
            "session_id": session_id,
            "audio_signals": audio,
            "visual_signals": visual,
        }
    )

    result = response.json()
    print(f"   Response: {result}")

    if result.get("intervention"):
        print(f"\n   🚨 INTERVENTION TRIGGERED!")
        print(f"      Type: {result['intervention'].get('type')}")
        print(f"      Message: {result['intervention'].get('message', '')[:100]}...")

    return result

def simulate_interaction_error(session_id: str, error_count: int):
    """Simulate interaction errors by updating session directly."""
    mongo_db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"consecutive_errors": error_count, "last_activity": datetime.utcnow()}}
    )
    print(f"\n📝 Set consecutive_errors to {error_count}")

def cleanup_session(session_id: str):
    """Remove test session."""
    mongo_db.sessions.delete_one({"session_id": session_id})
    print(f"\n🧹 Cleaned up test session: {session_id}")

def main():
    print("\n" + "="*60)
    print("🧪 MULTI-SIGNAL STRUGGLE DETECTION TEST")
    print("="*60)
    print("\nThis test simulates:")
    print("  - Audio signals (hesitation, pauses, volume)")
    print("  - Visual signals (emotion, engagement, attention)")
    print("  - Interaction signals (errors)")
    print("\nWatch the TeachingAssistant logs for multi-signal processing!")
    print("  tail -f /Users/gaganarora/Desktop/ai_tutor/logs/teaching_assistant.log")

    # Create test session
    session_id = create_test_session()

    try:
        # Test 1: Normal state - no struggle
        print("\n" + "="*60)
        print("TEST 1: Normal state (no struggle expected)")
        print("="*60)
        send_signals(
            session_id,
            audio={"hesitation_score": 0.1, "long_pauses": 0, "volume_trend": "stable", "is_speaking": True},
            visual={"emotion": "neutral", "engagement_score": 0.9, "is_distracted": False, "face_detected": True},
            description="Student engaged, speaking normally"
        )
        time.sleep(1)

        # Test 2: Audio hesitation only
        print("\n" + "="*60)
        print("TEST 2: Audio hesitation (moderate struggle)")
        print("="*60)
        send_signals(
            session_id,
            audio={"hesitation_score": 0.6, "long_pauses": 3, "volume_trend": "decreasing", "is_speaking": False},
            visual={"emotion": "neutral", "engagement_score": 0.8, "is_distracted": False, "face_detected": True},
            description="Student hesitating, volume dropping"
        )
        time.sleep(1)

        # Test 3: Visual frustration
        print("\n" + "="*60)
        print("TEST 3: Visual frustration (moderate struggle)")
        print("="*60)
        send_signals(
            session_id,
            audio={"hesitation_score": 0.2, "long_pauses": 1, "volume_trend": "stable", "is_speaking": True},
            visual={"emotion": "frustrated", "emotion_struggle_score": 0.7, "engagement_score": 0.5, "is_distracted": False, "face_detected": True},
            description="Student showing frustration on face"
        )
        time.sleep(1)

        # Test 4: Combined audio + visual struggle
        print("\n" + "="*60)
        print("TEST 4: Combined audio + visual (high struggle)")
        print("="*60)
        send_signals(
            session_id,
            audio={"hesitation_score": 0.8, "long_pauses": 4, "volume_trend": "decreasing", "is_speaking": False},
            visual={"emotion": "confused", "emotion_struggle_score": 0.6, "engagement_score": 0.3, "is_distracted": True, "face_detected": True},
            description="Student confused, hesitating, looking away"
        )
        time.sleep(1)

        # Test 5: Add interaction errors for full multi-signal
        print("\n" + "="*60)
        print("TEST 5: Full multi-signal (interaction + audio + visual)")
        print("="*60)
        simulate_interaction_error(session_id, 3)  # 3 consecutive errors
        send_signals(
            session_id,
            audio={"hesitation_score": 0.7, "long_pauses": 3, "volume_trend": "decreasing", "is_speaking": False},
            visual={"emotion": "frustrated", "emotion_struggle_score": 0.8, "engagement_score": 0.2, "is_distracted": True, "face_detected": True},
            description="3 errors + hesitating + frustrated + disengaged"
        )
        time.sleep(1)

        print("\n" + "="*60)
        print("✅ TEST COMPLETE")
        print("="*60)
        print("\nCheck the logs for multi-signal processing details:")
        print("  - Interaction scores (errors, pauses, hints)")
        print("  - Audio scores (hesitation, silence, volume)")
        print("  - Visual scores (emotion, engagement, attention)")
        print("  - Combined struggle score and intervention decisions")

    finally:
        cleanup_session(session_id)

if __name__ == "__main__":
    main()

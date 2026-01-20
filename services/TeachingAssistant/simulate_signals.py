#!/usr/bin/env python3
"""
Live Signal Simulator for Multi-Signal Struggle Detection
Run this while using the frontend to simulate Vision Agents signals.

Usage:
  python simulate_signals.py [mode]

Modes:
  normal     - Student is doing fine (default)
  hesitant   - Audio hesitation (pausing, low confidence)
  frustrated - Visual frustration (negative emotion)
  confused   - Combined confusion signals
  struggling - Full struggle (all signals high)
"""

import requests
import time
import sys
import random

BASE_URL = "http://localhost:8002"

SIGNAL_PRESETS = {
    "normal": {
        "audio": {"hesitation_score": 0.1, "long_pauses": 0, "volume_trend": "stable", "is_speaking": True},
        "visual": {"emotion": "engaged", "engagement_score": 0.9, "is_distracted": False, "face_detected": True},
    },
    "hesitant": {
        "audio": {"hesitation_score": 0.7, "long_pauses": 3, "volume_trend": "decreasing", "is_speaking": False},
        "visual": {"emotion": "neutral", "engagement_score": 0.7, "is_distracted": False, "face_detected": True},
    },
    "frustrated": {
        "audio": {"hesitation_score": 0.3, "long_pauses": 1, "volume_trend": "stable", "is_speaking": True},
        "visual": {"emotion": "frustrated", "emotion_struggle_score": 0.8, "engagement_score": 0.4, "is_distracted": False, "face_detected": True},
    },
    "confused": {
        "audio": {"hesitation_score": 0.6, "long_pauses": 2, "volume_trend": "decreasing", "is_speaking": False},
        "visual": {"emotion": "confused", "emotion_struggle_score": 0.7, "engagement_score": 0.5, "is_distracted": True, "face_detected": True},
    },
    "struggling": {
        "audio": {"hesitation_score": 0.9, "long_pauses": 5, "volume_trend": "decreasing", "is_speaking": False},
        "visual": {"emotion": "frustrated", "emotion_struggle_score": 0.9, "engagement_score": 0.2, "is_distracted": True, "face_detected": True},
    },
}

def get_active_session():
    """Get the first active session."""
    try:
        resp = requests.get(f"{BASE_URL}/sessions/active?api_key=dev-observer-key-12345")
        sessions = resp.json().get("sessions", [])
        if sessions:
            return sessions[0]["session_id"]
    except:
        pass
    return None

def send_signals(session_id, mode):
    """Send signals for the given mode."""
    preset = SIGNAL_PRESETS.get(mode, SIGNAL_PRESETS["normal"])

    # Add slight randomness
    audio = preset["audio"].copy()
    visual = preset["visual"].copy()
    audio["hesitation_score"] = min(1.0, audio["hesitation_score"] + random.uniform(-0.1, 0.1))
    visual["engagement_score"] = max(0.0, min(1.0, visual["engagement_score"] + random.uniform(-0.1, 0.1)))

    try:
        resp = requests.post(
            f"{BASE_URL}/signals/update",
            json={"session_id": session_id, "audio_signals": audio, "visual_signals": visual}
        )
        result = resp.json()

        intervention = result.get("intervention")
        if intervention:
            return f"🚨 INTERVENTION: {intervention['type']}"
        return "✓"
    except Exception as e:
        return f"❌ Error: {e}"

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    if mode not in SIGNAL_PRESETS:
        print(f"Unknown mode: {mode}")
        print(f"Available modes: {', '.join(SIGNAL_PRESETS.keys())}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🎭 LIVE SIGNAL SIMULATOR - Mode: {mode.upper()}")
    print(f"{'='*60}")
    print(f"\nWaiting for active session...")
    print(f"Start a session in the frontend: http://localhost:3000")
    print(f"\nPress Ctrl+C to stop")
    print(f"\n{'─'*60}")

    try:
        while True:
            session_id = get_active_session()

            if session_id:
                result = send_signals(session_id, mode)
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Session: {session_id[:20]}... | Mode: {mode:10} | {result}")
            else:
                print(f"⏳ No active session - waiting...", end="\r")

            time.sleep(2)  # Send signals every 2 seconds

    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print("Simulator stopped.")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

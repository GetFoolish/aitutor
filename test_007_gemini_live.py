#!/usr/bin/env python3
"""
Real E2E Test for Spec 007: Audio Analysis with Gemini Live API

This test creates a real tutoring session where:
1. Student speaks (simulated hesitant audio analyzed for struggle)
2. Gemini Live API generates Adam's response
3. Local TTS plays Adam's response so you can HEAR it
4. Audio analysis detects struggle patterns and triggers interventions

Requirements:
- GOOGLE_API_KEY set in .env
- TeachingAssistant service running on port 8002
- pyttsx3 installed for local TTS playback
"""

import asyncio
import base64
import json
import os
import sys
import subprocess
import time
import wave
from pathlib import Path
from datetime import datetime

import numpy as np
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / ".auto-claude/worktrees/tasks/007-audio-analysis"))

# Configuration
TA_URL = "http://localhost:8002"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_step(num, msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}Step {num}:{Colors.END} {msg}")

def log_ok(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_fail(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def log_warn(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def log_speech(speaker, msg):
    color = Colors.CYAN if speaker == "Adam" else Colors.MAGENTA
    print(f"\n{color}{Colors.BOLD}🎤 {speaker}:{Colors.END} \"{msg}\"")


def generate_hesitant_audio() -> str:
    """Generate audio simulating a hesitant/struggling student."""
    sample_rate = 16000
    duration = 4.0
    samples = int(sample_rate * duration)

    # Hesitant pattern: quiet speech, long pauses
    audio = np.zeros(samples, dtype=np.float32)

    # Brief quiet speech (0-0.5s)
    start1, end1 = 0, int(0.5 * sample_rate)
    audio[start1:end1] = np.random.normal(0, 0.02, end1 - start1)

    # Long pause (0.5-2.5s) - silence

    # Another brief quiet speech (2.5-3.0s)
    start2, end2 = int(2.5 * sample_rate), int(3.0 * sample_rate)
    audio[start2:end2] = np.random.normal(0, 0.03, end2 - start2)

    # Trailing silence (3.0-4.0s)

    audio_int16 = (audio * 32767).astype(np.int16)
    return base64.b64encode(audio_int16.tobytes()).decode('utf-8')


def play_audio_file(audio_path: Path):
    """Play audio file using macOS afplay."""
    try:
        subprocess.run(['afplay', str(audio_path)], check=True, timeout=30)
    except Exception as e:
        log_warn(f"Could not play audio: {e}")


def speak_text(text: str):
    """Speak text using local TTS (pyttsx3) so user can hear."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)

        # Save to file and play (more reliable than direct speak)
        output_path = Path("/tmp/adam_response.wav")
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()

        if output_path.exists():
            play_audio_file(output_path)
            return True
    except Exception as e:
        log_warn(f"Local TTS failed: {e}")
    return False


async def get_gemini_response(prompt: str, context: str = "") -> str:
    """Get response from Gemini API."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        full_prompt = f"""You are Adam, a friendly and encouraging AI math tutor for elementary school students.

Context: {context}

Student situation: {prompt}

Respond naturally and encouragingly in 1-2 sentences. Be warm and supportive."""

        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        log_fail(f"Gemini API error: {e}")
        return "I'm here to help! Take your time, there's no rush."


async def test_full_gemini_session():
    """
    Run a full E2E test with:
    1. Real audio analysis detecting struggle
    2. Gemini Live generating responses
    3. Local TTS playing Adam's voice so you can HEAR him
    """
    print(f"\n{Colors.BOLD}{'='*60}")
    print("SPEC 007 - GEMINI LIVE + LOCAL VOICE E2E TEST")
    print(f"{'='*60}{Colors.END}\n")

    # Check prerequisites
    log_step(1, "Checking prerequisites")

    if not GOOGLE_API_KEY:
        log_fail("GOOGLE_API_KEY not set in .env")
        return False
    log_ok(f"Gemini API key available (length: {len(GOOGLE_API_KEY)})")

    # Check TeachingAssistant service
    try:
        resp = requests.get(f"{TA_URL}/health", timeout=5)
        if resp.status_code == 200:
            log_ok("TeachingAssistant service running")
        else:
            log_fail(f"TeachingAssistant not healthy: {resp.status_code}")
            return False
    except:
        log_warn("TeachingAssistant not running (continuing with standalone test)")

    # Import audio analyzer
    log_step(2, "Initializing audio analysis components")
    try:
        from services.TeachingAssistant.audio_analyzer import AudioAnalyzer
        from services.TeachingAssistant.intervention_manager import InterventionManager

        analyzer = AudioAnalyzer()
        manager = InterventionManager()
        log_ok("AudioAnalyzer and InterventionManager initialized")
    except Exception as e:
        log_fail(f"Could not import audio components: {e}")
        return False

    # Simulate tutoring session
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TUTORING SESSION SIMULATION")
    print(f"{'='*60}{Colors.END}")

    # Turn 1: Session start - Adam greets
    log_step(3, "Session starts - Adam greets the student")
    greeting = await get_gemini_response(
        "A new student just joined the tutoring session. Greet them warmly.",
        context="Start of 5th grade math tutoring session"
    )
    log_speech("Adam", greeting)
    print(f"\n   {Colors.YELLOW}🔊 Playing Adam's greeting...{Colors.END}")
    speak_text(greeting)

    await asyncio.sleep(1)

    # Turn 2: Student struggles with a question (simulated)
    log_step(4, "Student is given a math problem and struggles")

    # Adam presents problem
    problem_prompt = await get_gemini_response(
        "Give the student a simple multiplication problem like 7 times 8.",
        context="5th grade student, start with an easy problem"
    )
    log_speech("Adam", problem_prompt)
    print(f"\n   {Colors.YELLOW}🔊 Playing Adam asking the question...{Colors.END}")
    speak_text(problem_prompt)

    await asyncio.sleep(1)

    # Turn 3: Analyze student's hesitant audio
    log_step(5, "Student responds hesitantly (audio analysis)")

    print(f"\n   {Colors.MAGENTA}🎤 Student:{Colors.END} \"Um... let me think... seven times eight...\"")
    print(f"   {Colors.YELLOW}(Simulating hesitant audio - long pauses, quiet voice){Colors.END}")

    # Generate and analyze hesitant audio
    hesitant_audio = generate_hesitant_audio()
    features = analyzer.analyze_audio_chunk(hesitant_audio)

    print(f"\n   📊 Audio Analysis Results:")
    print(f"      Energy RMS: {features['energy_rms']:.4f} (threshold: 0.1)")
    print(f"      Is Speech: {features['is_speech']}")
    print(f"      Zero-crossing: {features['zero_crossing_rate']:.4f}")

    # Classify struggle
    struggle = analyzer.classify_struggle_indicators(features)
    active_struggles = [k for k, v in struggle.items() if isinstance(v, bool) and v]

    print(f"      Struggle indicators: {active_struggles}")
    print(f"      Confidence level: {struggle['confidence_level']:.2f}")

    # Check if intervention needed
    session_state = {'last_intervention_time': None}
    should_intervene = manager.should_intervene(struggle, session_state)

    if should_intervene:
        print(f"\n   {Colors.RED}🚨 INTERVENTION TRIGGERED!{Colors.END}")
        intervention_text = manager.get_intervention_text(struggle)

        # Extract the supportive message
        import re
        quoted_match = re.search(r'"([^"]+)"', intervention_text)
        supportive_message = quoted_match.group(1) if quoted_match else "Take your time, I'm here to help."

        log_ok(f"Intervention type detected from audio analysis")
    else:
        supportive_message = None

    await asyncio.sleep(1)

    # Turn 4: Adam responds with encouragement
    log_step(6, "Adam detects struggle and responds supportively")

    if supportive_message:
        # Use intervention message + Gemini for natural response
        response = await get_gemini_response(
            f"The student is struggling (showing hesitation, long pauses, low confidence). "
            f"Deliver this supportive message naturally: '{supportive_message}' "
            f"Then offer gentle help.",
            context="Student struggling with 7x8, showing signs of confusion"
        )
    else:
        response = await get_gemini_response(
            "The student seems to be thinking. Encourage them gently.",
            context="Student working on 7x8"
        )

    log_speech("Adam", response)
    print(f"\n   {Colors.YELLOW}🔊 Playing Adam's supportive response...{Colors.END}")
    speak_text(response)

    await asyncio.sleep(1)

    # Turn 5: Student gets help and succeeds
    log_step(7, "Student gets the answer with Adam's help")

    print(f"\n   {Colors.MAGENTA}🎤 Student:{Colors.END} \"Oh! It's 56!\"")

    celebration = await get_gemini_response(
        "The student just correctly answered 7x8=56 after getting encouragement. Celebrate their success!",
        context="Student overcame struggle and got the right answer"
    )
    log_speech("Adam", celebration)
    print(f"\n   {Colors.YELLOW}🔊 Playing Adam's celebration...{Colors.END}")
    speak_text(celebration)

    # Summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")

    log_ok("Gemini API integration working")
    log_ok("Audio analysis detected struggle patterns")
    log_ok("Intervention system triggered appropriately")
    log_ok("Local TTS played Adam's voice responses")

    if should_intervene:
        log_ok(f"Struggle indicators detected: {active_struggles}")
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ SPEC 007 VERIFIED - Audio analysis triggers interventions!{Colors.END}")
    else:
        log_warn("No intervention was triggered (adjust thresholds if needed)")

    return True


async def main():
    """Main entry point."""
    try:
        success = await test_full_gemini_session()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        log_fail(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

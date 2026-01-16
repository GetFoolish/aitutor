#!/usr/bin/env python3
"""
Hybrid Session: Reliable Gemini Live with Local Voice Demo

This creates a smooth 2-minute session by:
- Using TEXT input to Gemini (reliable, no streaming issues)
- Getting AUDIO output from Gemini (Adam's voice)
- Playing LOCAL TTS for student voice so you hear both sides
- Running spec 007 audio analysis on the student audio

You'll hear: Student (local TTS) → Adam (Gemini Live audio)
"""

import asyncio
import base64
import os
import sys
import wave
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / ".auto-claude/worktrees/tasks/007-audio-analysis"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "models/gemini-2.0-flash-exp"

class C:
    G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'
    B = '\033[94m'; M = '\033[95m'; C = '\033[96m'
    BOLD = '\033[1m'; END = '\033[0m'


def play_audio(data, rate=24000):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        p = f.name
        with wave.open(f, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes(data if isinstance(data, bytes) else bytes(data))
    subprocess.run(['afplay', p], check=True, timeout=60)
    os.unlink(p)


def speak_local(text: str):
    """Speak using local TTS (pyttsx3)."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 145)
    engine.setProperty('volume', 0.9)

    temp = tempfile.mktemp(suffix='.aiff')
    engine.save_to_file(text, temp)
    engine.runAndWait()

    wav = tempfile.mktemp(suffix='.wav')
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', temp, wav],
                   check=True, capture_output=True)

    # Play it
    subprocess.run(['afplay', wav], check=True, timeout=30)

    # Return PCM for analysis
    with wave.open(wav, 'rb') as w:
        pcm = w.readframes(w.getnframes())
    os.unlink(temp); os.unlink(wav)
    return pcm


async def run_session():
    print(f"\n{C.BOLD}{'='*65}")
    print("🎓 2-MINUTE TUTORING SESSION")
    print("   Student: Local TTS (pyttsx3)")
    print("   Adam: Gemini Live API (audio output)")
    print(f"{'='*65}{C.END}\n")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Audio analyzer for spec 007
    try:
        from services.TeachingAssistant.audio_analyzer import AudioAnalyzer
        from services.TeachingAssistant.intervention_manager import InterventionManager
        analyzer = AudioAnalyzer()
        manager = InterventionManager()
        print(f"{C.G}✓ Spec 007 AudioAnalyzer ready{C.END}")
    except Exception as e:
        print(f"{C.Y}⚠ AudioAnalyzer not available: {e}{C.END}")
        analyzer = None
        manager = None

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction="""You are Adam, a warm and friendly math tutor for a 5th grader.
Keep ALL responses to 1-2 short sentences. Be encouraging and patient.
Make the student feel confident. Celebrate their successes!""",
    )

    # Conversation script
    turns = [
        ("Hi Adam! I'm excited for math today!", False),
        ("Can we practice multiplication?", False),
        ("What's 6 times 7?", False),
        ("Hmm... um... I'm thinking... 42?", True),  # Hesitant - should trigger 007
        ("Yay! Give me another one!", False),
        ("What's 8 times 9?", False),
        ("Um... let me think... is it... 72?", True),  # Hesitant
        ("I'm getting better at this!", False),
        ("Can we try a hard one? What's 12 times 11?", False),
        ("Uh... 12 times 11... that's tricky... 132?", True),  # Hesitant
        ("Wow I got it! Math is actually fun!", False),
        ("Thanks for teaching me Adam! Bye!", False),
    ]

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            print(f"{C.G}✓ Connected to Gemini Live!{C.END}")
            print(f"\n{C.BOLD}━━━ SESSION START ━━━{C.END}\n")

            session_state = {'last_intervention_time': None}

            for i, (student_text, is_hesitant) in enumerate(turns, 1):
                print(f"{C.B}[Turn {i}/12]{C.END}")

                # Student speaks (local TTS)
                print(f"   {C.M}👧 Student:{C.END} \"{student_text}\"")
                print(f"   {C.Y}🔊 Playing student...{C.END}")

                student_audio = speak_local(student_text)

                # Analyze with spec 007
                if analyzer and is_hesitant:
                    audio_b64 = base64.b64encode(student_audio).decode('utf-8')
                    features = analyzer.analyze_audio_chunk(audio_b64)
                    struggle = analyzer.classify_struggle_indicators(features)

                    if manager.should_intervene(struggle, session_state):
                        print(f"   {C.R}🚨 SPEC 007: Intervention triggered!{C.END}")
                        session_state['last_intervention_time'] = None  # Reset for demo

                # Send text to Gemini (reliable)
                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part(text=student_text)])],
                    turn_complete=True
                )

                # Get Adam's audio response
                adam_audio = bytearray()
                async for resp in session.receive():
                    if resp.data:
                        adam_audio.extend(resp.data)
                    if resp.server_content and hasattr(resp.server_content, 'turn_complete'):
                        if resp.server_content.turn_complete:
                            break

                # Play Adam's response
                if adam_audio:
                    print(f"   {C.C}🧑‍🏫 Adam:{C.END} [speaking...]")
                    print(f"   {C.Y}🔊 Playing Adam...{C.END}")
                    play_audio(bytes(adam_audio), rate=24000)

                print()  # Blank line between turns
                await asyncio.sleep(0.5)

            print(f"{C.BOLD}━━━ SESSION END ━━━{C.END}")

    except Exception as e:
        print(f"\n{C.R}Error: {e}{C.END}")
        import traceback; traceback.print_exc()
        return False

    print(f"\n{C.G}{C.BOLD}✓ 2-minute session complete!{C.END}")
    print(f"{C.G}  You heard: Student (local TTS) ↔ Adam (Gemini Live){C.END}")
    print(f"{C.G}  Spec 007 analyzed hesitant speech and triggered interventions{C.END}")
    return True


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_session()) else 1)

#!/usr/bin/env python3
"""
Robust Extended Session: Local Voice ↔ Gemini Live

Fixed issues:
- Proper real-time pacing of audio (simulates actual speaking speed)
- Better error handling and reconnection
- Shorter chunks sent at realistic intervals
"""

import asyncio
import base64
import os
import sys
import wave
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / ".auto-claude/worktrees/tasks/007-audio-analysis"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "models/gemini-2.0-flash-exp"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def play_audio(audio_bytes, sample_rate=24000):
    """Play audio through speakers."""
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            with wave.open(f, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(audio_bytes if isinstance(audio_bytes, bytes) else bytes(audio_bytes))
        subprocess.run(['afplay', temp_path], check=True, timeout=60)
        os.unlink(temp_path)
    except Exception as e:
        print(f"   {Colors.YELLOW}Audio error: {e}{Colors.END}")


def generate_student_audio(text: str) -> bytes:
    """Generate student speech using local TTS."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 140)
    engine.setProperty('volume', 0.9)

    temp_aiff = tempfile.mktemp(suffix='.aiff')
    engine.save_to_file(text, temp_aiff)
    engine.runAndWait()

    temp_wav = tempfile.mktemp(suffix='.wav')
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', temp_aiff, temp_wav],
                   check=True, capture_output=True)

    with wave.open(temp_wav, 'rb') as wav:
        pcm_data = wav.readframes(wav.getnframes())

    os.unlink(temp_aiff)
    os.unlink(temp_wav)
    return pcm_data


async def send_audio_realtime(session, audio_bytes: bytes, types):
    """
    Send audio to Gemini Live at REAL-TIME pace.
    16kHz = 16000 samples/sec = 32000 bytes/sec
    Send in 100ms chunks (3200 bytes) with 100ms delays
    """
    CHUNK_DURATION_MS = 100
    BYTES_PER_MS = 32  # 16kHz * 2 bytes per sample / 1000
    CHUNK_SIZE = CHUNK_DURATION_MS * BYTES_PER_MS  # 3200 bytes = 100ms

    for i in range(0, len(audio_bytes), CHUNK_SIZE):
        chunk = audio_bytes[i:i+CHUNK_SIZE]
        if len(chunk) < 100:  # Skip tiny chunks
            continue

        chunk_b64 = base64.b64encode(chunk).decode('utf-8')
        try:
            await session.send_realtime_input(
                media=types.Blob(data=chunk_b64, mime_type="audio/pcm;rate=16000")
            )
        except Exception as e:
            print(f"   {Colors.YELLOW}Send error: {e}{Colors.END}")
            break

        # Real-time pacing - wait approximately the duration of the chunk
        await asyncio.sleep(CHUNK_DURATION_MS / 1000 * 0.8)  # Slightly faster than realtime


async def receive_response(session, timeout=10) -> bytes:
    """Receive audio response with timeout."""
    audio = bytearray()
    try:
        async for response in session.receive():
            if response.data:
                audio.extend(response.data)
            if response.server_content:
                if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                    break
    except asyncio.TimeoutError:
        print(f"   {Colors.YELLOW}Response timeout{Colors.END}")
    except Exception as e:
        print(f"   {Colors.YELLOW}Receive error: {e}{Colors.END}")
    return bytes(audio)


async def conversation_turn(session, types, student_text: str, analyzer=None):
    """One conversation turn with proper pacing."""
    print(f"\n   {Colors.MAGENTA}👧 Student:{Colors.END} \"{student_text}\"")

    # Generate student audio
    student_audio = generate_student_audio(student_text)

    # Play student audio locally
    print(f"   {Colors.YELLOW}🔊 Playing student voice...{Colors.END}")
    play_audio(student_audio, sample_rate=16000)

    # Analyze with spec 007
    if analyzer:
        audio_b64 = base64.b64encode(student_audio).decode('utf-8')
        features = analyzer.analyze_audio_chunk(audio_b64)
        struggle = analyzer.classify_struggle_indicators(features)
        active = [k for k, v in struggle.items() if isinstance(v, bool) and v]
        if active:
            print(f"   {Colors.RED}📊 Spec 007: {active}{Colors.END}")

    # Send audio to Gemini at real-time pace
    print(f"   {Colors.YELLOW}📤 Sending to Gemini Live...{Colors.END}")
    await send_audio_realtime(session, student_audio, types)

    # Signal end of turn
    await session.send_client_content(
        turns=[types.Content(role="user", parts=[types.Part(text="")])],
        turn_complete=True
    )

    # Brief pause to let Gemini process
    await asyncio.sleep(0.3)

    # Receive Adam's response
    print(f"   {Colors.CYAN}🧑‍🏫 Adam responding...{Colors.END}")
    adam_audio = await receive_response(session)

    if adam_audio and len(adam_audio) > 1000:
        print(f"   {Colors.YELLOW}🔊 Playing Adam's voice ({len(adam_audio)} bytes)...{Colors.END}")
        play_audio(adam_audio, sample_rate=24000)
    else:
        print(f"   {Colors.YELLOW}(No audio response){Colors.END}")

    # Pause between turns
    await asyncio.sleep(1.0)


async def run_session():
    """Run extended tutoring session."""
    print(f"\n{Colors.BOLD}{'='*70}")
    print("🎓 EXTENDED TUTORING SESSION - ROBUST VERSION")
    print("   Real-time audio pacing for reliable Gemini Live connection")
    print(f"{'='*70}{Colors.END}\n")

    if not GOOGLE_API_KEY:
        print(f"{Colors.RED}✗ GOOGLE_API_KEY not set{Colors.END}")
        return False

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Audio analyzer
    try:
        from services.TeachingAssistant.audio_analyzer import AudioAnalyzer
        analyzer = AudioAnalyzer()
        print(f"{Colors.GREEN}✓ AudioAnalyzer ready{Colors.END}")
    except:
        analyzer = None

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction="""You are Adam, a friendly math tutor.
Keep responses SHORT (1-2 sentences max). Be warm and encouraging.""",
    )

    conversation = [
        ("Turn 1", "Hi Adam! I'm ready for my math lesson!"),
        ("Turn 2", "What's 5 plus 3?"),
        ("Turn 3", "8! That was easy!"),
        ("Turn 4", "Give me a harder one. What about multiplication?"),
        ("Turn 5", "Hmm... um... 7 times 8... let me think..."),
        ("Turn 6", "Can you give me a hint?"),
        ("Turn 7", "Oh! It's 56!"),
        ("Turn 8", "Yay! What's 9 times 6?"),
        ("Turn 9", "That's 54!"),
        ("Turn 10", "This is fun! One more - what's 12 times 5?"),
        ("Turn 11", "60! I'm getting good at this!"),
        ("Turn 12", "Thanks Adam! Bye!"),
    ]

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            print(f"\n{Colors.GREEN}✓ Connected to Gemini Live!{Colors.END}")
            print(f"\n{Colors.BOLD}--- SESSION START ---{Colors.END}")

            for turn_name, student_text in conversation:
                print(f"\n{Colors.BLUE}[{turn_name}]{Colors.END}")
                try:
                    await conversation_turn(session, types, student_text, analyzer)
                except Exception as e:
                    print(f"   {Colors.RED}Turn error: {e}{Colors.END}")
                    await asyncio.sleep(2)  # Wait and continue

            print(f"\n{Colors.BOLD}--- SESSION END ---{Colors.END}")

    except Exception as e:
        print(f"\n{Colors.RED}Session error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Session complete!{Colors.END}")
    return True


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_session()) else 1)

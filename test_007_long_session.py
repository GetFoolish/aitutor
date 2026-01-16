#!/usr/bin/env python3
"""
Extended 2-Minute Tutoring Session: Local Voice ↔ Gemini Live

Full tutoring session with multiple turns:
- Greeting and warmup
- Easy question
- Harder question with struggle
- Hint and encouragement
- Success and celebration
- Another problem
- Session wrap-up

All voices played through speakers - student (local TTS) and Adam (Gemini Live)
"""

import asyncio
import base64
import os
import sys
import wave
import subprocess
import tempfile
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
    """Play PCM audio through speakers."""
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
    engine.setProperty('rate', 135)
    engine.setProperty('volume', 0.85)

    temp_aiff = tempfile.mktemp(suffix='.aiff')
    engine.save_to_file(text, temp_aiff)
    engine.runAndWait()

    temp_wav = tempfile.mktemp(suffix='.wav')
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', temp_aiff, temp_wav], check=True)

    with wave.open(temp_wav, 'rb') as wav:
        pcm_data = wav.readframes(wav.getnframes())

    os.unlink(temp_aiff)
    os.unlink(temp_wav)
    return pcm_data


async def send_audio_to_gemini(session, audio_bytes: bytes, types):
    """Send audio chunks to Gemini Live."""
    chunk_size = 4800
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        chunk_b64 = base64.b64encode(chunk).decode('utf-8')
        await session.send_realtime_input(
            media=types.Blob(data=chunk_b64, mime_type="audio/pcm;rate=16000")
        )
        await asyncio.sleep(0.03)

    await session.send_client_content(
        turns=[types.Content(role="user", parts=[types.Part(text="[audio]")])],
        turn_complete=True
    )


async def receive_gemini_audio(session) -> bytes:
    """Receive audio response from Gemini."""
    audio = bytearray()
    async for response in session.receive():
        if response.data:
            audio.extend(response.data)
        if response.server_content:
            if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                break
    return bytes(audio)


async def conversation_turn(session, types, student_text: str, analyzer=None, turn_num=0):
    """Execute one conversation turn: student speaks → Adam responds."""
    print(f"\n   {Colors.MAGENTA}👧 Student:{Colors.END} \"{student_text}\"")

    # Generate and play student audio
    student_audio = generate_student_audio(student_text)
    print(f"   {Colors.YELLOW}🔊 [Student speaking...]{Colors.END}")
    play_audio(student_audio, sample_rate=16000)

    # Analyze with spec 007
    if analyzer:
        audio_b64 = base64.b64encode(student_audio).decode('utf-8')
        features = analyzer.analyze_audio_chunk(audio_b64)
        struggle = analyzer.classify_struggle_indicators(features)
        active = [k for k, v in struggle.items() if isinstance(v, bool) and v]
        if active:
            print(f"   {Colors.RED}📊 Spec 007: Detected {active}{Colors.END}")

    # Send to Gemini
    await send_audio_to_gemini(session, student_audio, types)

    # Get Adam's response
    adam_audio = await receive_gemini_audio(session)

    if adam_audio:
        print(f"   {Colors.CYAN}🧑‍🏫 Adam:{Colors.END} [responding...]")
        print(f"   {Colors.YELLOW}🔊 [Adam speaking...]{Colors.END}")
        play_audio(adam_audio, sample_rate=24000)

    await asyncio.sleep(0.5)  # Brief pause between turns


async def run_extended_session():
    """Run a 2-minute tutoring session."""
    print(f"\n{Colors.BOLD}{'='*70}")
    print("🎓 EXTENDED TUTORING SESSION (~2 MINUTES)")
    print("   Local Voice (pyttsx3) ↔ Gemini Live API")
    print(f"{'='*70}{Colors.END}\n")

    if not GOOGLE_API_KEY:
        print(f"{Colors.RED}✗ GOOGLE_API_KEY not set{Colors.END}")
        return False

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Initialize audio analyzer
    try:
        from services.TeachingAssistant.audio_analyzer import AudioAnalyzer
        analyzer = AudioAnalyzer()
        print(f"{Colors.GREEN}✓ AudioAnalyzer (spec 007) ready{Colors.END}")
    except:
        analyzer = None

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction="""You are Adam, a warm and patient math tutor for a 5th grade student.
- Keep responses to 1-3 sentences
- Be encouraging and friendly
- When student struggles, offer gentle hints
- Celebrate successes enthusiastically
- Make math fun!""",
    )

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            print(f"\n{Colors.GREEN}✓ Connected to Gemini Live!{Colors.END}")
            print(f"\n{Colors.BOLD}--- SESSION START ---{Colors.END}\n")

            # Turn 1: Greeting
            print(f"{Colors.BLUE}[Turn 1: Greeting]{Colors.END}")
            await conversation_turn(session, types,
                "Hi Adam! I'm ready for my math lesson today!",
                analyzer, 1)

            # Turn 2: Warmup question
            print(f"\n{Colors.BLUE}[Turn 2: Easy warmup]{Colors.END}")
            await conversation_turn(session, types,
                "Can we start with something easy? What's 5 plus 3?",
                analyzer, 2)

            # Turn 3: Answer warmup
            print(f"\n{Colors.BLUE}[Turn 3: Warmup answer]{Colors.END}")
            await conversation_turn(session, types,
                "That's 8!",
                analyzer, 3)

            # Turn 4: Request harder problem
            print(f"\n{Colors.BLUE}[Turn 4: Request multiplication]{Colors.END}")
            await conversation_turn(session, types,
                "Okay, can you give me a multiplication problem now?",
                analyzer, 4)

            # Turn 5: Struggle with problem (spec 007 should detect)
            print(f"\n{Colors.BLUE}[Turn 5: Student struggles]{Colors.END}")
            await conversation_turn(session, types,
                "Hmm... um... let me think... I'm not sure... this is hard...",
                analyzer, 5)

            # Turn 6: Ask for hint
            print(f"\n{Colors.BLUE}[Turn 6: Asking for hint]{Colors.END}")
            await conversation_turn(session, types,
                "Can you give me a hint please? I'm stuck.",
                analyzer, 6)

            # Turn 7: Try again
            print(f"\n{Colors.BLUE}[Turn 7: Trying with hint]{Colors.END}")
            await conversation_turn(session, types,
                "Oh! So I should think of it as groups? Let me try... is it 56?",
                analyzer, 7)

            # Turn 8: Celebrate and move on
            print(f"\n{Colors.BLUE}[Turn 8: Excitement]{Colors.END}")
            await conversation_turn(session, types,
                "Yay! I got it right! Can we do another one?",
                analyzer, 8)

            # Turn 9: New problem
            print(f"\n{Colors.BLUE}[Turn 9: New problem]{Colors.END}")
            await conversation_turn(session, types,
                "What's 9 times 6?",
                analyzer, 9)

            # Turn 10: Quick answer
            print(f"\n{Colors.BLUE}[Turn 10: Quick answer]{Colors.END}")
            await conversation_turn(session, types,
                "Hmm, 9 times 6... that's 54!",
                analyzer, 10)

            # Turn 11: Division
            print(f"\n{Colors.BLUE}[Turn 11: Try division]{Colors.END}")
            await conversation_turn(session, types,
                "Can we try division? What's 24 divided by 4?",
                analyzer, 11)

            # Turn 12: Answer
            print(f"\n{Colors.BLUE}[Turn 12: Division answer]{Colors.END}")
            await conversation_turn(session, types,
                "That's 6! Because 6 times 4 is 24!",
                analyzer, 12)

            # Turn 13: Wrap up
            print(f"\n{Colors.BLUE}[Turn 13: Session ending]{Colors.END}")
            await conversation_turn(session, types,
                "This was really fun Adam! I feel like I'm getting better at math!",
                analyzer, 13)

            # Turn 14: Goodbye
            print(f"\n{Colors.BLUE}[Turn 14: Goodbye]{Colors.END}")
            await conversation_turn(session, types,
                "Thank you for helping me today! Bye Adam!",
                analyzer, 14)

            print(f"\n{Colors.BOLD}--- SESSION END ---{Colors.END}")

    except Exception as e:
        print(f"\n{Colors.RED}✗ Session error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Extended session complete!{Colors.END}")
    print(f"{Colors.GREEN}  Local Voice ↔ Gemini Live working for full tutoring session!{Colors.END}")
    return True


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_extended_session()) else 1)

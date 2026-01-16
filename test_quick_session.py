#!/usr/bin/env python3
"""Quick 4-turn tutoring session to demonstrate specs 007-010"""

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
    subprocess.run(['afplay', p], check=True, timeout=30)
    os.unlink(p)

def speak_local(text: str):
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    temp = tempfile.mktemp(suffix='.aiff')
    engine.save_to_file(text, temp)
    engine.runAndWait()
    wav = tempfile.mktemp(suffix='.wav')
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', temp, wav], check=True, capture_output=True)
    subprocess.run(['afplay', wav], check=True, timeout=30)
    with wave.open(wav, 'rb') as w:
        pcm = w.readframes(w.getnframes())
    os.unlink(temp); os.unlink(wav)
    return pcm

async def run_session():
    print(f"\n{C.BOLD}{'='*60}")
    print("QUICK TUTORING SESSION - Specs 007-010 Demo")
    print(f"{'='*60}{C.END}\n")

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
        print(f"{C.Y}⚠ AudioAnalyzer: {e}{C.END}")
        analyzer = None

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction="You are Adam, a warm math tutor. Keep responses to 1 sentence. Be encouraging!",
    )

    turns = [
        ("Hi Adam! What's 5 plus 3?", False),
        ("8! That was easy!", False),
        ("Hmm... um... what's 7 times 6... I'm not sure...", True),  # Hesitant
        ("42! Thanks Adam, bye!", False),
    ]

    try:
        async with client.aio.live.connect(model="models/gemini-2.0-flash-exp", config=config) as session:
            print(f"{C.G}✓ Connected to Gemini Live!{C.END}")
            print(f"\n{C.BOLD}━━━ SESSION START ━━━{C.END}\n")

            session_state = {'last_intervention_time': None}

            for i, (text, is_hesitant) in enumerate(turns, 1):
                print(f"{C.B}[Turn {i}/4]{C.END}")
                print(f"   {C.M}👧 Student:{C.END} \"{text}\"")

                student_audio = speak_local(text)

                # Spec 007: Analyze audio
                if analyzer and is_hesitant:
                    audio_b64 = base64.b64encode(student_audio).decode('utf-8')
                    features = analyzer.analyze_audio_chunk(audio_b64)
                    struggle = analyzer.classify_struggle_indicators(features)
                    active = [k for k,v in struggle.items() if isinstance(v,bool) and v]
                    if active:
                        print(f"   {C.R}🚨 SPEC 007: Struggle detected - {active}{C.END}")
                    if manager.should_intervene(struggle, session_state):
                        intervention = manager.get_intervention_text(struggle)
                        print(f"   {C.Y}💡 SPEC 010: Intervention - \"{intervention[:50]}...\"{C.END}")

                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part(text=text)])],
                    turn_complete=True
                )

                adam_audio = bytearray()
                async for resp in session.receive():
                    if resp.data:
                        adam_audio.extend(resp.data)
                    if resp.server_content and hasattr(resp.server_content, 'turn_complete'):
                        if resp.server_content.turn_complete:
                            break

                if adam_audio:
                    print(f"   {C.C}🧑‍🏫 Adam:{C.END} [speaking...]")
                    play_audio(bytes(adam_audio), rate=24000)
                print()
                await asyncio.sleep(0.5)

            print(f"{C.BOLD}━━━ SESSION END ━━━{C.END}")

    except Exception as e:
        print(f"\n{C.R}Error: {e}{C.END}")
        return False

    print(f"\n{C.G}{C.BOLD}✓ Session complete!{C.END}")
    print(f"{C.G}  Demonstrated: Local Voice ↔ Gemini Live + Spec 007 Analysis{C.END}")
    return True

if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_session()) else 1)

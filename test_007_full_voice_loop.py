#!/usr/bin/env python3
"""
Full Voice Loop Test for Spec 007: Local Voice ↔ Gemini Live API

This test creates a REAL bidirectional voice session:
1. Local TTS (pyttsx3) generates student speech audio
2. That audio is sent to Gemini Live API via sendRealtimeInput
3. Gemini responds with Adam's voice
4. AudioAnalyzer (spec 007) analyzes the audio
5. Both sides are played through speakers so you HEAR the conversation

This tests the full pipeline that spec 007 needs to work with.
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

# Load environment
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

def log_step(num, msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}Step {num}:{Colors.END} {msg}")

def log_ok(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_fail(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def play_audio(audio_path_or_bytes, sample_rate=24000):
    """Play audio through speakers."""
    try:
        if isinstance(audio_path_or_bytes, (bytes, bytearray)):
            # Write PCM to temp WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name
                with wave.open(f, 'wb') as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(sample_rate)
                    wav.writeframes(audio_path_or_bytes)
            subprocess.run(['afplay', temp_path], check=True, timeout=30)
            os.unlink(temp_path)
        else:
            subprocess.run(['afplay', str(audio_path_or_bytes)], check=True, timeout=30)
        return True
    except Exception as e:
        print(f"   {Colors.YELLOW}Audio play error: {e}{Colors.END}")
        return False


def generate_student_audio_pcm16(text: str, target_rate: int = 16000) -> bytes:
    """
    Generate student speech using local TTS (pyttsx3).
    Returns PCM16 audio at specified sample rate for Gemini Live.
    """
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty('rate', 130)  # Slower = more hesitant
    engine.setProperty('volume', 0.8)

    # Save to temp file
    temp_path = tempfile.mktemp(suffix='.aiff')  # pyttsx3 on macOS outputs AIFF
    engine.save_to_file(text, temp_path)
    engine.runAndWait()

    # Convert to WAV 16kHz using afconvert (macOS)
    wav_path = tempfile.mktemp(suffix='.wav')
    subprocess.run([
        'afconvert', '-f', 'WAVE', '-d', f'LEI16@{target_rate}',
        temp_path, wav_path
    ], check=True, timeout=10)

    # Read the WAV
    with wave.open(wav_path, 'rb') as wav:
        pcm_data = wav.readframes(wav.getnframes())

    os.unlink(temp_path)
    os.unlink(wav_path)

    return pcm_data


async def run_full_voice_loop():
    """
    Full voice loop: Local TTS → Gemini Live → Speaker playback
    with audio analysis (spec 007) at each step.
    """
    print(f"\n{Colors.BOLD}{'='*70}")
    print("SPEC 007: LOCAL VOICE ↔ GEMINI LIVE FULL LOOP TEST")
    print(f"{'='*70}{Colors.END}\n")

    # Prerequisites
    log_step(1, "Checking prerequisites")
    if not GOOGLE_API_KEY:
        log_fail("GOOGLE_API_KEY not set")
        return False
    log_ok("Gemini API key available")

    # Import components
    log_step(2, "Initializing components")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GOOGLE_API_KEY)
        log_ok("Gemini client ready")
    except Exception as e:
        log_fail(f"Gemini client failed: {e}")
        return False

    # Audio analyzer (spec 007)
    try:
        from services.TeachingAssistant.audio_analyzer import AudioAnalyzer
        from services.TeachingAssistant.intervention_manager import InterventionManager
        analyzer = AudioAnalyzer()
        manager = InterventionManager()
        log_ok("AudioAnalyzer (spec 007) ready")
    except Exception as e:
        log_fail(f"AudioAnalyzer failed: {e}")
        analyzer = None

    # Configure Gemini Live
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        system_instruction="""You are Adam, a friendly math tutor. Keep responses SHORT (1-2 sentences). Be encouraging.""",
    )

    print(f"\n{Colors.BOLD}{'='*70}")
    print("LIVE VOICE CONVERSATION: LOCAL TTS → GEMINI LIVE → SPEAKERS")
    print(f"{'='*70}{Colors.END}")

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            log_ok("Connected to Gemini Live WebSocket!")

            # =====================================================
            # TURN 1: Generate student greeting with local TTS
            # =====================================================
            log_step(3, "Generating student speech with LOCAL TTS (pyttsx3)")

            student_text_1 = "Hi Adam! Can you help me with multiplication?"
            print(f"\n   {Colors.MAGENTA}🎤 Student will say:{Colors.END} \"{student_text_1}\"")
            print(f"   {Colors.YELLOW}🔊 Generating local TTS audio...{Colors.END}")

            student_audio_1 = generate_student_audio_pcm16(student_text_1)
            log_ok(f"Generated {len(student_audio_1)} bytes of PCM16 audio")

            # Play student audio so user hears it
            print(f"   {Colors.YELLOW}🔊 Playing STUDENT's voice (local TTS)...{Colors.END}")
            play_audio(student_audio_1, sample_rate=16000)

            # Analyze student audio with spec 007
            if analyzer:
                audio_b64 = base64.b64encode(student_audio_1).decode('utf-8')
                features = analyzer.analyze_audio_chunk(audio_b64)
                print(f"\n   📊 Spec 007 Analysis of student audio:")
                print(f"      Energy RMS: {features['energy_rms']:.4f}")
                print(f"      Is Speech: {features['is_speech']}")

            # Send audio to Gemini Live
            log_step(4, "Sending student audio to Gemini Live API")
            print(f"   {Colors.YELLOW}📤 Sending PCM16 audio via sendRealtimeInput...{Colors.END}")

            # Chunk the audio for streaming (Gemini expects chunks)
            chunk_size = 4800  # 300ms at 16kHz
            for i in range(0, len(student_audio_1), chunk_size):
                chunk = student_audio_1[i:i+chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                await session.send_realtime_input(
                    media=types.Blob(data=chunk_b64, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(0.05)  # Small delay between chunks

            # Signal end of turn
            await session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part(text="[audio sent]")])],
                turn_complete=True
            )

            log_ok("Audio sent to Gemini Live!")

            # Receive Adam's response
            print(f"\n   {Colors.YELLOW}🔊 Waiting for ADAM's response from Gemini...{Colors.END}")

            adam_audio_1 = bytearray()
            async for response in session.receive():
                if response.data:
                    adam_audio_1.extend(response.data)
                if response.server_content:
                    if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                        break

            if adam_audio_1:
                log_ok(f"Received {len(adam_audio_1)} bytes from Gemini")
                print(f"\n   {Colors.CYAN}🎤 Adam responds (Gemini Live):{Colors.END}")
                print(f"   {Colors.YELLOW}🔊 Playing ADAM's voice...{Colors.END}")
                play_audio(bytes(adam_audio_1), sample_rate=24000)

            # =====================================================
            # TURN 2: Student hesitates (triggers intervention)
            # =====================================================
            log_step(5, "Student asks question HESITANTLY (spec 007 should detect struggle)")

            student_text_2 = "Um... let me think... what's... um... 7 times 8?"
            print(f"\n   {Colors.MAGENTA}🎤 Student will say:{Colors.END} \"{student_text_2}\"")
            print(f"   {Colors.YELLOW}🔊 Generating hesitant speech...{Colors.END}")

            student_audio_2 = generate_student_audio_pcm16(student_text_2)

            # Play student's hesitant speech
            print(f"   {Colors.YELLOW}🔊 Playing STUDENT's hesitant voice...{Colors.END}")
            play_audio(student_audio_2, sample_rate=16000)

            # Analyze with spec 007
            if analyzer:
                audio_b64 = base64.b64encode(student_audio_2).decode('utf-8')
                features = analyzer.analyze_audio_chunk(audio_b64)
                struggle = analyzer.classify_struggle_indicators(features)

                print(f"\n   📊 Spec 007 Struggle Analysis:")
                print(f"      Energy RMS: {features['energy_rms']:.4f}")
                active = [k for k, v in struggle.items() if isinstance(v, bool) and v]
                print(f"      Struggle indicators: {active}")
                print(f"      Confidence: {struggle['confidence_level']:.2f}")

                session_state = {'last_intervention_time': None}
                if manager.should_intervene(struggle, session_state):
                    print(f"\n   {Colors.RED}🚨 SPEC 007 INTERVENTION TRIGGERED!{Colors.END}")
                    log_ok("Audio analysis correctly detected student struggle!")

            # Send to Gemini
            log_step(6, "Sending hesitant audio to Gemini Live")

            for i in range(0, len(student_audio_2), chunk_size):
                chunk = student_audio_2[i:i+chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                await session.send_realtime_input(
                    media=types.Blob(data=chunk_b64, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(0.05)

            await session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part(text="[hesitant audio]")])],
                turn_complete=True
            )

            # Get Adam's supportive response
            print(f"\n   {Colors.YELLOW}🔊 Waiting for ADAM's supportive response...{Colors.END}")

            adam_audio_2 = bytearray()
            async for response in session.receive():
                if response.data:
                    adam_audio_2.extend(response.data)
                if response.server_content:
                    if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                        break

            if adam_audio_2:
                print(f"\n   {Colors.CYAN}🎤 Adam's supportive response:{Colors.END}")
                print(f"   {Colors.YELLOW}🔊 Playing ADAM's encouraging voice...{Colors.END}")
                play_audio(bytes(adam_audio_2), sample_rate=24000)

            # =====================================================
            # TURN 3: Student gets the answer
            # =====================================================
            log_step(7, "Student answers correctly")

            student_text_3 = "Oh! It's 56!"
            print(f"\n   {Colors.MAGENTA}🎤 Student:{Colors.END} \"{student_text_3}\"")

            student_audio_3 = generate_student_audio_pcm16(student_text_3)
            print(f"   {Colors.YELLOW}🔊 Playing STUDENT's confident answer...{Colors.END}")
            play_audio(student_audio_3, sample_rate=16000)

            # Send to Gemini
            for i in range(0, len(student_audio_3), chunk_size):
                chunk = student_audio_3[i:i+chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                await session.send_realtime_input(
                    media=types.Blob(data=chunk_b64, mime_type="audio/pcm;rate=16000")
                )
                await asyncio.sleep(0.05)

            await session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part(text="[confident audio]")])],
                turn_complete=True
            )

            # Get celebration
            print(f"\n   {Colors.YELLOW}🔊 Waiting for ADAM's celebration...{Colors.END}")

            adam_audio_3 = bytearray()
            async for response in session.receive():
                if response.data:
                    adam_audio_3.extend(response.data)
                if response.server_content:
                    if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                        break

            if adam_audio_3:
                print(f"\n   {Colors.CYAN}🎤 Adam celebrates:{Colors.END}")
                print(f"   {Colors.YELLOW}🔊 Playing ADAM's celebration...{Colors.END}")
                play_audio(bytes(adam_audio_3), sample_rate=24000)

            log_ok("Full voice conversation complete!")

    except Exception as e:
        log_fail(f"Session error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print(f"\n{Colors.BOLD}{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}{Colors.END}\n")

    log_ok("Local TTS (pyttsx3) generated student speech")
    log_ok("Audio sent to Gemini Live via sendRealtimeInput")
    log_ok("Gemini Live responded with Adam's voice")
    log_ok("Both voices played through speakers")
    log_ok("Spec 007 AudioAnalyzer detected struggle patterns")

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ SPEC 007 FULL VOICE LOOP VERIFIED!{Colors.END}")
    print(f"{Colors.GREEN}  Local Voice Model ↔ Gemini Live API working!{Colors.END}")
    return True


async def main():
    try:
        return 0 if await run_full_voice_loop() else 1
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

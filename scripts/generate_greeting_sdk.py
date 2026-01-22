#!/usr/bin/env python3
"""
Generate Greeting Audio using Cartesia SDK (same as LiveKit plugin).
"""

import os
import sys
import wave
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from cartesia import Cartesia

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = "71a7ad14-091c-4e8e-a314-022ece01c121"  # Charlotte - Heiress (same as live session)

OUTPUT_PATH = Path(__file__).parent.parent / "frontend" / "public" / "avatar-greeting.mp3"

GREETING_TEXT = "Hello! I'm Ms. Davis, your AI math tutor. I can see your scratchpad and I'm ready to help you work through any problem. Let's get started!"

def main():
    print("=" * 60)
    print("Generating intro with Cartesia SDK (same as live TTS)")
    print("=" * 60)
    print(f"Voice: Charlotte - Heiress ({CARTESIA_VOICE_ID})")
    print(f"Text: {GREETING_TEXT}")
    print()

    client = Cartesia(api_key=CARTESIA_API_KEY)

    # Use the same settings as LiveKit plugin
    output_format = {
        "container": "raw",
        "encoding": "pcm_s16le",
        "sample_rate": 16000  # 16kHz for Hedra lip sync
    }

    print("Generating speech...")
    import base64
    audio_data = b""
    for output in client.tts.sse(
        model_id="sonic-2",
        transcript=GREETING_TEXT,
        voice={"id": CARTESIA_VOICE_ID},
        output_format=output_format,
        language="en"
    ):
        # Data is base64 encoded PCM audio
        if hasattr(output, 'data') and output.data:
            audio_data += base64.b64decode(output.data)

    print(f"Generated {len(audio_data)} bytes of raw PCM audio")

    # Convert to WAV first
    wav_path = "/tmp/greeting.wav"
    with wave.open(wav_path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(16000)
        wav.writeframes(audio_data)

    print(f"Saved WAV to {wav_path}")

    # Convert to MP3
    result = subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        str(OUTPUT_PATH)
    ], capture_output=True, text=True)

    if result.returncode == 0:
        file_size = OUTPUT_PATH.stat().st_size / 1024
        print(f"\nSUCCESS! Saved to: {OUTPUT_PATH} ({file_size:.2f} KB)")
        print("\nNow run: python scripts/generate_greeting_video.py")
    else:
        print(f"FFmpeg error: {result.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()

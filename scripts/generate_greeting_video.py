#!/usr/bin/env python3
"""
Generate Greeting Video with Lip Sync using Hedra's API.

This script generates a lip-synced greeting video using the Gemini-generated
audio to match the live tutor voice.

Usage:
    python scripts/generate_greeting_video.py

Output:
    frontend/public/avatar-greeting.mp4
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
OUTPUT_PATH = Path(__file__).parent.parent / "frontend" / "public" / "avatar-greeting.mp4"
TEMP_DIR = Path(__file__).parent.parent / "temp"

# Use Ms. Davis avatar image
AVATAR_IMAGE_PATH = Path(__file__).parent.parent / "frontend" / "public" / "avatar-ms-davis-clean.png"
# Use Gemini-generated audio (matches Kore voice)
AUDIO_PATH = Path(__file__).parent.parent / "frontend" / "public" / "avatar-greeting.mp3"

# Hedra API Base URL
HEDRA_API_BASE = "https://api.hedra.com/web-app/public"

# Character-3 model ID
CHARACTER_3_MODEL_ID = "d1dd37a3-e39a-4854-a298-6510289f9cf2"


def create_asset(asset_type: str, name: str) -> str:
    """Create an asset in Hedra and return the asset ID."""
    print(f"Creating {asset_type} asset: {name}")

    response = requests.post(
        f"{HEDRA_API_BASE}/assets",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": HEDRA_API_KEY,
        },
        json={
            "name": name,
            "type": asset_type,
        }
    )

    if response.status_code != 200:
        print(f"Error creating asset: {response.status_code} - {response.text}")
        return None

    data = response.json()
    asset_id = data.get("id")
    print(f"Created asset with ID: {asset_id}")
    return asset_id


def upload_asset(asset_id: str, file_path: Path) -> bool:
    """Upload a file to an existing asset."""
    print(f"Uploading {file_path.name} to asset {asset_id}...")

    # Determine mime type
    suffix = file_path.suffix.lower()
    mime_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    mime_type = mime_types.get(suffix, "application/octet-stream")

    with open(file_path, "rb") as f:
        response = requests.post(
            f"{HEDRA_API_BASE}/assets/{asset_id}/upload",
            headers={
                "X-API-Key": HEDRA_API_KEY,
            },
            files={
                "file": (file_path.name, f, mime_type)
            }
        )

    if response.status_code != 200:
        print(f"Error uploading asset: {response.status_code} - {response.text}")
        return False

    print(f"Upload successful")
    return True


def get_audio_duration_ms(audio_path: Path) -> int:
    """Get audio duration in milliseconds using ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ], capture_output=True, text=True)

    duration_seconds = float(result.stdout.strip())
    duration_ms = int(duration_seconds * 1000)
    print(f"Audio duration: {duration_seconds:.2f}s ({duration_ms}ms)")
    return duration_ms


def generate_video(image_id: str, audio_id: str, duration_ms: int) -> str:
    """Generate a video using Hedra's Character-3 model."""
    print(f"Generating lip-synced video (duration: {duration_ms}ms)...")

    response = requests.post(
        f"{HEDRA_API_BASE}/generations",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": HEDRA_API_KEY,
        },
        json={
            "type": "video",
            "ai_model_id": CHARACTER_3_MODEL_ID,
            "start_keyframe_id": image_id,
            "audio_id": audio_id,
            "generated_video_inputs": {
                "text_prompt": "Portrait video, looking directly into camera lens, locked eye contact with viewer, gentle friendly smile, perfectly still head position, no head movement, speaking naturally with clear lip movements, professional lighting, centered face composition",
                "resolution": "720p",
                "aspect_ratio": "1:1",
                "duration_ms": duration_ms,
            }
        }
    )

    if response.status_code != 200:
        print(f"Error generating video: {response.status_code} - {response.text}")
        return None

    data = response.json()
    generation_id = data.get("id")
    print(f"Generation started with ID: {generation_id}")
    return generation_id


def poll_generation_status(generation_id: str, timeout_seconds: int = 300) -> str:
    """Poll for generation status and return the video URL when complete."""
    print(f"Polling for generation status (timeout: {timeout_seconds}s)...")

    start_time = time.time()
    last_progress = -1

    while time.time() - start_time < timeout_seconds:
        response = requests.get(
            f"{HEDRA_API_BASE}/generations/{generation_id}/status",
            headers={
                "X-API-Key": HEDRA_API_KEY,
            }
        )

        if response.status_code != 200:
            print(f"Error checking status: {response.status_code} - {response.text}")
            time.sleep(5)
            continue

        data = response.json()
        status = data.get("status")
        progress = data.get("progress", 0)

        # Print progress updates
        progress_pct = int(progress * 100)
        if progress_pct != last_progress:
            print(f"  Status: {status} | Progress: {progress_pct}%", end="\r")
            last_progress = progress_pct

        if status == "complete":
            print()  # New line after progress
            video_url = data.get("url")
            print(f"Generation complete! Video URL: {video_url}")
            return video_url

        if status == "error":
            print()  # New line
            error_msg = data.get("error_message", "Unknown error")
            print(f"Generation failed: {error_msg}")
            return None

        time.sleep(3)

    print("\nGeneration timed out")
    return None


def download_video(url: str, output_path: Path) -> bool:
    """Download video from URL."""
    print(f"Downloading video to {output_path}...")

    response = requests.get(url, stream=True)

    if response.status_code != 200:
        print(f"Error downloading video: {response.status_code}")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    file_size = output_path.stat().st_size / 1024 / 1024
    print(f"Video saved: {output_path} ({file_size:.2f} MB)")
    return True


def main():
    """Main function to generate greeting video."""
    print("=" * 60)
    print("Greeting Video Generator (Lip-Synced)")
    print("=" * 60)

    if not HEDRA_API_KEY:
        print("Error: HEDRA_API_KEY environment variable is not set.")
        sys.exit(1)

    # Check for required files
    if not AVATAR_IMAGE_PATH.exists():
        print(f"Error: Avatar image not found at {AVATAR_IMAGE_PATH}")
        sys.exit(1)

    if not AUDIO_PATH.exists():
        print(f"Error: Audio file not found at {AUDIO_PATH}")
        print("Please run generate_intro_gemini.py first.")
        sys.exit(1)

    print(f"Avatar image: {AVATAR_IMAGE_PATH}")
    print(f"Audio file: {AUDIO_PATH}")

    # Get audio duration
    duration_ms = get_audio_duration_ms(AUDIO_PATH)

    try:
        # Step 1: Create and upload image asset
        print("\n--- Step 1: Upload Avatar Image ---")
        image_asset_id = create_asset("image", "ms_davis_greeting")
        if not image_asset_id:
            raise Exception("Failed to create image asset")

        if not upload_asset(image_asset_id, AVATAR_IMAGE_PATH):
            raise Exception("Failed to upload image")

        # Step 2: Create and upload audio asset
        print("\n--- Step 2: Upload Audio ---")
        audio_asset_id = create_asset("audio", "greeting_audio_kore")
        if not audio_asset_id:
            raise Exception("Failed to create audio asset")

        if not upload_asset(audio_asset_id, AUDIO_PATH):
            raise Exception("Failed to upload audio")

        # Step 3: Generate video
        print("\n--- Step 3: Generate Lip-Synced Video ---")
        generation_id = generate_video(image_asset_id, audio_asset_id, duration_ms)
        if not generation_id:
            raise Exception("Failed to start video generation")

        # Step 4: Poll for completion
        print("\n--- Step 4: Wait for Completion ---")
        video_url = poll_generation_status(generation_id, timeout_seconds=300)
        if not video_url:
            raise Exception("Video generation failed or timed out")

        # Step 5: Download video
        print("\n--- Step 5: Download Video ---")
        if not download_video(video_url, OUTPUT_PATH):
            raise Exception("Failed to download video")

        print("\n" + "=" * 60)
        print(f"SUCCESS! Greeting video saved to: {OUTPUT_PATH}")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Video Avatar Integration Guide

This document explains how the AI Tutor video avatar system works and how to set it up.

## Overview

The video avatar provides a lip-synced talking head that speaks with the AI tutor's voice. It uses:
- **Hedra** for real-time lip-sync video generation
- **Cartesia** for text-to-speech (same voice for intro and live sessions)
- **LiveKit** for real-time audio/video streaming

## Architecture

```
User speaks → Deepgram STT → Gemini LLM → Cartesia TTS → Hedra Lip-Sync → User sees avatar
```

## Required API Keys

Add these to your `.env` file:

```env
# LiveKit (real-time communication)
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# Deepgram (speech-to-text)
DEEPGRAM_API_KEY=your_key

# Google Gemini (LLM)
GEMINI_API_KEY=your_key

# Cartesia (text-to-speech)
CARTESIA_API_KEY=your_key

# Hedra (video avatar)
HEDRA_API_KEY=your_key
USE_HEDRA_AVATAR=true
```

## Avatar Image

The avatar uses a single image for consistency across:
- Idle state video
- Introduction greeting video
- Live session video

**Image location:** `frontend/public/avatar-ms-davis-clean.png`

**Requirements:**
- PNG or JPG format
- Square aspect ratio recommended (will be cropped to 1:1)
- Clear face, front-facing
- Good lighting

## Files Structure

```
frontend/public/
├── avatar-ms-davis-clean.png   # Source avatar image
├── avatar-greeting.mp3         # Intro audio (Cartesia voice)
├── avatar-greeting.mp4         # Intro video with lip-sync
└── avatar-idle-static.mp4      # Idle loop video (no lip movement)

services/LiveKitAgent/
├── agent.py                    # Main agent with Hedra integration
└── tutor_agent.py              # Tutor behavior logic

scripts/
├── generate_greeting_sdk.py    # Generate intro audio with Cartesia
└── generate_greeting_video.py  # Generate lip-synced intro video with Hedra
```

## Setup Steps

### 1. Install Dependencies

```bash
cd aitutor
source venv/bin/activate
pip install cartesia livekit-plugins-hedra
```

### 2. Generate Intro Assets

```bash
# Generate intro audio (uses Cartesia - same voice as live session)
python scripts/generate_greeting_sdk.py

# Generate lip-synced intro video (uses Hedra)
python scripts/generate_greeting_video.py
```

### 3. Start the Agent

```bash
./run_tutor.sh
# Or manually:
python services/LiveKitAgent/agent.py dev
```

### 4. Start Frontend

```bash
cd frontend
npm run dev
```

## How It Works

### Idle State
- Shows `avatar-idle-static.mp4` (10-second loop, no lip movement)
- Speaker button available to play intro greeting

### Intro Greeting
- Click speaker button
- Plays `avatar-greeting.mp4` (lip-synced) with `avatar-greeting.mp3` (audio)
- Same voice as live session (Cartesia Charlotte/Heiress voice)

### Connecting State
- Shows spinner with "CONNECTING..." text
- Appears when session starts, before Hedra video track arrives

### Live Session
- Hedra generates real-time lip-synced video
- Uses same avatar image as intro videos
- Audio routed through Hedra for lip-sync

## Voice Configuration

The Cartesia voice used is **Charlotte - Heiress**:
- Voice ID: `71a7ad14-091c-4e8e-a314-022ece01c121`
- Sample rate: 16000 Hz (required for Hedra)
- Model: `sonic-2`

To change the voice, update in:
1. `services/LiveKitAgent/agent.py` (live session)
2. `scripts/generate_greeting_sdk.py` (intro audio)

## Estimated Costs (per hour)

| Service | Cost |
|---------|------|
| LiveKit | ~$0.24 |
| Deepgram STT | ~$0.26 |
| Gemini LLM | ~$0.50-2.00 |
| Cartesia TTS | ~$6-9 |
| Hedra | ~$1.20-3.00 |
| **Total** | **~$8-15/hour** |

## Troubleshooting

### Avatar not showing in live session
- Check agent logs: `tail -f logs/livekit_agent.log`
- Verify `USE_HEDRA_AVATAR=true` in .env
- Ensure avatar image exists at `frontend/public/avatar-ms-davis-clean.png`

### "Cannot write mode RGBA as JPEG" error
- The agent automatically converts RGBA to RGB
- If using a new image, ensure it's a valid PNG/JPG

### Intro audio sounds wrong
- Regenerate with: `python scripts/generate_greeting_sdk.py`
- Verify Cartesia API key is valid

### Video track not detected
- Check browser console for LiveKit connection logs
- Verify LiveKit credentials in .env

## Customization

### Change Avatar Image
1. Replace `frontend/public/avatar-ms-davis-clean.png`
2. Regenerate intro videos:
   ```bash
   python scripts/generate_greeting_sdk.py
   python scripts/generate_greeting_video.py
   ```
3. Restart agent

### Change Greeting Text
Edit `GREETING_TEXT` in `scripts/generate_greeting_sdk.py`, then regenerate.

### Change Voice
1. Find voice ID from Cartesia dashboard
2. Update `CARTESIA_VOICE_ID` in both:
   - `services/LiveKitAgent/agent.py`
   - `scripts/generate_greeting_sdk.py`
3. Regenerate intro audio and video

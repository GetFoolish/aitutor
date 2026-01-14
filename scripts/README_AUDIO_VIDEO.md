# Avatar Video Audio Guide

## Overview

The avatar idle loop video (`frontend/public/videos/avatar-idle-loop.mp4`) now includes an audio track. This document explains how to manage and customize the audio.

## Current Status

✅ **Video has audio track**: The video includes a stereo audio track (44100Hz)
- Currently: Silent audio track
- Purpose: Ensures video has audio track for compatibility

## Scripts Available

### 1. Generate Video with Audio (Initial Creation)

```bash
./scripts/generate-avatar-idle-video-with-audio.sh
```

Creates a new 2-minute avatar idle loop video with a silent audio track.

**Output**: `frontend/public/videos/avatar-idle-loop.mp4`

### 2. Add/Replace Audio

```bash
./scripts/add-audio-to-avatar-video.sh [audio_type]
```

**Options for `audio_type`:**

1. **Silent** (default):
   ```bash
   ./scripts/add-audio-to-avatar-video.sh silent
   ```
   - Creates a silent audio track
   - Good for compatibility without sound

2. **Background Tone**:
   ```bash
   ./scripts/add-audio-to-avatar-video.sh tone
   ```
   - Adds a subtle 220Hz sine wave tone
   - Very quiet (10% volume) with fade in/out
   - Good for subtle background presence

3. **Custom Audio File**:
   ```bash
   ./scripts/add-audio-to-avatar-video.sh /path/to/your/audio.mp3
   ```
   - Uses your own audio file
   - Automatically loops if shorter than 2 minutes
   - Adds fade in/out for smooth looping
   - Supports: MP3, WAV, M4A, OGG, etc.

## Examples

### Add Background Music

```bash
# Download or use your own music file
./scripts/add-audio-to-avatar-video.sh ~/Music/background-music.mp3
```

### Add Voice Narration

```bash
# Record or use a voice file
./scripts/add-audio-to-avatar-video.sh ~/recordings/avatar-greeting.wav
```

### Add Subtle Tone

```bash
./scripts/add-audio-to-avatar-video.sh tone
```

### Restore Silent Audio

```bash
./scripts/add-audio-to-avatar-video.sh silent
```

## Video Specifications

- **Duration**: 2 minutes (120 seconds)
- **Resolution**: 512x512 pixels
- **Frame Rate**: 30 fps
- **Video Codec**: H.264 (libx264)
- **Audio Codec**: AAC (128kbps)
- **Audio Sample Rate**: 44100 Hz
- **Audio Channels**: Stereo (2)

## Backup

The script automatically creates a backup:
- **Backup location**: `frontend/public/videos/avatar-idle-loop-backup.mp4`
- Created on first run
- Restore manually if needed: `cp avatar-idle-loop-backup.mp4 avatar-idle-loop.mp4`

## Troubleshooting

### Video has no audio track

Run the generation script:
```bash
./scripts/generate-avatar-idle-video-with-audio.sh
```

### Audio is too loud/quiet

Edit the script and adjust the `volume` filter:
```bash
# In add-audio-to-avatar-video.sh, find:
-af "volume=0.1,..."
# Change 0.1 to your desired volume (0.0 = silent, 1.0 = full)
```

### Audio doesn't loop smoothly

The script automatically adds fade in/out. If you need different fade timing, edit:
```bash
# In add-audio-to-avatar-video.sh:
afade=t=in:st=0:d=2,afade=t=out:st=$((DURATION-2)):d=2
# Change 'd=2' to adjust fade duration (in seconds)
```

## Requirements

- **ffmpeg**: Required for video/audio processing
  - Install: `sudo apt-get install ffmpeg` (Ubuntu/Debian)
  - Install: `brew install ffmpeg` (macOS)

## Notes

- The video component (`AvatarIdleLoop.tsx`) plays the video with `muted` attribute
- To hear the audio, you may need to unmute the video element in the component
- Audio is primarily for compatibility and future features
- The video loops seamlessly for continuous playback


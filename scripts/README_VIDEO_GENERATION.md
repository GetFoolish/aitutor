# Generate Avatar Idle Loop Video

This directory contains scripts to generate a 2-minute video loop for the avatar idle state.

## Quick Start

### Option 1: Simple Method (Recommended)

```bash
./scripts/generate-avatar-idle-video-simple.sh
```

This creates a simple 2-minute video with a purple gradient background.

### Option 2: Advanced Method

```bash
./scripts/generate-avatar-idle-video.sh
```

This creates a more sophisticated animated gradient video.

## Requirements

- **ffmpeg** must be installed

### Install ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## What the Script Does

1. Creates a 512x512 pixel video (square format for avatar)
2. Generates a 2-minute (120 second) video
3. Uses purple gradient colors matching the avatar UI theme
4. Saves to `frontend/public/videos/avatar-idle-loop.mp4`
5. Optimizes for web playback (H.264, fast start)

## Video Specifications

- **Resolution**: 512x512 pixels
- **Duration**: 120 seconds (2 minutes)
- **Frame Rate**: 30 fps
- **Format**: MP4 (H.264)
- **Color**: Purple gradient (#7C3AED to #C4B5FD)

## Alternative: Use Your Own Video

If you have your own 2-minute video file:

1. Place it at: `frontend/public/videos/avatar-idle-loop.mp4`
2. Ensure it's:
   - MP4 format
   - 2 minutes long (or it will loop)
   - Square aspect ratio (recommended: 512x512 or 1024x1024)
   - Optimized for web (H.264 codec)

## Troubleshooting

### "ffmpeg is not installed"
Install ffmpeg using the instructions above.

### "Permission denied"
Make the script executable:
```bash
chmod +x scripts/generate-avatar-idle-video*.sh
```

### Video file is still empty
1. Check ffmpeg installation: `ffmpeg -version`
2. Try the simple script first: `./scripts/generate-avatar-idle-video-simple.sh`
3. Check disk space: `df -h`

### Video doesn't loop smoothly
The video should loop seamlessly. If it doesn't:
1. Ensure the video is exactly 2 minutes
2. Use a video editor to make the first and last frames match
3. Or use the generated video which is designed to loop

## Manual Video Creation

If you prefer to create the video manually:

1. Use any video editor (e.g., DaVinci Resolve, Adobe Premiere, or even online tools)
2. Create a 2-minute video with:
   - Square aspect ratio (512x512 or larger)
   - Purple gradient background
   - Smooth animation (optional)
3. Export as MP4 (H.264)
4. Place at: `frontend/public/videos/avatar-idle-loop.mp4`



#!/bin/bash

# Simple script to generate a 2-minute avatar idle loop video
# Creates a minimal video file that will work for testing

set -e

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VIDEO_DIR="$PROJECT_ROOT/frontend/public/videos"
OUTPUT_FILE="$VIDEO_DIR/avatar-idle-loop.mp4"

echo "Generating 2-minute avatar idle loop video..."

# Create videos directory if it doesn't exist
mkdir -p "$VIDEO_DIR"

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed"
    echo ""
    echo "Please install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    exit 1
fi

# Generate a simple 2-minute video with animated gradient
# Using purple theme colors that match the avatar UI
ffmpeg -f lavfi -i "color=c=0x7C3AED:s=512x512:d=120:r=30" \
       -vf "scale=512:512,eq=brightness=0.15:contrast=1.1" \
       -c:v libx264 \
       -preset medium \
       -crf 23 \
       -pix_fmt yuv420p \
       -movflags +faststart \
       -t 120 \
       -y \
       "$OUTPUT_FILE"

if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "✅ Video generated successfully!"
    echo "   Location: $OUTPUT_FILE"
    echo "   Size: $FILE_SIZE"
    echo "   Duration: 2 minutes"
else
    echo "❌ Failed to generate video"
    exit 1
fi



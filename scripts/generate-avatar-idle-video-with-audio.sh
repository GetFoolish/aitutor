#!/bin/bash

# Script to generate a 2-minute avatar idle loop video WITH AUDIO
# This creates an animated gradient video with a silent audio track (or optional background sound)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VIDEO_DIR="$PROJECT_ROOT/frontend/public/videos"
OUTPUT_FILE="$VIDEO_DIR/avatar-idle-loop.mp4"

echo -e "${GREEN}Generating 2-minute avatar idle loop video WITH AUDIO...${NC}"

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg is not installed${NC}"
    echo ""
    echo "Please install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi

# Create videos directory if it doesn't exist
mkdir -p "$VIDEO_DIR"

# Video parameters
DURATION=120  # 2 minutes in seconds
WIDTH=512
HEIGHT=512
FPS=30
AUDIO_SAMPLE_RATE=44100

echo -e "${YELLOW}Step 1: Creating animated gradient video...${NC}"

# Generate animated gradient video
VIDEO_TEMP="$VIDEO_DIR/temp_video.mp4"
ffmpeg -f lavfi -i "color=c=0x7C3AED:s=${WIDTH}x${HEIGHT}:d=${DURATION}:r=${FPS}" \
       -f lavfi -i "color=c=0xC4B5FD:s=${WIDTH}x${HEIGHT}:d=${DURATION}:r=${FPS}" \
       -filter_complex "
         [0:v]scale=${WIDTH}:${HEIGHT}[bg];
         [1:v]scale=${WIDTH}:${HEIGHT},fade=t=in:st=0:d=5:alpha=1,fade=t=out:st=$((DURATION-5)):d=5:alpha=1[fg];
         [bg][fg]blend=all_mode=addition:all_opacity=0.6,
         scale=${WIDTH}:${HEIGHT},
         fps=${FPS}
       " \
       -t ${DURATION} \
       -c:v libx264 \
       -preset medium \
       -crf 23 \
       -pix_fmt yuv420p \
       -movflags +faststart \
       -y \
       "$VIDEO_TEMP" 2>&1 | grep -E "(frame|time|bitrate|error)" || true

# If first method fails, try simpler approach
if [ ! -f "$VIDEO_TEMP" ] || [ ! -s "$VIDEO_TEMP" ]; then
    echo -e "${YELLOW}Trying simpler video generation...${NC}"
    
    ffmpeg -f lavfi -i "color=c=0x7C3AED:s=${WIDTH}x${HEIGHT}:d=${DURATION}:r=${FPS}" \
           -vf "scale=${WIDTH}:${HEIGHT},eq=brightness=0.1:contrast=1.2" \
           -c:v libx264 \
           -preset medium \
           -crf 23 \
           -pix_fmt yuv420p \
           -movflags +faststart \
           -t ${DURATION} \
           -y \
           "$VIDEO_TEMP" 2>&1 | grep -E "(frame|time|bitrate|error)" || true
fi

# Last resort: very simple solid color
if [ ! -f "$VIDEO_TEMP" ] || [ ! -s "$VIDEO_TEMP" ]; then
    echo -e "${YELLOW}Using simplest method...${NC}"
    
    ffmpeg -f lavfi -i "color=c=0x7C3AED:s=${WIDTH}x${HEIGHT}:d=${DURATION}:r=${FPS}" \
           -c:v libx264 \
           -preset ultrafast \
           -crf 28 \
           -pix_fmt yuv420p \
           -movflags +faststart \
           -t ${DURATION} \
           -y \
           "$VIDEO_TEMP"
fi

if [ ! -f "$VIDEO_TEMP" ] || [ ! -s "$VIDEO_TEMP" ]; then
    echo -e "${RED}❌ Failed to generate video${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Video generated${NC}"

echo -e "${YELLOW}Step 2: Creating silent audio track...${NC}"

# Generate silent audio track (required for video to have audio track)
AUDIO_TEMP="$VIDEO_DIR/temp_audio.wav"
ffmpeg -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=${AUDIO_SAMPLE_RATE}" \
       -t ${DURATION} \
       -c:a pcm_s16le \
       -y \
       "$AUDIO_TEMP" 2>&1 | grep -E "(frame|time|bitrate|error)" || true

if [ ! -f "$AUDIO_TEMP" ] || [ ! -s "$AUDIO_TEMP" ]; then
    echo -e "${RED}❌ Failed to generate audio track${NC}"
    rm -f "$VIDEO_TEMP"
    exit 1
fi

echo -e "${GREEN}✅ Audio track generated${NC}"

echo -e "${YELLOW}Step 3: Combining video and audio...${NC}"

# Combine video and audio
ffmpeg -i "$VIDEO_TEMP" \
       -i "$AUDIO_TEMP" \
       -c:v copy \
       -c:a aac \
       -b:a 128k \
       -ar ${AUDIO_SAMPLE_RATE} \
       -shortest \
       -movflags +faststart \
       -y \
       "$OUTPUT_FILE" 2>&1 | grep -E "(frame|time|bitrate|error)" || true

# Cleanup temp files
rm -f "$VIDEO_TEMP" "$AUDIO_TEMP"

# Check if final file was created successfully
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    
    # Verify audio track exists
    AUDIO_STREAMS=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$OUTPUT_FILE" 2>/dev/null | wc -l)
    
    echo -e "${GREEN}✅ Video with audio generated successfully!${NC}"
    echo -e "   Location: $OUTPUT_FILE"
    echo -e "   Size: $FILE_SIZE"
    echo -e "   Duration: 2 minutes (120 seconds)"
    echo -e "   Resolution: ${WIDTH}x${HEIGHT}"
    echo -e "   FPS: ${FPS}"
    
    if [ "$AUDIO_STREAMS" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Audio track: Present${NC}"
        echo -e "   ${BLUE}   Audio: Silent track (stereo, ${AUDIO_SAMPLE_RATE}Hz)${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Audio track: Not detected${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}The video is ready to use!${NC}"
    echo ""
    echo -e "${BLUE}Note: The audio track is silent by default.${NC}"
    echo -e "${BLUE}To add actual sound, you can:${NC}"
    echo -e "${BLUE}  1. Replace the anullsrc with a music file${NC}"
    echo -e "${BLUE}  2. Use a tone generator for a subtle background sound${NC}"
    echo -e "${BLUE}  3. Add voice narration if needed${NC}"
else
    echo -e "${RED}❌ Failed to combine video and audio${NC}"
    exit 1
fi


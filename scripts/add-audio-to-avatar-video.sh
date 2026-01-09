#!/bin/bash

# Script to add audio (music, voice, or tone) to the avatar idle loop video

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
VIDEO_FILE="$VIDEO_DIR/avatar-idle-loop.mp4"
BACKUP_FILE="$VIDEO_DIR/avatar-idle-loop-backup.mp4"

# Audio options
AUDIO_TYPE="${1:-silent}"  # silent, tone, or path to audio file
DURATION=120  # 2 minutes
AUDIO_SAMPLE_RATE=44100

echo -e "${GREEN}Adding Audio to Avatar Idle Video...${NC}"

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg is not installed${NC}"
    exit 1
fi

# Check if video exists
if [ ! -f "$VIDEO_FILE" ]; then
    echo -e "${RED}Error: Video file not found: $VIDEO_FILE${NC}"
    exit 1
fi

# Backup original video
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${YELLOW}Creating backup of original video...${NC}"
    cp "$VIDEO_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup created${NC}"
fi

# Create temp files
TEMP_VIDEO="$VIDEO_DIR/temp_video_audio.mp4"
TEMP_AUDIO="$VIDEO_DIR/temp_audio_audio.wav"

# Cleanup function
cleanup() {
    rm -f "$TEMP_VIDEO" "$TEMP_AUDIO"
}
trap cleanup EXIT

echo -e "${YELLOW}Extracting video (without audio)...${NC}"
ffmpeg -i "$VIDEO_FILE" -c:v copy -an -y "$TEMP_VIDEO" 2>&1 | grep -E "(error|Error)" || true

# Generate audio based on type
case "$AUDIO_TYPE" in
    "silent")
        echo -e "${BLUE}Generating silent audio track...${NC}"
        ffmpeg -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=${AUDIO_SAMPLE_RATE}" \
               -t ${DURATION} \
               -c:a pcm_s16le \
               -y \
               "$TEMP_AUDIO" 2>&1 | grep -E "(error|Error)" || true
        ;;
    "tone")
        echo -e "${BLUE}Generating subtle background tone (220Hz)...${NC}"
        ffmpeg -f lavfi -i "sine=frequency=220:duration=${DURATION}:sample_rate=${AUDIO_SAMPLE_RATE}" \
               -af "volume=0.1,afade=t=in:st=0:d=2,afade=t=out:st=$((DURATION-2)):d=2" \
               -c:a pcm_s16le \
               -y \
               "$TEMP_AUDIO" 2>&1 | grep -E "(error|Error)" || true
        ;;
    *)
        # Assume it's a path to an audio file
        if [ ! -f "$AUDIO_TYPE" ]; then
            echo -e "${RED}Error: Audio file not found: $AUDIO_TYPE${NC}"
            exit 1
        fi
        
        echo -e "${BLUE}Using audio file: $AUDIO_TYPE${NC}"
        
        # Extract/convert audio to match video duration
        ffmpeg -i "$AUDIO_TYPE" \
               -t ${DURATION} \
               -ar ${AUDIO_SAMPLE_RATE} \
               -ac 2 \
               -af "afade=t=in:st=0:d=2,afade=t=out:st=$((DURATION-2)):d=2" \
               -c:a pcm_s16le \
               -y \
               "$TEMP_AUDIO" 2>&1 | grep -E "(error|Error)" || true
        
        # If audio is shorter than video, loop it
        AUDIO_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$TEMP_AUDIO" 2>/dev/null || echo "0")
        if (( $(echo "$AUDIO_DURATION < $DURATION" | bc -l 2>/dev/null || echo "1") )); then
            echo -e "${YELLOW}Audio is shorter than video, looping...${NC}"
            ffmpeg -stream_loop -1 -i "$TEMP_AUDIO" \
                   -t ${DURATION} \
                   -c:a pcm_s16le \
                   -y \
                   "$TEMP_AUDIO" 2>&1 | grep -E "(error|Error)" || true
        fi
        ;;
esac

if [ ! -f "$TEMP_AUDIO" ] || [ ! -s "$TEMP_AUDIO" ]; then
    echo -e "${RED}❌ Failed to generate audio${NC}"
    exit 1
fi

echo -e "${YELLOW}Combining video and audio...${NC}"
ffmpeg -i "$TEMP_VIDEO" \
       -i "$TEMP_AUDIO" \
       -c:v copy \
       -c:a aac \
       -b:a 128k \
       -ar ${AUDIO_SAMPLE_RATE} \
       -shortest \
       -movflags +faststart \
       -y \
       "$VIDEO_FILE" 2>&1 | grep -E "(error|Error|frame|time|bitrate)" || true

# Verify result
if [ -f "$VIDEO_FILE" ] && [ -s "$VIDEO_FILE" ]; then
    FILE_SIZE=$(du -h "$VIDEO_FILE" | cut -f1)
    AUDIO_STREAMS=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$VIDEO_FILE" 2>/dev/null | wc -l)
    
    echo -e "${GREEN}✅ Video updated successfully!${NC}"
    echo -e "   Location: $VIDEO_FILE"
    echo -e "   Size: $FILE_SIZE"
    
    if [ "$AUDIO_STREAMS" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Audio track: Present${NC}"
        if [ "$AUDIO_TYPE" = "silent" ]; then
            echo -e "   ${BLUE}   Type: Silent track${NC}"
        elif [ "$AUDIO_TYPE" = "tone" ]; then
            echo -e "   ${BLUE}   Type: Background tone (220Hz)${NC}"
        else
            echo -e "   ${BLUE}   Type: Custom audio from file${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠️  Audio track: Not detected${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}The video is ready!${NC}"
else
    echo -e "${RED}❌ Failed to update video${NC}"
    exit 1
fi


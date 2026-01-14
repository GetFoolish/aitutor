#!/bin/bash

# Script to generate a 2-minute avatar idle loop video
# This creates a simple animated gradient video that loops seamlessly

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VIDEO_DIR="$PROJECT_ROOT/frontend/public/videos"
OUTPUT_FILE="$VIDEO_DIR/avatar-idle-loop.mp4"

echo -e "${GREEN}Generating 2-minute avatar idle loop video...${NC}"

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

echo -e "${YELLOW}Creating animated gradient video (this may take a minute)...${NC}"

# Generate a smooth animated gradient video that loops seamlessly
# Using a color palette that matches the avatar theme (purple gradient)
ffmpeg -f lavfi -i "color=c=0x7C3AED:s=${WIDTH}x${HEIGHT}:d=${DURATION}" \
       -f lavfi -i "color=c=0xC4B5FD:s=${WIDTH}x${HEIGHT}:d=${DURATION}" \
       -filter_complex "
         [0:v]scale=${WIDTH}:${HEIGHT}[bg];
         [1:v]scale=${WIDTH}:${HEIGHT},fade=t=in:st=0:d=2:alpha=1,fade=t=out:st=$((DURATION-2)):d=2:alpha=1[fg];
         [bg][fg]blend=all_mode=addition:all_opacity=0.5,
         scale=${WIDTH}:${HEIGHT},
         fps=${FPS},
         loop=loop=-1:size=1:start=0
       " \
       -t ${DURATION} \
       -c:v libx264 \
       -preset medium \
       -crf 23 \
       -pix_fmt yuv420p \
       -movflags +faststart \
       -y \
       "$OUTPUT_FILE" 2>&1 | grep -E "(frame|time|bitrate|error)" || true

# Alternative: Create a simpler animated gradient using a single filter
if [ ! -f "$OUTPUT_FILE" ] || [ ! -s "$OUTPUT_FILE" ]; then
    echo -e "${YELLOW}Trying alternative method...${NC}"
    
    ffmpeg -f lavfi -i "testsrc2=duration=${DURATION}:size=${WIDTH}x${HEIGHT}:rate=${FPS}" \
           -vf "scale=${WIDTH}:${HEIGHT},eq=brightness=0.1:contrast=1.2,hue=s=0.5" \
           -c:v libx264 \
           -preset medium \
           -crf 23 \
           -pix_fmt yuv420p \
           -movflags +faststart \
           -t ${DURATION} \
           -y \
           "$OUTPUT_FILE" 2>&1 | grep -E "(frame|time|bitrate|error)" || true
fi

# Check if file was created successfully
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo -e "${GREEN}✅ Video generated successfully!${NC}"
    echo -e "   Location: $OUTPUT_FILE"
    echo -e "   Size: $FILE_SIZE"
    echo -e "   Duration: 2 minutes (120 seconds)"
    echo ""
    echo -e "${GREEN}The video is ready to use!${NC}"
else
    echo -e "${RED}❌ Failed to generate video${NC}"
    echo ""
    echo "Trying simplest method - solid color video..."
    
    # Last resort: Create a simple solid color video
    ffmpeg -f lavfi -i "color=c=0x7C3AED:s=${WIDTH}x${HEIGHT}:d=${DURATION}:r=${FPS}" \
           -c:v libx264 \
           -preset ultrafast \
           -crf 28 \
           -pix_fmt yuv420p \
           -movflags +faststart \
           -t ${DURATION} \
           -y \
           "$OUTPUT_FILE"
    
    if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
        FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        echo -e "${GREEN}✅ Simple video generated!${NC}"
        echo -e "   Location: $OUTPUT_FILE"
        echo -e "   Size: $FILE_SIZE"
    else
        echo -e "${RED}❌ All methods failed. Please check ffmpeg installation.${NC}"
        exit 1
    fi
fi



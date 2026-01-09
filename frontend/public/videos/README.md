# Avatar Video Files

## avatar-idle-loop.mp4

**Purpose:** 2-minute video loop that plays when the avatar session is stopped or paused.

**Requirements:**
- Format: MP4 (H.264 codec recommended)
- Duration: ~2 minutes (120 seconds)
- Aspect Ratio: Square (1:1) recommended
- Resolution: 512x512 or higher

**Placement:**
Place the video file at: `frontend/public/videos/avatar-idle-loop.mp4`

**Usage:**
The `AvatarIdleLoop` component automatically loads and plays this video when the session is not active.

**Fallback:**
If the video file is not found, a gradient placeholder with an avatar icon will be displayed instead.



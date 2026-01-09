# Avatar Integration Documentation

## Overview

This document describes the avatar integration feature for the AI Tutor platform. The avatar provides a visual representation of the AI tutor using Hedra video avatars, integrated seamlessly into the floating control panel.

## Architecture

### Service Rationalization

We've rationalized our service stack to reduce dependencies and simplify the architecture:

- **Google Gemini**: Handles LLM (intelligence), STT (speech-to-text), and TTS (text-to-speech)
  - Model: `gemini-2.0-flash`
  - Provides native audio capabilities
  - Reduces service dependencies

- **Hedra**: Video avatar only
  - Provides realistic video avatar with lip sync
  - Requires 16kHz audio sample rate for proper synchronization

**Removed Services:**
- Deepgram STT (replaced by Gemini STT)
- Cartesia TTS (replaced by Gemini TTS)

**Note:** Cartesia is excellent for voice moods (whispers, anger, etc.), but Gemini provides sufficient quality for now and reduces complexity.

## Component Structure

### Frontend Components

```
frontend/src/components/avatar/
├── AvatarVideoDisplay.tsx    # Main orchestrator component
├── AvatarLiveVideo.tsx        # Live video display (when connected)
├── AvatarIdleLoop.tsx         # 2-minute video loop (when stopped)
└── index.ts                   # Exports
```

### AvatarVideoDisplay

**Purpose:** Main component that orchestrates avatar display and expansion.

**Features:**
- Switches between live video and idle loop based on connection state
- Handles video expansion (2x size) on click
- Shows status indicators (speaking, listening, thinking, etc.)
- Smooth animations using Framer Motion

**Props:**
```typescript
interface AvatarVideoDisplayProps {
  isConnected: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  videoTrack?: any; // LiveKit video track
  agentState?: string; // 'speaking' | 'listening' | 'thinking' | 'connecting' | 'disconnected'
}
```

### AvatarLiveVideo

**Purpose:** Displays live avatar video from LiveKit/Hedra when session is active.

**Features:**
- Renders LiveKit video track
- Shows live indicator bar when active
- Displays connecting overlay during connection
- Falls back to placeholder if video track unavailable

### AvatarIdleLoop

**Purpose:** Plays a 2-minute video loop when the session is stopped or paused.

**Features:**
- Auto-plays video loop
- Loops continuously
- Graceful fallback if video file not found
- Video file location: `frontend/public/videos/avatar-idle-loop.mp4`

## Integration

### FloatingControlPanel Integration

The avatar is integrated into the `FloatingControlPanel` component:

1. **Position:** Centered at the top of the expanded panel
2. **Expansion:** Clicking the video expands both the panel (2x width) and video (2x size)
3. **State Management:** Uses `isVideoExpanded` state to control expansion

### More Menu

Buttons that were previously visible are now in a "More" menu dropdown:

- **Settings** (if `enableEditingSettings` is true)
- **Canvas** (paint tool)
- **View Media** (media mixer display)

**Implementation:**
- More button at bottom of panel
- Dropdown menu appears above button when clicked
- Menu closes when item is clicked or outside is clicked

## Video Expansion Feature

### Behavior

When the avatar video is clicked:
1. Panel width expands from ~250px to ~500px (2x)
2. Video scales to 2x size
3. Indicator changes from "Click to expand" to "2x"
4. Clicking again shrinks back to normal size

### Implementation Details

- Uses Framer Motion for smooth animations
- Panel width controlled by `isVideoExpanded` state
- Video scaling handled by CSS `scale-[2]` class
- Drag constraints updated to accommodate expanded width

## Backend Integration

### LiveKit Agent

The LiveKit agent (`services/LiveKitAgent/agent.py`) is configured with:

```python
session = AgentSession(
    stt=google.STT(language="en"),
    llm=google.LLM(model=GEMINI_MODEL, temperature=0.7),
    tts=google.TTS(voice="Aoede", sample_rate=16000),
    vad=_preloaded_vad,
)

# Hedra avatar integration
if use_avatar:
    avatar = hedra.AvatarSession(avatar_id=hedra_avatar_id)
    await avatar.start(session, room=ctx.room)
```

### Environment Variables

Required environment variables:

```bash
# LiveKit
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Gemini (for LLM/STT/TTS)
GOOGLE_API_KEY=...

# Hedra (for video avatar)
HEDRA_API_KEY=...
HEDRA_AVATAR_ID=...
```

## File Structure

```
aitutor/
├── services/
│   └── LiveKitAgent/
│       ├── agent.py              # Main agent entry point
│       └── tutor_agent.py       # Tutor agent implementation
├── frontend/
│   ├── src/
│   │   └── components/
│   │       ├── avatar/           # Avatar components
│   │       └── floating-control-panel/
│   │           └── FloatingControlPanel.tsx
│   └── public/
│       └── videos/
│           └── avatar-idle-loop.mp4  # 2-minute idle loop video
└── documentation/
    └── AVATAR_INTEGRATION.md     # This file
```

## Usage

### Starting a Session

1. User clicks "Start Session" button
2. LiveKit agent connects
3. Hedra avatar starts and publishes video track
4. Frontend receives video track and displays in `AvatarLiveVideo`
5. Avatar shows live video with status indicators

### Stopping a Session

1. User clicks "End Session" button
2. LiveKit connection closes
3. Avatar switches to idle loop (`AvatarIdleLoop`)
4. 2-minute video loop plays continuously

### Expanding Video

1. User clicks on avatar video
2. Panel expands to 2x width (~500px)
3. Video scales to 2x size
4. User can click again to shrink back

### Using More Menu

1. User clicks "More" button at bottom of panel
2. Dropdown menu appears with:
   - Settings (if enabled)
   - Canvas
   - View Media
3. User clicks desired option
4. Menu closes and action executes

## Future Enhancements

1. **Gemini Native Audio:** Migrate fully to Gemini's native audio capabilities when available
2. **Voice Moods:** Consider Cartesia integration for emotional voice variations
3. **Multiple Avatars:** Support for different avatar personalities
4. **Custom Idle Loops:** Allow users to upload custom idle loop videos
5. **Avatar Customization:** UI for selecting different avatars

## Troubleshooting

### Video Not Displaying

- Check LiveKit connection status
- Verify Hedra avatar is started in agent logs
- Check browser console for video track errors
- Ensure `agentVideoTrack` state is set correctly

### Expansion Not Working

- Verify `isVideoExpanded` state is updating
- Check panel width calculations
- Ensure Framer Motion is properly configured

### Idle Loop Not Playing

- Verify video file exists at `frontend/public/videos/avatar-idle-loop.mp4`
- Check browser autoplay policies
- Verify video format is supported (MP4 recommended)

### More Menu Not Appearing

- Check `moreMenuOpen` state
- Verify dropdown positioning (should appear above button)
- Check z-index conflicts

## Testing

### Manual Testing Checklist

- [ ] Avatar displays when session starts
- [ ] Avatar switches to idle loop when session stops
- [ ] Video expansion works (2x size)
- [ ] Panel expansion works (2x width)
- [ ] More menu appears and functions correctly
- [ ] Settings/Canvas/View Media buttons work from More menu
- [ ] Status indicators show correctly (speaking, listening, etc.)
- [ ] Idle loop plays continuously

## References

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [Hedra Avatar Documentation](https://docs.hedra.com/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)


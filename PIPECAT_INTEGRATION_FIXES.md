# Pipecat Pipeline Integration Fixes

## Overview
Fixed MediaMixer and Dash system integration with the Pipecat voice/video AI tutor pipeline to enable seamless video streaming and adaptive learning.

## Changes Made

### 1. MediaMixer Integration Fixes

#### Problem Identified
The MediaMixer video frames were not reaching the Gemini Live API due to incorrect frame injection and timing issues.

#### Fixes Applied

**File: `pipecat_pipeline/26c_gemini_live_video.py`**

1. **Fixed Frame Injection** (Line 72-114)
   - **Before**: `await task.queue_frames([image_frame])`
   - **After**: `await transport.input().push_video_frame(image_frame)`
   - **Why**: Frames must be pushed through the transport input, not queued directly to the task

2. **Fixed Timing Issues** (Line 246-290)
   - **Before**: MediaMixer started immediately, video input unpaused 2 seconds later
   - **After**: Video input unpaused first, then MediaMixer started
   - **Why**: Prevents early frames from being dropped due to paused video input

3. **Removed Unnecessary Frame Downsampling** (Line 87-108)
   - **Before**: Downsampled from 15 FPS to 1 FPS in the pipeline
   - **After**: Removed downsampling logic
   - **Why**: GeminiLiveLLMService already rate-limits to 1 FPS internally (llm.py:1287)

4. **Updated Function Signature** (Line 72)
   - **Before**: `async def mediamixer_video_receiver(task, llm)`
   - **After**: `async def mediamixer_video_receiver(transport, llm)`
   - **Why**: Need transport reference to push frames correctly

### 2. Dash API Integration

#### Problem Identified
The Pipecat pipeline had no integration with the Dash adaptive learning system. Questions and answers were not synchronized.

#### Solution Implemented

**File: `pipecat_pipeline/26c_gemini_live_video.py`**

1. **Added HTTP Client** (Line 9, 40)
   ```python
   import aiohttp
   DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")
   ```

2. **Added Dash API Helper Functions** (Line 122-166)
   - `fetch_next_question(user_id)`: Fetches questions from Dash API
   - `submit_answer_to_dash(...)`: Submits answers and receives skill updates

3. **Added LLM Tools for Dash Integration** (Line 206-239)
   - `submit_answer`: Tool for LLM to submit student answers
   - `get_next_question`: Tool for LLM to fetch next adaptive question

4. **Added Function Handlers** (Line 254-315)
   - `handle_submit_answer`: Processes answer submissions to Dash
   - `handle_get_next_question`: Fetches and formats next question
   - Registered handlers with LLM

5. **Updated System Instruction** (Line 173-204)
   - Added guidance for presenting questions
   - Added guidance for evaluating answers
   - Added guidance for Dash workflow integration

6. **Modified Initial Context** (Line 248, 250-277)
   - Fetches first question from Dash on client ready
   - Adds question to initial conversation context
   - Stores question metadata for answer evaluation

7. **Added User ID Support** (Line 171)
   ```python
   user_id = os.getenv("USER_ID", "demo_user")
   ```

### 3. Dash System Fixes

#### Problem Identified
Missing method `are_prerequisites_met` referenced in `dash_api.py:140`

#### Fix Applied

**File: `DashSystem/dash_system.py`**

Added missing method (Line 439-450):
```python
def are_prerequisites_met(self, student_id: str, skill_id: str,
                         current_time: float, threshold: float = 0.7) -> bool:
    """Check if all prerequisites for a skill are met"""
    skill = self.skills.get(skill_id)
    if not skill:
        return False

    for prereq_id in skill.prerequisites:
        prereq_prob = self.predict_correctness(student_id, prereq_id, current_time)
        if prereq_prob < threshold:
            return False

    return True
```

Updated `get_recommended_skills` to use the new method (Line 452-466).

### 4. Dependencies

**File: `requirements.txt`**

Added `aiohttp==3.11.11` for async HTTP requests to Dash API.

## How It Works

### Complete Flow

1. **Student Joins Session**
   - Pipecat bot connects to Daily room
   - MediaMixer connects to provide video stream
   - Video input is unpaused after 2 seconds

2. **Initial Question**
   - Bot fetches first question from Dash API
   - Question is presented via voice
   - Video frames from MediaMixer stream to Gemini for work observation

3. **Student Answers**
   - Bot listens to student's voice answer
   - Bot observes written work via MediaMixer video feed
   - Bot evaluates correctness

4. **Answer Submission**
   - Bot calls `submit_answer` tool
   - Answer is sent to Dash API
   - Dash updates skill states based on performance

5. **Next Question**
   - Bot calls `get_next_question` tool
   - Dash returns next adaptive question based on updated skills
   - Cycle repeats

### Architecture

```
┌─────────────┐
│   Student   │
└──────┬──────┘
       │
       ├─── Voice/Video ───┐
       │                   │
┌──────▼──────┐      ┌────▼────────┐
│ Daily Room  │      │ MediaMixer  │
│ (WebRTC)    │      │ (WebSocket) │
└──────┬──────┘      └────┬────────┘
       │                   │
       │            Video Frames
       │                   │
┌──────▼───────────────────▼──────┐
│   Pipecat Pipeline Bot          │
│   - Gemini Live API (LLM)       │
│   - MediaMixer Video Receiver   │
│   - Dash API Integration        │
└──────┬──────────────────────────┘
       │
       │ HTTP REST API
       │
┌──────▼──────┐
│  Dash API   │
│  (FastAPI)  │
└──────┬──────┘
       │
┌──────▼──────┐
│   MongoDB   │
│ (User Data) │
└─────────────┘
```

## Environment Variables

Add to `.env`:

```bash
# User identification (optional, defaults to "demo_user")
USER_ID=student_123

# Dash API URL (optional, defaults to http://localhost:8000)
DASH_API_URL=http://localhost:8000

# MediaMixer video stream (optional, defaults to ws://localhost:8766)
MEDIAMIXER_VIDEO_URL=ws://localhost:8766

# Google API Key (required)
GOOGLE_API_KEY=your_google_api_key

# Daily room URL (required)
DAILY_ROOM_URL=your_daily_room_url
```

## Testing

### Start Services

1. **Start MongoDB**
   ```bash
   # MongoDB should be running
   ```

2. **Start Dash API**
   ```bash
   cd DashSystem
   python dash_api.py
   # Runs on http://localhost:8000
   ```

3. **Start MediaMixer**
   ```bash
   python MediaMixer/media_mixer.py
   # WebSocket on ws://localhost:8765 (commands)
   # WebSocket on ws://localhost:8766 (video)
   ```

4. **Start Pipecat Bot**
   ```bash
   cd pipecat_pipeline
   python 26c_gemini_live_video.py
   ```

### Verification

1. **MediaMixer Integration**
   - Check logs for: `"Connected to MediaMixer video stream"`
   - Check logs for: `"Sent MediaMixer frame #N"` messages
   - Verify video frames are being sent to Gemini

2. **Dash Integration**
   - Check logs for: `"Fetched question [question_id]"`
   - Answer a question via voice
   - Check logs for: `"Submitted answer for question [question_id]"`
   - Verify MongoDB user data is updated

3. **End-to-End Flow**
   - Join Daily room
   - Hear welcome and first question
   - Answer question verbally
   - Receive feedback
   - Get next adaptive question

## Troubleshooting

### MediaMixer frames not showing up
- Ensure MediaMixer is running on ws://localhost:8766
- Check video input is unpaused: `llm.set_video_input_paused(False)`
- Verify `transport.input().push_video_frame()` is being called

### Dash API errors
- Ensure Dash API is running on http://localhost:8000
- Check MongoDB connection
- Verify user exists in database
- Check logs for HTTP error codes

### Questions not appearing
- Ensure Perseus questions exist in MongoDB
- Check `dash_api.py` `/next-question/{user_id}` endpoint
- Verify `fetch_next_question()` is returning data

### Answer submission failing
- Check network connectivity to Dash API
- Verify question_id and skill_ids are correct
- Check MongoDB write permissions

## File Changes Summary

```
Modified:
  ✓ pipecat_pipeline/26c_gemini_live_video.py (Major changes)
  ✓ DashSystem/dash_system.py (Added are_prerequisites_met method)
  ✓ requirements.txt (Added aiohttp)

Created:
  ✓ PIPECAT_INTEGRATION_FIXES.md (This file)
```

## Next Steps

1. Install new dependency: `pip install aiohttp==3.11.11`
2. Test MediaMixer video streaming
3. Test Dash API integration
4. Test end-to-end adaptive learning flow
5. Add error handling for network failures
6. Add retry logic for failed API calls
7. Consider adding metrics/telemetry
8. Add unit tests for Dash integration functions

## Notes

- The LLM rate-limits video frames to 1 FPS internally, so additional downsampling is unnecessary
- Perseus questions need to be loaded into MongoDB before testing
- User profiles are automatically created if they don't exist
- The bot stores current question in `llm._current_question` for answer evaluation
- Function handlers are async and called by Gemini when tools are invoked

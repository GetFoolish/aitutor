# Pipecat Voice Integration - Implementation Notes

## Overview
This branch implements voice-based AI tutoring using **Pipecat** with **Gemini Live API**, integrating with the existing DASH adaptive learning system and Perseus question rendering.

## Architecture

### Voice Pipeline (Pipecat)
- **File**: `pipecat_pipeline/26c_gemini_live_video.py`
- **Transport**: Daily.co WebRTC for real-time audio/video
- **LLM**: Google Gemini Live (multimodal - audio + video)
- **Port**: 7860 (HTTP endpoint for Daily.co room creation)

### MediaMixer (Screen Capture)
- **File**: `MediaMixer/media_mixer.py`
- **Function**: Combines screen share + scratchpad into single video feed
- **Layout**: 2-section vertical (2560x5120):
  - **Top Half (2560x2560)**: Scratchpad canvas
  - **Bottom Half (2560x2560)**: Question display area
- **Ports**:
  - 8765 (WebSocket - commands)
  - 8766 (WebSocket - video frames)
- **Format**: Base64-encoded JPEG frames at ~1 FPS

### Question Sync System
- **File**: `pipecat_pipeline/question_sync_server.py`
- **Function**: Synchronizes questions between backend (Pipecat) and frontend (React)
- **Ports**:
  - 8767 (WebSocket - frontend connection)
  - 8768 (WebSocket - backend connection)

### Frontend Updates
- **Voice Console**: Pipecat Voice UI Kit integration
- **Question Display**: Perseus renderer with scratchpad
- **MediaMixer Integration**: Dual WebSocket connections for commands + video

## How Next Question Generation Works

### DASH Algorithm Flow
Located in `DashSystem/dash_system.py`:

1. **Skill Recommendation** (`get_recommended_skills`)
   - Uses memory strength decay model
   - Formula: `strength = initial_strength * e^(-λt)`
   - Recommends skills with lowest memory strength

2. **Question Selection** (`get_next_question`, line 491)
   ```python
   def get_next_question(student_id, current_time, is_retry=False):
       # 1. Get recommended skills based on memory decay
       recommended_skills = get_recommended_skills(student_id, current_time)

       # 2. Load user's question history to avoid repeats
       answered_question_ids = {answered questions from history}

       # 3. Find unanswered question from recommended skills
       for skill_id in recommended_skills:
           candidate_questions = [q for q in questions
                                  if skill_id in q.skill_ids
                                  and q.question_id not in answered_question_ids]
           if candidate_questions:
               return candidate_questions[0]

       # 4. If no questions available, generate new one
       if not is_retry:
           generate_new_questions(recommended_skills)
           return get_next_question(student_id, current_time, is_retry=True)
   ```

3. **Question Generation** (if needed)
   - Uses QuestionGeneratorAgent with OpenRouter API
   - Generates Perseus-format questions for specific skills
   - Validates and stores in question database

### API Endpoints
- **GET** `/next-question/{user_id}` - Fetch next adaptive question
- **POST** `/submit-answer` - Submit answer and update memory strengths

## Critical Implementation Details

### Video Feed Issue Resolution
**Problem**: Gemini was not reading questions correctly from video feed.

**Root Cause**: MediaMixer sends 2-section vertical frame (2560x5120), with:
- Top half: Scratchpad
- Bottom half: Question

Gemini was looking at the wrong section or getting confused by the tall image.

**Solution**: Updated system instructions to explicitly tell Gemini:
```
- The video frame has TWO parts stacked vertically
- TOP HALF: Scratchpad (ignore when reading question)
- BOTTOM HALF: Math question (READ THIS for the question)
- LOOK at the BOTTOM HALF of the video frame to read the question
```

See `pipecat_pipeline/26c_gemini_live_video.py` lines 500-523.

### Session Management
**Problem**: Multiple concurrent voice sessions causing conflicts.

**Solution**: Added session lock mechanism (lines 48-50, 243-260):
- Global `active_session` variable
- `asyncio.Lock()` to prevent concurrent sessions
- Cleanup in finally block to release session

### Scratchpad Positioning Fix
**Problem**: Scratchpad was overlaying the question display.

**Solution**: Changed CSS from `position: absolute` to `position: relative` in:
- `frontend/src/App.scss` lines 280-284
- Removed z-index that was causing overlay

## Key Files Modified

### Backend
1. **pipecat_pipeline/26c_gemini_live_video.py** (NEW)
   - Main Pipecat voice bot implementation
   - Gemini Live LLM integration
   - MediaMixer video receiver
   - DASH API integration for questions
   - Session management

2. **MediaMixer/media_mixer.py**
   - Screen capture and mixing
   - Dual-section layout for scratchpad + question

3. **DashSystem/dash_api.py**
   - Question sync endpoints
   - Answer submission

### Frontend
1. **frontend/src/App.tsx**
   - Pipecat Voice UI Kit integration
   - MediaMixer WebSocket connections
   - Question sync client

2. **frontend/src/components/question-display/QuestionDisplay.tsx**
   - Perseus question renderer
   - Scratchpad integration
   - Layout fixes

3. **frontend/src/App.scss**
   - Voice console styling
   - Question panel layout
   - Scratchpad positioning

## Environment Variables Required

```bash
# Google Gemini
GOOGLE_API_KEY=your_gemini_api_key

# Daily.co (WebRTC)
DAILY_API_KEY=your_daily_api_key
DAILY_ROOM_URL=https://yourroom.daily.co

# DASH API
DASH_API_URL=http://localhost:8000

# MediaMixer
MEDIAMIXER_VIDEO_URL=ws://localhost:8766
MEDIAMIXER_COMMAND_URL=ws://localhost:8765
```

## Running the System

```bash
# Start all services
./run_tutor.sh

# Services start on:
# - Frontend: http://localhost:3000
# - DASH API: http://localhost:8000
# - SherlockED API: http://localhost:8001
# - Pipecat: http://localhost:7860
# - MediaMixer Command: ws://localhost:8765
# - MediaMixer Video: ws://localhost:8766
# - Question Sync (FE): ws://localhost:8767
# - Question Sync (BE): ws://localhost:8768
```

## Known Issues & Solutions

### Issue: Video frames being sent but Gemini not reading correctly
**Status**: RESOLVED
**Solution**: Added explicit instructions about 2-section layout

### Issue: Multiple concurrent sessions
**Status**: RESOLVED
**Solution**: Session lock mechanism

### Issue: Scratchpad overlaying question
**Status**: RESOLVED
**Solution**: CSS positioning fix

## Next Steps / Future Improvements

1. **OCR Integration**: Add Tesseract OCR as fallback for video reading
2. **Frame Rate Optimization**: Dynamic frame rate based on activity
3. **Multi-user Support**: Scale session management for multiple students
4. **Answer Validation**: Improve answer checking with visual feedback
5. **Performance Metrics**: Track response time and accuracy

## Testing Checklist

- [x] Voice connection establishes via Daily.co
- [x] MediaMixer captures screen correctly
- [x] Questions sync between backend and frontend
- [x] Gemini reads questions from video feed
- [x] Answer submission updates DASH memory strengths
- [x] Next question selection uses adaptive algorithm
- [x] Session cleanup prevents conflicts
- [x] Scratchpad doesn't overlay question

## Architecture Diagram

```
┌─────────────┐
│   Frontend  │ (React + Perseus + Pipecat UI Kit)
│ :3000       │
└──────┬──────┘
       │
       ├─── WebSocket ──> MediaMixer (screen + scratchpad)
       │                  :8765, :8766
       │
       ├─── WebSocket ──> Question Sync Server
       │                  :8767
       │
       ├─── HTTP ──────> DASH API (questions + answers)
       │                  :8000
       │
       └─── Daily.co ──> Pipecat Voice Bot
                          :7860
                          │
                          ├─── Gemini Live (LLM)
                          ├─── MediaMixer (video feed)
                          └─── DASH API (adaptive learning)
```

## Credits
- **Pipecat Framework**: Daily.co
- **Gemini Live API**: Google
- **DASH Algorithm**: Custom adaptive learning system
- **Perseus**: Khan Academy question renderer

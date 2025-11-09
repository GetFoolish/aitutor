# AI Tutor Testing Checklist

## Pre-Flight Check

### ✅ Completed
- [x] MongoDB connection configured (.env has MONGODB_URI)
- [x] DASH API updated with grade-level support
- [x] DASH System supports grade initialization
- [x] Python dependencies installed
- [x] Frontend dependencies installed
- [x] MediaMixer WebSocket ports configured (8765, 8766)
- [x] DASH System math documentation created

### 📋 Environment Variables Required
Check your `.env` file has these configured:
```bash
# Critical
GOOGLE_API_KEY=...              # For Gemini Live (Pipecat)
DAILY_API_KEY=...               # For Daily transport (Pipecat)
MONGODB_URI=...                 # For user/skill storage
OPENROUTER_API_KEY=...          # For video search (optional)
YOUTUBE_API_KEY=...             # For video recommendations (optional)

# Authentication
JWT_SECRET_KEY=...              # For auth tokens

# Optional
STRIPE_SECRET_KEY=...           # For payments
IMAGEKIT_* =...                 # For image hosting (if using question generation)
```

---

## 1. Start All Services

### Command:
```bash
./run_tutor.sh
```

### Expected Output:
```
Using conda environment: ai_tutor
Using Python: /opt/homebrew/Caskroom/miniforge/base/envs/ai_tutor/bin/python3
Starting Python backend... Logs -> logs/mediamixer.log
Starting Question Sync Server... Logs -> logs/question_sync.log
Starting Pipecat pipeline (transport: daily)... Logs -> logs/pipecat.log
Starting DASH API server... Logs -> logs/api.log
Starting SherlockED Exam API server... Logs -> logs/sherlocked_exam.log
Waiting for backend services to initialize...
Starting Node.js frontend... Logs -> logs/frontend.log

Tutor is running with the following PIDs: [12345, 12346, 12347, 12348, 12349, 12350]

📡 Service URLs:
  🌐 Frontend:           http://localhost:3000
  🔧 DASH API:           http://localhost:8000
  🕵️  SherlockED API:     http://localhost:8001
  📹 MediaMixer Command: ws://localhost:8765
  📺 MediaMixer Video:   ws://localhost:8766
  🔄 Question Sync (FE): ws://localhost:8767
  🔄 Question Sync (BE): ws://localhost:8768

Press Ctrl+C to stop.
```

### ✅ Verification:
```bash
# Check if all services are running
lsof -i :3000   # Frontend
lsof -i :8000   # DASH API
lsof -i :8001   # SherlockED API
lsof -i :8765   # MediaMixer Command WS
lsof -i :8766   # MediaMixer Video WS
lsof -i :8767   # Question Sync (Frontend)
lsof -i :8768   # Question Sync (Backend)
```

### 🔍 Check Logs:
```bash
tail -f logs/api.log          # DASH API
tail -f logs/mediamixer.log   # MediaMixer
tail -f logs/pipecat.log      # Pipecat pipeline
tail -f logs/frontend.log     # React frontend
```

---

## 2. Frontend Authentication

### Test: Login/Signup
1. Open http://localhost:3000
2. Should see LoginSignup component
3. Test signup with email/password
4. Test login with existing credentials
5. Verify JWT token stored in localStorage

### Expected Behavior:
- ✅ User can create account
- ✅ User can log in
- ✅ Redirects to main app after login
- ✅ Header shows user email and credits

---

## 3. DASH System - Grade Initialization

### Test: Create User with Grade Level

**API Call:**
```bash
curl "http://localhost:8000/next-question/alice123?grade=5"
```

**Expected Response:**
```json
{
  "question_id": "perseus_12345",
  "skill_ids": ["counting_1_10"],
  "content": { ...perseus JSON... },
  "difficulty": 0.5,
  "screenshot_path": "/Users/.../question_screenshots/perseus_12345.png"
}
```

**Backend Logs (dash_api.log):**
```
🚀 New user 'alice123' at grade GRADE_5. Initializing past skills as mastered...
  ✓ Mastered 'Counting 1-10' (K)
  ✓ Mastered 'Basic Addition' (GRADE_1)
  ✓ Mastered 'Basic Subtraction' (GRADE_1)
  ...
  ✓ Mastered 'Fraction Operations' (GRADE_4)
✅ Initialized alice123 with skills below GRADE_5 marked as mastered
```

### ✅ Verification:
```bash
curl "http://localhost:8000/skill-states/alice123" | jq '.skills[] | select(.grade_level == "K" or .grade_level == "GRADE_1")'
```

**Expected:**
```json
{
  "skill_id": "counting_1_10",
  "name": "Counting 1-10",
  "grade_level": "K",
  "memory_strength": 3.0,    ← Marked as mastered
  "practice_count": 0,
  "correct_count": 0,
  "is_locked": false
}
```

---

## 4. Learning Path Sidebar

### Test: Skill Visualization
1. Navigate to http://localhost:3000 (after login)
2. Left sidebar should show "Your Learning Path"
3. Verify skills grouped by category (Kindergarten, Arithmetic, etc.)
4. Check skill progress indicators:
   - **Green**: memory_strength ≥ 0.8 (mastered)
   - **Yellow**: 0.3 ≤ memory_strength < 0.8 (in progress)
   - **Red**: memory_strength < 0.3 (needs practice)
   - **Locked**: Prerequisites not met

### ✅ Verification:
- Skills K-4 should be green (memory_strength = 3.0)
- Skills Grade 5+ should be red or locked

---

## 5. Question Display and Perseus Rendering

### Test: Enhanced Question Display
1. Question should load automatically from `/next-question/{user_id}`
2. Perseus math widgets should render correctly
3. Check for:
   - Math equations (KaTeX rendering)
   - Interactive widgets (radio buttons, dropdowns, etc.)
   - Images (if present)
   - Hints (expandable)

### ✅ Verification:
- Math renders beautifully (no raw LaTeX)
- Widgets are interactive
- Question is readable and properly formatted

---

## 6. Answer Submission and Skill Updates

### Test: Submit Correct Answer

**API Call:**
```bash
curl -X POST "http://localhost:8000/submit-answer/alice123" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "perseus_12345",
    "skill_ids": ["multiplication_tables"],
    "is_correct": true,
    "response_time_seconds": 45
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "is_correct": true,
  "skill_details": [
    {
      "skill_id": "multiplication_tables",
      "name": "Multiplication Tables",
      "memory_strength": 4.0,    ← Increased from 3.0
      "is_direct": true
    }
  ],
  "affected_skills_count": 1,
  "gamification": {
    "xp_earned": 10,
    "new_level": 2,
    ...
  }
}
```

### Math Behind the Update:
```
Initial State:
- memory_strength: 3.0
- correct_count: 0

After Correct Answer:
strength_increment = 1.0 / (1 + 0.1 × 0) = 1.0
time_penalty = 1.0 (45 seconds < 180 seconds)
strength_increment = 1.0 × 1.0 = 1.0

new_strength = min(5.0, 3.0 + 1.0) = 4.0
```

---

### Test: Submit Incorrect Answer

**API Call:**
```bash
curl -X POST "http://localhost:8000/submit-answer/alice123" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "perseus_12346",
    "skill_ids": ["quadratic_equations"],
    "is_correct": false,
    "response_time_seconds": 120
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "is_correct": false,
  "skill_details": [
    {
      "skill_id": "quadratic_equations",
      "memory_strength": 0.8,    ← Decreased from 1.0
      "is_direct": true
    },
    {
      "skill_id": "quadratic_intro",
      "memory_strength": 1.4,    ← Prerequisite penalty
      "is_direct": false
    },
    {
      "skill_id": "linear_equations_1var",
      "memory_strength": 1.9,    ← Prerequisite penalty
      "is_direct": false
    }
  ],
  "affected_skills_count": 3
}
```

### Math Behind the Update:
```
Direct Skill (quadratic_equations):
new_strength = max(-2.0, 1.0 - 0.2) = 0.8

Prerequisites (quadratic_intro, linear_equations_1var, ...):
new_strength = max(-2.0, current_strength - 0.1)

Example for quadratic_intro:
new_strength = max(-2.0, 1.5 - 0.1) = 1.4
```

---

## 7. MediaMixer and Video Streaming

### Test: Floating Video Widget

#### 7.1. Open Widget
1. Click the floating recorder button (bottom-right)
2. Widget should expand
3. Should see MediaMixer video feed

#### 7.2. Toggle Camera
1. Click camera toggle button
2. Webcam should appear in bottom section
3. Check MediaMixer logs:
   ```
   Camera toggled: ON
   Camera initialized successfully
   ```

#### 7.3. Toggle Screen Sharing
1. Click screen share toggle
2. Middle section should show your screen
3. Verify by moving windows around

#### 7.4. Scratchpad
1. Open scratchpad tab
2. Draw something
3. Check MediaMixer logs:
   ```
   MediaMixer: Received scratchpad frame, data length: 45623
   MediaMixer: Scratchpad frame processed, size: (1920, 1080, 3)
   ```

### ✅ Verification:
```bash
# Check WebSocket connections
tail -f logs/mediamixer.log | grep "WebSocket"

# Expected:
# Command WebSocket server started on ws://localhost:8765
# Video WebSocket server started on ws://localhost:8766
# Command client connected
# Video client connected
```

---

## 8. Pipecat Pipeline Integration

### Test: Voice Connection

#### 8.1. Connect to Pipecat
1. Click "Connect" button in Floating Video Widget
2. Should see Daily room connection initiated
3. Verify logs:
   ```bash
   tail -f logs/pipecat.log | grep -E "(transport|Daily|Gemini)"
   ```

#### 8.2. Speak and Get Response
1. Say: "Can you help me with multiplication?"
2. Gemini should respond via voice
3. Check logs for:
   - Audio input received
   - Gemini API call
   - Audio output generated

### ✅ Verification:
```bash
# Pipecat should connect to MediaMixer video stream
tail -f logs/pipecat.log | grep "MediaMixer"

# Expected:
# Connecting to MediaMixer at ws://localhost:8766
# Connected to MediaMixer video stream
# Sent MediaMixer frame #1 (1920x3240) to Gemini
# Sent MediaMixer frame #2 (1920x3240) to Gemini
```

---

## 9. Question Synchronization

### Test: Question Updates via WebSocket

#### Setup:
1. Keep browser console open (DevTools → Console)
2. Submit an answer via frontend
3. Next question should load automatically

#### Expected Console Logs:
```javascript
[QuestionSync] Connected to ws://localhost:8767
[QuestionSync] Received question update: perseus_12346
[EnhancedQuestionDisplay] Loading new question...
[Perseus] Rendering math widgets...
```

### ✅ Verification:
```bash
# Check question sync server logs
tail -f logs/question_sync.log

# Expected:
# Question sync server started on ws://localhost:8768 (backend)
# Frontend client connected on ws://localhost:8767
# Broadcasting question update to 1 clients
```

---

## 10. End-to-End Integration Test

### Complete Flow:
1. **Login** as new user
2. **Specify grade level** (e.g., Grade 5)
3. **Verify skills initialized** (K-4 mastered, 5+ not started)
4. **Connect voice** (Pipecat + Daily)
5. **Enable camera and screen sharing** (MediaMixer)
6. **Get first question** (from DASH API)
7. **Ask Gemini for help via voice**
8. **Draw on scratchpad** (if needed)
9. **Submit answer** (correct)
10. **Verify skill update** (memory_strength increased)
11. **Get next question** (automatically)
12. **Check Learning Path** (progress updated)

### ✅ Success Criteria:
- All services running without errors
- Frontend loads and responds quickly
- Questions render correctly with Perseus math
- Voice AI works bidirectionally
- Video streams to Gemini (camera/screen/scratchpad)
- Skills update correctly based on correct/incorrect answers
- Prerequisites penalized on wrong answers
- Learning Path reflects current progress

---

## 11. Optional: YouTube Video Recommendations

### Setup:
The video recommendation backend is in a separate repo: https://github.com/gagan114662/youtube

#### Clone and Setup:
```bash
cd /Users/gaganarora/Desktop/projects
git clone https://github.com/gagan114662/youtube
cd youtube

# Install dependencies
pip install -r requirements.txt

# Configure .env with YouTube API key
echo "YOUTUBE_API_KEY=your_key_here" > .env

# Run video recommendation service
python app.py  # Should start on port 8002
```

### Test: Video Recommendations
1. Navigate to a question in the frontend
2. VideoRecommendations component should load
3. Should fetch videos related to the skill
4. Click a video to watch in modal

**API Call:**
```bash
curl -X POST "http://localhost:8002/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "multiplication tables",
    "max_videos": 3,
    "min_match_score": 60
  }'
```

**Expected Response:**
```json
[
  {
    "video_id": "abc123",
    "title": "Multiplication Tables Made Easy",
    "url": "https://youtube.com/watch?v=abc123",
    "thumbnail_url": "https://i.ytimg.com/...",
    "duration": 300,
    "match_score": 85,
    "transcript_available": true
  },
  ...
]
```

---

## 12. Common Issues and Fixes

### Issue: MongoDB connection fails
**Fix:**
```bash
# Check if MongoDB is running
pgrep -fl mongod

# If not running (cloud MongoDB Atlas):
# Verify MONGODB_URI in .env is correct
# Check firewall/network access

# If using local MongoDB:
brew services start mongodb-community
```

### Issue: Frontend shows "No user, showing LoginSignup" even after login
**Fix:**
- Check browser console for auth errors
- Verify JWT_SECRET_KEY in .env
- Clear localStorage and try again

### Issue: MediaMixer WebSocket connection refused
**Fix:**
```bash
# Check if MediaMixer is running
lsof -i :8765
lsof -i :8766

# Restart if needed
pkill -f media_mixer
python MediaMixer/media_mixer.py
```

### Issue: Pipecat can't connect to Gemini
**Fix:**
```bash
# Check GOOGLE_API_KEY in .env
echo $GOOGLE_API_KEY

# Verify API key is valid:
curl -H "x-goog-api-key: $GOOGLE_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
```

### Issue: Questions not rendering (Perseus errors)
**Fix:**
- Check MongoDB has Perseus questions
- Verify SherlockED API is running on port 8001
- Check browser console for Perseus widget errors

---

## Summary: System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  - Authentication (LoginSignup)                                 │
│  - Learning Path Sidebar (skill visualization)                  │
│  - Enhanced Question Display (Perseus rendering)                │
│  - Floating Video Widget (camera/screen/scratchpad)            │
│  - Video Recommendations                                        │
└──────────────┬──────────────────────────────────────────────────┘
               │
         WebSocket (8765, 8766, 8767)
               │
┌──────────────┴──────────────────────────────────────────────────┐
│                      BACKEND SERVICES                            │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  DASH API       │  │  MediaMixer      │  │  Pipecat       │ │
│  │  (Port 8000)    │  │  (WS 8765/8766)  │  │  Pipeline      │ │
│  │                 │  │                  │  │  (Port 7860)   │ │
│  │  - Next Q       │  │  - Video Mixer   │  │  - Gemini Live │ │
│  │  - Submit A     │  │  - Camera        │  │  - Daily       │ │
│  │  - Skill States │  │  - Screen Share  │  │  - VAD         │ │
│  │  - Grade Init   │  │  - Scratchpad    │  │  - Multimodal  │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ SherlockED API  │  │  Question Sync   │  │  Video Search  │ │
│  │ (Port 8001)     │  │  (WS 8767/8768)  │  │  (Port 8002)   │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────┬──────────────────────────────────────────────────┘
               │
         MongoDB (Cloud/Local)
               │
┌──────────────┴──────────────────────────────────────────────────┐
│                         DATABASE                                 │
│  - users (profiles, skill states, question history)             │
│  - skills_template (curriculum, prerequisites)                   │
│  - perseus_questions (Khan Academy content)                      │
│  - auth_users (authentication)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. Run `./run_tutor.sh` ✅
2. Check all service logs for errors ✅
3. Test authentication flow ✅
4. Create test user with grade level ✅
5. Verify skill initialization ✅
6. Test question display and Perseus rendering ✅
7. Submit answers and verify skill updates ✅
8. Test MediaMixer (camera, screen, scratchpad) ✅
9. Test Pipecat voice connection ✅
10. End-to-end integration test ✅

**You're ready to test!** 🚀

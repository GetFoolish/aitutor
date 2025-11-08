# AI Tutor - Setup Guide

## Prerequisites

### Required Software
1. **Python 3.10+** (preferably via Conda)
2. **Node.js 18+** and npm
3. **MongoDB Community Edition**
4. **Git**

### System Requirements
- macOS, Linux, or Windows with WSL2
- 8GB+ RAM recommended
- Stable internet connection for MongoDB Atlas

---

## Initial Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai_tutor
```

### 2. Install MongoDB
```bash
# macOS (using Homebrew)
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Linux (Ubuntu/Debian)
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

### 3. Python Environment Setup

**Option A: Using Conda (Recommended)**
```bash
conda create -n ai_tutor python=3.10
conda activate ai_tutor
pip install -r requirements.txt
```

**Option B: Using venv**
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 4. Frontend Setup
```bash
cd frontend
npm install --force
cd ..
```

---

## Configuration

### 1. Environment Variables
Create a `.env` file in the project root with the following:

```bash
# =================================
# OPENROUTER (Required for Video Search)
# =================================
OPENROUTER_API_KEY=<your-openrouter-api-key>
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free

# =================================
# GOOGLE APIs
# =================================
GOOGLE_API_KEY=<your-google-api-key>
YOUTUBE_API_KEY=<your-youtube-api-key>

# =================================
# MONGODB
# =================================
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.zbntx5t.mongodb.net/ai_tutor?retryWrites=true&w=majority

# =================================
# AUTHENTICATION
# =================================
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-client-secret>

# =================================
# PAYMENTS (Stripe)
# =================================
STRIPE_SECRET_KEY=<your-stripe-secret-key>
STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-secret>

# =================================
# IMAGEKIT (Optional)
# =================================
IMAGEKIT_PUBLIC_KEY=<your-imagekit-public-key>
IMAGEKIT_PRIVATE_KEY=<your-imagekit-private-key>
IMAGEKIT_URL_ENDPOINT=<your-imagekit-endpoint>

# =================================
# DAILY.CO (Required for Voice AI)
# =================================
DAILY_API_KEY=<your-daily-api-key>
DAILY_ROOM_URL=<your-daily-room-url>
```

### 2. MongoDB Atlas Setup
The project uses **MongoDB Atlas** (cloud database):
- Database: `ai_tutor`
- Collection: `perseus_questions` (currently has 920 questions)
- Ensure the MONGODB_URI in `.env` points to the Atlas cluster

**Note**: A local MongoDB instance is also installed but the application connects to Atlas by default.

---

## Running the Application

### Quick Start (Recommended)
Use the automated startup script:
```bash
./run_tutor.sh
```

This script automatically starts all required services:
- MediaMixer (video processing)
- Question Sync Server
- Pipecat Gemini Live Pipeline (voice AI)
- DASH API (question delivery)
- SherlockED Exam API (authentication & exams)
- Frontend (React app)

### Manual Start (for debugging)

**Terminal 1: MediaMixer**
```bash
python MediaMixer/media_mixer.py
```

**Terminal 2: Question Sync Server**
```bash
cd pipecat_pipeline
python question_sync_server.py
```

**Terminal 3: Pipecat Pipeline**
```bash
cd pipecat_pipeline
python 26c_gemini_live_video.py --transport daily
```

**Terminal 4: DASH API**
```bash
python DashSystem/dash_api.py
```

**Terminal 5: SherlockED API**
```bash
python SherlockEDApi/run_backend.py
```

**Terminal 6: Frontend**
```bash
cd frontend
npm run dev
```

---

## Service Ports & URLs

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Frontend | 3000/3001 | http://localhost:3001 | React UI |
| DASH API | 8000 | http://localhost:8000 | Question delivery & adaptive learning |
| SherlockED API | 8001 | http://localhost:8001 | Authentication & exam management |
| Pipecat Pipeline | 7860 | http://localhost:7860 | Voice AI (Gemini Live) |
| MediaMixer Command | 8765 | ws://localhost:8765 | Video processing commands |
| MediaMixer Video | 8766 | ws://localhost:8766 | Video stream |
| Question Sync (FE) | 8767 | ws://localhost:8767 | Frontend sync |
| Question Sync (BE) | 8768 | ws://localhost:8768 | Backend sync |

---

## Testing the Setup

### 1. Test User Login
- URL: http://localhost:3001
- Email: `test@test.com`
- Password: `test123`

### 2. Verify Services
```bash
# Check DASH API
curl http://localhost:8000/next-question/<user_id>

# Check SherlockED API
curl http://localhost:8001/health

# Check Pipecat
curl http://localhost:7860/status

# Check if all ports are listening
lsof -i :3001,8000,8001,7860,8765,8766,8767,8768
```

### 3. Check MongoDB Connection
```bash
mongosh "mongodb+srv://<connection-string>"
use ai_tutor
db.perseus_questions.countDocuments()  # Should return 920
db.users.find().limit(1)  # Check if users exist
```

---

## Architecture Overview

### Backend Services

1. **DASH API (Port 8000)**
   - Adaptive learning algorithm (DASH: Dynamic Adaptive Spaced Hypnosis)
   - Question selection based on memory strength
   - Skill tracking and spaced repetition
   - Uses MongoDB for question storage

2. **SherlockED Exam API (Port 8001)**
   - User authentication (JWT-based)
   - OAuth support (Google, Apple, Facebook)
   - Exam management
   - Payment integration (Stripe)
   - User credits and gamification

3. **Pipecat Pipeline (Port 7860)**
   - Voice AI integration using Google Gemini Live
   - Real-time voice interaction
   - Daily.co WebRTC transport
   - Screen sharing and video capabilities

4. **MediaMixer (Ports 8765/8766)**
   - Video processing and capture
   - WebSocket-based communication
   - Screen sharing functionality

5. **Question Sync Server (Ports 8767/8768)**
   - Synchronizes questions between frontend and backend
   - WebSocket communication

### Frontend (Port 3001)
- React + TypeScript
- Vite build tool
- Perseus renderer for Khan Academy-style math questions
- Pipecat Voice UI Kit integration
- Chakra UI components
- Authentication context
- Game context (XP, levels, streaks)

### Data Flow
1. User logs in → SherlockED API (port 8001)
2. Frontend requests next question → DASH API (port 8000)
3. DASH API queries MongoDB Atlas → Returns adaptive question
4. User answers → DASH updates memory strength in MongoDB
5. Voice interaction → Pipecat Pipeline (port 7860) → Gemini Live API
6. Video/Screen sharing → MediaMixer (ports 8765/8766)

---

## Common Issues & Troubleshooting

### bcrypt Version Error
**Error**: `ValueError: password cannot be longer than 72 bytes`
**Solution**:
```bash
pip install "bcrypt<5.0"
```

### MongoDB Connection Failed
**Error**: `ConfigurationError: MONGODB_URI is not set`
**Solution**:
- Verify `.env` file exists in project root
- Check `MONGODB_URI` is properly set
- Test connection: `mongosh "<your-mongodb-uri>"`

### Port Already in Use
**Error**: `Address already in use`
**Solution**:
```bash
# Find and kill the process
lsof -i :<port>
kill -9 <PID>
```

### Frontend Not Loading Questions
**Symptom**: "No question available"
**Solution**:
- Ensure DASH API is running on port 8000
- Check MongoDB has questions: `db.perseus_questions.countDocuments()`
- Verify user_id is being passed correctly

### Voice AI Connection Failed
**Error**: `Failed to fetch` at port 7860
**Solution**:
- Verify Pipecat pipeline is running
- Check `GOOGLE_API_KEY` is set in `.env`
- Check `DAILY_API_KEY` and `DAILY_ROOM_URL` are configured

### Frontend Hot Reload Issues
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install --force
```

---

## Development Workflow

### Code Structure
```
ai_tutor/
├── DashSystem/          # Adaptive learning algorithm
├── SherlockEDApi/       # Authentication & exam APIs
├── pipecat_pipeline/    # Voice AI integration
├── MediaMixer/          # Video processing
├── frontend/            # React frontend
├── auth/                # Auth utilities
├── db/                  # Database repositories
├── payments/            # Stripe integration
└── vector_db/           # Vector search (optional)
```

### Key Files
- `run_tutor.sh`: Main startup script
- `requirements.txt`: Python dependencies
- `frontend/package.json`: Node dependencies
- `.env`: Environment configuration
- `SherlockEDApi/run_backend.py`: Backend entry point
- `DashSystem/dash_api.py`: DASH system entry point

### Making Changes

**Backend Changes**:
- FastAPI with hot reload enabled
- Changes auto-reload in development mode
- MongoDB queries in `db/` directory

**Frontend Changes**:
- Vite with HMR (Hot Module Replacement)
- Changes reflect immediately
- Component structure in `frontend/src/components/`

---

## Database Schema

### Users Collection
```javascript
{
  user_id: String,
  email: String,
  name: String,
  hashed_password: String,
  account_type: "self-learner" | "parent",
  age: Number,
  language: String,
  region: String,
  credits: Number,
  parent_id: String,
  children: [String],
  profile_picture: String,
  created_at: Date,
  last_login: Date,
  is_active: Boolean,
  xp: Number,
  level: Number,
  streak_count: Number,
  last_practice_date: Date,
  daily_goal_xp: Number
}
```

### Perseus Questions Collection
```javascript
{
  question_id: String,
  content: Object,  // Perseus item format
  skill_ids: [String],
  difficulty: String,
  // ... Khan Academy Perseus format
}
```

---

## API Documentation

### DASH API Endpoints

**GET** `/next-question/{user_id}`
- Returns next adaptive question based on DASH algorithm
- Response: `{ question_id, skill_ids, content }`

**POST** `/submit-answer/{user_id}`
- Submit answer and update memory strength
- Body: `{ question_id, skill_ids, is_correct, response_time_seconds }`
- Response: `{ skill_details: [...] }`

### SherlockED API Endpoints

**POST** `/auth/signup`
- Create new user account
- Body: `{ email, password, name, account_type, language, region }`
- Response: `{ access_token, user }`

**POST** `/auth/login`
- Authenticate user
- Body: `{ email, password }`
- Response: `{ access_token, user }`

**GET** `/auth/me`
- Get current user info
- Headers: `Authorization: Bearer <token>`
- Response: `{ user }`

**GET** `/api/questions/{sample_size}`
- Get random questions from MongoDB
- Response: `[{ question, answerArea, hints }]`

---

## Deployment Notes

### Environment-Specific Configs
- Development: Uses `.env` file
- Production: Use environment variables directly
- Staging: Create `.env.staging`

### Security Checklist
- [ ] Change `JWT_SECRET_KEY` to a secure random value
- [ ] Update MongoDB credentials
- [ ] Set proper CORS origins in production
- [ ] Enable HTTPS/TLS
- [ ] Use production Daily.co room
- [ ] Rotate API keys regularly

### Performance Optimization
- MongoDB: Add indexes on frequently queried fields
- Frontend: Build with `npm run build` for production
- API: Use gunicorn/uvicorn with multiple workers
- Caching: Consider Redis for session management

---

## Support & Resources

- Main documentation: Check `README.md` files in each subdirectory
- Khan Academy Perseus: https://github.com/Khan/perseus
- Pipecat Docs: https://docs.pipecat.ai
- Daily.co Docs: https://docs.daily.co

---

## Quick Reference Commands

```bash
# Start everything
./run_tutor.sh

# Kill all services
pkill -f "python.*dash_api.py|python.*run_backend.py|python.*26c_gemini_live_video.py|python.*media_mixer.py|npm run dev"

# View logs (if using run_tutor.sh)
tail -f logs/api.log
tail -f logs/sherlocked_exam.log
tail -f logs/pipecat.log
tail -f logs/frontend.log

# Check MongoDB
mongosh "mongodb+srv://..."

# Test DASH API
curl http://localhost:8000/next-question/<user_id>

# Test Authentication
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

---

**Last Updated**: 2025-11-08
**Version**: 1.0

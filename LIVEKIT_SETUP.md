# LiveKit Voice AI Tutor - Developer Setup Guide

This guide will help you set up and run the LiveKit-powered AI tutoring system with Hedra avatar integration.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   LiveKit Cloud  │◀────│  LiveKit Agent  │
│   (React/Vite)  │     │   (WebRTC SFU)   │     │  (Python)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        │                        │                        ▼
        │                        │               ┌─────────────────┐
        │                        │               │  Hedra Avatar   │
        │                        │               │  (Video Avatar) │
        │                        │               └─────────────────┘
        ▼                        │                        │
┌─────────────────┐              │                        ▼
│   DASH API      │              │               ┌─────────────────┐
│   (FastAPI)     │              │               │  Deepgram STT   │
└─────────────────┘              │               │  Gemini LLM     │
                                 │               │  Cartesia TTS   │
                                 │               └─────────────────┘
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **npm or yarn**

## Required API Keys

You'll need accounts and API keys from:

| Service | Purpose | Get Key At |
|---------|---------|------------|
| LiveKit Cloud | WebRTC infrastructure | https://cloud.livekit.io |
| Deepgram | Speech-to-Text | https://deepgram.com |
| Google AI | Gemini LLM | https://makersuite.google.com/app/apikey |
| Cartesia | Text-to-Speech | https://cartesia.ai |
| Hedra | Video Avatar | https://hedra.com |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/GetFoolish/aitutor.git
cd aitutor
git checkout gagan_livekit_hedra
```

### 2. Set Up Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Speech-to-Text (Deepgram)
DEEPGRAM_API_KEY=your_deepgram_key

# LLM (Google Gemini)
GOOGLE_API_KEY=your_google_api_key
GEMINI_API_KEY=your_google_api_key

# Text-to-Speech (Cartesia)
CARTESIA_API_KEY=your_cartesia_key

# Video Avatar (Hedra)
HEDRA_API_KEY=your_hedra_key
HEDRA_AVATAR_ID=your_avatar_id
USE_HEDRA_AVATAR=true

# MongoDB (for user data)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/ai_tutor

# Auth
JWT_SECRET=your_jwt_secret
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

### 3. Set Up Python Virtual Environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

Install LiveKit agent plugins:

```bash
pip install livekit-agents livekit-plugins-deepgram livekit-plugins-cartesia \
            livekit-plugins-silero livekit-plugins-google livekit-plugins-hedra
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install --force
cd ..
```

### 5. Run Everything

The easiest way to start all services:

```bash
./run_tutor.sh
```

This starts:
- **Frontend** on http://localhost:3000
- **DASH API** on http://localhost:8000
- **Auth Service** on http://localhost:8003
- **LiveKit Agent** (connects to LiveKit Cloud)

## Manual Service Startup

If you prefer to run services individually:

### Start Backend Services

```bash
# Terminal 1: DASH API
source env/bin/activate
python services/DashSystem/dash_api.py

# Terminal 2: Auth Service
source env/bin/activate
python services/AuthService/auth_api.py

# Terminal 3: LiveKit Agent
source env/bin/activate
python services/LiveKitAgent/agent.py dev
```

### Start Frontend

```bash
# Terminal 4: Frontend
cd frontend
npm run dev
```

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| DASH API | 8000 | http://localhost:8000 |
| SherlockED API | 8001 | http://localhost:8001 |
| Teaching Assistant | 8002 | http://localhost:8002 |
| Auth Service | 8003 | http://localhost:8003 |

## Testing the Voice AI

1. Open http://localhost:3000/app/login
2. Sign in with Google OAuth
3. You'll see a math question displayed
4. Click **"Start Session"** in the floating control panel
5. The AI tutor (with Hedra avatar) will greet you
6. Speak to ask questions about the math problem

## Project Structure

```
aitutor/
├── frontend/                    # React/Vite frontend
│   └── src/
│       ├── features/
│       │   ├── livekit/        # LiveKit integration
│       │   │   ├── LiveKitContext.tsx
│       │   │   ├── VoiceSession.tsx
│       │   │   └── ScratchpadPublisher.tsx
│       │   └── heygen/         # HeyGen avatar (legacy)
│       └── components/
│           └── floating-control-panel/  # Voice session UI
│
├── services/
│   ├── LiveKitAgent/           # Voice AI agent
│   │   ├── agent.py            # Main entry point
│   │   ├── tutor_agent.py      # Tutor logic
│   │   └── tools/              # Agent tools
│   ├── DashSystem/             # Question API
│   └── AuthService/            # OAuth authentication
│
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── run_tutor.sh               # Startup script
```

## How It Works

### Voice Pipeline

1. **User speaks** → Microphone captures audio
2. **Deepgram STT** → Converts speech to text
3. **Gemini LLM** → Generates response based on context
4. **Cartesia TTS** → Converts text to speech
5. **Hedra Avatar** → Lip-syncs video to audio
6. **User sees/hears** → Avatar speaks the response

### Scratchpad Integration

The agent can see what students write:
- Frontend captures scratchpad canvas frames
- Frames are published as video track to LiveKit
- Agent receives and processes frames for context

## Configuration Options

### Disable Hedra Avatar

To use audio-only mode without video avatar:

```env
USE_HEDRA_AVATAR=false
```

### Change Voice

Edit `services/LiveKitAgent/agent.py`:

```python
tts=cartesia.TTS(
    model="sonic-2",
    voice="your_voice_id_here",  # Change this
    sample_rate=16000,
)
```

### Change LLM Model

```python
llm=google.LLM(
    model="gemini-2.0-flash",  # or gemini-1.5-pro
    temperature=0.7,
)
```

## Troubleshooting

### "GOOGLE_CLIENT_ID must be set" Error

The auth service needs environment variables. Ensure you start it with:

```bash
source env/bin/activate
export $(grep -v '^#' .env | xargs)
python services/AuthService/auth_api.py
```

### LiveKit Agent Not Connecting

1. Verify your LiveKit credentials in `.env`
2. Check if the agent is registered:
   ```bash
   cat logs/livekit_agent.log | grep "registered worker"
   ```
3. Ensure your LiveKit project allows agent connections

### Session Takes Long to Start

The Hedra avatar initialization adds latency. For faster startup:
- The greeting is now generated asynchronously (non-blocking)
- Consider disabling avatar for testing: `USE_HEDRA_AVATAR=false`

### Port Already in Use

Kill existing processes:

```bash
./kill_all_open_ports.sh
```

Or manually:

```bash
lsof -ti:3000,8000,8001,8002,8003 | xargs kill -9
```

## API Endpoints

### Get LiveKit Token

```bash
POST http://localhost:8000/api/livekit-token
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "room_name": "tutoring-session"
}
```

Response:
```json
{
  "token": "eyJ...",
  "url": "wss://your-project.livekit.cloud"
}
```

## Development Tips

1. **Hot Reload**: The frontend uses Vite with hot reload. The LiveKit agent in `dev` mode also auto-reloads.

2. **Logs**: Check `logs/` directory for service-specific logs:
   - `logs/livekit_agent.log`
   - `logs/dash_api.log`
   - `logs/auth_service.log`

3. **System Prompt**: Edit the AI tutor's personality in:
   `frontend/public/ai_tutor_system_prompt.md`

## Support

For issues or questions, open an issue on GitHub or contact the development team.

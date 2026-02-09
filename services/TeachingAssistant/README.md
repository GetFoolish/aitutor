# TeachingAssistant Service

An AI-powered teaching assistant that provides personalized tutoring with memory, context awareness, and real-time instruction delivery.

## 🎯 Overview

The TeachingAssistant service orchestrates:
- **Memory System**: Long-term memory storage and retrieval using Pinecone
- **Session Management**: Stateless sessions with MongoDB persistence
- **Dual-Channel Communication**: WebSocket (audio/transcript) + SSE (instructions)
- **Skills System**: Modular, auto-loaded capabilities
- **LLM Reflection**: Intelligent memory synthesis for contextual guidance

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MongoDB running locally or Atlas connection
- Pinecone account with valid API key
- Gemini API key

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables** (see [SETUP.md](SETUP.md)):
```bash
# Required
PINECONE_API_KEY=pcsk_your_key_here
GEMINI_API_KEY=AIzaSy_your_key_here
MONGODB_URI=mongodb://localhost:27017/ai_tutor

# Optional
PINECONE_ENVIRONMENT=us-east-1
EMBEDDING_DIMENSION=1024
```

3. **Start the service**:
```bash
cd services/TeachingAssistant
python api.py
```

The service will run on `http://0.0.0.0:8002`

## 🔧 Recent Fixes (December 2025)

### 1. ✅ CORS Configuration for SSE
**Issue**: Frontend couldn't connect to SSE endpoint due to missing CORS headers.

**Fix**: Added explicit CORS headers to `/sse/instructions` endpoint in `api.py`:
```python
headers = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
    "Access-Control-Allow-Credentials": "true"
}
```

**Verification**: Check logs for `[SSE] SSE connected` without CORS errors.

---

### 2. ✅ Pinecone Race Condition
**Issue**: Multiple sessions starting simultaneously caused 409 Conflict errors when creating the same index.

**Fix**: Added exception handling in `Memory/vector_store.py`:
```python
try:
    self.pc.create_index(...)
except PineconeApiException as e:
    if e.status == 409:
        logger.info("Index was created by another process. Continuing...")
    else:
        raise
```

**Verification**: Check logs for `Index already exists - using existing index` instead of 409 errors.

---

### 3. ✅ WebSocket 403 on Reconnection
**Issue**: WebSocket reconnection failed after session ended.

**Fix**: Added session validation in `api.py` before accepting WebSocket:
```python
session = ta.get_active_session(user_id)
if not session or not session.get("is_active"):
    await websocket.close(code=1008, reason="Session not active or ended")
    return
```

**Verification**: Check logs for clean disconnects with code 1000, no 403 errors.

---

### 4. ✅ LLM Reflection Layer
**Issue**: Raw memories were sent to tutor without intelligent synthesis.

**Fix**: Added `_synthesize_instruction()` method in `Memory/retriever.py`:
- Analyzes retrieved memories with conversation context
- Uses LLM to generate actionable instructions
- Only injects when memories are highly relevant

**Verification**: Check logs for `[REFLECTION]` entries when memories are retrieved.

---

### 5. ✅ Dynamic Skills Loading
**Issue**: Skills required manual registration in code.

**Fix**: Implemented auto-discovery in `skills_manager.py`:
- Scans `skills/` directory at startup
- Automatically loads all skill classes
- Instantiates with config injection

**Verification**: Check startup logs for:
```
[SKILLS_MANAGER] Loading skills from .../skills
[SKILLS_MANAGER] Loaded skill: greeting
```

---

### 6. ✅ Library Updates
**Issue**: Deprecated `google.generativeai` package causing warnings.

**Fix**: Migrated to `google.genai` in:
- `Memory/retriever.py`
- `Memory/extractor.py`
- `Memory/consolidator.py`

**Verification**: No deprecation warnings in logs.

## 🧪 Verification Checklist

### Backend Health Check

1. **Start the service** and check startup logs:
```bash
✅ [MONGODB] Connected to database: ai_tutor
✅ [SKILLS_MANAGER] Loading skills from .../skills
✅ [SKILLS_MANAGER] Loaded skill: greeting
✅ [TEACHING_ASSISTANT] Initialized with config-driven architecture
✅ Uvicorn running on http://0.0.0.0:8002
```

2. **Start a session** and verify:
```bash
✅ [SESSION_MANAGER] Created session sess_xxx for user user_xxx
✅ [GREETING_SKILL] Loaded opening data: True
✅ [WS] WebSocket connected for session sess_xxx
✅ [SSE] SSE connected for session sess_xxx
✅ [TEACHING_ASSISTANT] Background memory initialization complete
```

3. **End a session** and verify:
```bash
✅ [GREETING_SKILL] Loaded closing data: True
✅ [MEMORY_CONSOLIDATION] Starting session consolidation
✅ [MEMORY_CONSOLIDATION] Session consolidation complete
✅ Starting background opening context generation
✅ Background opening context generation complete
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `PINECONE_API_KEY not set` | Add valid key to `.env` file |
| `401 Unauthorized` (Pinecone) | Check API key is correct |
| `CORS policy` errors | Restart service after env changes |
| `409 Conflict` errors | Fixed - should auto-resolve now |
| `403 Forbidden` (WebSocket) | Fixed - session validation added |

## 📁 Architecture

```
TeachingAssistant/
├── api.py                    # FastAPI endpoints (session, WebSocket, SSE)
├── teaching_assistant.py     # Main orchestrator
├── session_manager.py        # MongoDB session state
├── skills_manager.py         # Dynamic skill loading
├── core/
│   ├── context.py           # Event and SessionContext models
│   ├── context_manager.py   # Context caching and persistence
│   └── event_processor.py   # Event-driven processing
├── handlers/
│   └── injection_manager.py # Instruction queue management
├── Memory/
│   ├── vector_store.py      # Pinecone integration
│   ├── retriever.py         # Memory search + reflection layer
│   ├── extractor.py         # Memory extraction from conversations
│   ├── consolidator.py      # Session closing + opening generation
│   └── schema.py            # Memory data models
└── skills/
    ├── base.py              # Skill interface
    └── greeting.py          # Opening/closing message generation
```

## 🔄 Data Flow

### Session Start
1. Frontend → `POST /session/start`
2. Create MongoDB session
3. Load opening context (from previous session)
4. Generate greeting via GreetingSkill
5. Initialize memory components (background)
6. Return greeting to frontend

### During Session
1. Frontend → WebSocket (Channel 1): Audio/transcript
2. Backend → Process events, extract memories
3. Backend → Retrieve relevant memories
4. Backend → LLM reflection layer synthesizes instruction
5. Backend → SSE (Channel 2): Send instruction to frontend
6. Frontend → Inject instruction into Gemini

### Session End
1. Frontend → `POST /session/end`
2. Generate closing message
3. Consolidate memories to Pinecone
4. Generate opening context for next session (background)
5. Return closing message

## 🛠️ Development

### Adding a New Skill

1. Create file in `skills/` directory:
```python
from .base import Skill

class MySkill(Skill):
    def __init__(self, config=None):
        super().__init__("my_skill")
        self.config = config
    
    def should_run(self, context):
        # Logic to determine if skill should execute
        return True
    
    def execute(self, context):
        # Skill logic
        return "instruction text"
```

2. Restart service - skill auto-loads!

### Running Tests

```bash
# Test memory system
python -m pytest tests/test_memory.py

# Test session management
python -m pytest tests/test_sessions.py
```

## 📊 Monitoring

### Key Metrics to Watch

- **API Latency**: Check `API_LATENCY` logs (should be < 5s)
- **Memory Operations**: Monitor Pinecone query times
- **Session Duration**: Track in MongoDB
- **Error Rates**: Watch for exceptions in logs

### Log Locations

- Service logs: `logs/teaching_assistant.log`
- MongoDB queries: Check `[MONGODB]` entries
- Memory operations: Check `[MEMORY_STORE]` entries
- Skills execution: Check `[SKILLS_MANAGER]` entries

## 🔐 Security Notes

- Never commit `.env` file with real API keys
- Use environment variables in production
- Rotate API keys regularly
- Monitor Pinecone usage and costs

## 📚 Additional Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [Memory System](Memory/README.md) - Memory architecture (if exists)
- [Skills Guide](skills/README.md) - Skill development guide (if exists)

## 🐛 Troubleshooting

### Service won't start
1. Check MongoDB is running: `mongosh`
2. Verify environment variables are set
3. Check port 8002 is available

### Memory system not working
1. Verify `PINECONE_API_KEY` is valid
2. Check Pinecone dashboard for index status
3. Review logs for Pinecone errors

### Frontend can't connect
1. Check CORS origins in logs
2. Verify service is running on port 8002
3. Check WebSocket/SSE connections in browser console

## 📝 License

[Your License Here]

## 👥 Contributors

[Your Team/Name Here]

---

**Last Updated**: December 30, 2025  
**Version**: 2.0.0 (Post-fixes)


# TeachingAssistant Setup Guide

## Required Environment Variables

The TeachingAssistant service requires the following environment variables to function properly:

### Memory System (Pinecone)

```bash
# Pinecone API Key (REQUIRED for memory functionality)
PINECONE_API_KEY=pcsk_xxxxx

# Pinecone Environment (optional, defaults to 'us-east-1')
PINECONE_ENVIRONMENT=us-east-1
```

**How to get your Pinecone API Key:**
1. Sign up at https://www.pinecone.io/
2. Create a new project
3. Go to API Keys section
4. Copy your API key (starts with `pcsk_`)

### LLM (Gemini)

```bash
# Gemini API Key (REQUIRED for memory extraction and reflection)
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**How to get your Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key

### MongoDB

```bash
# MongoDB Connection String (REQUIRED for session management)
MONGODB_URI=mongodb://localhost:27017/ai_tutor

# Or for MongoDB Atlas:
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai_tutor
```

## Configuration File

Create a `.env` file in the project root with all required variables:

```bash
# .env file
PINECONE_API_KEY=pcsk_your_key_here
PINECONE_ENVIRONMENT=us-east-1
GEMINI_API_KEY=AIzaSy_your_key_here
MONGODB_URI=mongodb://localhost:27017/ai_tutor
```

## Verification

After setting up environment variables, start the TeachingAssistant service:

```bash
python services/TeachingAssistant/api.py
```

Check the logs for:
- ✅ `[MONGODB] Connected to database: ai_tutor`
- ✅ `[TEACHING_ASSISTANT] Initialized with config-driven architecture`
- ✅ `[MEMORY_CONFIG] Loaded configuration`

If you see errors:
- ❌ `PINECONE_API_KEY not set` - Add the API key to your .env file
- ❌ `Invalid API Key` - Check that your Pinecone API key is correct
- ❌ `Unauthorized` - Verify your Gemini API key

## Troubleshooting

### Memory System Not Working

If you see `Error in background memory initialization: (401) Unauthorized`:
1. Check that `PINECONE_API_KEY` is set in your environment
2. Verify the key is valid and not expired
3. Ensure the key starts with `pcsk_`

### SSE Connection Blocked

If frontend shows CORS errors for `/sse/instructions`:
1. Ensure TeachingAssistant service is running
2. Check that frontend origin is in ALLOWED_ORIGINS
3. Restart the service after environment changes

## Optional Configuration

Additional environment variables for fine-tuning:

```bash
# Session sync interval (seconds)
TA_SESSION_SYNC_INTERVAL=1.0

# Context sync interval (seconds)
TA_CONTEXT_SYNC_INTERVAL=1.0

# Inactivity threshold (seconds)
TA_INACTIVITY_THRESHOLD=60

# Memory retrieval debounce (seconds)
TA_MEMORY_RETRIEVAL_DEBOUNCE=5.0
```


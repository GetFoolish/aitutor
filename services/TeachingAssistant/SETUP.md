# TeachingAssistant Setup Guide

## Required Environment Variables

The TeachingAssistant service requires the following environment variables to function properly:

### Memory System (MongoDB Atlas Vector Search)

The memory system uses **MongoDB Atlas Vector Search** by default. No additional vector database is required.

```bash
# MongoDB Connection String (REQUIRED - includes vector search)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai_tutor
MONGODB_DB_NAME=ai_tutor
```

> **Note:** Pinecone is available as an optional fallback but is NOT required.
> Set `MEMORY_STORE_BACKEND=pinecone` only if you specifically need Pinecone.

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
GEMINI_API_KEY=AIzaSy_your_key_here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai_tutor
MONGODB_DB_NAME=ai_tutor
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
- ❌ `MONGODB_URI not set` - Add MongoDB connection string to your .env file
- ❌ `Unauthorized` - Verify your Gemini API key
- ❌ `MongoDB connection failed` - Check your MongoDB URI and network access

## Troubleshooting

### Memory System Not Working

If memories are not being saved/retrieved:
1. Check that `MONGODB_URI` is set correctly
2. Verify MongoDB Atlas Vector Search index is configured (see below)
3. Check MongoDB Atlas IP whitelist includes your IP

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


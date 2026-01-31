# Memory System Testing Guide

This guide explains how to test the MongoDB-based memory retrieval system for the Teaching Assistant.

## Overview

The memory system uses **MongoDB Atlas Vector Search** to retrieve semantically relevant memories during tutoring sessions. This replaces the previous Pinecone-based implementation.

## Prerequisites

### 1. MongoDB Atlas Setup

You need a MongoDB Atlas cluster with Vector Search enabled:

1. Create a cluster on [MongoDB Atlas](https://cloud.mongodb.com/)
2. Get your connection string (starts with `mongodb+srv://`)
3. Create a Vector Search index on the `memories` collection:

**Index Configuration** (create in Atlas UI → Database → Search → Create Index):
- **Index Name:** `vector_index`
- **Database:** `ai_tutor`
- **Collection:** `memories`

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "student_id"
    },
    {
      "type": "filter",
      "path": "type"
    }
  ]
}
```

### 2. Environment Variables

Copy the example file and fill in your values:

```bash
cp services/TeachingAssistant/.env.example .env
```

Edit `.env` with your credentials (minimum required):

```bash
# REQUIRED - Get from MongoDB Atlas UI → Database → Connect
MONGODB_URI=mongodb+srv://YOUR_USER:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/ai_tutor

# REQUIRED - Get from https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# REQUIRED - Any random string for JWT auth
JWT_SECRET=your_random_secret_string_here

# MUST match your Atlas vector index (default: 768)
EMBEDDING_DIMENSION=768

# JWT for API auth
JWT_SECRET=your_jwt_secret
```

### 3. Python Dependencies

```bash
pip install pymongo google-genai python-dotenv
```

## Quick Start - One Command Test

Run the complete test with:

```bash
cd /path/to/aitutor-merge
source env/bin/activate && export $(grep -v '^#' .env | xargs) && python3 -c "
import sys
sys.path.insert(0, '.')
from services.TeachingAssistant.Memory.mongodb_vector_store import MongoDBMemoryStore

store = MongoDBMemoryStore()
print('Store enabled:', store.enabled)

# Test search
results = store.search(query_text='I feel frustrated with math', student_id='maya_final', top_k=3)
print(f'Found {len(results)} memories:')
for r in results:
    print(f'  - Score: {r.get(\"score\", 0):.2f} | {r.get(\"text\", \"\")[:60]}...')
"
```

Expected output (scores should vary, indicating vector search is working):
```
Store enabled: True
Found 3 memories:
  - Score: 0.72 | maybe. it's just hard when i feel so dumb compared to everyo...
  - Score: 0.71 | i guess. it's just... he's so good at math and science...
  - Score: 0.68 | okay i feel a little better about friday. still scared but...
```

**Note:** If you see flat scores like `0.60, 0.60, 0.60`, vector search is not working - check your Atlas vector index.

## Running the Server

```bash
# Start the Teaching Assistant server
source env/bin/activate && \
export $(grep -v '^#' .env | xargs) && \
python -m uvicorn services.TeachingAssistant.api:app --host 0.0.0.0 --port 8002
```

## Watching Memory Logs

In a separate terminal, watch for memory retrieval:

```bash
tail -f /tmp/ta_server.log | grep -i memory
```

You should see logs like:
```
[MEMORY] 🔍 Searching memories for user message: I feel frustrated...
[MEMORY] ✅ Found relevant memories, injecting into session
```

## Test Queries

These queries should retrieve memories for student `maya_final`:

| Query | Expected Memory Topic |
|-------|----------------------|
| "I love art and drawing" | Art, English, fantasy novels |
| "I play sports" | Soccer, midfielder |
| "My brother is better than me" | Sibling comparison, disappointment |
| "I feel nervous" | Test anxiety, game nervousness |
| "Tell me about your pet" | Biscuit the dog |

## Architecture

```
Frontend (React)
    ↓ WebSocket
TeachingAssistant API (FastAPI)
    ↓ Event Queue
Event Processor
    ↓ On USER_MESSAGE
Memory Retrieval (MongoDB Vector Search)
    ↓ SSE
Frontend (receives memory-informed responses)
```

## Key Files Changed

| File | Purpose |
|------|---------|
| `Memory/mongodb_vector_store.py` | MongoDB-based memory store (replaces Pinecone) |
| `session_manager.py` | Memory retrieval using MongoDB |
| `teaching_assistant.py` | Event loop with memory trigger |
| `api.py` | Removed Pinecone dependencies |
| `database/__init__.py` | Removed Pinecone exports |
| `handlers/queue_manager.py` | Event queue logging |

## Troubleshooting

### "Vector search failed" error
- Ensure you created the `vector_index` in MongoDB Atlas UI
- Check that `EMBEDDING_DIMENSION=768` matches your index

### No memories found
- Check the `student_id` matches what's in the database
- Run: `db.memories.distinct("student_id")` to see available IDs

### Dimension mismatch error
- Your Atlas index and `EMBEDDING_DIMENSION` env var must match
- Default is 768 for Gemini embeddings

### Flat scores (0.60, 0.50) instead of varied scores
- This means vector search failed and keyword fallback is being used
- Check that your Atlas vector index is named `vector_index`
- Verify index status is "READY" in Atlas UI
- Ensure memories have embeddings: `db.memories.countDocuments({embedding: {$exists: true}})`

## Verifying the Setup

```bash
# Check MongoDB connection and memories
python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.ai_tutor
print('Collections:', db.list_collection_names())
print('Memories:', db.memories.count_documents({}))
print('With embeddings:', db.memories.count_documents({'embedding': {'\$exists': True}}))
"
```

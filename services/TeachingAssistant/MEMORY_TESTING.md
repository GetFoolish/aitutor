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

Create a `.env` file with these required variables:

```bash
# MongoDB Atlas (REQUIRED)
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/ai_tutor?retryWrites=true&w=majority

# Embeddings - use Gemini (REQUIRED - pick one)
GOOGLE_API_KEY=your_google_api_key
# OR
GEMINI_API_KEY=your_gemini_api_key

# Embedding dimension - MUST match your Atlas vector index
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

Expected output:
```
Store enabled: True
Found 3 memories:
  - Score: 0.66 | maybe. it's just hard when i feel so dumb compared to everyo...
  - Score: 0.65 | i guess. it's just... he's so good at math and science...
  - Score: 0.64 | okay i feel a little better about friday. still scared but...
```

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

# Memory System Integration Guide

## New Components (Moltbot-Inspired)

This branch adds two new modules to enhance AITutor's memory system with features inspired by Moltbot:

### 1. ConversationStore (`conversation_store.py`)

**Purpose**: Full conversation history storage with search and auto-compaction.

**Features**:
- Store every turn in MongoDB (searchable)
- Full-text search across all sessions (like Moltbot's grep)
- Token counting with tiktoken
- Auto-compaction when context exceeds limits
- Cross-session conversation retrieval

**Key Methods**:
```python
from services.TeachingAssistant.Memory import get_conversation_store

store = get_conversation_store(student_id)

# Add a turn
store.add_turn(
    session_id="sess_123",
    speaker="student",  # or "tutor" or "system"
    text="I don't understand derivatives",
    emotion="confused"
)

# Search conversations (Moltbot grep equivalent)
results = store.search_conversations(
    query="derivatives",
    student_id="user_123",
    limit=10
)

# Get cross-session context
past_turns = store.get_cross_session_context(
    student_id="user_123",
    query="calculus help",
    current_session_id="sess_456"
)
```

### 2. ContextBuilder (`context_builder.py`)

**Purpose**: Intelligent context window construction for LLM prompts.

**Features**:
- Token budget management
- Priority-based content inclusion
- Automatic truncation of low-priority content
- Integrates biography, memories, conversation, and cross-session context

**Key Methods**:
```python
from services.TeachingAssistant.Memory import get_context_builder

builder = get_context_builder()

# Build optimal context for LLM
context = builder.build_context(
    session_id="sess_123",
    student_id="user_456",
    current_message="Can you explain integration?",
    biography="Student named Alex, struggles with calculus...",
    memories=[{"text": "Prefers visual explanations"}],
    injections=["[Use encouraging tone]"],
    include_cross_session=True
)

# Convert to messages format
messages = context.to_messages()

# Check what was included
print(f"Total tokens: {context.total_tokens}")
print(f"Included: {context.included_sources}")
print(f"Truncated: {context.truncated_sources}")
```

## Integration with Existing Code

### Session Manager Integration

Update `session_manager.py` to use ConversationStore:

```python
from .Memory import get_conversation_store

class SessionManager:
    def add_conversation_turn(self, session_id, speaker, text, emotion=None):
        # Existing MongoDB session update
        # ... existing code ...
        
        # NEW: Also store in ConversationStore
        session = self.sessions.find_one({"session_id": session_id})
        if session:
            store = get_conversation_store(session.get("student_id"))
            store.add_turn(
                session_id=session_id,
                student_id=session.get("student_id"),
                speaker=speaker,
                text=text,
                emotion=emotion
            )
```

### Teaching Assistant Integration

Update `teaching_assistant.py` to use ContextBuilder:

```python
from .Memory import get_context_builder

class TeachingAssistant:
    def get_llm_context(self, session_id, student_id, current_message):
        """Build context for LLM call"""
        builder = get_context_builder()
        
        # Get student info
        bio_data = self.session_manager.get_student_biography(student_id)
        
        # Get retrieved memories
        memories = self.session_manager.retrieve_relevant_memories(
            student_id=student_id,
            query_text=current_message
        )
        
        # Build context
        context = builder.build_context(
            session_id=session_id,
            student_id=student_id,
            current_message=current_message,
            biography=bio_data.get("biography", ""),
            memories=memories,
            include_cross_session=True
        )
        
        return context.to_messages()
```

### API Integration

In `api.py`, add search endpoint:

```python
from services.TeachingAssistant.Memory import get_conversation_store

@router.get("/memory/search")
async def search_conversations(
    query: str,
    user_id: str = Depends(get_current_user)
):
    store = get_conversation_store(user_id)
    results = store.search_conversations(
        query=query,
        student_id=user_id,
        limit=20
    )
    return {"results": results}

@router.get("/memory/stats")
async def get_memory_stats(
    user_id: str = Depends(get_current_user)
):
    store = get_conversation_store(user_id)
    return store.get_student_stats(user_id)
```

## Environment Variables

Add these to your `.env`:

```bash
# Compaction settings (Moltbot-style)
COMPACTION_MODE=safeguard  # off, safeguard, or aggressive
COMPACTION_MAX_TOKENS=100000
COMPACTION_TARGET_TOKENS=50000
COMPACTION_PRESERVE_RECENT=10

# Context builder budgets
CONTEXT_MAX_TOKENS=100000
CONTEXT_CONVERSATION_BUDGET=50000
CONTEXT_MEMORY_BUDGET=10000
CONTEXT_BIOGRAPHY_BUDGET=5000
```

## MongoDB Collections

New collection: `conversation_history`

Schema:
```javascript
{
    "_id": ObjectId,
    "session_id": "sess_abc123",
    "student_id": "user_456",
    "speaker": "student",  // "student", "tutor", "system"
    "text": "I don't understand derivatives",
    "timestamp": ISODate,
    "turn_number": 5,
    "emotion": "confused",
    "token_count": 12,
    "is_summary": false,
    "summarizes_turns": [],  // Only for summary turns
    "metadata": {}
}
```

Indexes (created automatically):
- `student_id`
- `session_id`
- `(student_id, session_id)`
- `(student_id, timestamp)`
- `text` (full-text search)

## Comparison: Before vs After

| Feature | Before (v1-homework) | After (v1-memory) |
|---------|---------------------|-------------------|
| Conversation storage | Session.conversation[] | conversation_history collection |
| Search | Memory vectors only | Full-text + vectors |
| Context limit | Last 5 turns | Token-aware, configurable |
| Compaction | None | Automatic summarization |
| Cross-session | Memory retrieval | Conversation + memories |
| Token tracking | None | tiktoken counting |

## Testing

```python
# Test conversation store
from services.TeachingAssistant.Memory import get_conversation_store

store = get_conversation_store("test_user")

# Add some turns
store.add_turn("sess_1", "student", "Hello!", student_id="test_user")
store.add_turn("sess_1", "tutor", "Hi! How can I help?", student_id="test_user")
store.add_turn("sess_1", "student", "I need help with calculus", student_id="test_user")

# Search
results = store.search_conversations("calculus", student_id="test_user")
print(f"Found {len(results)} results")

# Stats
stats = store.get_student_stats("test_user")
print(f"Total turns: {stats['total_turns']}")
```

## Migration

If you have existing conversation data in session documents, migrate with:

```python
from services.TeachingAssistant.Memory import get_conversation_store
from managers.mongodb_manager import MongoDBManager

mongo = MongoDBManager()
store = get_conversation_store()

# Migrate each session's conversation
for session in mongo.db.sessions.find({"conversation": {"$exists": True}}):
    student_id = session.get("student_id", session.get("user_id"))
    session_id = session["session_id"]
    
    for i, turn in enumerate(session.get("conversation", [])):
        store.add_turn(
            session_id=session_id,
            student_id=student_id,
            speaker=turn.get("speaker", "student"),
            text=turn.get("text", ""),
            emotion=turn.get("emotion")
        )
    
    print(f"Migrated {len(session.get('conversation', []))} turns from {session_id}")
```

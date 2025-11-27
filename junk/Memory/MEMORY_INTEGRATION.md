# Memory Integration for Live AI Conversation

## Overview

This system implements persistent memory for live AI conversations using Gemini Live API. The memory system allows the AI to remember student preferences, interests, and details across multiple conversation sessions.

## Architecture

### Components

1. **a2a.py** - Live conversation handler with memory integration
2. **gemini.py** - Memory analysis and generation engine
3. **student/** - Data storage structure

### Folder Structure

```
student/
├── conversation/
│   ├── last_conversation/     # Latest conversation (1 file)
│   └── all_conversation/       # All conversations (timestamped)
└── memory/
    ├── current_memory/         # Latest memory (1 file)
    └── all_memory/              # All memories (timestamped)
```

## Approach

### Memory Integration Strategy

**Problem**: Live AI models don't maintain memory between sessions.

**Solution**: 
- Extract student information from conversations
- Store as structured memory in JSON
- Inject memory into system instruction at session start
- Update memory after each session

### Key Design Decisions

1. **Turn-based Storage**: Conversations saved as complete turns (Student/AI pairs)
2. **Memory Persistence**: Latest memory always available in `current_memory/`
3. **Automatic Updates**: Memory regenerated after each session via `/sc` command
4. **System Instruction Injection**: Memory loaded and included in AI's system prompt

## Flow

### Session Lifecycle

```
1. Start Session (/start)
   ↓
   Load current_memory/memory.json
   ↓
   Inject into system instruction
   ↓
   Start live conversation

2. During Conversation
   ↓
   Real-time transcription
   ↓
   Save turns to conversation/last_conversation/
   ↓
   Also save to conversation/all_conversation/ (timestamped)

3. End Session (/sc)
   ↓
   Save final conversation
   ↓
   Trigger gemini.py for memory analysis
   ↓
   Generate/update memory from conversation
   ↓
   Save to memory/current_memory/ (overwrite)
   ↓
   Save to memory/all_memory/ (timestamped)

4. Next Session (/start)
   ↓
   Load updated memory
   ↓
   AI uses memory for personalized responses
```

### Memory Generation Process

```
gemini.py execution:
   ↓
   Load conversation from last_conversation/
   ↓
   Load previous memory from current_memory/
   ↓
   Build system instruction with:
     - Base instruction
     - Previous memory
     - Update instructions
   ↓
   Send to LLM (single request)
   ↓
   Extract student details (likes, dislikes, language, etc.)
   ↓
   Save updated memory
```

## Features

### 1. Persistent Memory
- Student preferences remembered across sessions
- Memory automatically updated after each conversation
- Third-person format for consistency

### 2. Automatic Memory Generation
- Triggered via `/sc` command
- Analyzes complete conversation
- Merges old and new information

### 3. Continuous Sessions
- Same terminal, multiple sessions
- Memory loaded fresh for each session
- No manual intervention required

### 4. Complete History
- All conversations archived with timestamps
- All memory versions preserved
- Easy to track changes over time

## Usage

### Commands

- `/start` - Begin new conversation session
- `/sc` - Close session and generate memory
- `q` - Quit application

### Running the System

```bash
# Start the application
python a2a.py

# Follow prompts:
# 1. Type '/start' to begin conversation
# 2. Have conversation with AI
# 3. Type '/sc' to close and generate memory
# 4. Type '/start' again for next session (with updated memory)
```

### Manual Memory Generation

```bash
# Generate memory from latest conversation
python gemini.py
```

## Testing

### Test Memory Persistence

1. Start session: `/start`
2. Share preferences: "I like dancing and prefer Hindi"
3. Close session: `/sc`
4. Check memory: `student/memory/current_memory/memory.json`
5. Start new session: `/start`
6. Verify: AI should remember dancing and Hindi preference

### Test Memory Updates

1. First session: Mention "I like painting"
2. Close: `/sc` → Memory generated
3. Second session: Say "I don't like painting anymore, I like dancing"
4. Close: `/sc` → Memory updated
5. Verify: Memory should show dancing, not painting

### Verify Files

```bash
# Check latest conversation
cat student/conversation/last_conversation/conversation.json

# Check current memory
cat student/memory/current_memory/memory.json

# List all conversations
ls student/conversation/all_conversation/

# List all memories
ls student/memory/all_memory/
```

## Technical Details

### Memory Format

```json
{
  "memory": "Student is a 10th grade student who likes Physics and Math, enjoys Cricket and Space topics, prefers English for study."
}
```

### Conversation Format

```json
[
  {
    "speaker": "Student",
    "text": "Hello"
  },
  {
    "speaker": "AI",
    "text": "Hi! How can I help?"
  }
]
```

### System Instruction Enhancement

Memory is injected into system instruction:
```
Base Instruction + Student Memory + Usage Instructions
```

## Benefits

1. **Personalization**: AI remembers student preferences
2. **Continuity**: Conversations feel connected across sessions
3. **Efficiency**: Single LLM request for memory generation
4. **Reliability**: File-based storage, no database needed
5. **Simplicity**: Easy to understand and modify

## Limitations

- Single student support (one memory file)
- File-based storage (not scalable for multiple users)
- Memory size limited by LLM context window
- Requires manual session close (`/sc`) for memory update

## Future Enhancements

- Multi-user support with user-specific folders
- Database backend for scalability
- Automatic memory updates during conversation
- Memory compression for long-term storage


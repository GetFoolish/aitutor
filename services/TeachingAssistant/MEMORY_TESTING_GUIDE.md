# Memory Implementation Testing Guide

This guide explains how to test the Living Biography and Cognitive Memory Pipeline implementation.

## Overview

The memory system consists of:
1. **Living Biography** - Dynamic student profile that evolves with each session
2. **Cognitive Memory Pipeline** - Extracts and stores memories with provenance tracking
3. **Interest Mapper** - Dynamically connects student interests to academic concepts
4. **Contextual Weaving** - Naturally integrates personalization into tutoring

## Prerequisites

1. **MongoDB** running locally or connection to cloud instance
2. **TeachingAssistant service** running on port 8002
3. **Frontend** running on port 5173
4. A test user account with some session history

## Quick Start

### 1. Start the TeachingAssistant Service

```bash
cd services/TeachingAssistant
python api.py
```

The service runs on `http://localhost:8002`

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

### 3. Verify Services Are Running

```bash
# Check TeachingAssistant health
curl http://localhost:8002/health

# Check biography endpoint
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:8002/biography
```

## Testing the Memory System

### A. Console Testing (Browser DevTools)

Open the browser console (F12) and use these debug functions:

```javascript
// Initialize memory debug functions
window.memoryDebug

// Fetch current biography
window.memoryDebug.fetchBiography()

// Fetch all memories
window.memoryDebug.fetchMemories()

// Fetch memories by type
window.memoryDebug.fetchMemoriesByType('INTEREST')
window.memoryDebug.fetchMemoriesByType('PREFERENCE')
window.memoryDebug.fetchMemoriesByType('ACHIEVEMENT')

// Test memory extraction from sample text
window.memoryDebug.testExtraction("I really love playing Minecraft with my brother")

// View current session context
window.memoryDebug.getSessionContext()
```

### B. Testing Biography Generation

1. Have a conversation with the tutor (at least 5-10 exchanges)
2. End the session (click "End Session" button)
3. Check the biography was updated:

```javascript
window.memoryDebug.fetchBiography()
```

You should see:
- `narrative_bio`: A flowing narrative about the student
- `structured_data`: Key facts (interests, learning style, etc.)
- `last_updated`: Recent timestamp

### C. Testing Interest-Based Connections

During a tutoring session, the system should naturally connect the student's interests to math concepts.

**Test scenario:**
1. Ensure the student has interests stored (e.g., "Minecraft", "soccer")
2. Start a session and work on a math problem
3. Check console logs for: `[InterestMapper] Generated connection:`

The tutor should reference interests naturally, e.g.:
- "Think of this like building in Minecraft..."
- "It's similar to tracking soccer scores..."

### D. Testing Memory/Bio Panel in UI

1. Open the Console sidebar (right panel)
2. Click the dropdown at the top
3. Select **"Memory/Bio"**
4. You should see:
   - Biography narrative
   - Structured data (interests, learning style, etc.)
   - Recent memories

### E. Testing Contextual Weaving

1. Start a tutoring session
2. Monitor the browser console for these logs:
   - `[EventProcessor] Initializing session context...`
   - `[EventProcessor] Session context initialized with X interests`
   - `[InterestMapper] Generated connection:`

3. The tutor should:
   - Greet the student by name
   - Reference personal details naturally
   - Connect math concepts to interests

## API Endpoints for Testing

### Biography Endpoints

```bash
# Get biography
GET /biography
Authorization: Bearer <token>

# Force biography regeneration
POST /biography/regenerate
Authorization: Bearer <token>
```

### Memory Endpoints

```bash
# Get all memories
GET /memories
Authorization: Bearer <token>

# Get memories by type
GET /memories?type=INTEREST
Authorization: Bearer <token>

# Search memories
GET /memories/search?query=minecraft
Authorization: Bearer <token>
```

### Session Endpoints

```bash
# Start session (triggers greeting with personalization)
POST /session/start
Authorization: Bearer <token>

# End session (triggers biography update)
POST /session/end
Authorization: Bearer <token>
```

## Test Data

Sample test conversations are available in:
```
services/TeachingAssistant/Memory/Memory_Brief/sample_conversations_for_testing/
```

- `session_1_intro.md` - First meeting, basic introduction
- `session_2_family.md` - Family details, home life
- `session_3_emotional.md` - Emotional moments, frustration handling
- `session_4_breakthrough.md` - Academic breakthroughs
- `session_5_deep_connection.md` - Deep personal connection

## Troubleshooting

### Biography not updating
1. Check TeachingAssistant logs for errors
2. Verify MongoDB connection
3. Ensure session has conversation turns stored

### Interests not being used
1. Check if student has interests in biography: `window.memoryDebug.fetchBiography()`
2. Check EventProcessor logs for initialization
3. Verify InterestMapper is generating connections

### Memory/Bio dropdown not showing
1. Hard refresh the page (Cmd+Shift+R)
2. Check console for errors
3. Verify TeachingAssistant service is running

### 404 on /biography endpoint
1. Restart TeachingAssistant service
2. Check if user exists in MongoDB
3. Verify JWT token is valid

## Files Modified in This Implementation

### Frontend
- `src/hooks/useMemoryDebug.ts` - Debug functions for console testing
- `src/components/side-panel/SidePanel.tsx` - Memory/Bio panel UI
- `src/features/tutor/tutor-service.ts` - Biography injection
- `src/App.tsx` - Media mixer configuration

### Backend (TeachingAssistant)
- `Memory/retriever.py` - Memory retrieval and synthesis
- `core/event_processor.py` - Contextual weaving integration
- `core/interest_mapper.py` - Dynamic interest-to-concept connections
- `core/learning_style_tracker.py` - Learning pattern tracking
- `core/followup_tracker.py` - Event/commitment tracking
- `handlers/injection_manager.py` - Memory injection formatting
- `greeting_handler.py` - Personalized greetings
- `session_manager.py` - Session lifecycle management

## Expected Behavior

When everything is working correctly:

1. **Session Start**: Tutor greets student by name, references something personal
2. **During Session**: Tutor connects math concepts to student's interests naturally
3. **Frustration Detected**: Tutor adapts pace, references past successes
4. **Session End**: Biography is updated with new learnings
5. **Next Session**: Tutor remembers and follows up on previous topics

## Contact

For issues with this implementation, check the git history on `v1-memory` branch.

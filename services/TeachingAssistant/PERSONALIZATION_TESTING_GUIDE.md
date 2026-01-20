# Memory & Personalization System - Testing Guide

Complete testing guide for the memory system and personalization features.

## Overview

The personalization system makes Adam (the AI tutor) deeply personal by:
1. **Remembering** - Biography, preferences, academic history
2. **Connecting** - Linking student interests to concepts dynamically
3. **Adapting** - Learning what explanation styles work best
4. **Following up** - Remembering tests, events, and commitments

## Prerequisites

1. **MongoDB** running with user data
2. **Gemini API key** configured for LLM-powered features
3. **TeachingAssistant service** running on port 8002
4. Active user session with JWT token

## Quick Start

### 1. Configure Environment

```bash
cd services/TeachingAssistant
cp .env.example .env

# Add your Gemini API key
echo "GEMINI_API_KEY=your-key-here" >> .env
```

### 2. Start the Service

```bash
python api.py
```

### 3. Verify Health

```bash
curl http://localhost:8002/health
```

---

## API Endpoints

### Biography Endpoints

#### GET /student/biography
Get the student's living biography.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8002/student/biography
```

**Response:**
```json
{
  "user_id": "user_123",
  "biography": {
    "narrative": "Alex is a 4th grader who loves Minecraft...",
    "structured_data": {
      "name": "Alex",
      "grade": 4,
      "interests": ["Minecraft", "soccer", "dogs"],
      "learning_preferences": ["visual", "hands-on"],
      "strengths": ["pattern recognition"],
      "challenges": ["word problems"]
    }
  },
  "has_biography": true
}
```

---

### Interest Mapping Endpoints

#### POST /personalization/map-interest
Generate a teaching connection between interests and a concept.

```bash
curl -X POST http://localhost:8002/personalization/map-interest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "interests": ["Minecraft", "soccer"],
    "topic": "area",
    "subject": "math"
  }'
```

**Response:**
```json
{
  "success": true,
  "interests": ["Minecraft", "soccer"],
  "topic": "area",
  "connection": "Think about Minecraft - when you're building a floor, you count how many blocks fit across and how many fit down. If your room is 4 blocks by 6 blocks, that's 24 blocks total for the floor. That's area! Same idea with a soccer field - how much grass is there?"
}
```

---

### Learning Style Endpoints

#### GET /personalization/learning-style
Get the student's learning style profile.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/learning-style
```

**Response:**
```json
{
  "user_id": "user_123",
  "has_profile": true,
  "profile": {
    "preferred_styles": ["visual", "example_first"],
    "pace": "moderate",
    "frustration_triggers": ["too many steps at once"],
    "breakthrough_patterns": ["real-world analogies"],
    "confidence": 0.75
  }
}
```

#### POST /personalization/learning-style/update
Update learning style based on an interaction.

```bash
curl -X POST http://localhost:8002/personalization/learning-style/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tutor_text": "Think of fractions like pizza slices...",
    "student_response": "Oh! So 1/4 is like having one slice of a pizza cut into 4 pieces!",
    "was_helpful": true,
    "topic": "fractions"
  }'
```

---

### Follow-up Tracking Endpoints

#### GET /personalization/followups
Get pending follow-ups (tests, events, commitments).

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/followups
```

**Response:**
```json
{
  "user_id": "user_123",
  "pending_count": 3,
  "due_count": 2,
  "followups": [
    {
      "type": "test",
      "description": "Math test on Friday",
      "due_date": "2024-01-26",
      "priority": 3,
      "context": "Covering fractions and decimals"
    },
    {
      "type": "commitment",
      "description": "Practice multiplication tables",
      "due_date": null,
      "priority": 2,
      "context": "Student said they would practice tonight"
    }
  ]
}
```

#### POST /personalization/followups/extract
Extract follow-ups from a conversation.

```bash
curl -X POST http://localhost:8002/personalization/followups/extract \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": [
      {"speaker": "student", "text": "I have a big math test on Friday"},
      {"speaker": "tutor", "text": "Good to know! What topics will it cover?"},
      {"speaker": "student", "text": "Fractions and decimals. I'm gonna practice tonight!"}
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "extracted_count": 2,
  "followups": [
    {"type": "test", "description": "Math test on Friday (fractions and decimals)", "priority": 3},
    {"type": "commitment", "description": "Practice tonight", "priority": 2}
  ]
}
```

---

### Session Context Endpoint

#### GET /personalization/session-context
Get full personalization context for a tutoring session.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/session-context
```

**Response:**
```json
{
  "user_id": "user_123",
  "biography": { ... },
  "learning_style": {
    "preferred_styles": ["visual", "analogy"],
    "pace": "moderate"
  },
  "interests": ["Minecraft", "soccer", "dogs"],
  "due_followups": [
    {"type": "test", "description": "Math test on Friday"}
  ],
  "personalization_available": true
}
```

---

## Testing Scenarios

### Scenario 1: New User (Cold Start)

```bash
# Get biography (should be empty)
curl -H "Authorization: Bearer <token>" http://localhost:8002/student/biography
# Expected: has_biography: false

# Get learning style (should be empty)
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/learning-style
# Expected: has_profile: false

# Get followups (should be empty)
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/followups
# Expected: pending_count: 0
```

### Scenario 2: Interest Mapping

```bash
# Map Minecraft to fractions
curl -X POST http://localhost:8002/personalization/map-interest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"interests": ["Minecraft"], "topic": "fractions", "subject": "math"}'

# Map cooking to chemical reactions
curl -X POST http://localhost:8002/personalization/map-interest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"interests": ["cooking"], "topic": "chemical reactions", "subject": "science"}'
```

### Scenario 3: Learning Style Evolution

```bash
# First interaction - visual worked
curl -X POST http://localhost:8002/personalization/learning-style/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tutor_text": "[Draws diagram of fraction]",
    "student_response": "That makes so much sense now!",
    "was_helpful": true,
    "topic": "fractions"
  }'

# Second interaction - step-by-step didn't work
curl -X POST http://localhost:8002/personalization/learning-style/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tutor_text": "Step 1: Find the denominator. Step 2: Multiply...",
    "student_response": "Wait I'm confused, can you show me?",
    "was_helpful": false,
    "topic": "fractions"
  }'

# Check profile - should now prefer visual over step-by-step
curl -H "Authorization: Bearer <token>" http://localhost:8002/personalization/learning-style
```

### Scenario 4: Follow-up Extraction

```bash
# Extract from conversation mentioning a test
curl -X POST http://localhost:8002/personalization/followups/extract \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": [
      {"speaker": "student", "text": "I have my spelling bee next Tuesday"},
      {"speaker": "tutor", "text": "Exciting! Are you practicing?"},
      {"speaker": "student", "text": "Yeah my mom is helping me. Also I have a soccer game Saturday!"}
    ]
  }'

# Should extract:
# - Event: Spelling bee on Tuesday
# - Event: Soccer game on Saturday
```

---

## Integration Points

### How Personalization is Used

1. **Session Start**
   - Call `/personalization/session-context`
   - Inject biography, interests, follow-ups into Adam's context
   - Adam greets by name and asks about due follow-ups

2. **During Tutoring**
   - Call `/personalization/map-interest` when explaining concepts
   - Adam connects topics to student's interests

3. **After Interactions**
   - Call `/personalization/learning-style/update` after each exchange
   - System learns what works for this student

4. **Session End**
   - Call `/personalization/followups/extract` on conversation
   - Captures tests, events, commitments for next session

---

## Files Involved

### Core Personalization

| File | Purpose |
|------|---------|
| `core/interest_mapper.py` | LLM-powered interest→concept connections |
| `core/learning_style_tracker.py` | Tracks what explanation styles work |
| `core/followup_tracker.py` | Tracks tests, events, commitments |
| `core/biographer.py` | Generates living biography |
| `core/memory_extractor.py` | Extracts memories from conversations |

### API Integration

| File | Purpose |
|------|---------|
| `api.py` | All personalization endpoints |
| `Memory/retriever.py` | Memory retrieval and synthesis |
| `handlers/injection_manager.py` | Injects personalization into context |

---

## Troubleshooting

### Interest Mapping Returns Empty

1. Check `GEMINI_API_KEY` is set
2. Check logs for Gemini initialization errors
3. Verify interest_mapper.enabled is True

### Learning Style Not Updating

1. Ensure calling with valid JWT token
2. Check MongoDB connection
3. Look for errors in logs

### Follow-ups Not Extracting

1. Verify conversation format is correct
2. Check Gemini API key
3. Ensure session is active

---

## Status

| Component | API Ready | Tested |
|-----------|-----------|--------|
| Biography | ✅ | ⏳ |
| Interest Mapper | ✅ | ⏳ |
| Learning Style | ✅ | ⏳ |
| Follow-up Tracker | ✅ | ⏳ |
| Session Context | ✅ | ⏳ |

All endpoints integrated and ready for end-to-end testing.

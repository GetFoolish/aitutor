# TeachingAssistant v5: Developer Implementation Guide
## Cognitive Memory Architecture with Living Biography

**Branch:** `teaching-assistant-v5`  
**Status:** New system rebuild (current TA moved to `TeachingAssistant_old/`)  
**Tech Stack:** MongoDB + Pinecone + FastAPI  
**Last Updated:** January 8, 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Why We're Rebuilding TA](#2-why-were-rebuilding-ta)
3. [Core Concept: The Living Biography](#3-core-concept-the-living-biography)
4. [System Architecture](#4-system-architecture)
5. [Database Schema (MongoDB)](#5-database-schema-mongodb)
6. [The Biographer Agent](#6-the-biographer-agent)
7. [Session Flow: Start to End](#7-session-flow-start-to-end)
8. [Migration Plan from Old TA](#8-migration-plan-from-old-ta)
9. [Implementation Phases](#9-implementation-phases)
10. [Testing Strategy](#10-testing-strategy)
11. [Code Examples & Prompts](#11-code-examples--prompts)
12. [Appendix: Key Differences from Old TA](#12-appendix-key-differences-from-old-ta)

---

## 1. Executive Summary

**What we're building:**  
A new TeachingAssistant that remembers students as **people with stories**, not just facts. Instead of searching through fragmented JSON files, Adam will read a continuously evolving **Living Biography** of each student at the start of every session.

**The "Before vs. After" moment:**

**Before (Old TA):**
```
Student: "Hey"
Adam: "Hey! How are you doing today? Ready to do some math?"
```

**After (TA v5):**
```
Student: "Hey"
Adam: "Hey Nicolas! How's basketball going? I remember you mentioned that big game 
last week. Ready to tackle some more rover trajectory stuff, or are you still 
thinking about that SpaceX launch?"
```

**Why this matters:**  
The difference between Adam feeling like a tutor who "searches notes" vs. a tutor who *knows you*.

---

## 2. Why We're Rebuilding TA

### Problems with Current TA

1. **Fragmented Memory:**  
   - Memories stored across separate JSON files (`academic.json`, `personal.json`, `context.json`)
   - No unified "story" of the student
   - Adam searches memories but doesn't "know" the student before the conversation starts

2. **No Continuity:**  
   - Opening message references "last session" but doesn't track long-term journey
   - "We started with basic quadratics 3 months ago, now you're mastering discriminants" ← This is missing

3. **Emotional Amnesia:**  
   - Emotional arc tracked per session, but no long-term emotional pattern recognition
   - Can't say "You tend to get anxious before tests, but you always push through"

4. **Technical Debt:**  
   - File-based storage (`TA-opening-retrieval.json`, `TA-closing-retrieval.json`)
   - No version control on biography
   - Hard to migrate or scale

### What v5 Solves

✅ **Biography-First Architecture:** Adam reads your story before saying "hello"  
✅ **Journey Tracking:** "We started here, moved to here, now we're here"  
✅ **Emotional Intelligence:** Pattern recognition across sessions  
✅ **Database-Backed:** MongoDB (structured) + Pinecone (semantic)  
✅ **Clean Slate:** No legacy JSON files, no technical debt

---

## 3. Core Concept: The Living Biography

### What Is a Living Biography?

A **narrative document** (300-500 words) that tells the story of who the student is, how they got here, and where they're going. It's written in prose, not bullet points, and evolves after every session.

### Example Biography (Iteration 1, Post-Onboarding)

```
Nicolas is a 16-year-old student with a deep curiosity about space and engineering. He values 
mastery and autonomy, but has a tendency to set impossibly high standards for himself. When he 
was younger, his father was dismissive of his interests, which created a lasting pattern: Nicolas 
now works obsessively to "prove himself" and becomes deeply discouraged if he falls short.

He's brilliant but struggles with perfectionism. His blindspot: he often underestimates the work 
he's done and fixates on what's incomplete. He plays basketball and has practice most afternoons.

On the platform, Nicolas is just starting his journey with quadratic equations. He's anxious about 
math but willing to try. His emotional baseline is cautiously optimistic.
```

### Example Biography (Iteration 10, After 3 Months)

```
Nicolas is a 16-year-old student with a deep curiosity about space and engineering. He values 
mastery and autonomy, but has a tendency to set impossibly high standards for himself. Early 
conversations revealed that his father was dismissive of his interests when he was younger, 
creating a lasting wound—Nicolas now works obsessively to "prove himself."

A key breakthrough came 6 weeks ago when he connected quadratic trajectories to rocket physics. 
Suddenly, the abstract became tangible. Since then, his confidence has steadily improved. He 
moved from avoiding problems to tackling them head-on.

Recently, Nicolas has been working on completing the square and the discriminant. He tends to 
procrastinate when stressed (especially before tests) but responds well to gentle accountability 
and real-world examples. Last week, he mentioned feeling "tired of school" but lit up when 
discussing the Mars rover landing.

His blindspot remains: he underestimates his own resilience. But he's beginning to see the 
pattern. His fear isn't failure itself; it's the story he tells himself about what failure means 
about him personally. This awareness is new, fragile, but real.

ACADEMIC JOURNEY:
- Month 1: Struggled with basic quadratic concepts. Needed heavy scaffolding. Emotional baseline: 
  anxious, resistant.
- Month 2: Breakthrough with vertex form. Started seeing patterns. Grew comfortable asking questions.
- Month 3 (Current): Working on discriminant and completing the square. Confidence is higher but 
  still fragile around "hard" problems. Ready for more complex applications.
```

### Why Prose, Not Bullets?

**Bullets:**  
- "Procrastinates when stressed"
- "Values autonomy"
- "Father was dismissive"

**Prose:**  
- "When he was younger, his father was dismissive of his interests, creating a lasting pattern: Nicolas now works obsessively to 'prove himself.'"

Prose captures **causality** (why he procrastinates), **emotional resonance** (how it feels), and **temporal evolution** (how it's changing).

---

## 4. System Architecture

### High-Level Flow

```
Session Start
    ↓
[Load Biography from MongoDB]
    ↓
[Inject Biography into System Prompt]
    ↓
[Adam greets student with full context]
    ↓
[Conversation happens]
    ↓
Session End
    ↓
[Extract session insights]
    ↓
[Biographer Agent updates Biography]
    ↓
[Save updated Biography to MongoDB]
    ↓
[Ready for next session]
```

### Tech Stack

**Database Layer:**
- **MongoDB:** Student profiles, biographies, sessions, memories
- **Pinecone:** Semantic search for "find similar emotional moments"

**Application Layer:**
- **FastAPI:** REST API for session management
- **LangChain/LangGraph:** Orchestrate Biographer Agent
- **OpenAI/Claude:** LLM for conversation + biography generation

**Storage Breakdown:**

| Data Type | Where | Why |
|-----------|-------|-----|
| Biography | MongoDB (`students.biography`) | Fast retrieval, versioning |
| Session history | MongoDB (`sessions`) | Conversation logs, stats |
| Factual memories | MongoDB (`memories`) | Entities, dates, commitments |
| Semantic embeddings | Pinecone | "Find similar emotional moments" |

---

## 5. Database Schema (MongoDB)

### Collection: `students`

```json
{
  "_id": "student_123",
  "name": "Nicolas",
  "onboarding_data": {
    "core_values": ["Autonomy", "Mastery", "Family"],
    "north_star_goals": [
      "Get into a good engineering college",
      "Understand math deeply, not just memorize"
    ],
    "personality_traits": ["Perfectionist", "Curious", "Introverted"],
    "blind_spots": ["Underestimates own progress", "Fixates on mistakes"],
    "emotional_baseline": "Anxious but willing",
    "interests": ["Space", "Basketball", "Engineering"],
    "created_at": "2025-10-01T00:00:00Z"
  },
  "biography": {
    "text": "Nicolas is a 16-year-old student...",
    "version": 10,
    "last_updated": "2026-01-08T10:30:00Z",
    "session_count": 28
  },
  "academic_journey": {
    "current_topic": "Discriminant and completing the square",
    "mastered_topics": ["Basic quadratics", "Vertex form", "Factoring"],
    "struggling_topics": ["Fractions", "Word problems"],
    "milestones": [
      {
        "date": "2025-11-15",
        "description": "Breakthrough: connected quadratics to rocket trajectories"
      }
    ]
  },
  "statistics": {
    "total_sessions": 28,
    "total_questions_answered": 142,
    "average_session_duration_minutes": 22.5,
    "last_session_date": "2026-01-07T15:00:00Z"
  }
}
```

### Collection: `sessions`

```json
{
  "_id": "session_abc123",
  "student_id": "student_123",
  "start_time": "2026-01-08T15:00:00Z",
  "end_time": "2026-01-08T15:25:00Z",
  "conversation": [
    {
      "speaker": "adam",
      "text": "Hey Nicolas! How's basketball going?",
      "timestamp": "2026-01-08T15:00:05Z"
    },
    {
      "speaker": "student",
      "text": "Pretty good! We won last night.",
      "timestamp": "2026-01-08T15:00:12Z"
    }
  ],
  "emotional_arc": ["excited", "neutral", "frustrated", "happy"],
  "topics_covered": ["Discriminant", "Quadratic formula"],
  "questions_answered": 5,
  "questions_correct": 4,
  "session_summary": "Nicolas worked through discriminant problems and showed strong understanding despite initial frustration.",
  "key_moments": [
    "Nicolas connected discriminant to rocket parabola example",
    "Showed frustration with arithmetic but persisted"
  ]
}
```

### Collection: `memories`

```json
{
  "_id": "memory_xyz789",
  "student_id": "student_123",
  "session_id": "session_abc123",
  "type": "personal",
  "text": "Won a basketball game last night",
  "importance": 0.6,
  "timestamp": "2026-01-08T15:00:12Z",
  "metadata": {
    "emotion": "excited",
    "topic": "sports"
  }
}
```

### Pinecone Index: `student_memories`

```python
# Vector metadata structure
{
  "id": "memory_xyz789",
  "values": [0.123, -0.456, ...],  # Embedding vector
  "metadata": {
    "student_id": "student_123",
    "text": "Won a basketball game last night",
    "emotion": "excited",
    "importance": 0.6,
    "timestamp": "2026-01-08T15:00:12Z"
  }
}
```

---

## 6. The Biographer Agent

### When It Runs

After **every session**, the Biographer Agent:
1. Reads the session transcript
2. Reads the current biography
3. Decides what to update
4. Writes a new version of the biography

### The Biographer Prompt

```
Role: You are a clinical psychologist and biographer. Your task is to write or update 
a living narrative of the student's psychological and academic journey.

Current Biography (if exists):
{current_biography}

Recent Session Transcript:
{session_transcript}

Session Summary:
- Topics covered: {topics_covered}
- Emotional arc: {emotional_arc}
- Key moments: {key_moments}

Task: Update the biography to reflect:
1. New information about formative experiences, interests, or patterns
2. Evidence of change, growth, or new understanding
3. Shifts in emotional baseline or mood trajectory
4. Contradictions between stated values and observed behavior
5. Breakthroughs or moments of self-awareness
6. Academic progress: what was mastered, what's still challenging

Output: A 300–500 word narrative that reads like a character study. Preserve the 
"thread" of who they are, but weave in new chapters.

Format:
PSYCHOLOGICAL PROFILE:
[Who they are, core values, patterns, blind spots, recent shifts]

ACADEMIC JOURNEY:
[Where they started, key breakthroughs, current focus, what's next]

Important Rules:
- Ground all statements in evidence from sessions. Never hallucinate past events.
- If uncertain, note it: "Nicolas hints that family dynamics shaped his perfectionism, 
  though he hasn't fully articulated this yet."
- Preserve anchor memories (original onboarding data) even as you add new insights.
- Use prose, not bullet points. Tell a story.
```

### Biography Versioning

Every time the biography updates, we increment the version and store:

```json
{
  "biography_history": [
    {
      "version": 1,
      "text": "Nicolas is a 16-year-old...",
      "created_at": "2025-10-01T10:00:00Z",
      "session_count": 1
    },
    {
      "version": 2,
      "text": "Nicolas is a 16-year-old... [updated]",
      "created_at": "2025-10-08T16:00:00Z",
      "session_count": 5
    }
  ]
}
```

This allows rollback if the biography drifts or becomes inaccurate.

---

## 7. Session Flow: Start to End

### Session Start (`POST /session/start`)

**Step 1: Load Biography**
```python
student = mongodb.students.find_one({"_id": student_id})
biography = student["biography"]["text"]
academic_journey = student["academic_journey"]
```

**Step 2: Build System Prompt**
```python
system_prompt = f"""
[SYSTEM PROMPT FOR ADAM]

STUDENT BIOGRAPHY:
{biography}

CURRENT ACADEMIC FOCUS:
{academic_journey["current_topic"]}

MEMORY AND INJECTION HANDLING:
During this session, you will receive 'System Updates' with retrieved memories.
- If an update arrives while you are speaking or just finished: DO NOT hallucinate 
  a new user turn.
- Maintain consistency with your previous response.
- Do not let internal system updates disrupt the natural flow of conversation.

OPENING INSTRUCTION:
Greet the student warmly. Reference something specific from their biography or last 
session. Make them feel seen and remembered.
"""
```

**Step 3: Return Opening Prompt**
```json
{
  "session_id": "session_abc123",
  "prompt": system_prompt,
  "session_info": {
    "student_name": "Nicolas",
    "total_sessions": 28,
    "last_session_date": "2026-01-07"
  }
}
```

### During Session

- **Light Memory Retrieval:** As the student talks, query Pinecone for semantically similar past moments
- **Inject as System Updates:** Send relevant memories to Adam mid-conversation
- **Track Emotional Arc:** Log student's emotional state at key moments

### Session End (`POST /session/end`)

**Step 1: Extract Session Data**
```python
session_data = {
  "conversation": conversation_log,
  "topics_covered": extract_topics(conversation_log),
  "emotional_arc": extract_emotions(conversation_log),
  "key_moments": extract_key_moments(conversation_log),
  "questions_answered": question_count,
  "questions_correct": correct_count
}
```

**Step 2: Run Biographer Agent**
```python
updated_biography = biographer_agent.update(
  current_biography=student["biography"]["text"],
  session_transcript=conversation_log,
  session_summary=session_data
)
```

**Step 3: Save Everything**
```python
# Update student document
mongodb.students.update_one(
  {"_id": student_id},
  {
    "$set": {
      "biography.text": updated_biography,
      "biography.last_updated": datetime.now(),
      "biography.version": student["biography"]["version"] + 1,
      "biography.session_count": student["biography"]["session_count"] + 1
    },
    "$push": {
      "biography_history": {
        "version": student["biography"]["version"] + 1,
        "text": updated_biography,
        "created_at": datetime.now()
      }
    }
  }
)

# Save session
mongodb.sessions.insert_one(session_data)

# Extract and save memories
memories = extract_memories(conversation_log)
mongodb.memories.insert_many(memories)

# Upsert to Pinecone
pinecone_upsert(memories)
```

**Step 4: Return Closing Prompt**
```json
{
  "prompt": "Great work today, Nicolas! I can see you're getting more comfortable with the discriminant. See you next time!",
  "session_info": {
    "duration_minutes": 25,
    "questions_answered": 5,
    "topics_covered": ["Discriminant", "Quadratic formula"]
  }
}
```

---

## 8. Migration Plan from Old TA

### Step 1: Archive Old TA

```bash
cd services/
mv TeachingAssistant TeachingAssistant_old
git checkout -b teaching-assistant-v5
```

### Step 2: Create New Directory Structure

```
services/
  TeachingAssistant/
    __init__.py
    api.py                    # FastAPI routes
    core/
      biographer.py           # Biography generation logic
      session_manager.py      # Session start/end
      memory_extractor.py     # Extract memories from conversation
    models/
      student.py              # Pydantic models
      session.py
      memory.py
    database/
      mongodb.py              # MongoDB connection
      pinecone_client.py      # Pinecone connection
    prompts/
      biographer_prompt.txt   # Biography update prompt
      opening_prompt.txt      # Session start prompt
    scripts/
      migrate_old_data.py     # Migration script
```

### Step 3: Migrate Existing Student Data

**Script: `migrate_old_data.py`**

```python
"""
Migrate students from old TA JSON files to new MongoDB + Biography structure
"""

import json
from pathlib import Path
from datetime import datetime

def migrate_student(old_data_path: str, student_id: str):
    """
    Read old TA data (JSON files) and create initial biography
    """
    # Load old data
    conversations = load_json(f"{old_data_path}/conversations/*.json")
    academic = load_json(f"{old_data_path}/memory/academic.json")
    personal = load_json(f"{old_data_path}/memory/personal.json")
    
    # Generate initial biography from historical data
    initial_biography = generate_initial_biography(
        conversations=conversations,
        academic_memories=academic,
        personal_memories=personal
    )
    
    # Create student document
    student_doc = {
        "_id": student_id,
        "name": extract_name_from_conversations(conversations),
        "onboarding_data": {
            "core_values": infer_values_from_history(conversations),
            "created_at": datetime.now().isoformat()
        },
        "biography": {
            "text": initial_biography,
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "session_count": len(conversations)
        },
        "academic_journey": extract_journey(conversations, academic),
        "statistics": calculate_stats(conversations)
    }
    
    # Insert to MongoDB
    mongodb.students.insert_one(student_doc)
    
    # Migrate memories to new structure
    migrate_memories(student_id, academic, personal)
    
    print(f"✅ Migrated {student_id}")

def generate_initial_biography(conversations, academic_memories, personal_memories):
    """
    Use LLM to generate initial biography from historical data
    """
    prompt = f"""
    You are creating the first biography for a student based on their historical 
    tutoring sessions.
    
    Historical Data:
    - Conversations: {len(conversations)} sessions
    - Academic memories: {academic_memories}
    - Personal memories: {personal_memories}
    
    Write a 300-word biography that captures:
    1. Who they are (interests, personality)
    2. Their academic journey so far
    3. Patterns you observe
    4. Where they are now
    
    Use prose, not bullets.
    """
    return llm.generate(prompt)
```

### Step 4: Run Migration

```bash
python scripts/migrate_old_data.py \
  --old-data-path "services/TeachingAssistant_old/Memory/data" \
  --output-db "mongodb://localhost:27017/teachr_v5"
```

### Step 5: Validate Migration

```python
# Test script
student = mongodb.students.find_one({"_id": "test_student_002"})
assert "biography" in student
assert "academic_journey" in student
print(student["biography"]["text"])
```

---

## 9. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Get basic session flow working without biography.

**Tasks:**
- [ ] Set up MongoDB connection
- [ ] Set up Pinecone connection
- [ ] Create `students`, `sessions`, `memories` collections
- [ ] Build `POST /session/start` endpoint (returns generic prompt)
- [ ] Build `POST /session/end` endpoint (saves session)
- [ ] Test with one student having a basic conversation

**Deliverable:** Can start/end a session and save conversation to MongoDB.

---

### Phase 2: Biography Generation (Week 2)

**Goal:** Implement the Biographer Agent.

**Tasks:**
- [ ] Write the Biographer Prompt template
- [ ] Build `biographer.py` module
- [ ] Test biography generation on 3 sample sessions
- [ ] Implement biography versioning
- [ ] Add biography to session start system prompt

**Deliverable:** Biography updates after each session and is injected at session start.

**Test:**
```python
# Run 3 sessions with test_student_002
# After session 3, check biography version == 3
student = mongodb.students.find_one({"_id": "test_student_002"})
assert student["biography"]["version"] == 3
print(student["biography"]["text"])
# Should mention specific details from all 3 sessions
```

---

### Phase 3: Academic Journey Tracking (Week 3)

**Goal:** Add "we started here, now we're here" to biography.

**Tasks:**
- [ ] Add `academic_journey` schema to student document
- [ ] Update Biographer Prompt to include journey section
- [ ] Build logic to detect topic mastery vs. struggle
- [ ] Add "milestones" tracking

**Deliverable:** Biography includes a dedicated "Academic Journey" section.

**Example Output:**
```
ACADEMIC JOURNEY:
- Month 1: Started with basic quadratics. Heavy scaffolding needed. Anxious.
- Month 2: Breakthrough with vertex form. Growing confidence.
- Month 3: Currently working on discriminant. Ready for complex applications.
```

---

### Phase 4: Emotional Pattern Detection (Week 4)

**Goal:** Track long-term emotional patterns.

**Tasks:**
- [ ] Build emotion extraction from conversation
- [ ] Store emotional arc in session document
- [ ] Update Biographer to identify patterns (e.g., "anxious before tests")
- [ ] Add pattern detection to biography

**Deliverable:** Biography mentions recurring emotional patterns.

**Example:**
```
Nicolas tends to procrastinate when stressed, especially before tests. However, 
he responds well to gentle accountability. Last week, despite anxiety, he 
completed all practice problems.
```

---

### Phase 5: Memory Retrieval Integration (Week 5)

**Goal:** Use Pinecone for "find similar moments" during conversation.

**Tasks:**
- [ ] Implement memory embedding pipeline
- [ ] Build Pinecone upsert after session end
- [ ] Build light memory retrieval during session
- [ ] Inject relevant memories as "System Updates" to Adam

**Deliverable:** During conversation, Adam can reference similar past moments.

**Example:**
```
Student: "I'm feeling overwhelmed"
[System retrieves: "Last time Nicolas felt overwhelmed, taking a 10-min break helped"]
Adam: "Remember last week when you felt similar? Taking that break really helped."
```

---

### Phase 6: Migration & Deployment (Week 6)

**Goal:** Migrate existing students and deploy v5.

**Tasks:**
- [ ] Run `migrate_old_data.py` for all students
- [ ] Validate migrations (spot-check 10 students)
- [ ] Deploy to staging environment
- [ ] A/B test: 10% of students on v5, 90% on old TA
- [ ] Collect qualitative feedback
- [ ] Full rollout if successful

**Deliverable:** v5 is live and serving all students.

---

## 10. Testing Strategy

### Qualitative Testing (No Hard Metrics)

**Goal:** Does it "feel" like Adam knows the student?

**Method:**
1. **Simulator Testing:**  
   - Run 10 sessions with `test_student_002`
   - After each session, read the biography
   - Ask: "Does this feel accurate? Does it capture Nicolas?"

2. **Human Review:**  
   - Pick 3 real students
   - Read their biographies after 5 sessions
   - Ask the student: "Does this feel like you?"

3. **Continuity Check:**  
   - Start a session, check opening message
   - Does Adam reference specific details from biography?
   - Does it feel personalized vs. generic?

4. **Drift Detection:**  
   - Compare biography version 1 vs. version 10
   - Did anchor memories (onboarding) stay intact?
   - Are there contradictions?

**What to Look For:**
- ✅ Adam mentions specific interests (basketball, space) without prompting
- ✅ Adam connects new topics to past breakthroughs
- ✅ Adam anticipates emotional patterns ("I know tests make you anxious")
- ❌ Biography includes hallucinated facts
- ❌ Biography forgets original onboarding data
- ❌ Adam sounds generic ("How are you today?") instead of specific

---

## 11. Code Examples & Prompts

### Example 1: Session Start API

```python
from fastapi import FastAPI, HTTPException
from datetime import datetime

app = FastAPI()

@app.post("/session/start")
async def start_session(student_id: str):
    # Load student
    student = mongodb.students.find_one({"_id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Create new session
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    session_doc = {
        "_id": session_id,
        "student_id": student_id,
        "start_time": datetime.now().isoformat(),
        "conversation": [],
        "emotional_arc": [],
        "topics_covered": []
    }
    mongodb.sessions.insert_one(session_doc)
    
    # Build system prompt with biography
    biography = student["biography"]["text"]
    system_prompt = build_opening_prompt(biography, student["academic_journey"])
    
    return {
        "session_id": session_id,
        "prompt": system_prompt,
        "session_info": {
            "student_name": student["name"],
            "total_sessions": student["statistics"]["total_sessions"]
        }
    }

def build_opening_prompt(biography: str, academic_journey: dict) -> str:
    return f"""
[SYSTEM PROMPT FOR ADAM]

STUDENT BIOGRAPHY:
{biography}

CURRENT ACADEMIC FOCUS:
{academic_journey["current_topic"]}

MEMORY AND INJECTION HANDLING:
During this session, you will receive 'System Updates' with retrieved memories.
- If an update arrives while you are speaking or just finished: DO NOT hallucinate a new user turn.
- Maintain consistency with your previous response.

OPENING INSTRUCTION:
Greet the student warmly. Reference something specific from their biography or last session.
Make them feel seen and remembered.
"""
```

### Example 2: Biographer Agent

```python
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

class BiographerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.prompt = self._load_prompt()
    
    def _load_prompt(self):
        return PromptTemplate.from_file("prompts/biographer_prompt.txt")
    
    def update_biography(
        self, 
        current_biography: str, 
        session_transcript: list, 
        session_summary: dict
    ) -> str:
        """Generate updated biography"""
        
        # Format transcript
        transcript_text = "\n".join([
            f"{turn['speaker']}: {turn['text']}" 
            for turn in session_transcript
        ])
        
        # Run LLM
        updated_biography = self.llm(
            self.prompt.format(
                current_biography=current_biography,
                session_transcript=transcript_text,
                topics_covered=session_summary["topics_covered"],
                emotional_arc=session_summary["emotional_arc"],
                key_moments=session_summary["key_moments"]
            )
        )
        
        return updated_biography
```

### Example 3: Memory Extraction

```python
def extract_memories(conversation: list) -> list:
    """Extract memories from conversation"""
    
    memories = []
    
    for turn in conversation:
        if turn["speaker"] == "student":
            # Use LLM to extract facts
            extracted = memory_extractor.extract(turn["text"])
            
            for fact in extracted:
                memory = {
                    "student_id": turn["student_id"],
                    "session_id": turn["session_id"],
                    "type": fact["type"],  # "personal", "academic", "context"
                    "text": fact["text"],
                    "importance": fact["importance"],
                    "timestamp": turn["timestamp"],
                    "metadata": {
                        "emotion": turn.get("emotion", "neutral"),
                        "topic": fact.get("topic", "general")
                    }
                }
                memories.append(memory)
    
    return memories
```

---

## 12. Appendix: Key Differences from Old TA

| Feature | Old TA | New TA v5 |
|---------|--------|-----------|
| **Memory Storage** | JSON files | MongoDB + Pinecone |
| **Biography** | None (fragments in JSON) | Living Biography (prose, versioned) |
| **Opening Message** | Generic + last session summary | Biography-driven, deeply personalized |
| **Journey Tracking** | None | "Started here, now here, going here" |
| **Emotional Patterns** | Per-session only | Long-term pattern recognition |
| **Semantic Search** | None | Pinecone for similar moments |
| **Scalability** | File I/O bottleneck | Database-backed, horizontally scalable |
| **Migration** | N/A | Backfill script from old JSON |

---

## Final Notes for Developers

**Philosophy:**  
You're not building a database. You're building a **biographer**. Every design decision should ask: "Does this help Adam remember Nicolas as a person with a story?"

**Technical Debt:**  
If something feels hacky, stop and refactor. This is a clean-slate rebuild—don't carry forward old patterns.

**Testing:**  
Read the biographies yourself. If they don't sound like real people, something's wrong. Trust your qualitative judgment.

**Questions?**  
Tag @vandan in Slack or open an issue on the `teaching-assistant-v5` branch.

---

**Good luck building the future of TeachingAssistant. Let's make Adam truly remember.**

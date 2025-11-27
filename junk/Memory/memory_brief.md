# Memory System - Developer Brief

# Vector DB (The "Sentient & Personal" Part)

This is where the magic happens. This is what makes the tutor feel like it actually *knows* the student.

The goal isn't just to remember facts. It's to remember the right things and bring them up at the right moments in a natural way.

### What makes it feel personal and sentient

It's three things:

1. **Unexpected recall** - Remembering something the student didn't expect you to remember
2. **Timing** - Bringing it up when it's actually relevant, not randomly
3. **Connection-making** - Linking personal details to what you're currently discussing

### What to capture

This is important. We're not just capturing academic stuff. We're capturing *who they are*. Organize by the 4 memory types:

**Academic (learning events):**
- "Student confused discriminant with leading coefficient"
- "Visual diagrams helped when explaining quadratic formula"
- "Had breakthrough connecting discriminant to graph shape"
- "Struggled with word problems - gets lost in the text"

**Personal (who they are):**
- "Student has basketball games on Fridays"
- "Student's dog is named Max"
- "Student prefers studying after dinner"
- "Student gets anxious before tests"
- "Student lights up when we talk about space"

**Preference (how they learn):**
- "Student responds well to humor"
- "Student likes sports analogies"
- "Student prefers shorter explanations, gets overwhelmed by long ones"
- "Student calls quadratic formula 'the big formula'"
- "Student prefers to work through problems silently first"

**Context (session continuity):**
- "Last session ended with excitement about understanding discriminant"
- "Started completing the square but ran out of time"
- "Was working on word problems when session crashed"

**Emotional patterns (critical - spans all types):**

These are especially important for the "sentient" feel. Store them with an `emotion` metadata field:
- "Student gets frustrated when they don't get it on first try" → preference
- "Student shuts down when pushed too hard" → preference
- "Student was excited after breakthrough with discriminant" → academic
- "Student seemed anxious today, shorter responses" → context

The emotional layer is what makes the tutor feel like it actually *cares*.

### Memory Schema

Keep types simple, use metadata for nuance. This avoids overlap and makes filtering clean.

**4 core types:**

| Type | What it captures |
|------|------------------|
| `academic` | Learning events - struggles, breakthroughs, explanations that worked |
| `personal` | Who they are - hobbies, pets, schedule, life context |
| `preference` | How they learn - communication style, pacing, emotional patterns |
| `context` | Session continuity - what happened last time, unfinished threads |

**Emotional patterns live in metadata across all types.** Use the `emotion` field to capture the feeling.

**Example memories:**

```python
# Academic memory (with emotion)
{
  "id": "mem_abc123",
  "student_id": "student_456",
  "type": "academic",
  "text": "Student confused discriminant with leading coefficient, visual diagram helped",
  "timestamp": "2024-01-15T10:30:00Z",
  "session_id": "sess_789",
  "importance": 0.8,
  "metadata": {
    "valence": "struggle",        # struggle | breakthrough | neutral
    "emotion": "frustrated",      # frustrated | confused | excited | anxious | null
    "resolution": "visual_helped",
    "topic": "quadratics.discriminant"
  }
}

# Personal memory (with emotion)
{
  "id": "mem_def456",
  "student_id": "student_456",
  "type": "personal",
  "text": "Student lights up when we talk about space",
  "timestamp": "2024-01-15T10:32:00Z",
  "session_id": "sess_789",
  "importance": 0.7,
  "metadata": {
    "category": "interest",       # schedule | hobby | family | pets | interest
    "emotion": "excited"
  }
}

# Preference memory (emotional pattern)
{
  "id": "mem_ghi789",
  "student_id": "student_456",
  "type": "preference",
  "text": "Student shuts down when pushed too hard - needs encouragement not pressure",
  "timestamp": "2024-01-15T10:35:00Z",
  "session_id": "sess_789",
  "importance": 0.9,
  "metadata": {
    "category": "emotional_response",  # communication | pacing | format | emotional_response
    "trigger": "pressure",
    "response": "withdrawal"
  }
}

# Context memory (with emotional state)
{
  "id": "mem_jkl012",
  "student_id": "student_456",
  "type": "context",
  "text": "Session ended with breakthrough on discriminant, student was excited",
  "timestamp": "2024-01-15T11:00:00Z",
  "session_id": "sess_789",
  "importance": 0.8,
  "metadata": {
    "session_end": true,
    "emotion": "excited",
    "topic": "quadratics.discriminant",
    "next_topic": "completing_square"
  }
}
```

The `type` field is for filtering. The `metadata.emotion` field captures feelings across all types. Start with 4 types - you can always add metadata fields as you learn what matters.

### When to save (triggers)

**Don't wait until session end.** Extract incrementally during the conversation.

After each meaningful exchange, run this extraction:

```python
EXTRACTION_PROMPT = """Analyze this conversation exchange for memorable details.

Types to extract:
- academic: struggles, breakthroughs, explanations that worked
- personal: hobbies, pets, family, schedule, life context, interests
- preference: communication style, pacing, emotional patterns (how they respond to frustration, pressure, success)
- context: session continuity, unfinished threads, emotional state

Student: {student_text}
AI: {ai_text}
Current Topic: {topic}

Return as JSON array. Each item needs:
- type: one of [academic, personal, preference, context]
- text: the memorable detail
- importance: 0-1 score
- metadata: ALWAYS include "emotion" field if any feeling is present (frustrated, confused, excited, anxious, etc.)

Return empty array if nothing worth remembering.

Example output:
[
  {
    "type": "academic",
    "text": "Student confused discriminant with coefficient, visual diagram helped",
    "importance": 0.8,
    "metadata": {"valence": "struggle", "emotion": "frustrated", "resolution": "visual_helped", "topic": "quadratics"}
  },
  {
    "type": "preference",
    "text": "Student shuts down when pushed too hard - needs encouragement",
    "importance": 0.9,
    "metadata": {"category": "emotional_response", "trigger": "pressure", "response": "withdrawal"}
  },
  {
    "type": "personal",
    "text": "Student lights up when we talk about space",
    "importance": 0.7,
    "metadata": {"category": "interest", "emotion": "excited"}
  }
]
"""
```

Run this after every turn. It's a cheap LLM call (use a fast model like Flash). Most of the time it returns null, and that's fine.

**Also run a consolidation at session end** to merge duplicates and clean up noise.

---

### Three-Phase Architecture (Efficiency)

Think about memory in three phases: **Opening**, **Ongoing**, and **Closing**. The key insight is to pre-compute what you can, so the student never waits.

#### Phase 1: Opening (Pre-computed)

**When it runs:** Immediately after student leaves the previous session

**Why:** When student returns, context is already waiting - zero latency

**What it generates:**
```python
opening_context = {
    "welcome_hook": "Last time you cracked the discriminant - ready to build on that?",
    "last_session_summary": "Worked on quadratics, breakthrough with visual diagrams",
    "unfinished_threads": ["Started completing the square but ran out of time"],
    "personal_relevance": "It's Friday - basketball game today?",
    "emotional_state_last": "Left feeling confident",
    "suggested_opener": "natural conversation starter based on all above"
}
```

**Storage:** Fast cache (Redis) or even just a JSON file per student. When student returns, just load it - no LLM calls needed.

#### Phase 2: Ongoing (Contextual retrieval)

**When it runs:**
- **Every turn** - lightweight vector search (fast, ~50ms)
- **On topic change** - deeper retrieval
- **On emotional cue** - pull relevant emotional patterns
- **On explicit reference** - "like we did before"

**The trigger logic:**
```python
async def should_deep_retrieve(current_message, conversation_so_far):
    # Always do lightweight retrieval
    light_context = await quick_vector_search(current_message)

    # Deep retrieval triggers:
    triggers = {
        "topic_change": detect_topic_shift(conversation_so_far),
        "emotional_cue": detect_emotion(current_message),
        "explicit_reference": has_past_reference(current_message),
        "every_n_turns": len(conversation_so_far) % 5 == 0
    }

    if any(triggers.values()):
        return await deep_retrieval(current_message, triggers)

    return light_context
```

**Lightweight vs Deep:**
- **Light:** Single vector search on current message (~50ms)
- **Deep:** Multi-type query + metadata filtering + re-ranking (~200ms, only when triggered)

#### Phase 3: Closing (Incrementally built, cached)

**When it runs:** Continuously during session, updated after each meaningful exchange

**The key insight:** Don't wait for goodbye - build it as you go

```python
class SessionClosingCache:
    def __init__(self, student_id):
        self.student_id = student_id
        self.cache = {
            "session_summary": "",
            "key_moments": [],
            "new_memories": [],
            "emotional_arc": [],
            "next_session_hooks": [],
            "goodbye_message": ""
        }

    async def update_after_exchange(self, student_text, ai_text, topic):
        # Extract any new memories (cheap LLM call)
        new_memories = await extract_memories(student_text, ai_text, topic)
        if new_memories:
            self.cache["new_memories"].extend(new_memories)

        # Update emotional arc
        emotion = detect_emotion(student_text)
        if emotion:
            self.cache["emotional_arc"].append(emotion)

        # Regenerate summary and goodbye (runs in background)
        asyncio.create_task(self._regenerate_closing())

    async def _regenerate_closing(self):
        self.cache["session_summary"] = await summarize_session(self.cache)
        self.cache["goodbye_message"] = await generate_goodbye(self.cache)
        self.cache["next_session_hooks"] = await generate_hooks(self.cache)

    def get_instant_closing(self):
        # Called when student hits STOP - instant, from cache
        return self.cache
```

**When student hits STOP:**
1. Read closing from cache (instant)
2. Save new_memories to vector DB
3. Generate opening_context for next session
4. Store in fast cache

#### The Full Flow

```
SESSION N ENDS
     │
     ▼
┌─────────────────────┐
│ Closing Cache       │──► Save to Vector DB
│ (already built)     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Generate Opening    │──► Store in Redis/cache
│ for Session N+1     │
└─────────────────────┘


SESSION N+1 STARTS
     │
     ▼
┌─────────────────────┐
│ Load Opening        │◄── From cache (instant)
│ Context             │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Ongoing Retrieval   │◄── Per-turn vector search
│ (light + triggered  │
│  deep retrieval)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Build Closing Cache │◄── Updated after each exchange
│ (continuous)        │
└─────────────────────┘
```

#### Efficiency Wins

| Phase | Latency | Why |
|-------|---------|-----|
| Opening | ~0ms | Pre-computed, just load from cache |
| Ongoing (light) | ~50ms | Single vector search |
| Ongoing (deep) | ~200ms | Only when triggered |
| Closing | ~0ms | Already in cache, just read |

**The expensive operations happen:**
- After student leaves (they don't notice)
- In background during session (async)

**The student experiences:**
- Instant personalized welcome
- Contextual responses without delay
- Instant goodbye with continuity hooks

---

### How to Retrieve (Ongoing Phase Implementation)

This is the core of the **Ongoing phase** - retrieving relevant memories for each turn.

```python
async def get_personalized_context(student_message, student_id):
    # Query all 4 types in parallel
    academic = vector_db.search(
        query=student_message,
        filter={"student_id": student_id, "type": "academic"},
        top_k=5
    )

    personal = vector_db.search(
        query=student_message,
        filter={"student_id": student_id, "type": "personal"},
        top_k=3
    )

    preferences = vector_db.search(
        query=student_message,
        filter={"student_id": student_id, "type": "preference"},
        top_k=3
    )

    # Context sorted by recency, not similarity
    context = vector_db.search(
        filter={"student_id": student_id, "type": "context"},
        sort_by="timestamp",
        limit=3
    )

    return {
        "academic": academic,
        "personal": personal,
        "preferences": preferences,
        "context": context
    }
```

**Filtering by metadata** for finer control:
```python
# Just struggles with frustrated emotion
frustrated_struggles = vector_db.search(
    query=student_message,
    filter={
        "student_id": student_id,
        "type": "academic",
        "metadata.valence": "struggle",
        "metadata.emotion": "frustrated"
    },
    top_k=5
)

# Emotional patterns when student seems stressed
emotional_patterns = vector_db.search(
    query=student_message,
    filter={
        "student_id": student_id,
        "type": "preference",
        "metadata.category": "emotional_response"
    },
    top_k=3
)
```

---

### How to Use It (Injecting into Prompt)

Prompt injection happens differently in each phase:

#### Opening Injection (Session Start)

Load from cache, inject immediately. This is pre-computed - no LLM calls needed.

```python
def build_opening_prompt(student_id):
    # Load pre-computed opening context from cache
    opening = cache.get(f"opening:{student_id}")

    return f"""You are {opening['student_name']}'s AI tutor.

SESSION START CONTEXT:
- Last session: {opening['last_session_summary']}
- Emotional state when they left: {opening['emotional_state_last']}
- Unfinished threads: {', '.join(opening['unfinished_threads'])}
- Personal relevance today: {opening['personal_relevance']}

SUGGESTED OPENER:
{opening['suggested_opener']}

Start the conversation naturally using this context. Reference their last session
or personal life only if it feels genuine."""
```

#### Ongoing Injection (Per-Turn Updates)

Retrieval happens every turn. The prompt grows with relevant memories.

```python
def build_ongoing_prompt(student_id, current_message, base_prompt):
    # Get retrieved memories from vector search
    memories = get_personalized_context(current_message, student_id)

    # Build dynamic context block
    context_block = f"""
RELEVANT MEMORIES (just retrieved):
Academic: {format_memories(memories['academic'])}
Personal: {format_memories(memories['personal'])}
Preferences: {format_memories(memories['preferences'])}
Recent context: {format_memories(memories['context'])}

EMOTIONAL PATTERNS TO WATCH:
{get_emotional_patterns(student_id)}

Use this context naturally. Adjust tone based on emotional patterns.
Don't force references - only mention when genuinely relevant."""

    return base_prompt + context_block
```

**Example ongoing prompt** (after retrieval):
```python
"""You are Alex's AI tutor.

[... base prompt ...]

RELEVANT MEMORIES (just retrieved):
Academic:
- Confused discriminant with coefficient (frustrated) - visual diagram helped
- Struggled with word problems - gets lost in text

Personal:
- Plays basketball on Fridays
- Lights up when we talk about space

Preferences:
- Responds well to sports analogies
- Shuts down when pushed too hard - needs encouragement

Recent context:
- Last session ended with breakthrough on discriminant (excited)
- Started completing the square but ran out of time

EMOTIONAL PATTERNS TO WATCH:
- Currently seems frustrated (short responses)
- Historical pattern: withdraws under pressure, needs encouragement

Adjust your approach based on their current emotional state."""
```

#### Closing Injection (Continuously Updated)

The closing context is built incrementally and always ready.

```python
class ClosingPromptBuilder:
    def __init__(self, student_id):
        self.student_id = student_id
        self.closing_context = {
            "session_summary": "",
            "emotional_arc": [],
            "key_moments": [],
            "goodbye_hook": "",
            "next_session_teaser": ""
        }

    async def update_after_exchange(self, exchange):
        """Called after every turn - keeps closing prompt fresh"""
        # Update emotional arc
        if emotion := detect_emotion(exchange['student_text']):
            self.closing_context['emotional_arc'].append(emotion)

        # Check for key moments
        if is_key_moment(exchange):
            self.closing_context['key_moments'].append(
                summarize_moment(exchange)
            )

        # Regenerate closing in background (async, doesn't block)
        asyncio.create_task(self._regenerate_closing())

    async def _regenerate_closing(self):
        """Runs in background after each exchange"""
        arc = self.closing_context['emotional_arc']
        moments = self.closing_context['key_moments']

        # Generate goodbye that matches how they're feeling NOW
        if arc and arc[-1] in ['frustrated', 'confused']:
            self.closing_context['goodbye_hook'] = \
                "We'll pick this up next time - you're closer than you think!"
        elif arc and arc[-1] == 'excited':
            self.closing_context['goodbye_hook'] = \
                "Great work today! Can't wait to build on this next time."

        # Tease next session based on where we stopped
        if moments:
            self.closing_context['next_session_teaser'] = \
                f"Next time: continue from {moments[-1]}"

    def get_closing_prompt(self):
        """Called when student hits STOP - instant, from cache"""
        return f"""SESSION ENDING:

Emotional journey today: {' → '.join(self.closing_context['emotional_arc'])}
Key moments: {', '.join(self.closing_context['key_moments'])}

GOODBYE MESSAGE:
{self.closing_context['goodbye_hook']}

NEXT SESSION HOOK:
{self.closing_context['next_session_teaser']}

End the conversation warmly, acknowledging their emotional state.
Mention the next session hook to create continuity."""
```

**Key insight:** The closing prompt is ALWAYS ready. When the student hits STOP, there's no delay - just read from cache and go.

---

### Examples: How the Three Phases Play Out

**Opening Phase - Session start:**
```
Student returns on Monday
Opening context loaded from cache:
- last_session: "breakthrough on discriminant, was excited"
- personal_relevance: "basketball game was Friday"
- emotional_state_last: "confident"

AI response: "Hey! How'd the game go Friday? Last time you were on fire
with that discriminant breakthrough - ready to tackle completing the square?"
```

**Ongoing Phase - Mid-conversation retrieval:**
```
Student says: "I'm so tired today"
Light retrieval finds: "Student has basketball on Fridays"
Today is Friday

AI response: "Rough day? Did you have your game today?"
```

**Ongoing Phase - Emotional pattern matching:**
```
Student is struggling, giving short responses
Deep retrieval triggered by emotional cue
Found: "Student shuts down when pushed too hard - needs encouragement"

AI response: "Hey, let's take a breather. Want to try a different approach,
or come back to this tomorrow?"
```

**Ongoing Phase - Using their world for analogies:**
```
Teaching: momentum
Retrieval finds: "Student plays basketball", "likes sports analogies"

AI response: "Think of momentum like when you're driving to the basket -
the faster and heavier you are, the harder you are to stop."
```

**Closing Phase - Building for next session:**
```
Student has breakthrough, says "Oh! That makes so much sense now!"
Closing cache updates:
- emotional_arc: [..., "excited"]
- key_moments: [..., "breakthrough on completing the square"]
- next_session_hooks: ["build on completing square success"]

When student hits STOP, goodbye is instant and hooks are ready for next time.
```

---

### The "Sentient" Secret

It's not about remembering everything. It's about:

1. **Selective recall** - The RIGHT detail at the RIGHT time
2. **Natural integration** - Don't say "I remember you said..." Just use it
3. **Emotional attunement** - Adjust tone based on their patterns
4. **Surprise factor** - Recall something they forgot they mentioned

**Bad (robotic):**
> "I recall from our conversation on January 15th that you mentioned having a dog named Max."

**Good (sentient):**
> "How's Max doing? Keeping you company while you study?"

The three phases work together:
- **Opening** pre-computes the personal touch
- **Ongoing** retrieves relevant memories in real-time
- **Closing** captures what matters for next time

The vector DB finds memories. The LLM weaves them in naturally. The three-phase architecture makes it instant.

---

## Tech Recommendations

**Vector DB:** Use Pinecone. It's cloud-hosted, scales well, and has a good Python SDK. The free tier should be enough to start.

**Embeddings:** Use sentence-transformers (`all-MiniLM-L6-v2` is fast and good enough). Or use OpenAI's embedding API if you want consistency.

**Code structure:**
```
memory/
├── schema.py          # Memory data models
├── embeddings.py      # Embedding generation (cache these!)
├── vector_store.py    # Pinecone wrapper
├── extractor.py       # LLM-based memory extraction
├── retriever.py       # Query and rank memories
└── consolidator.py    # Session-end cleanup
```

---

## What to build first

Build in this order - each phase builds on the previous:

**1. Core infrastructure:**
- Set up Pinecone with the memory schema
- Build embedding generation (cache these!)
- Create the 4-type memory structure

**2. Ongoing phase (most important):**
- Build the per-turn extractor (cheap LLM call)
- Build the retriever with type-based queries
- Implement light vs deep retrieval triggers
- Format retrieved memories into system prompt

**3. Closing phase:**
- Build SessionClosingCache class
- Update cache after each exchange
- Save to vector DB when session ends

**4. Opening phase:**
- Generate opening_context after session ends
- Store in fast cache (Redis or JSON)
- Load instantly when student returns

**5. Polish:**
- Add emotion detection
- Tune retrieval triggers
- Test with real conversations

Don't worry about the knowledge graph yet. Get the vector DB personalization working first - that's what will make the tutor feel alive.

Let me know if any of this is unclear or if you want to walk through any part in more detail.

---

### How to Demo (Memory Simulator)

Use the sample conversations to demonstrate the full memory system working end-to-end.

**Input:** `junk/Memory/sample_conversations_for_testing/`

These are multi-session conversation transcripts. Each file is a session with turns in format:
```json
[
  {"speaker": "Student", "text": "..."},
  {"speaker": "AI", "text": "..."},
  ...
]
```

**The Simulator:**

```python
class MemorySimulator:
    """
    Processes conversation transcripts turn-by-turn,
    simulating the full memory system with verbose logging.
    """

    def __init__(self, student_id, verbose=True):
        self.student_id = student_id
        self.verbose = verbose
        self.vector_db = PineconeClient()
        self.closing_cache = SessionClosingCache(student_id)

    def run_session(self, transcript_file, session_number):
        """Process a full session transcript"""
        transcript = load_json(transcript_file)

        self.log(f"=== SESSION {session_number} ===")
        self.log(f"[SESSION START] Student: {self.student_id}")

        # Opening phase
        if session_number == 1:
            self.log("[OPENING] No previous session - first time student")
        else:
            opening = self.load_opening_context()
            self.log(f"[OPENING] Loaded from cache:")
            self.log(f"  - last_session: {opening['last_session_summary']}")
            self.log(f"  - emotional_state: {opening['emotional_state_last']}")
            self.log(f"  - unfinished: {opening['unfinished_threads']}")

        # Process each turn
        for i in range(0, len(transcript), 2):
            student_turn = transcript[i]
            ai_turn = transcript[i+1] if i+1 < len(transcript) else None

            self.process_turn(
                turn_number=(i//2)+1,
                student_text=student_turn['text'],
                ai_text=ai_turn['text'] if ai_turn else ""
            )

        # Closing phase
        self.finalize_session(session_number)

    def process_turn(self, turn_number, student_text, ai_text):
        """Process a single conversation turn with full logging"""
        self.log(f"\n--- TURN {turn_number} ---")

        # 1. Log input
        self.log(f"[INPUT] Student: \"{student_text[:100]}...\"" if len(student_text) > 100 else f"[INPUT] Student: \"{student_text}\"")

        # 2. Retrieval
        self.log(f"[RETRIEVAL] Query embedding generated")
        self.log(f"[RETRIEVAL] Pinecone query: student_id={self.student_id}, top_k=10")

        results = self.vector_db.search(
            query=student_text,
            filter={"student_id": self.student_id},
            top_k=10
        )

        if results:
            self.log(f"[RETRIEVAL] Results:")
            for r in results[:5]:  # Show top 5
                self.log(f"  - {r['id']}: \"{r['text'][:50]}...\" (score: {r['score']:.2f})")
        else:
            self.log(f"[RETRIEVAL] Results: [] (no memories yet)")

        # 3. Extraction
        self.log(f"[EXTRACTION] Running extraction prompt...")
        memories = self.extract_memories(student_text, ai_text)

        if memories:
            self.log(f"[EXTRACTION] LLM response: {len(memories)} memories found")
            for i, mem in enumerate(memories):
                self.log(f"[EXTRACTION] Memory {i+1}: {{type: \"{mem['type']}\", text: \"{mem['text'][:50]}...\", importance: {mem['importance']}}}")
                if mem.get('metadata', {}).get('emotion'):
                    self.log(f"             emotion: {mem['metadata']['emotion']}")
        else:
            self.log(f"[EXTRACTION] [] (nothing worth remembering)")

        # 4. Save
        if memories:
            self.log(f"[SAVE] Generating embeddings for {len(memories)} memories...")
            saved_ids = self.save_memories(memories)
            self.log(f"[SAVE] Upserting to Pinecone: {', '.join(saved_ids)}")
            self.log(f"[SAVE] Success - {len(memories)} memories saved")

        # 5. Update closing cache
        self.closing_cache.update_after_exchange({
            'student_text': student_text,
            'ai_text': ai_text
        })
        self.log(f"[CLOSING CACHE] Updated: emotional_arc={self.closing_cache.cache['emotional_arc']}")

    def finalize_session(self, session_number):
        """End session - save closing and generate opening for next"""
        self.log(f"\n=== SESSION {session_number} END ===")

        closing = self.closing_cache.get_instant_closing()
        self.log(f"[CLOSING] Final emotional arc: {' → '.join(closing['emotional_arc'])}")
        self.log(f"[CLOSING] Key moments: {closing['key_moments']}")

        # Generate opening for next session
        self.log(f"[OPENING] Generating context for next session...")
        opening = self.generate_opening_context(closing)
        self.cache_opening(opening)

        self.log(f"[OPENING CACHE] Stored for {self.student_id}:")
        self.log(f"  - last_session: \"{opening['last_session_summary']}\"")
        self.log(f"  - emotional_state_last: \"{opening['emotional_state_last']}\"")
        self.log(f"  - unfinished: {opening['unfinished_threads']}")
        self.log(f"  - suggested_opener: \"{opening['suggested_opener'][:80]}...\"")

    def log(self, message):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")


# Run the demo
if __name__ == "__main__":
    simulator = MemorySimulator(student_id="alex_001", verbose=True)

    # Process all sessions in order
    transcripts = sorted(glob("junk/Memory/sample_conversations_for_testing/*.json"))
    for i, transcript in enumerate(transcripts, 1):
        simulator.run_session(transcript, session_number=i)
        print("\n" + "="*60 + "\n")
```

**Expected Output (Dev Mode):**

```
[10:00:01.234] === SESSION 1 ===
[10:00:01.235] [SESSION START] Student: alex_001
[10:00:01.236] [OPENING] No previous session - first time student

--- TURN 1 ---
[10:00:01.240] [INPUT] Student: "Hi, I need help with quadratics. I have a test Friday and I'm kinda stressed"
[10:00:01.245] [RETRIEVAL] Query embedding generated
[10:00:01.246] [RETRIEVAL] Pinecone query: student_id=alex_001, top_k=10
[10:00:01.312] [RETRIEVAL] Results: [] (no memories yet)
[10:00:01.315] [EXTRACTION] Running extraction prompt...
[10:00:01.892] [EXTRACTION] LLM response: 2 memories found
[10:00:01.893] [EXTRACTION] Memory 1: {type: "academic", text: "Starting quadratics, needs help...", importance: 0.5}
[10:00:01.894] [EXTRACTION] Memory 2: {type: "context", text: "Has test Friday, feeling stressed...", importance: 0.8}
             emotion: anxious
[10:00:01.900] [SAVE] Generating embeddings for 2 memories...
[10:00:01.956] [SAVE] Upserting to Pinecone: mem_001, mem_002
[10:00:02.012] [SAVE] Success - 2 memories saved
[10:00:02.013] [CLOSING CACHE] Updated: emotional_arc=['anxious']

--- TURN 2 ---
[10:00:02.100] [INPUT] Student: "Yeah I play basketball so Fridays are crazy with games and tests"
[10:00:02.105] [RETRIEVAL] Query embedding generated
[10:00:02.106] [RETRIEVAL] Pinecone query: student_id=alex_001, top_k=10
[10:00:02.178] [RETRIEVAL] Results:
  - mem_002: "Has test Friday, feeling stressed..." (score: 0.82)
[10:00:02.180] [EXTRACTION] Running extraction prompt...
[10:00:02.654] [EXTRACTION] LLM response: 1 memories found
[10:00:02.655] [EXTRACTION] Memory 1: {type: "personal", text: "Plays basketball, games on Fridays...", importance: 0.7}
[10:00:02.660] [SAVE] Generating embeddings for 1 memories...
[10:00:02.701] [SAVE] Upserting to Pinecone: mem_003
[10:00:02.745] [SAVE] Success - 1 memories saved
[10:00:02.746] [CLOSING CACHE] Updated: emotional_arc=['anxious']

...

--- TURN 15 ---
[10:00:45.200] [INPUT] Student: "Oh! So that's why the graph looks different!"
[10:00:45.205] [RETRIEVAL] Query embedding generated
[10:00:45.206] [RETRIEVAL] Pinecone query: student_id=alex_001, top_k=10
[10:00:45.278] [RETRIEVAL] Results:
  - mem_007: "Struggling with discriminant concept..." (score: 0.85)
  - mem_005: "Prefers visual explanations..." (score: 0.79)
  - mem_002: "Has test Friday..." (score: 0.61)
[10:00:45.280] [EXTRACTION] Running extraction prompt...
[10:00:45.812] [EXTRACTION] LLM response: 1 memories found
[10:00:45.813] [EXTRACTION] Memory 1: {type: "academic", text: "Breakthrough! Connected discriminant to graph shape...", importance: 0.9}
             emotion: excited
[10:00:45.820] [SAVE] Generating embeddings for 1 memories...
[10:00:45.865] [SAVE] Upserting to Pinecone: mem_012
[10:00:45.901] [SAVE] Success - 1 memories saved
[10:00:45.902] [CLOSING CACHE] Updated: emotional_arc=['anxious', 'confused', 'frustrated', 'excited']

=== SESSION 1 END ===
[10:00:46.000] [CLOSING] Final emotional arc: anxious → confused → frustrated → excited
[10:00:46.001] [CLOSING] Key moments: ['Breakthrough on discriminant with visual diagram']
[10:00:46.005] [OPENING] Generating context for next session...
[10:00:46.234] [OPENING CACHE] Stored for alex_001:
  - last_session: "Worked on quadratics, breakthrough on discriminant using visual diagram"
  - emotional_state_last: "excited"
  - unfinished: ["Started completing the square but ran out of time"]
  - suggested_opener: "Hey! How'd the test and game go Friday? Last time you had that great breakthrou..."

============================================================

[14:00:01.100] === SESSION 2 ===
[14:00:01.101] [SESSION START] Student: alex_001
[14:00:01.102] [OPENING] Loaded from cache:
  - last_session: Worked on quadratics, breakthrough on discriminant using visual diagram
  - emotional_state: excited
  - unfinished: ['Started completing the square but ran out of time']

--- TURN 1 ---
[14:00:01.200] [INPUT] Student: "Hey"
[14:00:01.205] [RETRIEVAL] Query embedding generated
[14:00:01.206] [RETRIEVAL] Pinecone query: student_id=alex_001, top_k=10
[14:00:01.289] [RETRIEVAL] Results:
  - mem_003: "Plays basketball, games on Fridays..." (score: 0.71)
  - mem_002: "Has test Friday, feeling stressed..." (score: 0.68)
  - mem_012: "Breakthrough! Connected discriminant to graph..." (score: 0.54)
[14:00:01.291] [EXTRACTION] Running extraction prompt...
[14:00:01.534] [EXTRACTION] [] (nothing worth remembering)
[14:00:01.535] [CLOSING CACHE] Updated: emotional_arc=[]

...
```

**What this demonstrates:**
- Memories being extracted from natural conversation
- Retrieval finding semantically relevant context
- Emotional arc building over the session
- Opening context loading for returning students
- The "sentient" moments visible (retrieval pulls basketball + test when contextually relevant)

---


"""
TeachingAssistant Prompt Templates
All LLM prompts used by the TeachingAssistant service are defined here.
Prompts use Python string formatting with placeholders for dynamic values.
"""

# ============================================================================
# Memory Retrieval Prompts
# ============================================================================

LIGHT_RETRIEVAL_ANALYSIS_PROMPT = """You are an efficient Retrieval Augmented Generation (RAG) optimizer.
            Analyze the conversation turn to decide precise memory retrieval needs.

            Previous AI: "{safe_model}"
            User Input: "{safe_user}"

            TASK 1: DECISION (need_retrieval)
            - FALSE if: 
                - Simple agreement/acknowledgment ("ok", "got it", "cool", "thanks").
                - Phatic expressions or greetings ("hard to say", "wow", "hi").
                - Rhetorical questions or emotional reactions without specific factual content.
            - TRUE if: 
                - Direct questions or requests for explanation.
                - Statements of confusion ("I don't get the quadratic formula").
                - Explicit statements of preference ("I hate reading").
                - Personal disclosures ("I play basketball").
                - Domain-specific terms that might need definition.

            TASK 2: QUERY GENERATION (retrieval_query)
            - If decision is TRUE, generate a **keyword-focused** search query.
            - REMOVE: "student says", "user wants to know", "retrieval for".
            - FOCUS ON: Core entities, concepts, and specific gaps.
            - EXAMPLE: User says "I don't get the discriminant". Query: "discriminant definition purpose quadratic formula explanation"
            - EXAMPLE: User says "My math teacher is strict". Query: "math teacher relationship classroom environment academic pressure"
            
            Return strict JSON:
            {{
                "need_retrieval": true/false,
                "retrieval_query": "string",
                "reasoning": "brief explanation"
            }}
            """

DEEP_QUERY_GENERATION_PROMPT = """You are an Expert Knowledge Synthesizer for an AI Tutor.
            Analyze the recent conversation history (last few minutes) to generate a Deep Search Query.

            Context: "{safe_context}"

            GOAL:
            Identify the **underlying themes**, **concepts**, or **patterns** that require checking long-term memory.
            We are NOT looking for exact keyword matches of what was just said. We are looking for **related past experiences**.

            INSTRUCTIONS:
            1. Identify the core academic topic (e.g., "quadratic equations").
            2. Identify the student's current state/struggle (e.g., "confused about variables").
            3. Identify any personal hooks mentioned (e.g., "basketball analogy").
            
            GENERATE A SINGLE SEARCH STRING that combines:
            - The Academic Concept
            - The Type of Struggle/Interaction
            - Potential Personal Connections

            EXAMPLE:
            Context: "I just don't get why t is negative. It's like the ball is going underground."
            Bad Query: "t is negative ball underground"
            Good Query: "negative variables logic physics trajectory misconceptions basketball analogies"

            Return strict JSON:
            {{
                "deep_query": "string"
            }}
            """

REFLECTION_LAYER_SYNTHESIS_PROMPT = """You are a reflection layer for an AI tutor system.

Retrieved Memories:
{memories_str}

Recent Conversation Context:
{conversation_context}

TASK: Synthesize these memories into a SINGLE actionable instruction for the tutor.
- Only return an instruction if memories are highly relevant to current conversation
- Make it specific and actionable
- Focus on HOW the tutor should adapt their teaching based on these memories

Return ONLY the instruction text, or "NONE" if memories aren't relevant enough.

Examples:
- "Student prefers visual diagrams - use a visual approach for this concept"
- "Student struggled with negative numbers last time - check understanding before proceeding"
- "Student gets frustrated with algebra - provide extra encouragement and break into smaller steps"
"""

# ============================================================================
# Memory Extraction Prompts
# ============================================================================

MEMORY_EXTRACTION_PROMPT = """Analyze these {exchange_count} conversation exchanges to update the Student Profile.

{exchanges_text}

Task 1: Extract STUDENT MEMORIES.
**GOLDEN RULE**: You are recording PERMANENT FACTS about the Student. You are NOT summarizing a conversation.

1. **STRICT PROHIBITION (Zero Tolerance)**:
   - **NEVER** mention "The AI", "The Tutor", "The System", "The Assistant", or "The Conversation".
   - **NEVER** output meta-commentary like "Student responded to the prompt" or "Student interacted with the system".
   - **BAD Example**: "Student asked the AI for help with algebra."
   - **GOOD Example**: "Student requested help with algebra."
   - **BAD Example**: "Student answered the AI correctly."
   - **GOOD Example**: "Student demonstrated mastery of [specific concept]."

2. **CRITICAL TRANSCRIPTION HANDLING (Audio Artifacts)**:
   - The "Student" text comes from realtime audio-to-text. It may contain broken words (e.g., "Cu rrent ly", "chem is try").
   - **REPAIR**: You MUST mentally repair these fragments to capture the INTENT (e.g. treat "chem is try" as "chemistry").
   - **NO META-MEMORIES**: DO NOT record memories about the text format (e.g., "Student types with spaces" -> DELETE THIS).
   - **IGNORE GARBAGE**: If text is unintelligible, IGNORE IT. Do not record "Student text is unclear".

3. **CATEGORIES**:
   - **Academic**: Knowledge gaps, misconceptions, or mastery (e.g., "Understands chain rule", "Confused by integrals").
   - **Personal**: Hobbies, life details (e.g., "Plays soccer", "Has a dog named Max").
   - **Preference**: Learning needs (e.g., "Prefers visual examples", "Dislikes long lectures").
   - **Context**: Emotional state (e.g., "Anxious about upcoming exam").

Task 2: Detect EMOTIONS (frustrated, confused, excited, anxious, tired, happy, or neutral).
Task 3: Identify KEY MOMENTS (breakthroughs, major struggles).
Task 4: Identify UNFINISHED TOPICS.

Return a SINGLE JSON object with this structure:
{{
  "memories": [
    {{
      "type": "academic|personal|preference|context",
      "text": "Fact about the student (e.g. 'Struggles with quadratic formula', ' Loves sci-fi movies')",
      "importance": 0.0-1.0,
      "metadata": {{ "emotion": "...", "topic": "..." }}
    }}
  ],
  "emotions": ["..."],
  "key_moments": ["..."],
  "unfinished_topics": ["..."]
}}

Return ONLY valid JSON.
"""

# ============================================================================
# Closing Message Prompts
# ============================================================================

CLOSING_ARTIFACTS_GENERATION_PROMPT = """Analyze this session data and generate closing artifacts.

Data:
- Topics: {topics}
- Key Moments: {moments}
- Emotional Journey: {emotions} (Ending: {current_emotion})
- Unfinished Topics: {unfinished_str}

Generate a JSON object with these 3 keys:
1. "summary": 1-2 conc sentences on what was learned and how they felt.
2. "goodbye": A warm, natural, personal goodbye message (1-2 sentences) acknowledging their emotion.
3. "hooks": Array of 2-3 specific, actionable next session limits/topics based on unfinished items or key moments.

Return ONLY valid JSON:
{{
  "summary": "...",
  "goodbye": "...",
  "hooks": ["...", "..."]
}}"""

GOODBYE_MESSAGE_GENERATION_PROMPT = """Generate a warm, natural goodbye message for a tutoring session.

Current emotional state: {current_emotion}
Key moments: {moments}
Topics covered: {topics}

Create a brief (1-2 sentences) goodbye that:
- Acknowledges their emotional state
- Encourages them appropriately
- Feels genuine and personal

Return ONLY the goodbye message, nothing else."""

NEXT_SESSION_HOOKS_ENHANCEMENT_PROMPT = """Based on unfinished topics and key moments, suggest 1-2 additional specific continuation topics.

Unfinished topics: {unfinished_topics}
Key moments: {key_moments}
Session summary: {session_summary}

Return as JSON array of strings. Each should be specific and actionable.
Example: ["Continue practicing completing the square", "Explore how discriminant relates to graph shape"]

Return ONLY the JSON array, nothing else."""

NEXT_SESSION_HOOKS_FROM_MOMENTS_PROMPT = """Based on key moments from this session, suggest 2-3 specific continuation topics.

Key moments: {key_moments}
Session summary: {session_summary}
Topics covered: {topics_covered}

Return as JSON array of strings. Each should be specific and actionable.
Example: ["Continue practicing completing the square", "Explore how discriminant relates to graph shape"]

Return ONLY the JSON array, nothing else."""

# ============================================================================
# Opening Context Prompts
# ============================================================================

PERSONAL_RELEVANCE_GENERATION_PROMPT = """Generate a brief, time-contextual personal relevance string (max 20 words) for a tutoring session.

Current day: {day_name}
Time of day: {time_context}
Personal memories: {personal_texts}

Create a natural, contextual string that references their personal life relevant to NOW.
Examples:
- "It's Friday - basketball game today?"
- "Ready for another week of learning?"
- "How's your week going?"

If no time-specific relevance, return empty string.
Return ONLY the relevance string or empty string, nothing else."""

WELCOME_HOOK_GENERATION_PROMPT = """Generate a warm, natural welcome message (1-2 sentences) that references a specific achievement from last session.

Last session summary: {session_summary}
Key achievement: {achievement}
Emotional state when they left: {emotional_state_last}

Reference the specific achievement naturally. Examples:
- "Last time you cracked the discriminant - ready to build on that?"
- "You had that breakthrough with visual diagrams - let's keep that momentum going!"

Return ONLY the welcome message, nothing else."""

SUGGESTED_OPENER_GENERATION_PROMPT = """Generate a natural, conversational opening line (1-2 sentences) for an AI tutor.

Last session: {last_session}
Emotional state: {emotional_state_last}
Personal context: {personal_relevance}
Unfinished topics: {unfinished_topics}

Create a warm, natural conversation starter that feels genuine. Reference last session or personal life if relevant.
Sound like a friendly tutor who remembers them.

Return ONLY the opener, nothing else."""

# ============================================================================
# Prompt Loader Functions
# ============================================================================

def get_light_retrieval_analysis_prompt(safe_user: str, safe_model: str) -> str:
    """Get formatted light retrieval analysis prompt."""
    return LIGHT_RETRIEVAL_ANALYSIS_PROMPT.format(
        safe_user=safe_user,
        safe_model=safe_model
    )


def get_deep_query_generation_prompt(safe_context: str) -> str:
    """Get formatted deep query generation prompt."""
    return DEEP_QUERY_GENERATION_PROMPT.format(
        safe_context=safe_context
    )


def get_reflection_layer_synthesis_prompt(memories_str: str, conversation_context: str) -> str:
    """Get formatted reflection layer synthesis prompt."""
    return REFLECTION_LAYER_SYNTHESIS_PROMPT.format(
        memories_str=memories_str,
        conversation_context=conversation_context
    )


def get_memory_extraction_prompt(exchange_count: int, exchanges_text: str) -> str:
    """Get formatted memory extraction prompt."""
    return MEMORY_EXTRACTION_PROMPT.format(
        exchange_count=exchange_count,
        exchanges_text=exchanges_text
    )


def get_closing_artifacts_generation_prompt(topics: str, moments: str, emotions: str, current_emotion: str, unfinished_str: str) -> str:
    """Get formatted closing artifacts generation prompt."""
    return CLOSING_ARTIFACTS_GENERATION_PROMPT.format(
        topics=topics,
        moments=moments,
        emotions=emotions,
        current_emotion=current_emotion,
        unfinished_str=unfinished_str
    )


def get_goodbye_message_generation_prompt(current_emotion: str, moments: str, topics: str) -> str:
    """Get formatted goodbye message generation prompt."""
    return GOODBYE_MESSAGE_GENERATION_PROMPT.format(
        current_emotion=current_emotion,
        moments=moments,
        topics=topics
    )


def get_next_session_hooks_enhancement_prompt(unfinished_topics: str, key_moments: str, session_summary: str) -> str:
    """Get formatted next session hooks enhancement prompt."""
    return NEXT_SESSION_HOOKS_ENHANCEMENT_PROMPT.format(
        unfinished_topics=unfinished_topics,
        key_moments=key_moments,
        session_summary=session_summary
    )


def get_next_session_hooks_from_moments_prompt(key_moments: str, session_summary: str, topics_covered: str) -> str:
    """Get formatted next session hooks from moments prompt."""
    return NEXT_SESSION_HOOKS_FROM_MOMENTS_PROMPT.format(
        key_moments=key_moments,
        session_summary=session_summary,
        topics_covered=topics_covered
    )


def get_personal_relevance_generation_prompt(day_name: str, time_context: str, personal_texts: str) -> str:
    """Get formatted personal relevance generation prompt."""
    return PERSONAL_RELEVANCE_GENERATION_PROMPT.format(
        day_name=day_name,
        time_context=time_context,
        personal_texts=personal_texts
    )


def get_welcome_hook_generation_prompt(session_summary: str, achievement: str, emotional_state_last: str) -> str:
    """Get formatted welcome hook generation prompt."""
    return WELCOME_HOOK_GENERATION_PROMPT.format(
        session_summary=session_summary,
        achievement=achievement,
        emotional_state_last=emotional_state_last
    )


def get_suggested_opener_generation_prompt(last_session: str, emotional_state_last: str, personal_relevance: str, unfinished_topics: str) -> str:
    """Get formatted suggested opener generation prompt."""
    return SUGGESTED_OPENER_GENERATION_PROMPT.format(
        last_session=last_session,
        emotional_state_last=emotional_state_last,
        personal_relevance=personal_relevance,
        unfinished_topics=unfinished_topics
    )


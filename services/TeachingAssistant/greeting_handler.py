"""
Greeting Handler for TeachingAssistant v5
Generates personalized prompts using student biography.
Based on the Cognitive Memory Pipeline architecture.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


class GreetingHandler:
    """
    Generates personalized greeting/closing prompts using the Living Biography.

    NEW in v5: Biography-driven personalization that makes Adam remember
    students as people with stories, not just facts.
    """

    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"

    def __init__(self):
        """Initialize and load prompt templates"""
        self.opening_prompt_template = self._load_prompt("opening_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from file"""
        try:
            prompt_path = PROMPTS_DIR / filename
            if prompt_path.exists():
                with open(prompt_path, "r") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"[GREETING_HANDLER] Could not load {filename}: {e}")
        return ""

    def get_greeting(
        self,
        user_id: str,
        biography_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate personalized greeting prompt for session start.

        NEW in v5: Uses biography to create deeply personalized opening.

        Args:
            user_id: The user's ID
            biography_data: Dict with biography, current_topic, total_sessions, etc.

        Returns:
            System prompt for Adam with student context
        """
        # If no biography data, return generic greeting
        if not biography_data or not biography_data.get("biography"):
            return self._get_generic_greeting()

        biography = biography_data.get("biography", "")
        current_topic = biography_data.get("current_topic", "General math topics")
        total_sessions = biography_data.get("total_sessions", 0)
        total_questions = biography_data.get("total_questions", 0)
        last_session = biography_data.get("last_session_date")

        # Format last session date
        last_session_str = "Never"
        if last_session:
            try:
                if hasattr(last_session, 'strftime'):
                    last_session_str = last_session.strftime("%B %d, %Y")
                else:
                    last_session_str = str(last_session)[:10]
            except:
                last_session_str = "Recently"

        # Use the template if available
        if self.opening_prompt_template:
            return self.opening_prompt_template.format(
                biography=biography,
                current_topic=current_topic or "General math topics",
                total_sessions=total_sessions,
                total_questions=total_questions,
                last_session_date=last_session_str,
            )

        # Fallback to inline prompt
        return f"""{self.SYSTEM_PROMPT_PREFIX}

STUDENT BIOGRAPHY:
{biography}

CURRENT ACADEMIC FOCUS:
{current_topic}

STUDENT STATISTICS:
- Total sessions: {total_sessions}
- Questions answered: {total_questions}
- Last session: {last_session_str}

MEMORY AND INJECTION HANDLING:
During this session, you will receive 'System Updates' with retrieved memories.
- If an update arrives while you are speaking or just finished: DO NOT hallucinate a new user turn.
- Maintain consistency with your previous response.
- Do not let internal system updates disrupt the natural flow of conversation.

OPENING INSTRUCTION:
Greet the student warmly. Reference something specific from their biography or last session.
Make them feel seen and remembered. Show that you know them as a person, not just a student.

Remember:
- You know this student's story. Use it naturally.
- Reference specific interests, breakthroughs, or challenges from the biography.
- Acknowledge their emotional patterns and growth.
- Connect new topics to their interests and past experiences.
- Be warm, personable, and genuinely interested in them."""

    def _get_generic_greeting(self) -> str:
        """Generate generic greeting when no biography exists"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session with a new student.
Please greet them warmly and ask how they're doing today.
Take a moment to learn about them - their interests, goals, and what they'd like to work on.
Make them feel welcome and excited to learn.

Remember:
- This may be a new student - be welcoming and curious about them
- Ask about their interests to help personalize future sessions
- Find out what they want to learn or improve
- Create a comfortable, supportive environment"""

    def get_closing(
        self,
        duration_minutes: float,
        questions_answered: int,
        topics_covered: Optional[list] = None,
        key_moments: Optional[list] = None
    ) -> str:
        """
        Generate closing prompt with session summary.

        NEW in v5: Includes topics and key moments from the session.

        Args:
            duration_minutes: Session duration
            questions_answered: Number of questions attempted
            topics_covered: List of topics discussed
            key_moments: List of notable moments

        Returns:
            System prompt for Adam's closing message
        """
        topics_str = ", ".join(topics_covered) if topics_covered else "various topics"
        moments_str = ""
        if key_moments:
            moments_str = "\n\nKEY MOMENTS THIS SESSION:\n" + "\n".join(f"- {m}" for m in key_moments)

        return f"""{self.SYSTEM_PROMPT_PREFIX}
The tutoring session is ending now.

SESSION SUMMARY:
- Duration: {duration_minutes:.1f} minutes
- Questions attempted: {questions_answered}
- Topics covered: {topics_str}
{moments_str}

CLOSING INSTRUCTION:
Please give the student a warm closing message that:
1. Acknowledges their specific work and effort today
2. Mentions any breakthroughs or progress you noticed
3. Connects to what they might work on next time
4. Encourages them based on their personality and journey

Make them feel proud of what they accomplished and excited to return."""

    def get_inactivity_prompt(self) -> str:
        """Generate inactivity check prompt"""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
The student has been quiet for a while.

Check in with them gently:
- Ask if they're still there and doing okay
- Offer to help if they're stuck on something
- Remind them of something interesting you could work on together

Be warm and supportive, not judgmental about the silence."""

    def get_memory_injection_prompt(
        self,
        memories: list,
        current_context: str = ""
    ) -> str:
        """
        Generate a system update with retrieved memories.

        NEW in v5: Injects relevant memories mid-conversation.

        Args:
            memories: List of relevant memories from Pinecone
            current_context: What's currently being discussed

        Returns:
            System update prompt for Adam
        """
        if not memories:
            return ""

        memory_text = "\n".join([
            f"- {m.get('text', '')} (importance: {m.get('importance', 0.5):.1f})"
            for m in memories[:3]  # Limit to 3 memories
        ])

        return f"""[SYSTEM UPDATE - RELEVANT MEMORIES]
Based on the current conversation, here are relevant memories about this student:

{memory_text}

INSTRUCTIONS:
- Use these memories naturally if they're relevant to the current discussion
- Don't force a reference - only mention if it flows naturally
- These are real facts about the student - treat them as such
- Do NOT announce that you're remembering something from a database
- Do NOT hallucinate a new user response"""

    def get_breakthrough_acknowledgment(
        self,
        breakthrough: str,
        topic: str = ""
    ) -> str:
        """
        Generate a prompt to acknowledge a breakthrough moment.

        Args:
            breakthrough: Description of the breakthrough
            topic: Topic area if known

        Returns:
            System prompt for Adam
        """
        topic_ref = f" with {topic}" if topic else ""
        return f"""{self.SYSTEM_PROMPT_PREFIX}
[BREAKTHROUGH DETECTED]

The student just had a breakthrough{topic_ref}:
"{breakthrough}"

Take a moment to:
1. Acknowledge this achievement genuinely
2. Help them see why this is significant
3. Connect it to their broader learning journey
4. Build their confidence without being over-the-top

This is a memorable moment - make it feel special."""

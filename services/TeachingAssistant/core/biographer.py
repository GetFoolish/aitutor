"""
Biographer Agent - The core innovation of TA v5
Based on the Cognitive Memory Pipeline architecture

This module handles:
- Generating initial biographies from onboarding data
- Updating biographies after each session
- Maintaining narrative consistency while adding new insights

Supports: Google Gemini (primary) and OpenAI (fallback)
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import logging

# Try Gemini first (primary)
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Fallback to OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BiographerAgent:
    """
    The Biographer Agent - generates and updates student biographies.

    Philosophy:
    "You're not building a database. You're building a biographer."

    The biography is a narrative document (300-500 words) that tells the story
    of who the student is, how they got here, and where they're going.

    Supports both Gemini (primary) and OpenAI (fallback).
    """

    def __init__(self):
        """
        Initialize the Biographer Agent.

        Tries Gemini first, falls back to OpenAI if not available.
        """
        self.enabled = False
        self.provider = None
        self.gemini_client = None
        self.gemini_model_name = None
        self.openai_client = None

        # Try Gemini first
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.gemini_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self.enabled = True
                self.provider = "gemini"
                logger.info(f"[BIOGRAPHER] Initialized with Gemini ({self.gemini_model_name})")
            except Exception as e:
                logger.warning(f"[BIOGRAPHER] Gemini initialization failed: {e}")

        # Fallback to OpenAI
        if not self.enabled:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and OPENAI_AVAILABLE:
                try:
                    self.openai_client = OpenAI(api_key=openai_key)
                    self.enabled = True
                    self.provider = "openai"
                    logger.info("[BIOGRAPHER] Initialized with OpenAI")
                except Exception as e:
                    logger.warning(f"[BIOGRAPHER] OpenAI initialization failed: {e}")

        if not self.enabled:
            logger.warning("[BIOGRAPHER] No LLM provider available. Biographer disabled.")

        # Load prompts
        self.biographer_prompt = self._load_prompt("biographer_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from file"""
        try:
            prompt_path = PROMPTS_DIR / filename
            with open(prompt_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[BIOGRAPHER] Failed to load prompt {filename}: {e}")
            return ""

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call the LLM with a prompt"""
        if not self.enabled:
            return None

        try:
            if self.provider == "gemini" and self.gemini_client:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=prompt,
                    config={
                        'temperature': 0.7,
                        'max_output_tokens': 1500
                    }
                )
                return response.text

            elif self.provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1500,
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[BIOGRAPHER] LLM call failed: {e}")
            return None

    def generate_initial_biography(
        self,
        name: str,
        onboarding_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate an initial biography from onboarding data.

        Called when a student is first created or during migration.

        Args:
            name: Student's name
            onboarding_data: Dict containing core_values, interests, etc.

        Returns:
            Initial biography text
        """
        if not self.enabled:
            return self._generate_fallback_biography(name, onboarding_data)

        prompt = f"""You are creating the first biography for a student based on their onboarding data.

Student Name: {name}

Onboarding Data:
- Core Values: {onboarding_data.get('core_values', [])}
- North Star Goals: {onboarding_data.get('north_star_goals', [])}
- Personality Traits: {onboarding_data.get('personality_traits', [])}
- Blind Spots: {onboarding_data.get('blind_spots', [])}
- Emotional Baseline: {onboarding_data.get('emotional_baseline', 'neutral')}
- Interests: {onboarding_data.get('interests', [])}

Write a 200-300 word biography that:
1. Introduces who they are as a person
2. Captures their values, interests, and personality
3. Notes potential blind spots or growth areas (compassionately)
4. Sets up their academic journey (just beginning)

Use prose, not bullet points. Write like a character study.

Format:
PSYCHOLOGICAL PROFILE:
[Who they are, values, patterns, blind spots]

ACADEMIC JOURNEY:
[Just starting out, no history yet, but note their goals and emotional state about learning]"""

        biography = self._call_llm(prompt)

        if not biography:
            return self._generate_fallback_biography(name, onboarding_data)

        logger.info(f"[BIOGRAPHER] Generated initial biography for {name}")
        return biography

    def _generate_fallback_biography(
        self,
        name: str,
        onboarding_data: Dict[str, Any]
    ) -> str:
        """Generate a simple biography when LLM is unavailable"""
        interests = onboarding_data.get('interests', [])
        values = onboarding_data.get('core_values', [])
        traits = onboarding_data.get('personality_traits', [])
        baseline = onboarding_data.get('emotional_baseline', 'neutral')

        interests_str = ", ".join(interests) if interests else "various subjects"
        values_str = ", ".join(values) if values else "learning and growth"
        traits_str = ", ".join(traits) if traits else "curious and engaged"

        return f"""PSYCHOLOGICAL PROFILE:
{name} is a student who values {values_str}. Their personality can be described as {traits_str}. They have shown interest in {interests_str}. Their emotional baseline as they begin this learning journey is {baseline}.

ACADEMIC JOURNEY:
{name} is just beginning their academic journey on this platform. No sessions have been completed yet, but they have shown willingness to learn and grow. The next steps will involve understanding their learning style and building foundational skills."""

    def update_biography(
        self,
        current_biography: str,
        session_transcript: List[Dict[str, Any]],
        session_summary: Dict[str, Any]
    ) -> Optional[str]:
        """
        Update biography after a session.

        This is the core function that runs after every session.

        Args:
            current_biography: The existing biography text
            session_transcript: List of conversation turns
            session_summary: Dict with topics_covered, emotional_arc, key_moments, etc.

        Returns:
            Updated biography text
        """
        if not self.enabled:
            logger.warning("[BIOGRAPHER] Not enabled, returning current biography")
            return current_biography

        # Format transcript
        transcript_text = self._format_transcript(session_transcript)

        # Extract summary fields
        topics = session_summary.get("topics_covered", [])
        emotional_arc = session_summary.get("emotional_arc", [])
        key_moments = session_summary.get("key_moments", [])
        questions_answered = session_summary.get("questions_answered", 0)
        questions_correct = session_summary.get("questions_correct", 0)

        # Build prompt
        prompt = self.biographer_prompt.format(
            current_biography=current_biography or "No biography exists yet.",
            session_transcript=transcript_text,
            topics_covered=", ".join(topics) if topics else "General discussion",
            emotional_arc=" → ".join(emotional_arc) if emotional_arc else "Neutral throughout",
            key_moments="\n".join(f"- {m}" for m in key_moments) if key_moments else "No specific key moments noted",
            questions_answered=questions_answered,
            questions_correct=questions_correct,
        )

        updated_biography = self._call_llm(prompt)

        if not updated_biography:
            logger.warning("[BIOGRAPHER] Failed to generate update, returning current")
            return current_biography

        logger.info("[BIOGRAPHER] Successfully updated biography")
        return updated_biography

    def _format_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """Format conversation transcript for the prompt"""
        if not transcript:
            return "No conversation recorded."

        lines = []
        for turn in transcript:
            speaker = turn.get("speaker", "unknown").upper()
            text = turn.get("text", "")
            emotion = turn.get("emotion", "")

            if emotion:
                lines.append(f"{speaker}: {text} [emotion: {emotion}]")
            else:
                lines.append(f"{speaker}: {text}")

        # Limit to last 50 turns to stay within context limits
        if len(lines) > 50:
            lines = lines[-50:]
            lines.insert(0, "[... earlier conversation truncated ...]")

        return "\n".join(lines)

    def generate_from_history(
        self,
        name: str,
        conversations: List[List[Dict[str, Any]]],
        academic_memories: List[str],
        personal_memories: List[str]
    ) -> Optional[str]:
        """
        Generate a biography from historical data (for migration).

        Args:
            name: Student name
            conversations: List of past conversation logs
            academic_memories: List of academic facts
            personal_memories: List of personal facts

        Returns:
            Generated biography
        """
        if not self.enabled:
            return self._generate_fallback_biography(name, {})

        prompt = f"""You are creating the first biography for a student based on their historical tutoring sessions.

Student Name: {name}

Historical Data:
- Number of past conversations: {len(conversations)}
- Academic memories: {academic_memories[:20]}  # Limit for prompt size
- Personal memories: {personal_memories[:20]}

Write a 300-500 word biography that captures:
1. Who they are (interests, personality inferred from conversations)
2. Their academic journey so far (topics, struggles, breakthroughs)
3. Patterns you observe (emotional, behavioral)
4. Where they are now

Use prose, not bullets. This should read like a character study.

Format:
PSYCHOLOGICAL PROFILE:
[Who they are, patterns, interests, blind spots]

ACADEMIC JOURNEY:
[Progress over time, key moments, current focus]"""

        return self._call_llm(prompt)

    def analyze_session_emotions(
        self,
        transcript: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Analyze emotional arc from a session transcript.

        Args:
            transcript: List of conversation turns

        Returns:
            List of emotions in sequence
        """
        if not self.enabled or not transcript:
            return ["neutral"]

        # Extract student turns only
        student_turns = [
            t["text"] for t in transcript
            if t.get("speaker") == "student"
        ]

        if not student_turns:
            return ["neutral"]

        prompt = f"""Analyze the emotional arc of this student across these conversation turns.

Student statements:
{chr(10).join(student_turns[:20])}

Return ONLY a comma-separated list of emotions (e.g., "anxious, confused, curious, excited, satisfied").
Focus on major emotional shifts, not every small change.
Use these emotion categories: anxious, confused, frustrated, curious, engaged, excited, happy, satisfied, tired, neutral"""

        result = self._call_llm(prompt)

        if result:
            emotions = [e.strip().lower() for e in result.split(",")]
            return emotions[:10]  # Limit to 10 emotions

        return ["neutral"]

    def extract_key_moments(
        self,
        transcript: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract key moments from a session.

        Args:
            transcript: List of conversation turns

        Returns:
            List of key moment descriptions
        """
        if not self.enabled or not transcript:
            return []

        transcript_text = self._format_transcript(transcript)

        prompt = f"""Identify 1-3 key moments from this tutoring session.
Key moments are:
- Breakthroughs in understanding
- Emotional shifts (positive or negative)
- Connections made to personal interests
- Moments of struggle that were overcome
- Expressed frustrations or concerns

Conversation:
{transcript_text}

Return each key moment as a brief sentence on its own line.
Return ONLY the key moments, no other text.
If there are no significant moments, return "No notable key moments"."""

        result = self._call_llm(prompt)

        if result:
            moments = [
                m.strip() for m in result.split("\n")
                if m.strip() and not m.strip().startswith("No notable")
            ]
            return moments[:3]

        return []


# Singleton instance - lazy initialization to ensure .env is loaded first
_biographer_agent_instance = None

def get_biographer_agent():
    """Get or create the singleton BiographerAgent instance"""
    global _biographer_agent_instance
    if _biographer_agent_instance is None:
        _biographer_agent_instance = BiographerAgent()
    return _biographer_agent_instance

# For backward compatibility, create a property that lazily initializes
class _BiographerAgentProxy:
    def __getattr__(self, name):
        return getattr(get_biographer_agent(), name)
    
    def __call__(self, *args, **kwargs):
        return get_biographer_agent()(*args, **kwargs)

biographer_agent = _BiographerAgentProxy()

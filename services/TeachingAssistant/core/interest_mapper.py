"""
Interest Mapper - LLM-Powered Dynamic Interest-to-Concept Connections

This module dynamically generates teaching connections between ANY student interest
and ANY learning concept across ALL subjects (math, science, history, coding,
languages, art, music, etc.). Unlike a static dictionary, it uses LLM to create
personalized, creative connections on-the-fly.

Examples:
    Math: interests=["origami"], topic="angles"
        → "Think about origami - each fold creates a precise angle..."

    History: interests=["video games"], topic="Roman Empire"
        → "Like in strategy games, Rome had to manage resources, expand territory..."

    Science: interests=["cooking"], topic="chemical reactions"
        → "When you bake, mixing baking soda and vinegar is a chemical reaction..."

    Coding: interests=["music"], topic="loops"
        → "A loop is like a repeating chorus - it plays the same thing until you stop it..."

Supports: Google Gemini (primary) and OpenAI (fallback)
"""

import os
from typing import Optional, List, Dict, Any
import logging

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class InterestMapper:
    """
    LLM-powered Interest-to-Concept Mapper (Gemini-only).

    Dynamically generates teaching connections between student interests
    and learning concepts across ALL subjects. Works for ANY interest.

    Philosophy:
    A great tutor connects any concept to the student's world.
    "You love origami? Let's see how angles work in paper folding..."
    """

    def __init__(self):
        """Initialize the Interest Mapper with Gemini."""
        self.enabled = False
        self.gemini_client = None
        self.gemini_model_name = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.gemini_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self.enabled = True
                logger.info(f"[INTEREST_MAPPER] Initialized with Gemini ({self.gemini_model_name})")
            except Exception as e:
                logger.warning(f"[INTEREST_MAPPER] Gemini initialization failed: {e}")

        if not self.enabled:
            logger.warning("[INTEREST_MAPPER] Gemini not available. Interest mapping disabled.")

    def _call_llm(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Call Gemini with a prompt."""
        if not self.enabled or not self.gemini_client:
            return None

        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
                config={
                    'temperature': temperature,
                    'max_output_tokens': 500
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"[INTEREST_MAPPER] Gemini call failed: {e}")
            return None

    def generate_connection(
        self,
        interests: List[str],
        current_topic: str,
        student_name: Optional[str] = None,
        difficulty_level: str = "middle school"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a teaching connection between student interests and a math concept.

        Args:
            interests: List of student interests (e.g., ["video games", "dogs", "K-pop"])
            current_topic: The math concept being taught (e.g., "percentages", "angles")
            student_name: Optional student name for personalization
            difficulty_level: Grade level for appropriate language

        Returns:
            Dict with:
                - connection_text: The actual teaching connection to use
                - interest_used: Which interest was connected
                - example_problem: Optional example problem using the interest
                - confidence: How strong the connection is (high/medium/low)
            Or None if no connection could be generated
        """
        if not self.enabled or not interests or not current_topic:
            return None

        interests_str = ", ".join(interests)
        name_context = f"The student's name is {student_name}. " if student_name else ""

        prompt = f"""You are helping an AI tutor connect learning concepts to a student's personal interests.
This works for ANY subject: math, science, history, coding, languages, art, music, etc.

{name_context}Student's interests: {interests_str}
Current topic: {current_topic}
Difficulty level: {difficulty_level}

Generate a NATURAL teaching connection that links one of their interests to this concept.

Rules:
1. Choose the interest that connects MOST naturally to this topic
2. Make it feel conversational, not forced
3. Include a concrete example or analogy
4. Keep it brief (2-3 sentences max)
5. Don't be condescending - be genuinely helpful
6. If no natural connection exists, say "NO_CONNECTION"

Output format (JSON):
{{
    "interest_used": "<which interest you're connecting>",
    "connection_text": "<the teaching connection/analogy>",
    "example_problem": "<optional: a practice question/scenario using their interest>",
    "confidence": "<high/medium/low>"
}}

Example outputs for different subjects:

Math + video games:
{{
    "interest_used": "video games",
    "connection_text": "Think about it like damage calculations - when you get a 25% damage boost, you're multiplying your base damage by 1.25.",
    "example_problem": "If your character does 80 base damage and gets a 25% boost, what's the total damage?",
    "confidence": "high"
}}

History + strategy games:
{{
    "interest_used": "strategy games",
    "connection_text": "The Roman Empire worked a lot like Civilization - they had to balance military expansion with keeping citizens happy and managing resources.",
    "example_problem": "Why do you think Rome focused on building roads throughout their empire?",
    "confidence": "high"
}}

Science + cooking:
{{
    "interest_used": "cooking",
    "connection_text": "Chemical reactions are happening every time you cook! When you caramelize onions, heat is breaking down sugars and creating new compounds.",
    "example_problem": "What do you think happens chemically when bread rises from yeast?",
    "confidence": "high"
}}

Generate the connection now:"""

        result = self._call_llm(prompt, temperature=0.7)

        if not result or "NO_CONNECTION" in result:
            return None

        # Parse the JSON response
        try:
            import json
            # Clean up the response (remove markdown code blocks if present)
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]

            connection = json.loads(result.strip())
            logger.info(f"[INTEREST_MAPPER] Generated connection: {connection.get('interest_used')} -> {current_topic}")
            return connection
        except json.JSONDecodeError as e:
            logger.warning(f"[INTEREST_MAPPER] Failed to parse LLM response: {e}")
            # Try to extract useful text anyway
            return {
                "interest_used": interests[0] if interests else "unknown",
                "connection_text": result,
                "example_problem": None,
                "confidence": "low"
            }

    def generate_example_problem(
        self,
        interest: str,
        topic: str,
        subject: str = "general",
        student_name: Optional[str] = None,
        difficulty_level: str = "middle school"
    ) -> Optional[str]:
        """
        Generate a practice question/scenario using the student's interest.

        Works for ANY subject - math, science, history, coding, languages, etc.

        Args:
            interest: The specific interest to use
            topic: The topic for the question
            subject: The subject area (math, science, history, etc.)
            student_name: Optional student name to include
            difficulty_level: Grade level

        Returns:
            A practice question/scenario string, or None
        """
        if not self.enabled:
            return None

        name_part = f"{student_name}'s" if student_name else "Your"

        prompt = f"""Create a practice question about {topic} ({subject}) using {interest} as the context.

Requirements:
- Difficulty: {difficulty_level}
- Make it engaging and relatable
- Include enough context to answer
- Use "{name_part}" to personalize

Output ONLY the question/scenario, nothing else.

Examples:
Math + video games: "{name_part} character has 120 HP. After a 35% health boost, how many HP total?"
History + K-pop: "How did the Korean Wave (Hallyu) influence global perceptions of South Korea?"
Science + cooking: "When {name_part} bread rises, what gas is the yeast producing?"
Coding + music: "If you wanted to repeat a chorus 4 times, what programming concept would you use?"

Generate the question:"""

        return self._call_llm(prompt, temperature=0.8)

    def extract_interests_from_text(self, text: str) -> List[str]:
        """
        Extract interests from free-form text (like a biography).

        Args:
            text: Biography or conversation text

        Returns:
            List of identified interests
        """
        if not self.enabled or not text:
            return []

        prompt = f"""Extract the student's hobbies and interests from this text.

Text:
{text[:2000]}

Output ONLY a comma-separated list of interests/hobbies.
Be specific (e.g., "Minecraft" not just "video games", "golden retriever named Max" not just "pets").
If no clear interests are found, output "NONE".

Examples of good extractions:
- "plays guitar, loves anime, has a cat named Whiskers"
- "basketball, cooking, building Lego sets"

Extract interests:"""

        result = self._call_llm(prompt, temperature=0.3)

        if not result or "NONE" in result.upper():
            return []

        interests = [i.strip() for i in result.split(",") if i.strip()]
        return interests[:10]  # Limit to 10 interests

    def get_teaching_suggestion(
        self,
        interests: List[str],
        topic: str,
        struggle_context: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a quick teaching suggestion incorporating interests.

        This is a lighter-weight call for mid-conversation use.

        Args:
            interests: Student's interests
            topic: Current topic
            struggle_context: Optional context about what they're struggling with

        Returns:
            A brief teaching suggestion string
        """
        if not self.enabled or not interests:
            return None

        struggle_part = f"\nThey're currently struggling with: {struggle_context}" if struggle_context else ""

        prompt = f"""Quick teaching tip: Connect "{topic}" to one of these interests: {', '.join(interests)}.
{struggle_part}

Give ONE brief, natural suggestion (1 sentence) for how the tutor could use their interest to explain this concept.
Output ONLY the suggestion, no preamble."""

        return self._call_llm(prompt, temperature=0.6)


# Singleton instance - lazy initialization
_interest_mapper_instance = None

def get_interest_mapper() -> InterestMapper:
    """Get or create the singleton InterestMapper instance."""
    global _interest_mapper_instance
    if _interest_mapper_instance is None:
        _interest_mapper_instance = InterestMapper()
    return _interest_mapper_instance


# Proxy class for backward compatibility and lazy initialization
class _InterestMapperProxy:
    def __getattr__(self, name):
        return getattr(get_interest_mapper(), name)

    def __call__(self, *args, **kwargs):
        return get_interest_mapper()(*args, **kwargs)

interest_mapper = _InterestMapperProxy()

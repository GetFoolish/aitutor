"""
Learning Style Tracker - Adaptive Teaching Based on What Works

This module tracks and adapts to each student's learning preferences:
- What explanation styles resonate (visual, analogy, step-by-step, etc.)
- Preferred pace (quick/moderate/slow)
- What causes frustration
- What leads to breakthroughs

Works across ALL subjects - the learning style is about HOW they learn,
not WHAT they're learning.

Uses Gemini for intelligent analysis of student responses.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ExplanationStyle(str, Enum):
    """Types of explanation approaches"""
    VISUAL = "visual"              # Diagrams, drawings, spatial representations
    ANALOGY = "analogy"            # Real-world comparisons, metaphors
    STEP_BY_STEP = "step_by_step"  # Detailed sequential procedures
    BIG_PICTURE = "big_picture"    # Why it matters, context first
    EXAMPLE_FIRST = "example_first"  # Show example, then explain concept
    INTERACTIVE = "interactive"     # Lots of back-and-forth questions
    NARRATIVE = "narrative"         # Story-based, contextual learning
    HANDS_ON = "hands_on"          # Learning by doing/practicing


class Pace(str, Enum):
    """Learning pace preferences"""
    QUICK = "quick"        # Grasps concepts fast, don't over-explain
    MODERATE = "moderate"  # Standard pacing
    SLOW = "slow"          # Needs more time, check understanding often


@dataclass
class LearningStyleProfile:
    """
    Profile of what works for a specific student.

    This evolves over time as we learn more about the student.
    """
    # Preferred explanation styles (ordered by effectiveness)
    preferred_styles: List[ExplanationStyle] = field(default_factory=list)

    # Styles that haven't worked well
    avoided_styles: List[ExplanationStyle] = field(default_factory=list)

    # Pace preference
    preferred_pace: Pace = Pace.MODERATE

    # Specific observations
    works_well: List[str] = field(default_factory=list)  # "visual diagrams for geometry"
    doesnt_work: List[str] = field(default_factory=list)  # "abstract definitions"

    # Emotional patterns
    gets_frustrated_with: List[str] = field(default_factory=list)  # Topics/approaches
    engages_well_with: List[str] = field(default_factory=list)    # Topics/approaches

    # Breakthrough patterns
    breakthrough_methods: List[str] = field(default_factory=list)  # What's led to "aha" moments

    def to_prompt_text(self) -> str:
        """Convert profile to text for injection into prompts"""
        lines = []

        if self.preferred_styles:
            styles = [s.value.replace("_", " ") for s in self.preferred_styles[:3]]
            lines.append(f"Preferred learning styles: {', '.join(styles)}")

        if self.avoided_styles:
            styles = [s.value.replace("_", " ") for s in self.avoided_styles[:2]]
            lines.append(f"Styles to avoid: {', '.join(styles)}")

        if self.preferred_pace != Pace.MODERATE:
            pace_desc = {
                Pace.QUICK: "quick - grasps concepts fast, don't over-explain",
                Pace.SLOW: "slower - needs time to process, check understanding often"
            }
            lines.append(f"Pace: {pace_desc.get(self.preferred_pace, self.preferred_pace.value)}")

        if self.works_well:
            lines.append(f"What works: {'; '.join(self.works_well[:3])}")

        if self.doesnt_work:
            lines.append(f"What doesn't work: {'; '.join(self.doesnt_work[:2])}")

        if self.gets_frustrated_with:
            lines.append(f"Gets frustrated with: {', '.join(self.gets_frustrated_with[:2])}")

        if self.breakthrough_methods:
            lines.append(f"Breakthrough methods: {'; '.join(self.breakthrough_methods[:2])}")

        return '\n'.join(lines) if lines else "Learning style not yet determined - observe and adapt"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "preferred_styles": [s.value for s in self.preferred_styles],
            "avoided_styles": [s.value for s in self.avoided_styles],
            "preferred_pace": self.preferred_pace.value,
            "works_well": self.works_well,
            "doesnt_work": self.doesnt_work,
            "gets_frustrated_with": self.gets_frustrated_with,
            "engages_well_with": self.engages_well_with,
            "breakthrough_methods": self.breakthrough_methods
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningStyleProfile":
        """Create from dictionary"""
        return cls(
            preferred_styles=[ExplanationStyle(s) for s in data.get("preferred_styles", [])],
            avoided_styles=[ExplanationStyle(s) for s in data.get("avoided_styles", [])],
            preferred_pace=Pace(data.get("preferred_pace", "moderate")),
            works_well=data.get("works_well", []),
            doesnt_work=data.get("doesnt_work", []),
            gets_frustrated_with=data.get("gets_frustrated_with", []),
            engages_well_with=data.get("engages_well_with", []),
            breakthrough_methods=data.get("breakthrough_methods", [])
        )


class LearningStyleTracker:
    """
    Tracks and updates student learning style profiles using Gemini.

    Analyzes conversation turns to detect:
    - Style preferences (visual, analogy, step-by-step, etc.)
    - Pace signals (too fast, too slow)
    - Engagement and frustration patterns
    - Breakthrough moments
    """

    def __init__(self):
        """Initialize the Learning Style Tracker with Gemini."""
        self.enabled = False
        self.gemini_client = None
        self.gemini_model_name = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.gemini_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self.enabled = True
                logger.info(f"[LEARNING_STYLE] Initialized with Gemini ({self.gemini_model_name})")
            except Exception as e:
                logger.warning(f"[LEARNING_STYLE] Gemini initialization failed: {e}")

        if not self.enabled:
            logger.warning("[LEARNING_STYLE] Gemini not available. Learning style tracking disabled.")

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
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
            logger.error(f"[LEARNING_STYLE] Gemini call failed: {e}")
            return None

    def analyze_turn(
        self,
        student_text: str,
        tutor_text: str,
        emotion: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a conversation turn for learning style signals.

        Args:
            student_text: What the student said
            tutor_text: What the tutor said (to understand context)
            emotion: Detected emotion (if available)
            topic: Current topic being discussed

        Returns:
            Dict with detected signals:
                - style_preferences: List of ExplanationStyle
                - engagement: "positive" | "frustrated" | "neutral"
                - pace_signal: "slower" | "faster" | None
                - breakthrough: bool
                - observation: str (specific observation to store)
        """
        if not self.enabled:
            return self._rule_based_analysis(student_text, emotion)

        prompt = f"""Analyze this tutoring conversation turn for learning style signals.

Student said: "{student_text}"
Tutor had said: "{tutor_text[:300]}"
{f'Detected emotion: {emotion}' if emotion else ''}
{f'Current topic: {topic}' if topic else ''}

Identify:
1. Style preferences - Did the student ask for or respond well to:
   - visual (diagrams, drawings)
   - analogy (real-world comparisons)
   - step_by_step (detailed procedures)
   - big_picture (why it matters)
   - example_first (show me an example)
   - interactive (more questions)
   - narrative (story-based)
   - hands_on (let me try)

2. Engagement level: positive (understanding, excited), frustrated, or neutral

3. Pace signal: Did they indicate "too fast" (slow down) or "I get it" (faster)?

4. Breakthrough: Did they have an "aha moment"?

5. Specific observation: One sentence about their learning pattern (if any)

Output as JSON:
{{
    "style_preferences": ["style1", "style2"],
    "engagement": "positive|frustrated|neutral",
    "pace_signal": "slower|faster|null",
    "breakthrough": true|false,
    "observation": "specific observation or null"
}}

If no clear signals, use empty lists and null values."""

        result = self._call_llm(prompt)

        if result:
            try:
                import json
                # Clean up response
                result = result.strip()
                if result.startswith("```json"):
                    result = result[7:]
                if result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]

                data = json.loads(result.strip())

                # Convert style strings to enums
                styles = []
                for s in data.get("style_preferences", []):
                    try:
                        styles.append(ExplanationStyle(s))
                    except ValueError:
                        pass

                return {
                    "style_preferences": styles,
                    "engagement": data.get("engagement", "neutral"),
                    "pace_signal": data.get("pace_signal"),
                    "breakthrough": data.get("breakthrough", False),
                    "observation": data.get("observation")
                }
            except json.JSONDecodeError:
                logger.warning("[LEARNING_STYLE] Failed to parse LLM response")

        return self._rule_based_analysis(student_text, emotion)

    def _rule_based_analysis(
        self,
        student_text: str,
        emotion: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback rule-based analysis when LLM is unavailable."""
        result = {
            "style_preferences": [],
            "engagement": "neutral",
            "pace_signal": None,
            "breakthrough": False,
            "observation": None
        }

        student_lower = student_text.lower()

        # Style detection keywords
        style_keywords = {
            ExplanationStyle.VISUAL: ["show me", "draw", "picture", "diagram", "see", "visualize"],
            ExplanationStyle.ANALOGY: ["like what", "similar to", "is it like", "compare", "real world"],
            ExplanationStyle.STEP_BY_STEP: ["step by step", "one at a time", "slowly", "each step", "break it down"],
            ExplanationStyle.BIG_PICTURE: ["why", "what's the point", "when would i", "purpose"],
            ExplanationStyle.EXAMPLE_FIRST: ["show me an example", "can you show", "example first"],
            ExplanationStyle.HANDS_ON: ["let me try", "can i try", "i want to do it"],
        }

        for style, keywords in style_keywords.items():
            if any(kw in student_lower for kw in keywords):
                result["style_preferences"].append(style)

        # Engagement detection
        positive_signals = ["oh!", "aha", "got it", "makes sense", "i understand", "that helps", "cool", "nice"]
        frustration_signals = ["i don't get", "confused", "what?", "huh?", "still don't", "this is hard", "frustrated"]

        if any(s in student_lower for s in positive_signals):
            result["engagement"] = "positive"
        elif any(s in student_lower for s in frustration_signals):
            result["engagement"] = "frustrated"

        # Override with explicit emotion
        if emotion in ["frustrated", "confused", "anxious"]:
            result["engagement"] = "frustrated"
        elif emotion in ["excited", "happy", "engaged", "curious"]:
            result["engagement"] = "positive"

        # Pace signals
        if any(w in student_lower for w in ["too fast", "slow down", "wait", "hold on"]):
            result["pace_signal"] = "slower"
        elif any(w in student_lower for w in ["i know", "already", "yeah yeah", "skip", "i get it"]):
            result["pace_signal"] = "faster"

        # Breakthrough detection
        if any(w in student_lower for w in ["oh!", "aha!", "ohhh", "i see!", "that makes sense!"]):
            result["breakthrough"] = True

        return result

    def update_profile(
        self,
        current_profile: LearningStyleProfile,
        turn_analysis: Dict[str, Any],
        topic: Optional[str] = None,
        tutor_approach_used: Optional[str] = None
    ) -> LearningStyleProfile:
        """
        Update a learning style profile based on turn analysis.

        Args:
            current_profile: Current profile to update
            turn_analysis: Analysis from analyze_turn()
            topic: Current topic (for context-specific observations)
            tutor_approach_used: What approach the tutor used

        Returns:
            Updated profile
        """
        # Add style preferences (avoid duplicates, maintain order)
        for style in turn_analysis.get("style_preferences", []):
            if style not in current_profile.preferred_styles:
                current_profile.preferred_styles.append(style)
                # Keep top 5
                current_profile.preferred_styles = current_profile.preferred_styles[:5]

        # Update engagement patterns
        engagement = turn_analysis.get("engagement")
        if topic and engagement == "frustrated":
            if topic not in current_profile.gets_frustrated_with:
                current_profile.gets_frustrated_with.append(topic)
                current_profile.gets_frustrated_with = current_profile.gets_frustrated_with[:5]
        elif topic and engagement == "positive":
            if topic not in current_profile.engages_well_with:
                current_profile.engages_well_with.append(topic)
                current_profile.engages_well_with = current_profile.engages_well_with[:5]

        # Update pace preference
        pace_signal = turn_analysis.get("pace_signal")
        if pace_signal == "slower":
            current_profile.preferred_pace = Pace.SLOW
        elif pace_signal == "faster":
            current_profile.preferred_pace = Pace.QUICK

        # Track breakthrough methods
        if turn_analysis.get("breakthrough") and tutor_approach_used:
            if tutor_approach_used not in current_profile.breakthrough_methods:
                current_profile.breakthrough_methods.append(tutor_approach_used)
                current_profile.breakthrough_methods = current_profile.breakthrough_methods[:5]

        # Store specific observations
        observation = turn_analysis.get("observation")
        if observation:
            context = f" ({topic})" if topic else ""
            full_observation = f"{observation}{context}"
            if engagement == "positive" and full_observation not in current_profile.works_well:
                current_profile.works_well.append(full_observation)
                current_profile.works_well = current_profile.works_well[:5]
            elif engagement == "frustrated" and full_observation not in current_profile.doesnt_work:
                current_profile.doesnt_work.append(full_observation)
                current_profile.doesnt_work = current_profile.doesnt_work[:3]

        return current_profile

    def generate_teaching_guidance(
        self,
        profile: LearningStyleProfile,
        current_topic: str,
        student_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate teaching guidance based on learning style profile.

        Args:
            profile: Student's learning style profile
            current_topic: Topic being taught
            student_name: Student's name (optional)

        Returns:
            Teaching guidance string for injection
        """
        if not profile.preferred_styles and not profile.gets_frustrated_with:
            return None

        lines = []
        name = student_name or "This student"

        # Check if current topic is in frustration list
        for frustration_topic in profile.gets_frustrated_with:
            if current_topic.lower() in frustration_topic.lower() or frustration_topic.lower() in current_topic.lower():
                lines.append(
                    f"NOTE: {name} has struggled with {current_topic} before. "
                    "Provide extra encouragement and break into smaller steps."
                )
                break

        # Add style guidance
        if profile.preferred_styles:
            style = profile.preferred_styles[0]
            style_guidance = {
                ExplanationStyle.VISUAL: f"{name} learns best visually - lead with diagrams or visual representations",
                ExplanationStyle.ANALOGY: f"{name} responds well to analogies - find a real-world comparison",
                ExplanationStyle.STEP_BY_STEP: f"{name} prefers step-by-step - break down into clear sequential steps",
                ExplanationStyle.BIG_PICTURE: f"{name} wants the 'why' first - explain importance before details",
                ExplanationStyle.EXAMPLE_FIRST: f"{name} learns from examples - show a worked example before explaining",
                ExplanationStyle.HANDS_ON: f"{name} learns by doing - get them practicing quickly",
            }
            if style in style_guidance:
                lines.append(style_guidance[style])

        # Add pace guidance
        if profile.preferred_pace == Pace.SLOW:
            lines.append(f"{name} needs a slower pace - check understanding frequently, don't rush")
        elif profile.preferred_pace == Pace.QUICK:
            lines.append(f"{name} grasps things quickly - don't over-explain, trust their processing")

        # Add breakthrough method if relevant
        if profile.breakthrough_methods:
            method = profile.breakthrough_methods[0]
            lines.append(f"Past breakthrough using: {method}")

        if lines:
            return "\n".join(lines)
        return None


# Singleton instance - lazy initialization
_learning_style_tracker_instance = None

def get_learning_style_tracker() -> LearningStyleTracker:
    """Get or create the singleton LearningStyleTracker instance."""
    global _learning_style_tracker_instance
    if _learning_style_tracker_instance is None:
        _learning_style_tracker_instance = LearningStyleTracker()
    return _learning_style_tracker_instance


class _LearningStyleTrackerProxy:
    def __getattr__(self, name):
        return getattr(get_learning_style_tracker(), name)

learning_style_tracker = _LearningStyleTrackerProxy()

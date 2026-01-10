"""
Skill Base Class - Abstract base for all skills
Based on v4 teaching-assistant branch implementation

Skills are modular components that:
- Analyze session context
- Decide whether to activate
- Generate instruction injections
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging

from ..core.context import SessionContext
from ..core.config import TeachingAssistantConfig

logger = logging.getLogger(__name__)


class Skill(ABC):
    """
    Abstract base class for all skills.

    Skills are triggered based on session context and can inject
    instructions into the tutor's response to modify behavior.

    Example usage:
        class GreetingSkill(Skill):
            name = "greeting"
            description = "Handles session greetings"

            def should_run(self, context: SessionContext) -> bool:
                return context.turn_count == 1

            def execute(self, context: SessionContext) -> Optional[str]:
                if context.student_name:
                    return f"Greet {context.student_name} warmly."
                return "Greet the student warmly."
    """

    # Skill metadata (override in subclasses)
    name: str = "base_skill"
    description: str = "Base skill class"
    priority: int = 0  # Higher priority = runs first
    enabled: bool = True

    def __init__(self, config: Optional[TeachingAssistantConfig] = None):
        self.config = config or TeachingAssistantConfig()
        self._state: Dict[str, Any] = {}
        logger.debug(f"[SKILL:{self.name}] Initialized")

    @abstractmethod
    def should_run(self, context: SessionContext) -> bool:
        """
        Determine if this skill should execute.

        Args:
            context: Current session context

        Returns:
            True if skill should execute
        """
        pass

    @abstractmethod
    def execute(self, context: SessionContext) -> Optional[str]:
        """
        Execute the skill and return an instruction injection.

        Args:
            context: Current session context

        Returns:
            Instruction string to inject, or None
        """
        pass

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get skill state value"""
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any):
        """Set skill state value"""
        self._state[key] = value

    def reset_state(self):
        """Reset skill state"""
        self._state = {}

    def __repr__(self) -> str:
        return f"<Skill:{self.name} enabled={self.enabled} priority={self.priority}>"


class GreetingSkill(Skill):
    """
    Skill for handling session greetings.

    Triggers on the first turn to personalize the greeting
    based on student biography and session history.
    """

    name = "greeting"
    description = "Personalizes session greetings based on student context"
    priority = 10  # High priority for first turn

    def should_run(self, context: SessionContext) -> bool:
        """Run only on the first turn"""
        return context.turn_count <= 1

    def execute(self, context: SessionContext) -> Optional[str]:
        """Generate personalized greeting instruction"""
        parts = []

        if context.student_name:
            parts.append(f"Address the student as {context.student_name}.")

        if context.is_first_session:
            parts.append("This is their first session - make them feel welcome and comfortable.")
        elif context.last_session_date:
            parts.append("Welcome them back and briefly acknowledge your previous sessions together.")

        if context.interests:
            interests_str = ", ".join(context.interests[:3])
            parts.append(f"You know they're interested in: {interests_str}. Consider referencing these.")

        if context.biography:
            # Extract key personality traits from biography
            parts.append("Use your knowledge of their personality to set the right tone.")

        if not parts:
            return None

        return "Greeting guidance: " + " ".join(parts)


class EmotionResponseSkill(Skill):
    """
    Skill for responding to detected emotions.

    Monitors emotional state and provides guidance for
    appropriate responses to emotional shifts.
    """

    name = "emotion_response"
    description = "Guides response to student emotional states"
    priority = 8

    def should_run(self, context: SessionContext) -> bool:
        """Run when emotion is detected"""
        return context.current_emotion is not None

    def execute(self, context: SessionContext) -> Optional[str]:
        """Generate emotion-appropriate instruction"""
        emotion = context.current_emotion

        if not emotion:
            return None

        emotion_guidance = {
            "frustrated": "The student seems frustrated. Slow down, validate their feelings, and break the problem into smaller steps.",
            "confused": "The student appears confused. Ask clarifying questions and try a different explanation approach.",
            "excited": "The student is excited! Build on this energy and deepen the engagement.",
            "anxious": "The student seems anxious. Be encouraging and reassuring. Emphasize that making mistakes is part of learning.",
            "tired": "The student may be tired. Keep explanations brief and consider suggesting a break.",
            "happy": "The student is in a good mood. This is a great time for challenging material.",
            "bored": "The student might be bored. Try to connect the material to their interests or increase the challenge level.",
            "curious": "The student is curious! Encourage their questions and explore tangents they find interesting.",
        }

        guidance = emotion_guidance.get(emotion.lower())
        if guidance:
            return f"Emotional awareness: {guidance}"

        return None


class MemoryInjectionSkill(Skill):
    """
    Skill for injecting retrieved memories into context.

    Checks for pending memory injections and formats them
    for the tutor.
    """

    name = "memory_injection"
    description = "Injects relevant memories into tutor context"
    priority = 5

    def should_run(self, context: SessionContext) -> bool:
        """Run when there are retrieved memories or pending injection"""
        return bool(context.pending_injection) or bool(context.retrieved_memories)

    def execute(self, context: SessionContext) -> Optional[str]:
        """Return pending injection or format memories"""
        # First check for synthesized injection
        if context.pending_injection:
            injection = context.clear_pending_injection()
            return injection

        # Otherwise format retrieved memories
        if context.retrieved_memories:
            memory_texts = []
            for mem_result in context.retrieved_memories[:5]:
                mem = mem_result.get("memory")
                if hasattr(mem, "text"):
                    memory_texts.append(f"- {mem.text}")
                elif isinstance(mem, dict):
                    memory_texts.append(f"- {mem.get('text', '')}")

            if memory_texts:
                context.retrieved_memories = []  # Clear after use
                return f"""Relevant context from previous sessions:

{chr(10).join(memory_texts)}

Use this naturally without explicitly mentioning past sessions."""

        return None


# Default skills to load
DEFAULT_SKILLS = [
    GreetingSkill,
    EmotionResponseSkill,
    MemoryInjectionSkill,
]

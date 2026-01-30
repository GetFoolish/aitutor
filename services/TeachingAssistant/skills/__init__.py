"""
Skills Module - Dynamic skill execution system
Based on v4 teaching-assistant branch implementation

Skills are triggered based on session context and can inject
instructions into the tutor's response.
"""

from .base import (
    Skill,
    GreetingSkill,
    EmotionResponseSkill,
    MemoryInjectionSkill,
    DEFAULT_SKILLS,
)

__all__ = [
    "Skill",
    "GreetingSkill",
    "EmotionResponseSkill",
    "MemoryInjectionSkill",
    "DEFAULT_SKILLS",
]

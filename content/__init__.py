"""
Content Generation Module

Generates personalized questions using:
- Local MongoDB (questions_unified) as reference
- Gemini API for generation
- Innocent Drinks tone
- User memory personalization
"""

from .question_generator import QuestionGenerator, GeneratedQuestion, DEFAULT_USER_MEMORIES
from .tone_guidelines import get_tone_prompt, rewrite_question_prompt, TONE_GUIDELINES

__all__ = [
    "QuestionGenerator",
    "GeneratedQuestion", 
    "DEFAULT_USER_MEMORIES",
    "get_tone_prompt",
    "rewrite_question_prompt",
    "TONE_GUIDELINES"
]

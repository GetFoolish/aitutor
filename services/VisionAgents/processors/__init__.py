"""
Vision Agents Processors for AI Tutor
Custom processors for emotion detection, voice activity, and engagement tracking.
"""

from .emotion_processor import EmotionProcessor
from .vad_processor import VADProcessor
from .engagement_processor import EngagementProcessor

__all__ = ["EmotionProcessor", "VADProcessor", "EngagementProcessor"]

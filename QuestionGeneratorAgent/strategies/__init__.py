"""
Question Generation Strategies Module
Contains different strategies for generating questions.
"""

from .base_strategy import BaseGenerationStrategy
from .simple_variation_strategy import SimpleVariationStrategy
from .image_question_strategy import ImageQuestionStrategy

__all__ = ['BaseGenerationStrategy', 'SimpleVariationStrategy', 'ImageQuestionStrategy']

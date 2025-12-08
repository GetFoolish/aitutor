"""
Question Generator Agent Module

A modular, OOP-based system for generating educational question variations.

Components:
- generator: Main QuestionBankGenerator class
- filters: Question filtering (e.g., ImageQuestionFilter)
- strategies: Generation strategies (e.g., SimpleVariationStrategy, ImageQuestionStrategy)
- storage: Database adapters (e.g., MongoDBStorage)
- validators: Answer validation (MathValidator, FactBasedValidator)
"""

# Main generator
from .generator import QuestionBankGenerator

# Filters
from .filters import BaseQuestionFilter, ImageQuestionFilter

# Strategies
from .strategies import (
    BaseGenerationStrategy,
    SimpleVariationStrategy,
    ImageQuestionStrategy
)
from .strategies.base_strategy import GenerationResult

# Storage
from .storage import BaseStorage, MongoDBStorage

# Validators (legacy support)
from .validators import SubjectValidator, MathValidator, FactBasedValidator, BaseValidator

# Legacy class (kept for backwards compatibility)
from .question_generator_agent import QuestionGeneratorAgent

__all__ = [
    # Main
    'QuestionBankGenerator',

    # Filters
    'BaseQuestionFilter',
    'ImageQuestionFilter',

    # Strategies
    'BaseGenerationStrategy',
    'GenerationResult',
    'SimpleVariationStrategy',
    'ImageQuestionStrategy',

    # Storage
    'BaseStorage',
    'MongoDBStorage',

    # Validators
    'SubjectValidator',
    'MathValidator',
    'FactBasedValidator',
    'BaseValidator',

    # Legacy
    'QuestionGeneratorAgent',
]

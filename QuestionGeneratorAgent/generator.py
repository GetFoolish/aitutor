"""
Question Bank Generator - Main Module

This module provides the main QuestionBankGenerator class that orchestrates
question generation using configurable strategies and filters.
"""

import os
import sys
import random
from typing import Dict, Any, Optional, List, Type
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .filters.base_filter import BaseQuestionFilter
from .filters.image_filter import ImageQuestionFilter
from .strategies.base_strategy import BaseGenerationStrategy, GenerationResult
from .strategies.simple_variation_strategy import SimpleVariationStrategy
from .strategies.image_question_strategy import ImageQuestionStrategy
from .logging_config import get_logger

logger = get_logger(__name__)


# Determine project root for config
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.json'


class QuestionBankGenerator:
    """
    Main class for generating question variations.

    This class provides a unified interface for:
    - Filtering questions (e.g., finding questions with images)
    - Generating variations using pluggable strategies
    - Storing results to MongoDB or files

    Usage:
        generator = QuestionBankGenerator()

        # Generate from local JSON files
        results = generator.generate_from_directory(
            directory="path/to/CurriculumBuilder",
            n=5,  # Generate 5 questions
            filter_type="image"  # Only from questions with images
        )

        # Or with custom strategy
        generator.set_strategy(MyCustomStrategy(llm_client))
        results = generator.generate(source_question)
    """

    def __init__(
        self,
        llm_client=None,
        strategy: Optional[BaseGenerationStrategy] = None,
        question_filter: Optional[BaseQuestionFilter] = None
    ):
        """
        Initialize the Question Bank Generator.

        Args:
            llm_client: LLM client for generation (optional, will create default)
            strategy: Generation strategy to use (optional, auto-selects based on question)
            question_filter: Filter for selecting questions (optional)
        """
        self.llm_client = llm_client
        self._strategy = strategy
        self._filter = question_filter
        self._strategies: Dict[str, BaseGenerationStrategy] = {}

        # Initialize LLM client if not provided
        if not self.llm_client:
            self._init_llm_client()

        # Register default strategies
        self._register_default_strategies()

    def _init_llm_client(self):
        """Initialize the default LLM client."""
        try:
            from LLMBase.llm_client import OpenRouterClient
            self.llm_client = OpenRouterClient(config_path=str(CONFIG_PATH))
        except ImportError:
            logger.warning("Could not import OpenRouterClient")
            self.llm_client = None

    def _register_default_strategies(self):
        """Register default generation strategies."""
        config = {'use_case': 'question_generator'}

        self._strategies['simple'] = SimpleVariationStrategy(
            llm_client=self.llm_client,
            config=config
        )
        self._strategies['image'] = ImageQuestionStrategy(
            llm_client=self.llm_client,
            config=config
        )

    def register_strategy(self, name: str, strategy: BaseGenerationStrategy):
        """
        Register a custom generation strategy.

        Args:
            name: Unique name for the strategy
            strategy: Strategy instance
        """
        self._strategies[name] = strategy

    def set_strategy(self, strategy: BaseGenerationStrategy):
        """Set the active generation strategy."""
        self._strategy = strategy

    def set_filter(self, question_filter: BaseQuestionFilter):
        """Set the question filter."""
        self._filter = question_filter

    def _auto_select_strategy(self, question: Dict[str, Any]) -> BaseGenerationStrategy:
        """
        Automatically select the best strategy for a question.

        Args:
            question: Question to analyze

        Returns:
            Most appropriate strategy
        """
        # Check if question has images
        if self._strategies['image'].supports_question_type(question):
            return self._strategies['image']

        # Default to simple variation
        return self._strategies['simple']

    def generate(self, source_question: Dict[str, Any], strategy_name: Optional[str] = None) -> GenerationResult:
        """
        Generate a new question from a source question.

        Args:
            source_question: Source question data
            strategy_name: Optional name of strategy to use

        Returns:
            GenerationResult with the generated question
        """
        # Select strategy
        if strategy_name and strategy_name in self._strategies:
            strategy = self._strategies[strategy_name]
        elif self._strategy:
            strategy = self._strategy
        else:
            strategy = self._auto_select_strategy(source_question)

        logger.info(f"Using strategy: {strategy.get_strategy_name()}")

        # Generate
        return strategy.generate(source_question)

    def generate_batch(
        self,
        source_questions: List[Dict[str, Any]],
        strategy_name: Optional[str] = None
    ) -> List[GenerationResult]:
        """
        Generate questions from multiple sources.

        Args:
            source_questions: List of source questions
            strategy_name: Optional strategy name

        Returns:
            List of GenerationResults
        """
        results = []
        for i, question in enumerate(source_questions):
            print(f"\nGenerating {i+1}/{len(source_questions)}...")
            result = self.generate(question, strategy_name)
            results.append(result)

            if result.success:
                logger.info("  Success!")
            else:
                logger.error(f"  Failed: {result.error_message}")

        return results

    def generate_from_directory(
        self,
        directory: str,
        n: int = 1,
        filter_type: str = "image",
        strategy_name: Optional[str] = None
    ) -> List[GenerationResult]:
        """
        Generate n questions from JSON files in a directory.

        Args:
            directory: Path to directory with JSON question files
            n: Number of questions to generate
            filter_type: Type of filter ("image", "all")
            strategy_name: Optional strategy name

        Returns:
            List of GenerationResults
        """
        directory = Path(directory)

        # Set up filter
        if filter_type == "image":
            self._filter = ImageQuestionFilter(require_question_images=True)
        else:
            self._filter = None

        # Load and filter questions
        if self._filter:
            questions = self._filter.filter_from_directory(directory)
            logger.info(f"Found {len(questions)} questions matching filter '{filter_type}'")
        else:
            questions = self._load_all_questions(directory)
            logger.info(f"Loaded {len(questions)} total questions")

        if not questions:
            logger.warning("No questions found!")
            return []

        # Select n random questions
        if len(questions) > n:
            selected = random.sample(questions, n)
        else:
            selected = questions

        logger.info(f"Selected {len(selected)} questions for generation")

        # Generate
        return self.generate_batch(selected, strategy_name)

    def _load_all_questions(self, directory: Path) -> List[Dict[str, Any]]:
        """Load all JSON questions from a directory."""
        import json

        questions = []
        for json_file in directory.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['_file_path'] = str(json_file)
                data['_file_name'] = json_file.name
                questions.append(data)
            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")

        return questions

    def filter_questions_with_images(self, directory: str) -> List[Dict[str, Any]]:
        """
        Filter questions that contain images from a directory.

        Args:
            directory: Path to directory with JSON files

        Returns:
            List of questions that contain images
        """
        image_filter = ImageQuestionFilter(require_question_images=True)
        return image_filter.filter_from_directory(Path(directory))

    def get_available_strategies(self) -> List[str]:
        """Get list of registered strategy names."""
        return list(self._strategies.keys())


# CLI interface for the generator
def main():
    """Command line interface for question generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate question variations from existing questions'
    )
    parser.add_argument(
        '-n', '--num',
        type=int,
        default=1,
        help='Number of questions to generate (default: 1)'
    )
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default=None,
        help='Directory containing source questions'
    )
    parser.add_argument(
        '-f', '--filter',
        type=str,
        choices=['image', 'all'],
        default='image',
        help='Filter type (default: image)'
    )
    parser.add_argument(
        '-s', '--strategy',
        type=str,
        choices=['simple', 'image', 'auto'],
        default='auto',
        help='Generation strategy (default: auto)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory for generated questions'
    )
    parser.add_argument(
        '--list-images',
        action='store_true',
        help='List questions with images and exit'
    )

    args = parser.parse_args()

    # Default directory
    if not args.directory:
        args.directory = str(PROJECT_ROOT / 'SherlockEDApi' / 'CurriculumBuilder')

    # Initialize generator
    generator = QuestionBankGenerator()

    # List mode
    if args.list_images:
        questions = generator.filter_questions_with_images(args.directory)
        print(f"\nFound {len(questions)} questions with images:\n")
        for q in questions[:20]:  # Show first 20
            content = q.get('question', {}).get('content', '')[:100]
            print(f"  - {q.get('_file_name', 'unknown')}")
            print(f"    {content}...")
            print()
        return

    # Generate mode
    print(f"\nQuestion Bank Generator")
    print(f"=" * 50)
    print(f"Directory: {args.directory}")
    print(f"Filter: {args.filter}")
    print(f"Strategy: {args.strategy}")
    print(f"Count: {args.num}")
    print()

    strategy = None if args.strategy == 'auto' else args.strategy
    results = generator.generate_from_directory(
        directory=args.directory,
        n=args.num,
        filter_type=args.filter,
        strategy_name=strategy
    )

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Generation Summary:")
    successful = sum(1 for r in results if r.success)
    print(f"  Successful: {successful}/{len(results)}")

    # Save to output if specified
    if args.output and successful > 0:
        import json
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, result in enumerate(results):
            if result.success:
                output_file = output_dir / f"generated_{i+1}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result.question, f, indent=2)
                print(f"  Saved: {output_file}")


if __name__ == "__main__":
    main()

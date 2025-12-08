#!/usr/bin/env python3
"""
Question Bank Generator - CLI Runner

This is the main entry point for the Question Bank Generator.
Run with -h for help on available options.

Usage Examples:
    # List all questions with images
    python run_generator.py --list-images

    # Generate 5 questions from image-based questions
    python run_generator.py -n 5 -f image

    # Generate with specific strategy
    python run_generator.py -n 3 -s simple

    # Save generated questions to directory
    python run_generator.py -n 5 -o ./generated_questions

    # Generate and save to MongoDB
    python run_generator.py -n 5 --mongodb
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from QuestionGeneratorAgent.generator import QuestionBankGenerator
from QuestionGeneratorAgent.filters.image_filter import ImageQuestionFilter
from QuestionGeneratorAgent.logging_config import get_logger, enable_debug, enable_info

logger = get_logger(__name__)


def setup_args():
    """Setup command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate question variations from existing questions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-images                    # List questions with images
  %(prog)s -n 5 -f image                    # Generate 5 from image questions
  %(prog)s -n 3 -s simple -o ./output       # Generate 3 with simple strategy
  %(prog)s -n 10 --mongodb                  # Generate and save to MongoDB
        """
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
        help='Directory containing source question JSON files'
    )

    parser.add_argument(
        '-f', '--filter',
        type=str,
        choices=['image', 'all'],
        default='image',
        help='Filter type for selecting source questions (default: image)'
    )

    parser.add_argument(
        '-s', '--strategy',
        type=str,
        choices=['simple', 'image', 'auto'],
        default='auto',
        help='Generation strategy to use (default: auto)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory for generated questions (JSON files)'
    )

    parser.add_argument(
        '--mongodb',
        action='store_true',
        help='Save generated questions to MongoDB'
    )

    parser.add_argument(
        '--mongodb-uri',
        type=str,
        default=None,
        help='MongoDB connection URI (default: from MONGODB_URI env)'
    )

    parser.add_argument(
        '--list-images',
        action='store_true',
        help='List questions with images and exit'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


def get_default_directory():
    """Get the default CurriculumBuilder directory."""
    project_root = Path(__file__).parent.parent
    return str(project_root / 'SherlockEDApi' / 'CurriculumBuilder')


def list_image_questions(directory: str, verbose: bool = False):
    """List all questions with images."""
    print(f"\nScanning directory: {directory}\n")

    image_filter = ImageQuestionFilter(require_question_images=True)
    questions = image_filter.filter_from_directory(Path(directory))

    print(f"Found {len(questions)} questions with images:\n")
    print("-" * 80)

    for i, q in enumerate(questions, 1):
        file_name = q.get('_file_name', 'unknown')
        content = q.get('question', {}).get('content', '')

        # Get image info
        image_info = image_filter.get_image_info(q)

        # Truncate content for display
        content_preview = content[:100].replace('\n', ' ')
        if len(content) > 100:
            content_preview += '...'

        print(f"{i:4}. {file_name}")
        print(f"      Images: {image_info['total_count']} (question: {len(image_info['question_images'])}, hints: {len(image_info['hint_images'])})")

        if verbose:
            print(f"      Content: {content_preview}")
            for img in image_info['question_images'][:2]:
                print(f"      - {img['widget_name']}: {img['alt'][:50]}...")

        print()

    print("-" * 80)
    print(f"Total: {len(questions)} questions with images")


def generate_questions(args):
    """Generate questions based on arguments."""
    directory = args.directory or get_default_directory()
    strategy = None if args.strategy == 'auto' else args.strategy

    print("\n" + "=" * 60)
    print("Question Bank Generator")
    print("=" * 60)
    print(f"Directory: {directory}")
    print(f"Filter: {args.filter}")
    print(f"Strategy: {args.strategy}")
    print(f"Count: {args.num}")
    print(f"Output: {args.output or 'None (display only)'}")
    print(f"MongoDB: {'Yes' if args.mongodb else 'No'}")
    print("=" * 60 + "\n")

    # Initialize generator
    generator = QuestionBankGenerator()

    # Generate
    results = generator.generate_from_directory(
        directory=directory,
        n=args.num,
        filter_type=args.filter,
        strategy_name=strategy
    )

    # Process results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\n" + "=" * 60)
    print("Generation Results")
    print("=" * 60)
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")

    # Show failures
    if failed and args.verbose:
        print("\nFailures:")
        for i, f in enumerate(failed, 1):
            print(f"  {i}. {f.error_message}")

    # Save to output directory
    if args.output and successful:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\nSaving to: {output_dir}")

        for i, result in enumerate(successful, 1):
            output_file = output_dir / f"generated_{timestamp}_{i}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result.question, f, indent=2, ensure_ascii=False)
            print(f"  Saved: {output_file.name}")

    # Save to MongoDB
    if args.mongodb and successful:
        asyncio.run(save_to_mongodb(successful, args))

    return results


async def save_to_mongodb(results, args):
    """Save generated questions to MongoDB."""
    from QuestionGeneratorAgent.storage.mongodb_storage import MongoDBStorage

    print("\nSaving to MongoDB...")

    uri = args.mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    storage = MongoDBStorage(connection_string=uri)

    try:
        await storage.connect()

        for i, result in enumerate(results, 1):
            try:
                # We need the source question ID - for now use a placeholder
                # In production, this should come from the generation process
                source_id = result.source_question_id or "unknown"

                question_id = await storage.save_generated_question(
                    question=result.question,
                    source_question_id=source_id,
                    generation_cost=result.generation_cost,
                    cost_breakdown=result.cost_breakdown,
                    tokens_used=result.tokens_used
                )
                print(f"  Saved question {i}: {question_id}")

            except Exception as e:
                print(f"  Error saving question {i}: {e}")

    finally:
        await storage.disconnect()


def main():
    """Main entry point."""
    args = setup_args()

    # Set logging level based on verbose flag
    if args.verbose:
        enable_debug()
        logger.info("Verbose mode enabled")
    else:
        enable_info()

    # List mode
    if args.list_images:
        directory = args.directory or get_default_directory()
        list_image_questions(directory, args.verbose)
        return

    # Generate mode
    generate_questions(args)


if __name__ == "__main__":
    main()

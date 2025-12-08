"""
Terminal script to regenerate questions with verbose output.
Shows all prompts sent to OpenRouter.
"""

import json
import sys
import io
import os
from pathlib import Path

# Fix Windows encoding for both stdout and stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Also set environment variable for subprocesses
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, str(Path(__file__).parent.parent))

from QuestionGeneratorAgent.rewrite_image_questions import ImageQuestionRewriter
from QuestionGeneratorAgent.question_regenerator import QuestionRegenerator

# Your API key
API_KEY = "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"


def load_question_file(file_path):
    """Load a question JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['_file_path'] = str(file_path)
    data['_file_name'] = file_path.name
    return data


def main():
    print("=" * 80)
    print("QUESTION REGENERATOR - TERMINAL MODE")
    print("=" * 80)

    # Load questions
    curriculum_dir = Path(__file__).parent.parent / "SherlockEDApi" / "CurriculumBuilder"
    rewriter = ImageQuestionRewriter(curriculum_dir)
    questions = rewriter.load_image_questions(limit=10)

    print(f"\nLoaded {len(questions)} questions with images")

    # Create regenerator with API enabled
    print("\n" + "-" * 80)
    print("INITIALIZING REGENERATOR")
    print("-" * 80)

    regenerator = QuestionRegenerator(API_KEY)
    regenerator.enable_apis()

    print("\nAPIs ENABLED - will show all prompts sent to OpenRouter")

    # Process first 3 questions
    for i, q in enumerate(questions[:3]):
        print("\n" + "=" * 80)
        print(f"QUESTION {i+1}: {q.file_path.name}")
        print(f"TYPE: {q.question_type}")
        print("=" * 80)

        # Load full question data
        data = load_question_file(q.file_path)

        # Show original
        print("\n[ORIGINAL CONTENT]:")
        content = data.get('question', {}).get('content', '')[:300]
        print(f"  {content}...")

        # Show images
        widgets = data.get('question', {}).get('widgets', {})
        print("\n[ORIGINAL IMAGES]:")
        for name, widget in widgets.items():
            if widget.get('type') == 'image':
                alt = widget.get('options', {}).get('alt', '')
                print(f"  - {name}: {alt}")

        # Regenerate
        print("\n" + "-" * 40)
        print("REGENERATING (sending to OpenRouter)...")
        print("-" * 40)

        result = regenerator.regenerate_question(data, target_difficulty="easier")

        if result:
            print("\n[NEW CONTENT]:")
            print(f"  {result.new_content[:500]}...")

            print("\n[NEW ANSWER]:")
            print(f"  {result.new_answer}")

            print("\n[CHANGES MADE]:")
            print(f"  {result.changes_made}")

            print("\n[NEW IMAGES]:")
            for img in result.new_images:
                # Show first 100 chars of URL (it's base64 so very long)
                url_preview = img['url'][:100] + "..." if len(img['url']) > 100 else img['url']
                print(f"  - {img['name']}: {img['alt']}")
                print(f"    URL: {url_preview}")
        else:
            print("  FAILED to regenerate")

        print("\n")

    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()

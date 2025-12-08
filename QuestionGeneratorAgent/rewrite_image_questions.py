"""
Rewrite Image Questions - Syncs question text with image alt text.

This script:
1. Reads questions that have images
2. Extracts alt text from images to understand what's shown
3. Rewrites the question content to match the image
4. Ensures answers are consistent with the image content
"""

import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from QuestionGeneratorAgent.logging_config import get_logger, enable_debug

logger = get_logger(__name__)


@dataclass
class ImageInfo:
    """Information extracted from an image widget."""
    widget_name: str
    alt_text: str
    url: str

    def describe(self) -> str:
        """Get clean description from alt text."""
        # Remove trailing "!" and extra spaces
        return self.alt_text.rstrip(' !').strip()


@dataclass
class QuestionAnalysis:
    """Analysis of a question with images."""
    file_path: Path
    original_content: str
    images: List[ImageInfo]
    answers: Dict[str, Any]  # widget_name -> answer value
    question_type: str  # 'counting', 'place_value', 'other'

    def get_image_context(self) -> str:
        """Combine all image alt texts for context."""
        descriptions = [img.describe() for img in self.images]
        return "; ".join(descriptions)


class ImageQuestionRewriter:
    """Rewrites questions to sync with image content."""

    def __init__(self, curriculum_dir: Path):
        self.curriculum_dir = curriculum_dir
        self.questions: List[QuestionAnalysis] = []

    def load_image_questions(self, limit: int = None) -> List[QuestionAnalysis]:
        """Load all questions that have images."""
        logger.info(f"Scanning {self.curriculum_dir} for image questions...")

        json_files = list(self.curriculum_dir.glob("*.json"))
        logger.debug(f"Found {len(json_files)} JSON files")

        count = 0
        for file_path in json_files:
            if limit and count >= limit:
                break

            try:
                analysis = self._analyze_question(file_path)
                if analysis and analysis.images:
                    self.questions.append(analysis)
                    count += 1
                    logger.debug(f"Loaded: {file_path.name} ({analysis.question_type})")
            except Exception as e:
                logger.warning(f"Error loading {file_path.name}: {e}")

        logger.info(f"Loaded {len(self.questions)} image questions")
        return self.questions

    def _analyze_question(self, file_path: Path) -> Optional[QuestionAnalysis]:
        """Analyze a question file and extract image info."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        question = data.get('question', {})
        content = question.get('content', '')
        widgets = question.get('widgets', {})

        # Extract images
        images = []
        for name, widget in widgets.items():
            if widget.get('type') == 'image':
                opts = widget.get('options', {})
                alt = opts.get('alt', '')
                url = opts.get('backgroundImage', {}).get('url', '')
                if alt:
                    images.append(ImageInfo(name, alt, url))

        if not images:
            return None

        # Extract answers
        answers = {}
        for name, widget in widgets.items():
            if widget.get('type') == 'numeric-input':
                ans_list = widget.get('options', {}).get('answers', [])
                for ans in ans_list:
                    if ans.get('status') == 'correct':
                        answers[name] = ans.get('value')
            elif widget.get('type') == 'radio':
                choices = widget.get('options', {}).get('choices', [])
                for choice in choices:
                    if choice.get('correct'):
                        answers[name] = choice.get('content', '')

        # Determine question type
        question_type = self._detect_question_type(images, content)

        return QuestionAnalysis(
            file_path=file_path,
            original_content=content,
            images=images,
            answers=answers,
            question_type=question_type
        )

    def _detect_question_type(self, images: List[ImageInfo], content: str) -> str:
        """Detect the type of question based on images and content."""
        image_text = " ".join(img.alt_text.lower() for img in images)

        if any(word in image_text for word in ['thousands', 'hundreds', 'tens', 'ones', 'block']):
            return 'place_value'
        elif any(word in image_text for word in ['group', 'seals', 'monkeys', 'sheep', 'birds', 'fish']):
            return 'counting'
        elif 'number line' in image_text:
            return 'number_line'
        elif 'graph' in image_text or 'chart' in image_text:
            return 'graph'
        else:
            return 'other'

    def rewrite_question(self, analysis: QuestionAnalysis) -> Dict[str, Any]:
        """Rewrite a question to sync with its images."""

        if analysis.question_type == 'place_value':
            return self._rewrite_place_value(analysis)
        elif analysis.question_type == 'counting':
            return self._rewrite_counting(analysis)
        else:
            return self._rewrite_generic(analysis)

    def _rewrite_place_value(self, analysis: QuestionAnalysis) -> Dict[str, Any]:
        """Rewrite a place value question."""
        # Parse the image alt text to extract block counts
        image_desc = analysis.get_image_context()

        # Extract numbers from alt text
        blocks = self._parse_place_value_blocks(image_desc)

        # Calculate expected answer
        expected = (
            blocks.get('thousands', 0) * 1000 +
            blocks.get('hundreds', 0) * 100 +
            blocks.get('tens', 0) * 10 +
            blocks.get('ones', 0)
        )

        # Build block description
        parts = []
        if blocks.get('thousands'):
            parts.append(f"{blocks['thousands']} thousands block{'s' if blocks['thousands'] > 1 else ''}")
        if blocks.get('hundreds'):
            parts.append(f"{blocks['hundreds']} hundreds block{'s' if blocks['hundreds'] > 1 else ''}")
        if blocks.get('tens'):
            parts.append(f"{blocks['tens']} tens block{'s' if blocks['tens'] > 1 else ''}")
        if blocks.get('ones'):
            parts.append(f"{blocks['ones']} ones block{'s' if blocks['ones'] > 1 else ''}")

        block_desc = ", ".join(parts[:-1]) + f", and {parts[-1]}" if len(parts) > 1 else parts[0] if parts else "blocks"

        # Generate new content
        new_content = f"""**Look at the place value blocks below.**

The image shows {block_desc}.

[[☃ image 1]]

**What number do these blocks represent?**

[[☃ numeric-input 2]]"""

        return {
            'original': analysis.original_content,
            'rewritten': new_content,
            'image_context': image_desc,
            'expected_answer': expected,
            'actual_answers': analysis.answers,
            'question_type': 'place_value',
            'blocks': blocks
        }

    def _parse_place_value_blocks(self, text: str) -> Dict[str, int]:
        """Parse block counts from alt text."""
        text = text.lower()
        blocks = {'thousands': 0, 'hundreds': 0, 'tens': 0, 'ones': 0}

        # Number word mapping
        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }

        # Pattern: "X thousands" or "X thousand"
        for place in ['thousands', 'hundreds', 'tens', 'ones']:
            singular = place.rstrip('s')
            # Try numeric pattern first
            pattern = rf'(\d+)\s*{singular}'
            match = re.search(pattern, text)
            if match:
                blocks[place] = int(match.group(1))
            else:
                # Try word pattern
                for word, num in word_to_num.items():
                    if f'{word} {singular}' in text or f'{word} {place}' in text:
                        blocks[place] = num
                        break

        return blocks

    def _rewrite_counting(self, analysis: QuestionAnalysis) -> Dict[str, Any]:
        """Rewrite a counting/grouping question."""
        image_desc = analysis.get_image_context()

        # Parse what's being counted
        count_info = self._parse_counting_info(image_desc)

        # Build the rewritten question
        item = count_info.get('item', 'items')
        per_group = count_info.get('per_group', 0)
        num_groups = len(analysis.images)
        total = per_group * num_groups

        # Create image placeholders
        image_placeholders = "\n\n".join([f"[[☃ {img.widget_name}]]" for img in analysis.images])

        new_content = f"""**Count the {item} shown in the images below.**

{image_placeholders}

Each group shows **{per_group} {item}**. There are **{num_groups} groups** in total.

How many {item} are in each group? [[☃ numeric-input 1]]

How many {item} are there in all? [[☃ numeric-input 2]]"""

        return {
            'original': analysis.original_content,
            'rewritten': new_content,
            'image_context': image_desc,
            'expected_answer': {'per_group': per_group, 'total': total},
            'actual_answers': analysis.answers,
            'question_type': 'counting',
            'count_info': count_info
        }

    def _parse_counting_info(self, text: str) -> Dict[str, Any]:
        """Parse counting information from alt text."""
        text_lower = text.lower()

        # Find the item being counted
        items = ['seals', 'monkeys', 'sheep', 'birds', 'fish', 'stars', 'apples', 'dogs', 'cats']
        found_item = 'items'
        for item in items:
            if item in text_lower:
                found_item = item
                break

        # Find the count per group
        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }

        count = 0
        # Try "group of X"
        match = re.search(r'group of (\w+)', text_lower)
        if match:
            num_str = match.group(1)
            if num_str.isdigit():
                count = int(num_str)
            elif num_str in word_to_num:
                count = word_to_num[num_str]

        return {'item': found_item, 'per_group': count}

    def _rewrite_generic(self, analysis: QuestionAnalysis) -> Dict[str, Any]:
        """Rewrite a generic question based on image context."""
        image_desc = analysis.get_image_context()

        # Create image placeholders
        image_placeholders = "\n\n".join([f"[[☃ {img.widget_name}]]" for img in analysis.images])

        # For generic questions, we just ensure the image reference is clear
        new_content = f"""**Study the image below carefully.**

{image_placeholders}

*Image shows: {image_desc}*

{analysis.original_content.split('[[')[0].strip()}"""

        return {
            'original': analysis.original_content,
            'rewritten': new_content,
            'image_context': image_desc,
            'actual_answers': analysis.answers,
            'question_type': 'generic'
        }


def main():
    """Main entry point - rewrite questions and show 10 samples."""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    enable_debug()

    curriculum_dir = Path(__file__).parent.parent / "SherlockEDApi" / "CurriculumBuilder"

    print("=" * 80)
    print("IMAGE QUESTION REWRITER")
    print("=" * 80)

    rewriter = ImageQuestionRewriter(curriculum_dir)
    questions = rewriter.load_image_questions(limit=50)

    print(f"\nLoaded {len(questions)} questions with images")
    print("\n" + "=" * 80)
    print("10 SAMPLE REWRITTEN QUESTIONS")
    print("=" * 80)

    samples = []
    for q in questions[:15]:  # Process more to get variety
        result = rewriter.rewrite_question(q)
        samples.append({
            'file': q.file_path.name,
            'type': q.question_type,
            'result': result
        })

    # Show 10 samples with variety
    shown = 0
    shown_types = set()

    for sample in samples:
        if shown >= 10:
            break

        # Try to show variety
        q_type = sample['type']

        print(f"\n{'-' * 80}")
        print(f"SAMPLE {shown + 1}: {sample['file']} ({q_type})")
        print(f"{'-' * 80}")

        result = sample['result']

        print("\n[IMAGE CONTEXT]:")
        print(f"   {result['image_context'][:200]}...")

        print("\n[ORIGINAL QUESTION]:")
        orig = result['original'].replace('\n', '\n   ')
        print(f"   {orig[:300]}...")

        print("\n[REWRITTEN QUESTION]:")
        rewritten = result['rewritten'].replace('\n', '\n   ')
        print(f"   {rewritten}")

        print("\n[ANSWERS]:")
        if 'expected_answer' in result:
            print(f"   Expected: {result['expected_answer']}")
        print(f"   Actual: {result['actual_answers']}")

        shown += 1
        shown_types.add(q_type)

    print("\n" + "=" * 80)
    print(f"Showed {shown} samples covering types: {shown_types}")
    print("=" * 80)


if __name__ == "__main__":
    main()

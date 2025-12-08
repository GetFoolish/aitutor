"""
Image Question Strategy for Question Generation

Handles questions that contain images, preserving image references
while generating new mathematical or contextual variations.
"""

import re
import json
import copy
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

from .base_strategy import BaseGenerationStrategy, GenerationResult

# Import logger
import sys
import os as os_module
sys.path.insert(0, os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__))))
from logging_config import get_logger

logger = get_logger(__name__)


class ImageQuestionStrategy(BaseGenerationStrategy):
    """
    Strategy for generating variations of questions that contain images.

    This strategy:
    1. Preserves all image widgets and references
    2. Generates new question text that references the same images
    3. Creates new numerical answers based on image descriptions
    4. Updates hints to match the new question

    Best for:
    - Counting questions with visual groups
    - Geometry questions with diagrams
    - Word problems with illustrations
    """

    def __init__(self, llm_client=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(llm_client, config)
        self.use_case = config.get('use_case', 'question_generator') if config else 'question_generator'
        logger.debug(f'ImageQuestionStrategy use_case: {self.use_case}')

    def supports_question_type(self, question: Dict[str, Any]) -> bool:
        """Check if question contains images."""
        widgets = self._extract_widgets(question)
        for widget_data in widgets.values():
            if widget_data.get('type') == 'image':
                return True
            options = widget_data.get('options', {})
            if 'backgroundImage' in options:
                return True
        return False

    def generate(self, source_question: Dict[str, Any]) -> GenerationResult:
        """Generate a variation preserving images."""
        source_file = source_question.get('_file_name', 'unknown')
        logger.info(f'Generating image-based variation for: {source_file}')
        try:
            # Extract image information
            image_info = self._extract_image_info(source_question)

            if not image_info['images']:
                return GenerationResult(
                    success=False,
                    error_message="No images found in source question"
                )

            # Extract question content and answers
            content = self._extract_content(source_question)
            answers = self._get_correct_answers(source_question)
            hints = source_question.get('hints', [])

            # Build prompt with image context
            prompt = self._build_generation_prompt(content, answers, image_info, hints)
            system_prompt = self._get_system_prompt()

            if not self.llm_client:
                return GenerationResult(
                    success=False,
                    error_message="LLM client not configured"
                )

            response = self.llm_client.generate(prompt, self.use_case, system_prompt)

            # Parse response
            generated_data = self._parse_llm_response(response)

            if not generated_data:
                return GenerationResult(
                    success=False,
                    error_message="Failed to parse LLM response"
                )

            # Build new question preserving images
            new_question = self._build_question_document(source_question, generated_data, image_info)

            # Validate
            is_valid, error = self.validate(new_question)
            if not is_valid:
                return GenerationResult(
                    success=False,
                    error_message=f"Validation failed: {error}"
                )

            return GenerationResult(
                success=True,
                question=new_question,
                generated_at=datetime.now(),
                source_question_id=source_question.get('_file_name', 'unknown')
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=f"Generation error: {str(e)}"
            )

    def validate(self, generated_question: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate generated question with images."""
        # Basic structure validation
        if 'question' not in generated_question:
            return False, "Missing 'question' field"

        question = generated_question['question']
        widgets = question.get('widgets', {})

        # Verify images are preserved
        has_images = False
        for widget_data in widgets.values():
            if widget_data.get('type') == 'image':
                has_images = True
                break

        if not has_images:
            return False, "Images were not preserved in generated question"

        # Check answer widgets
        answer_widgets = self._get_answer_widgets(generated_question)
        if not answer_widgets:
            return False, "No answer widgets found"

        # Verify answers have values
        for widget_name, widget_data in answer_widgets.items():
            if widget_data.get('type') == 'numeric-input':
                answers = widget_data.get('options', {}).get('answers', [])
                has_correct = any(
                    a.get('status') == 'correct' and a.get('value') is not None
                    for a in answers
                )
                if not has_correct:
                    return False, f"Widget {widget_name} has no correct answer"

        return True, ""

    def _extract_image_info(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed image information from question."""
        result = {
            'images': [],
            'image_count': 0,
            'image_descriptions': []
        }

        # Process question widgets
        widgets = self._extract_widgets(question)
        for widget_name, widget_data in widgets.items():
            if widget_data.get('type') == 'image':
                options = widget_data.get('options', {})
                image_entry = {
                    'widget_name': widget_name,
                    'alt': options.get('alt', ''),
                    'url': options.get('backgroundImage', {}).get('url', ''),
                    'width': options.get('backgroundImage', {}).get('width'),
                    'height': options.get('backgroundImage', {}).get('height')
                }
                result['images'].append(image_entry)
                if image_entry['alt']:
                    result['image_descriptions'].append(image_entry['alt'])

        result['image_count'] = len(result['images'])
        return result

    def _get_system_prompt(self) -> str:
        return """You are an expert educational content creator specializing in visual math problems.
Your task is to create variations of questions that use images while:
1. Keeping references to the SAME images (they cannot be changed)
2. Creating new questions that make sense with the existing images
3. Ensuring mathematical accuracy
4. Maintaining the same difficulty level

The images show specific objects that you must reference correctly.
IMPORTANT: Respond with valid JSON only. No markdown, no explanations outside JSON."""

    def _build_generation_prompt(self, content: str, answers: Dict[str, Any],
                                  image_info: Dict[str, Any], hints: List[Dict]) -> str:
        # Build image descriptions
        image_desc = "\n".join([
            f"- {img['widget_name']}: {img['alt']}"
            for img in image_info['images']
        ])

        # Clean content
        clean_content = re.sub(r'\[\[☃ image \d+\]\]', '[IMAGE]', content)
        clean_content = re.sub(r'\[\[☃ numeric-input \d+\]\]', '[ANSWER]', clean_content)

        answers_str = json.dumps(answers, indent=2)

        # Count images for context
        num_images = image_info['image_count']

        prompt = f"""Create a variation of this image-based math question.

AVAILABLE IMAGES (these cannot be changed):
{image_desc}

Number of image groups shown: {num_images}

ORIGINAL QUESTION:
{clean_content}

ORIGINAL ANSWERS:
{answers_str}

Requirements:
1. The question MUST reference the same {num_images} images
2. Create a different but related question using these images
3. The new question should ask about the same objects shown
4. Ensure answers are mathematically correct based on the images
5. Keep all image references in order (image 1, image 2, etc.)

Respond with ONLY valid JSON:
{{
    "new_content": "New question text using [IMAGE] for images and [ANSWER] for answer blanks",
    "new_answers": {{
        "numeric-input 1": <correct_number>,
        "numeric-input 2": <correct_number>
    }},
    "reasoning": "How the answers relate to the images",
    "new_hints": [
        {{"content": "First hint text", "images": {{}}, "widgets": {{}}}},
        {{"content": "Second hint text", "images": {{}}, "widgets": {{}}}}
    ]
}}

Note: For counting questions, if there are {num_images} groups and each shows N items, consider:
- How many groups? ({num_images})
- Items per group? (from image descriptions)
- Total items? (groups × items_per_group)"""

        return prompt

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            return None

    def _build_question_document(self, source: Dict[str, Any], generated: Dict[str, Any],
                                  image_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build question document preserving all images."""
        new_doc = copy.deepcopy(source)

        # Update content with new text but preserve widget references
        new_content = generated.get('new_content', '')
        if new_content:
            new_doc['question']['content'] = self._restore_all_placeholders(
                new_content,
                source.get('question', {}).get('content', ''),
                image_info['image_count']
            )

        # Update answers
        new_answers = generated.get('new_answers', {})
        widgets = new_doc.get('question', {}).get('widgets', {})

        for widget_name, new_value in new_answers.items():
            if widget_name in widgets:
                widget = widgets[widget_name]
                if widget.get('type') == 'numeric-input':
                    answers = widget.get('options', {}).get('answers', [])
                    for ans in answers:
                        if ans.get('status') == 'correct':
                            ans['value'] = new_value

        # Update hints if provided
        if 'new_hints' in generated and generated['new_hints']:
            # Keep original hint structure but update content
            original_hints = source.get('hints', [])
            new_hints = generated['new_hints']

            for i, new_hint in enumerate(new_hints):
                if i < len(original_hints):
                    # Preserve original widget structure
                    new_doc['hints'][i]['content'] = new_hint.get('content', '')
                else:
                    # Add new hint
                    new_doc['hints'].append({
                        'content': new_hint.get('content', ''),
                        'images': {},
                        'replace': False,
                        'widgets': {}
                    })

        # Clean up internal fields
        new_doc.pop('_file_path', None)
        new_doc.pop('_file_name', None)

        return new_doc

    def _restore_all_placeholders(self, new_content: str, original_content: str,
                                   image_count: int) -> str:
        """Restore all widget placeholders (images and inputs)."""
        result = new_content

        # Restore image placeholders
        for i in range(1, image_count + 1):
            placeholder = f'[[☃ image {i}]]'
            result = result.replace('[IMAGE]', placeholder, 1)

        # Find and restore numeric-input placeholders
        input_widgets = re.findall(r'\[\[☃ numeric-input \d+\]\]', original_content)
        for widget in input_widgets:
            result = result.replace('[ANSWER]', widget, 1)

        return result

"""
Simple Variation Strategy for Question Generation

Generates variations of math questions by changing numbers while
preserving the mathematical structure and relationships.
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


class SimpleVariationStrategy(BaseGenerationStrategy):
    """
    Strategy that generates variations by asking LLM to create
    mathematically similar questions with different numbers.

    Best for:
    - Arithmetic questions (addition, subtraction, multiplication, division)
    - Simple algebra questions
    - Word problems with numerical answers
    """

    def __init__(self, llm_client=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(llm_client, config)
        self.use_case = config.get('use_case', 'question_generator') if config else 'question_generator'
        logger.debug(f'SimpleVariationStrategy use_case: {self.use_case}')

    def supports_question_type(self, question: Dict[str, Any]) -> bool:
        """Check if question is suitable for simple variation."""
        answer_widgets = self._get_answer_widgets(question)

        # Best suited for numeric-input questions
        for widget_data in answer_widgets.values():
            if widget_data.get('type') == 'numeric-input':
                return True
        return False

    def generate(self, source_question: Dict[str, Any]) -> GenerationResult:
        """Generate a variation of the source question."""
        source_file = source_question.get('_file_name', 'unknown')
        logger.info(f'Generating variation for: {source_file}')
        try:
            # Extract key information
            content = self._extract_content(source_question)
            answers = self._get_correct_answers(source_question)
            hints = source_question.get('hints', [])

            # Build prompt for LLM
            prompt = self._build_generation_prompt(content, answers, hints)
            system_prompt = self._get_system_prompt()

            # Generate using LLM
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

            # Build the new question in Perseus format
            new_question = self._build_question_document(source_question, generated_data)

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
        """Validate the generated question structure."""
        # Check required fields
        if 'question' not in generated_question:
            return False, "Missing 'question' field"

        question = generated_question['question']

        if 'content' not in question:
            return False, "Missing 'content' in question"

        if 'widgets' not in question:
            return False, "Missing 'widgets' in question"

        # Check for answer widgets
        answer_widgets = self._get_answer_widgets(generated_question)
        if not answer_widgets:
            return False, "No answer widgets found"

        # Check that answers have values
        for widget_name, widget_data in answer_widgets.items():
            if widget_data.get('type') == 'numeric-input':
                answers = widget_data.get('options', {}).get('answers', [])
                has_correct = any(a.get('status') == 'correct' and a.get('value') is not None for a in answers)
                if not has_correct:
                    return False, f"Widget {widget_name} has no correct answer"

        return True, ""

    def _get_system_prompt(self) -> str:
        return """You are an expert educational content creator specializing in mathematics.
Your task is to create variations of math questions while:
1. Maintaining the same mathematical concept and operation
2. Using different numbers that result in clean, whole-number answers when possible
3. Keeping the same difficulty level
4. Preserving the question structure and format

IMPORTANT: You must respond with valid JSON only. No markdown, no explanations outside JSON."""

    def _build_generation_prompt(self, content: str, answers: Dict[str, Any], hints: List[Dict]) -> str:
        # Clean content for display (remove widget placeholders for readability)
        clean_content = re.sub(r'\[\[☃ [^\]]+\]\]', '[BLANK]', content)

        answers_str = json.dumps(answers, indent=2)

        prompt = f"""Create a variation of this math question:

ORIGINAL QUESTION:
{clean_content}

ORIGINAL ANSWERS:
{answers_str}

Requirements:
1. Keep the same mathematical concept and operations
2. Use DIFFERENT numbers than the original
3. Ensure all answers are mathematically correct
4. Keep similar difficulty level

Respond with ONLY valid JSON in this exact format:
{{
    "new_content": "The new question text with [BLANK] for answer inputs",
    "new_answers": {{
        "numeric-input 1": <number>,
        "numeric-input 2": <number>
    }},
    "explanation": "Brief description of what was changed"
}}

If the original has numeric-input 1, numeric-input 2, etc., include all of them in new_answers with their correct numerical values."""

        return prompt

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM response to extract generated question data."""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            return None

    def _build_question_document(self, source: Dict[str, Any], generated: Dict[str, Any]) -> Dict[str, Any]:
        """Build a complete question document from generated data."""
        # Deep copy the source to preserve structure
        new_doc = copy.deepcopy(source)

        # Update content
        new_content = generated.get('new_content', '')
        if new_content:
            # Restore widget placeholders in content
            original_content = source.get('question', {}).get('content', '')
            new_doc['question']['content'] = self._restore_widget_placeholders(
                new_content, original_content
            )

        # Update answers in widgets
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
        if 'new_hints' in generated:
            new_doc['hints'] = generated['new_hints']

        # Remove internal fields
        new_doc.pop('_file_path', None)
        new_doc.pop('_file_name', None)

        return new_doc

    def _restore_widget_placeholders(self, new_content: str, original_content: str) -> str:
        """Restore widget placeholders from original content."""
        # Find all widget references in original
        widgets = re.findall(r'\[\[☃ [^\]]+\]\]', original_content)

        # Replace [BLANK] placeholders with widget references
        result = new_content
        blank_count = 0

        for widget in widgets:
            if '[BLANK]' in result and blank_count < result.count('[BLANK]'):
                result = result.replace('[BLANK]', widget, 1)
                blank_count += 1

        return result

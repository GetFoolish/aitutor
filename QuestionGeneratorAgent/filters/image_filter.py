"""
Image Question Filter
Filters questions that contain images in their content, hints, or widgets.
"""

from typing import List, Dict, Any
from pathlib import Path
from .base_filter import BaseQuestionFilter

# Import logger
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import get_logger

logger = get_logger(__name__)


class ImageQuestionFilter(BaseQuestionFilter):
    """
    Filter that identifies questions containing images.

    Looks for images in:
    - question.widgets (widgets with type="image")
    - question.content (references like [[☃ image X]])
    - hints[].widgets (image widgets in hints)
    - hints[].content (image references in hints)
    - backgroundImage fields
    """

    def __init__(self, require_question_images: bool = True, include_hint_images: bool = True):
        """
        Args:
            require_question_images: If True, only match questions with images in the main question
            include_hint_images: If True, also consider images in hints when matching
        """
        self.require_question_images = require_question_images
        self.include_hint_images = include_hint_images
        logger.debug(
            "ImageQuestionFilter initialized",
            require_question_images=require_question_images,
            include_hint_images=include_hint_images
        )

    def filter(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter list of questions to those containing images."""
        logger.info(f"Filtering {len(questions)} questions for images")
        with logger.timer("filter_questions"):
            result = [q for q in questions if self.matches(q)]
        logger.info(f"Found {len(result)} questions with images ({len(result)}/{len(questions)})")
        return result

    def filter_from_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """Load and filter questions from a directory of JSON files."""
        import json
        directory = Path(directory)
        logger.info(f"Scanning directory: {directory}")
        filtered_questions = []
        total_files = 0
        errors = 0

        with logger.timer("scan_directory"):
            json_files = list(directory.glob("*.json"))
            total_files = len(json_files)
            logger.debug(f"Found {total_files} JSON files")

            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        question_data = json.load(f)
                    if self.matches(question_data):
                        question_data["_file_path"] = str(json_file)
                        question_data["_file_name"] = json_file.name
                        filtered_questions.append(question_data)
                        logger.debug(f"MATCH: {json_file.name}")
                except (json.JSONDecodeError, IOError) as e:
                    errors += 1
                    logger.warning(f"Error reading {json_file.name}: {e}")
                    continue

        logger.info(
            f"Directory scan complete",
            total_files=total_files,
            matches=len(filtered_questions),
            errors=errors
        )
        return filtered_questions

    def matches(self, question: Dict[str, Any]) -> bool:
        """Check if question contains images."""
        file_name = question.get("_file_name", "unknown")
        has_question_images = self._check_question_images(question)
        has_hint_images = self._check_hint_images(question) if self.include_hint_images else False

        logger.debug(
            f"Checking question",
            file=file_name,
            question_images=has_question_images,
            hint_images=has_hint_images
        )

        if self.require_question_images:
            return has_question_images
        return has_question_images or has_hint_images

    def _check_question_images(self, question_data: Dict[str, Any]) -> bool:
        """Check if the main question section contains images."""
        question = question_data.get("question", {})
        has_images = self._has_images_in_section(question)
        if has_images:
            logger.debug("Found images in question section")
        return has_images

    def _check_hint_images(self, question_data: Dict[str, Any]) -> bool:
        """Check if any hints contain images."""
        hints = question_data.get("hints", [])
        if not hints:
            return False
        for i, hint in enumerate(hints):
            if self._has_images_in_section(hint):
                logger.debug(f"Found images in hint {i}")
                return True
        return False

    def _has_images_in_section(self, section: Dict[str, Any]) -> bool:
        """Check if a section (question or hint) contains images."""
        # Check widgets for image type
        widgets = section.get("widgets", {})
        for widget_name, widget_data in widgets.items():
            if self._is_image_widget(widget_data):
                logger.debug(f"Found image widget: {widget_name}")
                return True

        # Check content for image references
        content = section.get("content", "")
        if self._has_image_reference(content):
            logger.debug("Found image reference in content")
            return True

        # Check for direct images field with data
        images = section.get("images", {})
        if images and len(images) > 0:
            logger.debug(f"Found {len(images)} direct images")
            return True

        return False

    def _is_image_widget(self, widget: Dict[str, Any]) -> bool:
        """Check if a widget is an image widget."""
        if not isinstance(widget, dict):
            return False

        # Check widget type
        if widget.get("type") == "image":
            return True

        # Check for backgroundImage in options
        options = widget.get("options", {})
        if isinstance(options, dict):
            if "backgroundImage" in options:
                bg_image = options["backgroundImage"]
                if isinstance(bg_image, dict) and bg_image.get("url"):
                    return True

        return False

    def _has_image_reference(self, content: str) -> bool:
        """Check if content string contains image references."""
        if not content:
            return False
        # Khan Academy Perseus format: [[☃ image X]]
        return "[[☃ image" in content or "[[☃ image-" in content

    def get_image_info(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract detailed information about images in a question.

        Returns:
            Dictionary with:
            - question_images: List of image widgets in question
            - hint_images: List of image widgets in hints
            - total_count: Total number of images
        """
        logger.debug("Extracting image info from question")
        result = {
            "question_images": [],
            "hint_images": [],
            "total_count": 0
        }

        # Extract question images
        question = question_data.get("question", {})
        result["question_images"] = self._extract_images_from_section(question)

        # Extract hint images
        hints = question_data.get("hints", [])
        for hint in hints:
            result["hint_images"].extend(self._extract_images_from_section(hint))

        result["total_count"] = len(result["question_images"]) + len(result["hint_images"])

        logger.debug(
            f"Image info extracted",
            question_images=len(result["question_images"]),
            hint_images=len(result["hint_images"]),
            total=result["total_count"]
        )
        return result

    def _extract_images_from_section(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image information from a section."""
        images = []
        widgets = section.get("widgets", {})

        for widget_name, widget_data in widgets.items():
            if self._is_image_widget(widget_data):
                image_info = {
                    "widget_name": widget_name,
                    "type": widget_data.get("type"),
                    "alt": widget_data.get("options", {}).get("alt", ""),
                    "url": None
                }

                # Extract URL
                options = widget_data.get("options", {})
                bg_image = options.get("backgroundImage", {})
                if isinstance(bg_image, dict):
                    image_info["url"] = bg_image.get("url")
                    image_info["width"] = bg_image.get("width")
                    image_info["height"] = bg_image.get("height")

                images.append(image_info)
                alt_text = image_info["alt"][:50] if image_info["alt"] else "N/A"
                logger.debug(f"Extracted image", widget=widget_name, alt=alt_text)

        return images

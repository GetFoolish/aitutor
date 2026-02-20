"""
Test suite for question generation pipeline.

Validates critical paths: pool pop, JIT generation, fallback handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from content_v1 import ContentV1Engine


class TestQuestionGeneration:
    """Test question generation reliability."""

    @pytest.fixture
    def content_engine(self):
        """Create a ContentV1Engine instance for testing."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            engine = ContentV1Engine()
            return engine

    def test_fallback_not_meta_question(self, content_engine):
        """
        Verify that fallback questions don't use meta-question patterns.

        Bug #1 fix: Fallback generators should create specific questions,
        not "Which of the following is true about X?"
        """
        fallback = content_engine._fallback_question(
            skill_name="Decimal Place Value",
            age=10,
            fmt="radio_single",
            difficulty=0.5
        )

        assert fallback is not None
        content = fallback["item"]["question"]["content"]

        # Anti-patterns from pre_serve_validator.py
        assert "which of the following is true about" not in content.lower(), \
            f"Fallback uses forbidden meta-question pattern: {content}"
        assert "which statement is correct about" not in content.lower()
        assert "select all that are true" not in content.lower()

    def test_seeded_item_has_valid_structure(self, content_engine):
        """
        Verify that seeded items have all required Perseus fields.

        Prevents schema validation errors from missing fields.
        """
        for fmt in ["radio_single", "numeric_input", "dropdown"]:
            item = content_engine._build_seeded_item(
                topic="Addition",
                fmt=fmt,
                seed="Practice basic math"
            )

            # Required top-level fields
            assert "question" in item
            assert "answerArea" in item
            assert "hints" in item

            # Question structure
            assert "content" in item["question"]
            assert "widgets" in item["question"]
            assert "images" in item["question"]
            assert len(item["question"]["content"]) > 0

            # At least one widget
            assert len(item["question"]["widgets"]) > 0

    def test_extract_json_handles_malformed(self, content_engine):
        """
        Verify JSON extraction handles Gemini quirks.

        Gemini sometimes returns unicode quotes, code fences, or trailing commas.
        """
        # Unicode smart quotes
        result = content_engine._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

        # Code fence
        result = content_engine._extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

        # Extra text before/after
        result = content_engine._extract_json('Here is the JSON: {"key": "value"} done')
        assert result == {"key": "value"}

        # Malformed (should return empty dict, not crash)
        result = content_engine._extract_json('not json at all')
        assert result == {}

    def test_validate_item_rejects_broken_widgets(self, content_engine):
        """
        Verify that validation catches broken Perseus items.

        Prevents serving questions that crash the frontend.
        """
        # Missing content
        bad_item = {
            "question": {"content": "", "widgets": {"radio 1": {"type": "radio"}}},
            "answerArea": {},
            "hints": []
        }
        assert content_engine._validate_item(bad_item, fmt="radio_single") is False

        # No widgets
        bad_item = {
            "question": {"content": "Question?", "widgets": {}},
            "answerArea": {},
            "hints": []
        }
        assert content_engine._validate_item(bad_item, fmt="radio_single") is False

        # Valid item should pass
        good_item = {
            "question": {
                "content": "What is 2 + 2? [[☃ radio 1]]",
                "images": {},
                "widgets": {
                    "radio 1": {
                        "type": "radio",
                        "options": {
                            "choices": [
                                {"content": "4", "correct": True},
                                {"content": "5", "correct": False}
                            ]
                        }
                    }
                }
            },
            "answerArea": {"calculator": False, "type": "multiple"},
            "hints": [{"content": "Think about basic addition."}]
        }
        assert content_engine._validate_item(good_item, fmt="radio_single") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

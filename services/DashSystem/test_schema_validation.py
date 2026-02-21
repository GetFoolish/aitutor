"""
Test suite for MongoDB schema validation.

Validates that Pydantic models catch malformed data.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from services.DashSystem.models.question_schemas import (
    PerseusItem,
    PerseusQuestion,
    PerseusWidget,
    QuestionDocument,
    ContentPoolDocument,
    validate_perseus_item,
    safe_get_perseus_item,
)


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_valid_perseus_item_passes(self):
        """Valid Perseus item should validate successfully."""
        valid_item = {
            "question": {
                "content": "What is 2 + 2?",
                "images": {},
                "widgets": {
                    "radio 1": {
                        "type": "radio",
                        "graded": True,
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
            "hints": [
                {"content": "Think about basic addition.", "images": {}, "widgets": {}}
            ]
        }

        # Should not raise
        validated = validate_perseus_item(valid_item)
        assert validated.question.content == "What is 2 + 2?"
        assert len(validated.question.widgets) == 1

    def test_empty_content_rejected(self):
        """Empty question content should fail validation."""
        bad_item = {
            "question": {
                "content": "",  # Empty!
                "images": {},
                "widgets": {"radio 1": {"type": "radio"}}
            },
            "answerArea": {},
            "hints": []
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_perseus_item(bad_item)

        assert "content" in str(exc_info.value).lower()

    def test_no_widgets_rejected(self):
        """Question without widgets should fail validation."""
        bad_item = {
            "question": {
                "content": "Question?",
                "images": {},
                "widgets": {}  # No widgets!
            },
            "answerArea": {},
            "hints": []
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_perseus_item(bad_item)

        assert "widget" in str(exc_info.value).lower()

    def test_short_hint_rejected(self):
        """Hints shorter than 10 chars should fail validation."""
        bad_item = {
            "question": {
                "content": "What is X?",
                "images": {},
                "widgets": {"radio 1": {"type": "radio"}}
            },
            "answerArea": {},
            "hints": [{"content": "Try"}]  # Too short!
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_perseus_item(bad_item)

        assert "hint" in str(exc_info.value).lower() or "too short" in str(exc_info.value).lower()

    def test_question_document_structure(self):
        """Validate QuestionDocument schema."""
        doc = {
            "question_id": "q123",
            "skill_id": "skill_abc",
            "skill_name": "Addition",
            "item": {
                "question": {
                    "content": "What is 1 + 1?",
                    "images": {},
                    "widgets": {"radio 1": {"type": "radio"}}
                },
                "answerArea": {},
                "hints": []
            },
            "difficulty": 0.5,
            "format": "radio_single",
            "created_at": datetime.utcnow(),
            "content_hash": "abc123hash"
        }

        validated = QuestionDocument.model_validate(doc)
        assert validated.question_id == "q123"
        assert validated.difficulty == 0.5

    def test_invalid_difficulty_rejected(self):
        """Difficulty outside [0, 1] should fail."""
        doc = {
            "question_id": "q123",
            "skill_id": "skill_abc",
            "skill_name": "Addition",
            "item": {
                "question": {
                    "content": "Question?",
                    "images": {},
                    "widgets": {"radio 1": {"type": "radio"}}
                },
                "answerArea": {},
                "hints": []
            },
            "difficulty": 1.5,  # Invalid!
            "format": "radio_single",
            "created_at": datetime.utcnow()
        }

        with pytest.raises(ValidationError):
            QuestionDocument.model_validate(doc)

    def test_safe_get_returns_none_on_invalid(self):
        """safe_get_perseus_item should return None instead of raising."""
        bad_item = {
            "question": {
                "content": "",  # Invalid
                "widgets": {}
            }
        }

        result = safe_get_perseus_item(bad_item)
        assert result is None  # Should not raise

    def test_content_pool_document_schema(self):
        """Validate ContentPoolDocument schema."""
        doc = {
            "question_id": "pool_q1",
            "skill_id": "skill_123",
            "difficulty_bucket": "medium",
            "item": {
                "question": {
                    "content": "Question?",
                    "images": {},
                    "widgets": {"radio 1": {"type": "radio"}}
                },
                "answerArea": {},
                "hints": []
            },
            "seed": "abc123seed",
            "format": "radio_single",
            "created_at": datetime.utcnow(),
            "content_hash": "hash123",
            "verified": True,
            "assessment_verified": False
        }

        validated = ContentPoolDocument.model_validate(doc)
        assert validated.difficulty_bucket == "medium"
        assert validated.verified is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

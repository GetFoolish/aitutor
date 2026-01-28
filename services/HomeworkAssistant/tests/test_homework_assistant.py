"""
Unit tests for HomeworkAssistant
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.HomeworkAssistant.homework_assistant import HomeworkAssistant


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB connection"""
    mock_db = Mock()
    mock_db.db = Mock()
    mock_db.db.__getitem__ = Mock(return_value=Mock())
    return mock_db


@pytest.fixture
def homework_assistant(mock_mongo_db):
    """Create HomeworkAssistant instance with mocked DB"""
    assistant = HomeworkAssistant(mock_mongo_db)
    assistant.homework_collection = Mock()
    return assistant


class TestAskQuestion:
    """Tests for ask_question method"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_ask_question_success(self, mock_genai, homework_assistant):
        """Test successful question answering"""
        # Mock homework document
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Math worksheet:\nPROBLEM 1: 2+2=?",
            "conversation_history": []
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Great question! Let's work through 2+2 step by step..."
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="How do I solve problem 1?"
        )

        # Verify result
        assert "response" in result
        assert result["homework_id"] == "hw123"
        assert "timestamp" in result
        assert "Great question!" in result["response"]

        # Verify conversation was saved
        assert homework_assistant.homework_collection.update_one.called

    def test_ask_question_homework_not_found(self, homework_assistant):
        """Test asking question about non-existent homework"""
        homework_assistant.homework_collection.find_one.return_value = None

        result = homework_assistant.ask_question(
            homework_id="nonexistent",
            user_id="user123",
            question="What is this?"
        )

        assert "error" in result
        assert "not found" in result["error"]

    def test_ask_question_wrong_user(self, homework_assistant):
        """Test asking question about homework belonging to different user"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "different_user",
            "extracted_text": "Content"
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="What is this?"
        )

        assert "error" in result
        assert "not found" in result["error"]

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_ask_question_with_conversation_history(self, mock_genai, homework_assistant):
        """Test question answering with existing conversation history"""
        # Mock homework with conversation history
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Math problems",
            "conversation_history": [
                {"role": "user", "content": "What is 2+2?", "timestamp": datetime.now()},
                {"role": "assistant", "content": "2+2=4", "timestamp": datetime.now()},
                {"role": "user", "content": "What is 3+3?", "timestamp": datetime.now()},
                {"role": "assistant", "content": "3+3=6", "timestamp": datetime.now()},
            ]
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Based on our previous discussion..."
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="Can you explain more?"
        )

        assert "response" in result
        # Verify Gemini was called with conversation history
        call_args = mock_model.generate_content.call_args
        assert call_args is not None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_ask_question_limits_history_to_5_turns(self, mock_genai, homework_assistant):
        """Test that conversation history is limited to last 5 turns"""
        # Mock homework with long conversation history (6 turns)
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Math problems",
            "conversation_history": [
                {"role": "user", "content": "Q1", "timestamp": datetime.now()},
                {"role": "assistant", "content": "A1", "timestamp": datetime.now()},
                {"role": "user", "content": "Q2", "timestamp": datetime.now()},
                {"role": "assistant", "content": "A2", "timestamp": datetime.now()},
                {"role": "user", "content": "Q3", "timestamp": datetime.now()},
                {"role": "assistant", "content": "A3", "timestamp": datetime.now()},
            ]
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Answer"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="Q4"
        )

        # Verify only last 5 turns were used (Q2, A2, Q3, A3, Q4 should be in context)
        # First turn (Q1, A1) should be excluded
        call_args = mock_model.generate_content.call_args[0][0]

        # The context should NOT include the oldest turn
        assert "Q1" not in call_args
        # But should include recent turns
        assert "Q2" in call_args or "Q3" in call_args

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_ask_question_missing_api_key(self, homework_assistant):
        """Test error when GEMINI_API_KEY is not set"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Content"
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="What is this?"
        )

        assert "error" in result
        assert "API key" in result["error"] or "not configured" in result["error"]

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_ask_question_handles_gemini_error(self, mock_genai, homework_assistant):
        """Test error handling when Gemini API fails"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Content",
            "conversation_history": []
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini to raise an error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API rate limit exceeded")
        mock_genai.GenerativeModel.return_value = mock_model

        result = homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="What is this?"
        )

        assert "error" in result

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_ask_question_saves_conversation(self, mock_genai, homework_assistant):
        """Test that conversation is saved after each question"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Math problems",
            "conversation_history": []
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Here's the answer..."
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="How do I solve this?"
        )

        # Verify update_one was called to save conversation
        assert homework_assistant.homework_collection.update_one.called

        # Verify the update includes both user question and assistant response
        call_args = homework_assistant.homework_collection.update_one.call_args
        update_data = call_args[0][1]
        assert "$push" in update_data or "$set" in update_data


class TestSocraticTeachingApproach:
    """Tests for Socratic teaching methodology"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_uses_socratic_method_prompt(self, mock_genai, homework_assistant):
        """Test that Socratic teaching method is mentioned in system prompt"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "2+2=?",
            "conversation_history": []
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini
        mock_response = Mock()
        mock_response.text = "Let's think about this together..."
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="What's the answer?"
        )

        # Verify Socratic method is mentioned in the prompt
        call_args = mock_model.generate_content.call_args[0][0]
        assert "Socratic" in call_args or "guide" in call_args.lower()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.homework_assistant.genai')
    def test_does_not_give_direct_answers(self, mock_genai, homework_assistant):
        """Test that system prompt instructs not to give direct answers"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "extracted_text": "Math problem",
            "conversation_history": []
        }
        homework_assistant.homework_collection.find_one.return_value = mock_homework

        # Mock Gemini
        mock_response = Mock()
        mock_response.text = "Think about..."
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        homework_assistant.ask_question(
            homework_id="hw123",
            user_id="user123",
            question="Just tell me the answer"
        )

        # Verify the prompt discourages direct answers
        call_args = mock_model.generate_content.call_args[0][0]
        assert "don't" in call_args.lower() or "avoid" in call_args.lower() or "guide" in call_args.lower()

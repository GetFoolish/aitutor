"""
Homework Assistant - Stateless AI integration for homework help
All state is stored in MongoDB via homework collection.
Uses Google Gemini API for AI-powered homework assistance.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from shared.logging_config import get_logger
from shared.model_router import route_llm_request, ModelTier

logger = get_logger(__name__)


class HomeworkAssistant:
    """
    Stateless homework assistant powered by Google Gemini AI.
    Manages conversation history and provides intelligent homework help.
    """

    def __init__(self, mongo_db):
        """
        Initialize HomeworkAssistant with MongoDB connection

        Args:
            mongo_db: MongoDBManager instance
        """
        self.db = mongo_db.db
        self.homework_collection = self.db['homework']

        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not configured")
            raise ValueError("GEMINI_API_KEY environment variable is required")

        self.api_key = api_key
        logger.info("[HOMEWORK_ASSISTANT] Initialized with Gemini AI integration")

    def _get_gemini_client(self):
        """Get Gemini client instance"""
        import google.genai as genai
        return genai.Client(api_key=self.api_key)

    def _get_homework(self, homework_id: str, user_id: str) -> Optional[Dict]:
        """
        Get homework document from MongoDB

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)

        Returns:
            Homework document or None
        """
        return self.homework_collection.find_one({
            "homework_id": homework_id,
            "user_id": user_id
        })

    def _build_conversation_context(
        self,
        homework_content: str,
        conversation_history: List[Dict],
        question: str
    ) -> str:
        """
        Build conversation context for Gemini

        Args:
            homework_content: Extracted text from homework file
            conversation_history: Previous conversation turns
            question: Current user question

        Returns:
            Formatted prompt for Gemini
        """
        # System instruction
        system_prompt = """You are a helpful homework assistant. Your goal is to help students understand their homework without giving away direct answers.

Guidelines:
- Ask leading questions to guide the student's thinking
- Provide hints and explanations, not complete solutions
- Encourage critical thinking and problem-solving
- Be patient, friendly, and encouraging
- If the homework content is unclear or incomplete, ask clarifying questions
- Break down complex problems into manageable steps"""

        # Build conversation history
        history_text = ""
        for turn in conversation_history[-5:]:  # Last 5 turns for context
            history_text += f"\nStudent: {turn['question']}\nAssistant: {turn['response']}\n"

        # Build full prompt
        prompt = f"""{system_prompt}

--- HOMEWORK CONTENT ---
{homework_content[:3000]}
--- END HOMEWORK CONTENT ---

{history_text}

Student: {question}
Assistant:"""

        return prompt

    def ask_question(
        self,
        homework_id: str,
        user_id: str,
        question: str
    ) -> Dict[str, Any]:
        """
        Ask a question about homework and get AI response

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)
            question: User's question

        Returns:
            Dictionary with response and metadata
        """
        try:
            # Get homework document
            homework = self._get_homework(homework_id, user_id)
            if not homework:
                logger.warning(f"[HOMEWORK_ASSISTANT] Homework not found: {homework_id}")
                return {
                    "error": "Homework not found",
                    "response": None
                }

            # Get extracted text content
            homework_content = homework.get("extracted_text", "")
            if not homework_content or homework_content.startswith("["):
                # Content extraction failed or unavailable
                homework_content = f"Homework file: {homework.get('filename', 'unknown')}"

            # Get conversation history
            conversation_history = homework.get("conversation_history", [])

            # Build prompt
            prompt = self._build_conversation_context(
                homework_content,
                conversation_history,
                question
            )

            # Route to appropriate model based on complexity
            model_config, complexity = route_llm_request(
                task_type="homework_assistance",
                prompt=prompt,
                requires_reasoning=True
            )

            logger.info(f"[HOMEWORK_ASSISTANT] Using {model_config.name} for homework assistance")

            # Call Gemini API
            client = self._get_gemini_client()
            response = client.models.generate_content(
                model=model_config.name,
                contents=prompt
            )

            # Extract response text
            ai_response = response.text if hasattr(response, 'text') else str(response)

            # Store conversation turn in MongoDB
            conversation_turn = {
                "question": question,
                "response": ai_response,
                "timestamp": datetime.utcnow(),
                "model_used": model_config.name
            }

            self.homework_collection.update_one(
                {"homework_id": homework_id, "user_id": user_id},
                {
                    "$push": {"conversation_history": conversation_turn},
                    "$set": {"last_accessed": datetime.utcnow()}
                }
            )

            logger.info(f"[HOMEWORK_ASSISTANT] Answered question for homework {homework_id}")

            return {
                "response": ai_response,
                "homework_id": homework_id,
                "timestamp": conversation_turn["timestamp"].isoformat()
            }

        except Exception as e:
            logger.error(f"[HOMEWORK_ASSISTANT] Error answering question: {e}", exc_info=True)
            return {
                "error": f"Failed to generate response: {str(e)}",
                "response": None
            }

    def get_conversation_history(
        self,
        homework_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get conversation history for homework

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)
            limit: Maximum number of turns to return

        Returns:
            List of conversation turns
        """
        homework = self._get_homework(homework_id, user_id)
        if not homework:
            return []

        conversation_history = homework.get("conversation_history", [])

        # Return last N turns
        return conversation_history[-limit:]

    def clear_conversation_history(
        self,
        homework_id: str,
        user_id: str
    ) -> bool:
        """
        Clear conversation history for homework

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)

        Returns:
            True if successful
        """
        try:
            result = self.homework_collection.update_one(
                {"homework_id": homework_id, "user_id": user_id},
                {"$set": {"conversation_history": []}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"[HOMEWORK_ASSISTANT] Error clearing history: {e}")
            return False

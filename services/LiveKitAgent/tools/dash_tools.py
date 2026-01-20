"""
DASH System Integration Tools for LiveKit Agent

These tools allow the AI tutor agent to interact with the DASH
adaptive learning system for:
- Recording student answer attempts
- Fetching recommended questions
- Getting skill scores
"""

import os
import aiohttp
from typing import Optional
from livekit.agents import function_tool


DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")


class DashTools:
    """Tools for interacting with the DASH adaptive learning system."""

    def __init__(self, user_id: str, auth_token: Optional[str] = None):
        """Initialize DASH tools with user context.

        Args:
            user_id: The student's user ID
            auth_token: JWT token for authenticated requests
        """
        self.user_id = user_id
        self.auth_token = auth_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @function_tool()
    async def record_answer_attempt(
        self,
        question_id: str,
        skill_ids: list[str],
        is_correct: bool,
        response_time_seconds: float
    ) -> dict:
        """Record a student's answer attempt for adaptive learning.

        Args:
            question_id: The ID of the question answered
            skill_ids: List of skill IDs associated with the question
            is_correct: Whether the answer was correct
            response_time_seconds: Time taken to answer in seconds

        Returns:
            Result with affected skills and success status
        """
        session = await self._get_session()

        try:
            async with session.post(
                f"{DASH_API_URL}/api/submit-answer",
                json={
                    "question_id": question_id,
                    "skill_ids": skill_ids,
                    "is_correct": is_correct,
                    "response_time_seconds": response_time_seconds
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "affected_skills": result.get("affected_skills", []),
                        "message": "Answer recorded successfully"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to record answer: {response.status} - {error_text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error recording answer: {str(e)}"
            }

    @function_tool()
    async def get_next_question(self) -> dict:
        """Get the next recommended question for the student.

        Uses DASH adaptive learning to select the optimal next question
        based on the student's skill levels and learning journey.

        Returns:
            Question data with Perseus format and DASH metadata
        """
        session = await self._get_session()

        try:
            async with session.get(
                f"{DASH_API_URL}/api/questions/1"
            ) as response:
                if response.status == 200:
                    questions = await response.json()
                    if questions and len(questions) > 0:
                        question = questions[0]
                        return {
                            "success": True,
                            "question": question,
                            "metadata": question.get("dash_metadata", {})
                        }
                    return {
                        "success": False,
                        "error": "No questions available"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to get question: {response.status} - {error_text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting question: {str(e)}"
            }

    @function_tool()
    async def get_skill_scores(self) -> dict:
        """Get all skill scores for the current student.

        Returns skill states including memory strength, practice count,
        and accuracy for each skill the student has practiced.

        Returns:
            Dictionary of skill states keyed by skill ID
        """
        session = await self._get_session()

        try:
            async with session.get(
                f"{DASH_API_URL}/api/skill-scores"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "skill_states": result.get("skill_states", {})
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to get skill scores: {response.status} - {error_text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting skill scores: {str(e)}"
            }

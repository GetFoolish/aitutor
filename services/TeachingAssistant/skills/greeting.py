"""
Greeting Skill for TeachingAssistant
Generates greeting/closing prompts with optional memory awareness.
Session timing is handled by SessionManager in MongoDB.
"""

import time
import asyncio
from typing import Optional
import logging

from .base import Skill
from ..core.context import SessionContext
from ..core.config import TeachingAssistantConfig
from ..core.file_utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)


class GreetingSkill(Skill):
    """
    Skill that generates greeting/closing prompts with optional memory awareness.
    """

    def __init__(self, config: Optional[TeachingAssistantConfig] = None):
        super().__init__(name="greeting")
        self.config = config or TeachingAssistantConfig()

    def should_run(self, context: SessionContext) -> bool:
        """
        Greetings and closings are lifecycle events triggered explicitly,
        so this skill doesn't run automatically in the generic loop.
        """
        return False

    def execute(self, context: SessionContext) -> Optional[str]:
        """
        No automatic execution logic.
        """
        return None

    def get_greeting(self, user_id: str) -> str:
        """Generate greeting prompt for session start (backward compatibility)"""
        return f"""{self.config.system_prompt_prefix}
You are Adam, an advanced AI Teaching Assistant.
You are starting a tutoring session.

Please greet the student warmly and ask how they're doing today.
Make them feel welcome and excited to learn."""

    async def start_session(self, user_id: str, session_id: str) -> str:
        """Generate memory-aware greeting prompt for session start"""
        logger.info(f"[GREETING_SKILL] Generating greeting for user {user_id}, session {session_id}")
        opening = await self._load_opening(user_id)
        logger.info(f"[GREETING_SKILL] Loaded opening data: {bool(opening)}")
        
        # Clear opening cache after loading (so it's fresh for next session)
        self._clear_opening_cache(user_id)
        
        if opening:
            welcome = opening.get("welcome_hook", "")
            last_summary = opening.get("last_session_summary", "")
            unfinished = opening.get("unfinished_threads", [])
            personal = opening.get("personal_relevance", [])
            
            # If welcome_hook is empty (LLM failed or cleared), use fallback
            if not welcome:
                return self.get_greeting(user_id)
            
            greeting_parts = [welcome]
            if last_summary:
                greeting_parts.append(f"Last time we worked on: {last_summary}")
            if unfinished:
                greeting_parts.append(f"Unfinished topics: {', '.join(unfinished)}")
            if personal:
                greeting_parts.append("Personal context available.")
            
            greeting_text = f"{self.config.system_prompt_prefix}\n" + \
                            "[MEMORY AND INJECTION HANDLING]\n" + \
                            "During this session, you will receive 'System Updates' with retrieved memories.\n" + \
                            "- If an update arrives while you are speaking or just finished: DO NOT hallucinate a new user turn.\n" + \
                            "- If you have just finished a response, simply maintain consistency with that response.\n" + \
                            "- Do not let internal system updates disrupt the natural flow of conversation.\n\n" + \
                            " ".join(greeting_parts)
            logger.info(f"[GREETING_SKILL] Generated memory-aware greeting ({len(greeting_text)} chars)")
            return greeting_text
        
        fallback_greeting = self.get_greeting(user_id)
        logger.info(f"[GREETING_SKILL] Using fallback greeting ({len(fallback_greeting)} chars)")
        return fallback_greeting

    def get_closing(self, duration_minutes: float, questions_answered: int) -> str:
        """Generate closing prompt with session stats (backward compatibility)"""
        return f"""{self.config.system_prompt_prefix}
The tutoring session is ending now.
Session stats: {duration_minutes:.1f} minutes, {questions_answered} questions attempted.
Please give the student a warm closing message, acknowledge their hard work,
and encourage them for next session."""

    def end_session(self, user_id: str, session_id: str) -> str:
        """Generate memory-aware closing prompt for session end"""
        logger.info(f"[GREETING_SKILL] Generating closing for user {user_id}, session {session_id}")
        closing = self._load_closing(user_id, session_id)
        logger.info(f"[GREETING_SKILL] Loaded closing data: {bool(closing)}")
        if closing:
            goodbye = closing.get("goodbye_message", "Goodbye!")
            next_hooks = closing.get("next_session_hooks", [])
            
            closing_parts = [goodbye]
            if next_hooks:
                closing_parts.append(f"Next time: {', '.join(next_hooks)}")
            
            closing_text = f"{self.config.system_prompt_prefix}\nStudent wants to leave the session.\n" + " ".join(closing_parts)
            logger.info(f"[GREETING_SKILL] Generated memory-aware closing ({len(closing_text)} chars)")
            return closing_text
        
        fallback_closing = self.get_closing(0, 0)  # Fallback
        logger.info(f"[GREETING_SKILL] Using fallback closing ({len(fallback_closing)} chars)")
        return fallback_closing

    def get_inactivity_prompt(self) -> str:
        """Generate inactivity check prompt"""
        return f"""{self.config.system_prompt_prefix}
Check with the student if they're there, and if they want to continue...
We have some very interesting problems to solve."""

    async def _load_opening(self, user_id: str) -> Optional[dict]:
        """
        Load opening data from memory retrieval file.
        Checks for file once and returns immediately (no polling).
        """
        file_path = self.config.get_opening_retrieval_path(user_id)
        
        # Check ONCE for the opening cache file
        # If it exists, use it. If not, return None immediately to use default fallback.
        data = load_json_file(file_path)
        if data:
            return data
            
        return None

    def _load_closing(self, user_id: str, session_id: str) -> Optional[dict]:
        """Load closing data from memory retrieval file"""
        file_path = self.config.get_closing_retrieval_path(user_id)
        data = load_json_file(file_path)
        
        if data and data.get("session_id") == session_id:
            return data
        return None
    
    def _clear_opening_cache(self, user_id: str):
        """Clear opening cache after it's been used for greeting"""
        file_path = self.config.get_opening_retrieval_path(user_id)
        
        # Initialize with empty structure
        opening_data = {
            "timestamp": time.time(),
            "welcome_hook": "",
            "last_session_summary": "",
            "unfinished_threads": [],
            "personal_relevance": [],
            "emotional_state_last": "neutral",
            "suggested_opener": ""
        }
        
        if save_json_file(file_path, opening_data):
            logger.info(f"Cleared opening cache after use for user: {user_id}")
        else:
            logger.error(f"Failed to clear opening cache for user: {user_id}")


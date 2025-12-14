from typing import Optional
from .base import Skill
from ..core.context import SessionContext


class MemoryRetrievalSkill(Skill):
    def __init__(self, memory_retriever=None):
        super().__init__("memory_retrieval")
        self.memory_retriever = memory_retriever
        self.last_injection_turn = {}
        self.last_deep_retrieval_time = {}
        self.deep_retrieval_interval = 180

    def should_run(self, context: SessionContext) -> bool:
        if not context.last_user_text:
            return False

        if context.turn_count > self.last_injection_turn.get(context.session_id, 0):
            return True

        return False

    def execute(self, context: SessionContext) -> Optional[str]:
        """Memory injection is now handled directly in _trigger_memory_retrieval_async after retrieval completes.
        This skill is kept for backward compatibility but returns None to avoid duplicate injections."""
        # Injection happens in teaching_assistant.py after async retrieval completes
        # Return None to avoid duplicate injections
        return None


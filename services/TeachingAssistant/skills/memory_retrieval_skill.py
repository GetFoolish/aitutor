import time
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
        if not self.memory_retriever:
            return None

        session_id = context.session_id
        user_id = context.user_id

        if not context.last_user_text:
            return None

        current_time = time.time()
        last_deep = self.last_deep_retrieval_time.get(session_id, 0)

        try:
            self.memory_retriever.on_user_turn(
                session_id=session_id,
                user_id=user_id,
                user_text=context.last_user_text,
                timestamp=context.last_user_turn_time or time.time(),
                adam_text=context.last_adam_text or ""
            )

            if current_time - last_deep >= self.deep_retrieval_interval:
                self.last_deep_retrieval_time[session_id] = current_time

            injection_text = self.memory_retriever.get_memory_injection(session_id)

            if injection_text:
                self.last_injection_turn[session_id] = context.turn_count
                return injection_text

        except Exception:
            pass

        return None


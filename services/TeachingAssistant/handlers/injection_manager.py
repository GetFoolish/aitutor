"""
Injection Manager - Queue instructions for SSE delivery
Based on v4 teaching-assistant branch implementation

Manages instruction injection to the tutor via MongoDB queue.
Instructions are delivered via SSE (Server-Sent Events).
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from ..core.config import TeachingAssistantConfig

logger = logging.getLogger(__name__)


class InjectionManager:
    """
    Manages instruction injection to the tutor.

    Uses MongoDB instruction queue instead of HTTP for SSE delivery.
    Instructions are queued and delivered asynchronously.
    """

    def __init__(
        self,
        session_manager=None,
        config: Optional[TeachingAssistantConfig] = None
    ):
        self.session_manager = session_manager
        self.config = config or TeachingAssistantConfig()

        # In-memory queue for when session_manager not available
        self._instruction_queue: Dict[str, List[Dict[str, Any]]] = {}

        logger.info("[INJECTION_MANAGER] Initialized")

    def queue_instruction(
        self,
        session_id: str,
        message: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue an instruction for delivery.

        Args:
            session_id: Session to deliver instruction to
            message: The instruction text
            priority: Priority (higher = more urgent)
            metadata: Additional metadata

        Returns:
            Instruction ID
        """
        instruction_id = str(uuid.uuid4())

        # Add system instruction prefix if not present
        if not message.startswith(self.config.system_instruction_prefix):
            full_message = f"{self.config.system_instruction_prefix}\n{message}"
        else:
            full_message = message

        instruction = {
            "id": instruction_id,
            "session_id": session_id,
            "message": full_message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "delivered": False
        }

        # Try to use session_manager's push_instruction if available
        if self.session_manager and hasattr(self.session_manager, 'push_instruction'):
            try:
                self.session_manager.push_instruction(session_id, full_message)
                logger.info(
                    f"[INJECTION_MANAGER] Queued instruction {instruction_id[:8]}... "
                    f"for session {session_id}"
                )
                return instruction_id
            except Exception as e:
                logger.error(f"[INJECTION_MANAGER] Session manager push failed: {e}")

        # Fallback to in-memory queue
        if session_id not in self._instruction_queue:
            self._instruction_queue[session_id] = []

        self._instruction_queue[session_id].append(instruction)
        self._instruction_queue[session_id].sort(key=lambda x: -x["priority"])

        logger.info(
            f"[INJECTION_MANAGER] Queued instruction {instruction_id[:8]}... "
            f"(in-memory) for session {session_id}"
        )

        return instruction_id

    async def send_to_tutor(
        self,
        message: str,
        session_id: str,
        user_id: str
    ) -> bool:
        """
        Queue instruction for delivery (async interface).

        Args:
            message: Instruction message
            session_id: Session ID
            user_id: User ID

        Returns:
            True if queued successfully
        """
        try:
            self.queue_instruction(
                session_id=session_id,
                message=message,
                metadata={"user_id": user_id}
            )
            return True
        except Exception as e:
            logger.error(f"[INJECTION_MANAGER] Error queueing instruction: {e}")
            return False

    def get_pending_instructions(
        self,
        session_id: str,
        mark_delivered: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get pending instructions for a session.

        Args:
            session_id: Session to get instructions for
            mark_delivered: Whether to mark as delivered

        Returns:
            List of pending instructions
        """
        if session_id not in self._instruction_queue:
            return []

        pending = [
            inst for inst in self._instruction_queue[session_id]
            if not inst["delivered"]
        ]

        if mark_delivered:
            for inst in pending:
                inst["delivered"] = True

        return pending

    def get_next_instruction(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next pending instruction for a session.

        Returns:
            Next instruction or None
        """
        pending = self.get_pending_instructions(session_id, mark_delivered=False)
        if pending:
            instruction = pending[0]
            instruction["delivered"] = True
            return instruction
        return None

    def clear_session_instructions(self, session_id: str):
        """Clear all instructions for a session"""
        if session_id in self._instruction_queue:
            del self._instruction_queue[session_id]
            logger.info(f"[INJECTION_MANAGER] Cleared instructions for session {session_id}")

    def inject_memory_context(
        self,
        session_id: str,
        memories: List[Dict[str, Any]],
        synthesized_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Inject memory context as an instruction.

        Args:
            session_id: Session ID
            memories: Retrieved memories
            synthesized_instruction: Pre-synthesized instruction (if available)

        Returns:
            Instruction ID if queued, None otherwise
        """
        if synthesized_instruction:
            return self.queue_instruction(
                session_id=session_id,
                message=synthesized_instruction,
                priority=1,
                metadata={"type": "memory_injection", "memory_count": len(memories)}
            )

        if not memories:
            return None

        # Format memories as instruction
        memory_texts = []
        for mem in memories[:5]:  # Limit to 5 memories
            if isinstance(mem, dict):
                memory_obj = mem.get("memory")
                if hasattr(memory_obj, "text"):
                    memory_texts.append(f"- {memory_obj.text}")
                elif isinstance(memory_obj, dict):
                    memory_texts.append(f"- {memory_obj.get('text', '')}")

        if not memory_texts:
            return None

        instruction = f"""Based on previous interactions with this student:

{chr(10).join(memory_texts)}

Use this context to personalize your response, but do not explicitly mention these memories to the student."""

        return self.queue_instruction(
            session_id=session_id,
            message=instruction,
            priority=1,
            metadata={"type": "memory_injection", "memory_count": len(memories)}
        )

    def inject_biography_context(
        self,
        session_id: str,
        biography: str,
        student_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Inject biography context as an instruction.

        Args:
            session_id: Session ID
            biography: Student biography text
            student_name: Student name

        Returns:
            Instruction ID if queued, None otherwise
        """
        if not biography:
            return None

        name_part = f" ({student_name})" if student_name else ""

        instruction = f"""Student Biography{name_part}:

{biography[:self.config.max_injection_length]}

Use this understanding of the student to personalize your teaching approach.
Do not explicitly reference this biography to the student."""

        return self.queue_instruction(
            session_id=session_id,
            message=instruction,
            priority=2,  # Higher priority for biography
            metadata={"type": "biography_injection"}
        )


# Singleton instance
injection_manager = InjectionManager()

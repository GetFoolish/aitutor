"""
Injection Manager for TeachingAssistant
Queues instructions in MongoDB for delivery via SSE (replaces HTTP injection).
"""

import logging
from typing import Optional

from services.TeachingAssistant.session_manager import SessionManager
from services.TeachingAssistant.core.config import TeachingAssistantConfig

logger = logging.getLogger(__name__)


class InjectionManager:
    """
    Manages instruction injection to tutor.
    Uses MongoDB instruction queue instead of HTTP (for SSE delivery).
    """
    
    def __init__(self, session_manager: SessionManager, config: Optional[TeachingAssistantConfig] = None):
        self.session_manager = session_manager
        self.config = config or TeachingAssistantConfig()
        logger.info("[INJECTION_MANAGER] Initialized with MongoDB instruction queue")
    
    async def send_to_adam(self, message: str, session_id: str, user_id: str) -> bool:
        """
        Queue instruction in MongoDB (replaces HTTP injection).
        Instruction will be delivered via SSE automatically.
        """
        try:
            # Add system instruction prefix if not already present
            if not message.startswith(self.config.system_instruction_prefix):
                full_message = f"{self.config.system_instruction_prefix}\n{message}"
            else:
                full_message = message
            
            # Push to instruction queue (will be delivered via SSE)
            instruction_id = self.session_manager.push_instruction(session_id, full_message)
            logger.info(f"[INJECTION_MANAGER] Queued instruction {instruction_id} for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"[INJECTION_MANAGER] Error queueing instruction: {e}", exc_info=True)
            return False



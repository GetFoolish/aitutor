import threading
import asyncio
from typing import Dict, Optional
from .context import Event, SessionContext


class ContextManager:
    """Manages session contexts with thread-safe async file I/O."""
    
    def __init__(self):
        self.contexts: Dict[str, SessionContext] = {}
        self.lock = threading.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set event loop for non-blocking file I/O operations."""
        self._event_loop = loop

    def get_context(self, session_id: str) -> Optional[SessionContext]:
        """Thread-safe context retrieval."""
        with self.lock:
            return self.contexts.get(session_id)

    def create_context(self, session_id: str, user_id: str, start_time: float):
        """Create new session context (thread-safe)."""
        with self.lock:
            if session_id in self.contexts:
                return
            self.contexts[session_id] = SessionContext(
                session_id=session_id,
                user_id=user_id,
                start_time=start_time
            )

    def update_from_event(self, event: Event):
        """Update context from event. Schedules non-blocking file I/O."""
        context = self.get_context(event.session_id)
        if not context:
            if event.type == 'session_start':
                self.create_context(
                    event.session_id,
                    event.user_id,
                    event.timestamp
                )
                context = self.get_context(event.session_id)
            else:
                return

        if event.type == 'text':
            speaker = event.data.get('speaker')
            text = event.data.get('text')
            if speaker and text:
                previous_turn_count = len(context.conversation_turns)
                
                context.add_turn(speaker, text, event.timestamp)
                context.current_speaker = speaker
                
                if len(context.conversation_turns) > previous_turn_count:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"📝 Stored {speaker} turn (total turns: {len(context.conversation_turns)})")
                    self._schedule_async_save(context)

        elif event.type == 'session_end':
            self.clear_context(event.session_id)

        elif event.type == 'audio':
            context.has_audio = True

        elif event.type == 'video':
            context.has_video = True

    def clear_context(self, session_id: str):
        """Remove session context (thread-safe)."""
        with self.lock:
            if session_id in self.contexts:
                del self.contexts[session_id]
    
    def _schedule_async_save(self, context: SessionContext):
        """Schedule non-blocking file save in thread executor."""
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._save_conversation_realtime_async(context),
                self._event_loop
            )
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("⚠️ Event loop not available, using synchronous save")
            self._save_conversation_realtime_sync(context)
    
    async def _save_conversation_realtime_async(self, context: SessionContext):
        """Async wrapper: runs file I/O in thread executor."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_conversation_realtime_sync, context)
    
    def _save_conversation_realtime_sync(self, context: SessionContext):
        """Synchronous file save (runs in thread executor)."""
        import os
        import json
        import logging
        from datetime import datetime
        
        logger = logging.getLogger(__name__)
        
        try:
            data_dir = f"Memory/data/{context.user_id}/conversations"
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = f"{data_dir}/{context.session_id}.json"
            conversation_data = {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "start_time": datetime.fromtimestamp(context.start_time).isoformat(),
                "last_updated": datetime.now().isoformat(),
                "turn_count": context.turn_count,
                "turns": context.conversation_turns
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Real-time save: {file_path} ({len(context.conversation_turns)} turns)")
        except Exception as e:
            logger.error(f"❌ Error saving conversation: {e}", exc_info=True)


import threading
import time
from typing import Dict, Optional
from .context import Event, SessionContext


class ContextManager:
    def __init__(self):
        self.contexts: Dict[str, SessionContext] = {}
        self.lock = threading.Lock()

    def get_context(self, session_id: str) -> Optional[SessionContext]:
        with self.lock:
            return self.contexts.get(session_id)

    def create_context(self, session_id: str, user_id: str, start_time: float):
        with self.lock:
            if session_id in self.contexts:
                return
            self.contexts[session_id] = SessionContext(
                session_id=session_id,
                user_id=user_id,
                start_time=start_time
            )

    def update_from_event(self, event: Event):
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

        if event.type == 'text' and event.data.get('is_complete'):
            speaker = event.data.get('speaker')
            text = event.data.get('text')
            if speaker and text:
                context.add_turn(speaker, text, event.timestamp)
                context.current_speaker = speaker

        elif event.type == 'text' and not event.data.get('is_complete'):
            context.current_speaker = event.data.get('speaker')

        elif event.type == 'session_end':
            self.clear_context(event.session_id)

        elif event.type == 'audio':
            context.has_audio = True

        elif event.type == 'video':
            context.has_video = True

    def clear_context(self, session_id: str):
        with self.lock:
            if session_id in self.contexts:
                del self.contexts[session_id]


import queue
import threading
from typing import List
from ..core.context import Event
from shared.logging_config import get_logger

logger = get_logger(__name__)


class EventQueueManager:
    def __init__(self, max_size: int = 1000):
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.lock = threading.Lock()
        self._counter = 0  # Counter to break ties in priority queue

    def _get_priority(self, event_type: str) -> int:
        priority_map = {
            'session_start': 1,
            'session_end': 1,
            'user_message': 2,
            'tutor_message': 2,
            'text': 2,
            'audio': 3,
            'video': 4
        }
        return priority_map.get(event_type, 5)

    def enqueue(self, event: Event):
        # Use event_type.value if it's an enum, otherwise use string directly
        event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        priority = self._get_priority(event_type_str)
        with self.lock:
            try:
                # Use counter to break ties - ensures Events are always comparable
                self._counter += 1
                self.queue.put((priority, event.timestamp, self._counter, event), block=False)
                logger.info(f"[QUEUE] 📥 Enqueued event: {event_type_str}, session: {event.session_id[:8]}..., text: {event.user_text[:30] if event.user_text else 'N/A'}...")
            except queue.Full:
                logger.warning("[QUEUE] Queue full, dropping event")

    def dequeue_batch(self, max_batch_size: int = 10) -> List[Event]:
        events = []
        with self.lock:
            try:
                while len(events) < max_batch_size:
                    priority, timestamp, counter, event = self.queue.get_nowait()
                    events.append(event)
            except queue.Empty:
                pass
        if events:
            logger.info(f"[QUEUE] 📤 Dequeued {len(events)} events")
        return events




import queue
import threading
import time
from typing import List, Optional
from ..core.context import Event


class EventQueueManager:
    def __init__(self, max_size: int = 1000):
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.lock = threading.Lock()

    def _get_priority(self, event_type: str) -> int:
        priority_map = {
            'session_start': 1,
            'session_end': 1,
            'text': 2,
            'audio': 3,
            'video': 4
        }
        return priority_map.get(event_type, 5)

    def enqueue(self, event: Event):
        priority = self._get_priority(event.type)
        with self.lock:
            try:
                self.queue.put((priority, event.timestamp, event), block=False)
            except queue.Full:
                pass

    def dequeue_batch(self, max_batch_size: int = 10) -> List[Event]:
        events = []
        with self.lock:
            try:
                while len(events) < max_batch_size:
                    priority, timestamp, event = self.queue.get_nowait()
                    events.append(event)
            except queue.Empty:
                pass
        return events

    def size(self) -> int:
        return self.queue.qsize()


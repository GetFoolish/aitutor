import time
from typing import Optional
from .base import Skill
from ..core.context import SessionContext


class InactivityCheckSkill(Skill):
    def __init__(self):
        super().__init__("inactivity_check")
        self.inactivity_threshold = 60
        self.grace_period = 60
        self.last_check_time = {}
        self.last_injection_time = {}
        self.check_interval = 5

    def should_run(self, context: SessionContext) -> bool:
        session_id = context.session_id
        current_time = time.time()

        if session_id not in self.last_check_time:
            self.last_check_time[session_id] = current_time
            return False

        if current_time - self.last_check_time[session_id] < self.check_interval:
            return False

        self.last_check_time[session_id] = current_time

        if current_time - context.start_time < self.grace_period:
            return False

        time_since_activity = context.time_since_activity

        if time_since_activity < self.inactivity_threshold:
            return False

        last_injection = self.last_injection_time.get(session_id, 0)
        if current_time - last_injection < self.inactivity_threshold:
            return False

        return True

    def execute(self, context: SessionContext) -> Optional[str]:
        session_id = context.session_id
        self.last_injection_time[session_id] = time.time()

        return "{{The student has been inactive for over 60 seconds. Gently re-engage them by asking if they need help or if they're ready to continue. Keep it brief and friendly.}}"


import time
import threading
from typing import Optional


class InactivityHandler:
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"
    INACTIVITY_THRESHOLD_SECONDS = 60
    CHECK_INTERVAL_SECONDS = 5
    GRACE_PERIOD_SECONDS = 60
    
    def __init__(self):
        self.last_conversation_turn: Optional[float] = None
        self.last_question_submission: Optional[float] = None
        self.pending_prompt: Optional[str] = None
        self.monitoring_active: bool = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.session_start_time: Optional[float] = None
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        if self.monitoring_active:
            self.stop_monitoring()
        
        with self.lock:
            self.monitoring_active = True
            current_time = time.time()
            self.session_start_time = current_time
            self.last_conversation_turn = current_time
            self.last_question_submission = current_time
            self.pending_prompt = None
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        was_active = self.monitoring_active
        self.monitoring_active = False
        
        if was_active and self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        self.monitor_thread = None
        
        with self.lock:
            self.session_start_time = None
            self.pending_prompt = None
    
    def record_conversation_turn(self):
        with self.lock:
            if self.session_start_time is None:
                return
            self.last_conversation_turn = time.time()
            self.pending_prompt = None
    
    def record_question_submission(self):
        with self.lock:
            if self.session_start_time is None:
                return
            self.last_question_submission = time.time()
            self.pending_prompt = None
    
    def get_pending_prompt(self) -> Optional[str]:
        with self.lock:
            if self.session_start_time is None:
                return None
            
            current_time = time.time()
            time_since_start = current_time - self.session_start_time
            
            if time_since_start < self.GRACE_PERIOD_SECONDS:
                return None
            
            prompt = self.pending_prompt
            self.pending_prompt = None
            return prompt
    
    def reset(self):
        with self.lock:
            self.last_conversation_turn = None
            self.last_question_submission = None
            self.pending_prompt = None
            self.session_start_time = None
    
    def _monitor_loop(self):
        while self.monitoring_active:
            try:
                self._check_inactivity()
                time.sleep(self.CHECK_INTERVAL_SECONDS)
            except Exception as e:
                print(f"Error in inactivity monitor: {e}")
                time.sleep(self.CHECK_INTERVAL_SECONDS)
    
    def _check_inactivity(self):
        with self.lock:
            if self.pending_prompt:
                return
            
            if self.session_start_time is None:
                return
            
            current_time = time.time()
            time_since_start = current_time - self.session_start_time
            
            if time_since_start < self.GRACE_PERIOD_SECONDS:
                return
            
            threshold_time = current_time - self.INACTIVITY_THRESHOLD_SECONDS
            
            if self.last_conversation_turn is None or self.last_question_submission is None:
                return
            
            conversation_inactive = self.last_conversation_turn < threshold_time
            question_inactive = self.last_question_submission < threshold_time
            
            if conversation_inactive and question_inactive:
                self.pending_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
Check with the student if he's there, and if he wants to continue... we have some very interesting problems to solve."""


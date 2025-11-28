import time
from typing import Optional, Dict, Any
from .greeting_handler import GreetingHandler
from .inactivity_handler import InactivityHandler


class TeachingAssistant:
    def __init__(self):
        self.greeting_handler = GreetingHandler()
        self.inactivity_handler = InactivityHandler()
        self.current_user_id: Optional[str] = None
        self.session_active: bool = False
    
    def start_session(self, user_id: str) -> str:
        if self.session_active:
            self.end_session()
        
        self.current_user_id = user_id
        self.session_active = True
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        self.inactivity_handler.start_monitoring()
        return self.greeting_handler.start_session(user_id)
    
    def end_session(self) -> str:
        if not self.session_active or not self.current_user_id:
            return ""
        
        user_id = self.current_user_id
        self.session_active = False
        self.current_user_id = None
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        
        return self.greeting_handler.end_session(user_id)
    
    def record_question_answered(self, question_id: str, is_correct: bool):
        if self.session_active:
            self.greeting_handler.record_question(question_id, is_correct)
            self.inactivity_handler.record_question_submission()
    
    def record_conversation_turn(self):
        if self.session_active:
            self.inactivity_handler.record_conversation_turn()
    
    def get_inactivity_prompt(self) -> Optional[str]:
        if self.session_active:
            return self.inactivity_handler.get_pending_prompt()
        return None
    
    def get_session_info(self) -> Dict[str, Any]:
        stats = self.greeting_handler.get_session_stats()
        stats['user_id'] = self.current_user_id
        stats['session_active'] = self.session_active
        return stats


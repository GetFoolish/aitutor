import time
from typing import Optional, Dict, Any
from .greeting_handler import GreetingHandler
from .inactivity_handler import InactivityHandler


class TeachingAssistant:
    def __init__(self):
        self.greeting_handler = GreetingHandler()
        self.inactivity_handler = InactivityHandler()
        self.current_student_name: Optional[str] = None
        self.session_active: bool = False
    
    def start_session(self, student_name: str) -> str:
        if self.session_active:
            self.end_session()
        
        self.current_student_name = student_name
        self.session_active = True
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        self.inactivity_handler.start_monitoring()
        return self.greeting_handler.start_session(student_name)
    
    def end_session(self) -> str:
        if not self.session_active or not self.current_student_name:
            return ""
        
        student_name = self.current_student_name
        self.session_active = False
        self.current_student_name = None
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        
        return self.greeting_handler.end_session(student_name)
    
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
        stats['student_name'] = self.current_student_name
        stats['session_active'] = self.session_active
        return stats


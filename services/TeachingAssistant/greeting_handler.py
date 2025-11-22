import time
from typing import Optional, Dict, Any


class GreetingHandler:
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"
    
    def __init__(self):
        self.session_start_time: Optional[float] = None
        self.questions_log: list = []
    
    def start_session(self, user_id: str) -> str:
        self.session_start_time = time.time()
        self.questions_log = []
        
        greeting_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session.
Please greet the student warmly and ask how they're doing today.
Make them feel welcome and excited to learn."""
        
        return greeting_prompt
    
    def end_session(self, user_id: str) -> str:
        if self.session_start_time is None:
            session_duration = 0.0
        else:
            session_duration = (time.time() - self.session_start_time) / 60
        
        total_questions = len(self.questions_log)
        
        closing_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
The tutoring session is ending now.
Session stats: {session_duration:.1f} minutes, {total_questions} questions attempted.
Please give the student a warm closing message, acknowledge their hard work, 
and encourage them for next session."""
        
        self.session_start_time = None
        self.questions_log = []
        
        return closing_prompt
    
    def record_question(self, question_id: str, is_correct: bool):
        self.questions_log.append({
            'question_id': question_id,
            'timestamp': time.time(),
            'is_correct': is_correct
        })
    
    def get_session_stats(self) -> Dict[str, Any]:
        if self.session_start_time is None:
            return {
                'session_active': False,
                'duration_minutes': 0.0,
                'total_questions': 0
            }
        
        return {
            'session_active': True,
            'duration_minutes': (time.time() - self.session_start_time) / 60,
            'total_questions': len(self.questions_log)
        }


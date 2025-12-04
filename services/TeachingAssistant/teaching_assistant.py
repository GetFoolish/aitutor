from typing import Optional, Dict, Any
from .greeting_handler import GreetingHandler
from .inactivity_handler import InactivityHandler
from .Memory import MemoryRetriever


class TeachingAssistant:
    def __init__(self):
        self.greeting_handler = GreetingHandler()
        self.inactivity_handler = InactivityHandler()
        self.memory_retriever: Optional[MemoryRetriever] = None
        self.current_user_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        self.session_active: bool = False
    
    def start_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        if self.session_active:
            self.end_session()
        
        self.current_user_id = user_id
        self.current_session_id = session_id
        self.session_active = True
        # Create MemoryRetriever with student_id
        self.memory_retriever = MemoryRetriever(student_id=user_id)
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        self.inactivity_handler.start_monitoring()
        # COMMENTED: File polling disabled - using real-time events instead
        # Create watcher instance for file saving methods only (no polling)
        # self.memory_retriever.start_retrieval_watcher(poll_interval=1.0, verbose=True)
        # Initialize watcher for file saving methods (but don't start polling)
        from services.TeachingAssistant.Memory.retriever import MemoryRetrievalWatcher
        self.memory_retriever.watcher = MemoryRetrievalWatcher(
            retriever=self.memory_retriever,
            verbose=True
        )
        return self.greeting_handler.start_session(user_id, session_id)
    
    def end_session(self, session_id: Optional[str] = None) -> str:
        if not self.session_active or not self.current_user_id:
            return ""
        
        user_id = self.current_user_id
        # Use provided session_id or fallback to tracked session_id
        end_session_id = session_id or self.current_session_id
        
        self.session_active = False
        self.current_user_id = None
        session_id_to_clear = self.current_session_id
        self.current_session_id = None
        self.inactivity_handler.stop_monitoring()
        self.inactivity_handler.reset()
        # Stop memory retrieval watcher
        if self.memory_retriever:
            self.memory_retriever.stop_retrieval_watcher()
            self.memory_retriever = None
        
        return self.greeting_handler.end_session(user_id, end_session_id)
    
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
        stats['session_id'] = self.current_session_id
        stats['session_active'] = self.session_active
        return stats


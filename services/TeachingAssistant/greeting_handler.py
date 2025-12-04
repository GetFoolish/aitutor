import time
import os
import json
from typing import Optional, Dict, Any


class GreetingHandler:
    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"
    
    def __init__(self):
        self.session_start_time: Optional[float] = None
        self.questions_log: list = []
    
    def _get_ta_opening_filepath(self, user_id: str) -> str:
        """Get path to TA-opening-retrieval.json file for a user."""
        # Get the TeachingAssistant directory (parent of greeting_handler.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        memory_dir = os.path.join(base_dir, 'Memory')
        ta_dir = os.path.join(memory_dir, 'data', user_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-opening-retrieval.json')
    
    def _get_ta_closing_filepath(self, user_id: str) -> str:
        """Get path to TA-closing-retrieval.json file for a user."""
        # Get the TeachingAssistant directory (parent of greeting_handler.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        memory_dir = os.path.join(base_dir, 'Memory')
        ta_dir = os.path.join(memory_dir, 'data', user_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-closing-retrieval.json')
    
    def _load_latest_opening_retrieval(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load the most recent opening retrieval for a user."""
        try:
            filepath = self._get_ta_opening_filepath(user_id)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'openings' not in data:
                return None
            
            openings = data.get('openings', [])
            if not openings:
                return None
            
            # Return the most recent opening (last in list)
            return openings[-1]
        except (json.JSONDecodeError, IOError, Exception):
            return None
    
    def _load_session_closing(self, user_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load closing retrieval for a specific session or the most recent one."""
        try:
            filepath = self._get_ta_closing_filepath(user_id)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'closings' not in data:
                return None
            
            closings = data.get('closings', [])
            if not closings:
                return None
            
            # If session_id provided, find that specific closing
            if session_id:
                for closing in closings:
                    if closing.get('session_id') == session_id:
                        return closing
            
            # Otherwise return the most recent closing
            return closings[-1]
        except (json.JSONDecodeError, IOError, Exception):
            return None
    
    def start_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        self.session_start_time = time.time()
        self.questions_log = []
        
        # Try to load opening retrieval data
        opening_data = self._load_latest_opening_retrieval(user_id)
        
        if opening_data:
            # Build dynamic prompt from opening retrieval
            last_session_summary = opening_data.get('last_session_summary', '')
            welcome_hook = opening_data.get('welcome_hook', 'Welcome back!')
            unfinished_threads = opening_data.get('unfinished_threads', [])
            personal_relevance = opening_data.get('personal_relevance', '')
            emotional_state_last = opening_data.get('emotional_state_last', 'neutral')
            
            # Build context parts
            context_parts = []
            if last_session_summary:
                context_parts.append(f"Summary: {last_session_summary}")
            if emotional_state_last and emotional_state_last != 'neutral':
                context_parts.append(f"Emotional state when they left: {emotional_state_last}")
            if unfinished_threads:
                context_parts.append(f"Unfinished threads: {', '.join(unfinished_threads)}")
            if personal_relevance:
                context_parts.append(f"Personal relevance: {personal_relevance}")
            
            context_block = '\n'.join(f"- {part}" for part in context_parts) if context_parts else "No previous session context available."
            
            greeting_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session with {user_id}.

LAST SESSION CONTEXT:
{context_block}

WELCOME HOOK: {welcome_hook}

Please greet the student warmly, reference their last session naturally if relevant,
and ask how they're doing today. Make them feel welcome and excited to learn.
Use the welcome hook and context to create a personalized, natural greeting."""
        else:
            # Fallback to static prompt for first-time users
            greeting_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
You are starting a tutoring session.
Please greet the student warmly and ask how they're doing today.
Make them feel welcome and excited to learn."""
        
        return greeting_prompt
    
    def end_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        if self.session_start_time is None:
            session_duration = 0.0
        else:
            session_duration = (time.time() - self.session_start_time) / 60
        
        total_questions = len(self.questions_log)
        
        # Try to load closing retrieval data for current session
        closing_data = self._load_session_closing(user_id, session_id)
        
        if closing_data:
            # Build dynamic prompt from closing retrieval
            session_summary = closing_data.get('session_summary', '')
            key_moments = closing_data.get('key_moments', [])
            emotional_arc = closing_data.get('emotional_arc', [])
            topics_covered = closing_data.get('topics_covered', [])
            next_session_hooks = closing_data.get('next_session_hooks', [])
            
            # Build summary parts
            summary_parts = []
            if session_summary:
                summary_parts.append(f"Summary: {session_summary}")
            if topics_covered and topics_covered != ['general']:
                summary_parts.append(f"Topics covered: {', '.join(topics_covered)}")
            if key_moments:
                summary_parts.append(f"Key moments: {', '.join(key_moments)}")
            if emotional_arc:
                summary_parts.append(f"Emotional journey: {' → '.join(emotional_arc)}")
            
            summary_block = '\n'.join(f"- {part}" for part in summary_parts) if summary_parts else "Session completed."
            
            hooks_block = ', '.join(next_session_hooks) if next_session_hooks else 'Continue where we left off'
            
            closing_prompt = f"""{self.SYSTEM_PROMPT_PREFIX}
The tutoring session is ending now.

SESSION SUMMARY:
- Duration: {session_duration:.1f} minutes
- Questions attempted: {total_questions}
{summary_block}

NEXT SESSION HOOKS:
{hooks_block}

Please give the student a warm closing message that:
1. Acknowledges their hard work and progress
2. References key moments or emotional state if significant
3. Mentions what to continue next time
4. Encourages them for the next session"""
        else:
            # Fallback to static prompt if closing data not available
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


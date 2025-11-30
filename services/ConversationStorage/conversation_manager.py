import random
import string
from datetime import datetime
from .json_storage import JsonStorage

class ConversationManager:
    """Manages conversation sessions and turns for transcription storage."""
    
    def __init__(self, storage=None):
        self.storage = storage or JsonStorage()
        self.session = None
    
    def start_session(self, user_id='anonymous'):
        """Start a new conversation session."""
        timestamp = datetime.utcnow()
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        session_id = f"sess_{timestamp.strftime('%Y%m%d_%H%M%S')}_{random_suffix}"
        
        self.session = {
            'session_id': session_id,
            'user_id': user_id,
            'start_time': timestamp.isoformat() + 'Z',
            'end_time': None,
            'turns': []
        }
        return session_id
    
    def add_user_turn(self, text):
        """Add user transcription to conversation."""
        if not self.session or not text:
            return
        
        self.session['turns'].append({
            'speaker': 'user',
            'text': text.strip(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    def add_adam_turn(self, text):
        """Add Adam transcription to conversation."""
        if not self.session or not text:
            return
        
        self.session['turns'].append({
            'speaker': 'adam',
            'text': text.strip(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    def end_session(self):
        """End session and save to storage."""
        if not self.session:
            return None
        
        self.session['end_time'] = datetime.utcnow().isoformat() + 'Z'
        filepath = self.storage.save(self.session)
        
        session_id = self.session['session_id']
        self.session = None
        return filepath
    
    def get_current_session(self):
        """Get current session data."""
        return self.session











import os
import json
from datetime import datetime

class JsonStorage:
    """Handles saving and loading conversation JSON files."""
    
    def __init__(self, storage_path=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_path = os.path.join(base_dir, 'data', 'conversations')
        
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
    
    def save(self, session_data):
        """Save conversation session to JSON file."""
        session_id = session_data.get('session_id', f'sess_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        filepath = os.path.join(self.storage_path, f'{session_id}.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load(self, session_id):
        """Load conversation session from JSON file."""
        filepath = os.path.join(self.storage_path, f'{session_id}.json')
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_sessions(self):
        """List all saved session IDs."""
        sessions = []
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                sessions.append(filename[:-5])
        return sorted(sessions, reverse=True)











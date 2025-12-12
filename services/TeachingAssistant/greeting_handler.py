import os
import json
from typing import Optional

class GreetingHandler:
    def __init__(self):
        pass

    def start_session(self, user_id: str, session_id: str) -> str:
        opening = self._load_opening(user_id)
        if opening:
            welcome = opening.get("welcome_hook", "Welcome back!")
            last_summary = opening.get("last_session_summary", "")
            unfinished = opening.get("unfinished_threads", [])
            personal = opening.get("personal_relevance", [])
            
            greeting_parts = [welcome]
            if last_summary:
                greeting_parts.append(f"Last time we worked on: {last_summary}")
            if unfinished:
                greeting_parts.append(f"Unfinished topics: {', '.join(unfinished)}")
            if personal:
                greeting_parts.append("Personal context available.")
            
            return " ".join(greeting_parts)
        return "Hello! How can I help you today?"

    def end_session(self, user_id: str, session_id: str) -> str:
        closing = self._load_closing(user_id, session_id)
        if closing:
            goodbye = closing.get("goodbye_message", "Goodbye!")
            next_hooks = closing.get("next_session_hooks", [])
            
            closing_parts = [goodbye]
            if next_hooks:
                closing_parts.append(f"Next time: {', '.join(next_hooks)}")
            
            return " ".join(closing_parts)
        return "Thank you for the session! See you next time."

    def _load_opening(self, user_id: str) -> Optional[dict]:
        file_path = f"Memory/data/{user_id}/memory/TeachingAssistant/TA-opening-retrieval.json"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _load_closing(self, user_id: str, session_id: str) -> Optional[dict]:
        file_path = f"Memory/data/{user_id}/memory/TeachingAssistant/TA-closing-retrieval.json"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("session_id") == session_id:
                    return data
        return None


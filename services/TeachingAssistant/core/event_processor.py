from typing import List
from .context import Event
from .context_manager import ContextManager


class EventProcessor:
    """Processes events and triggers skill execution. Context updates handled in main loop."""
    
    def __init__(self, context_manager: ContextManager, skills_manager=None):
        self.context_manager = context_manager
        self.skills_manager = skills_manager

    def process_event(self, event: Event) -> List[str]:
        """Process event and return skill-based injections."""
        context = self.context_manager.get_context(event.session_id)
        
        if not context:
            return []

        if self.skills_manager:
            return self.skills_manager.execute_skills(context)
        
        return []


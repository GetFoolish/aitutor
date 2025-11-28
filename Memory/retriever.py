from typing import List, Dict, Any, Optional
from datetime import datetime

from .schema import Memory, MemoryType
from .vector_store import MemoryStore
from .extractor import detect_topic_shift, has_past_reference, MemoryExtractor


class MemoryRetriever:
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self._extractor = None

    def _get_extractor(self) -> MemoryExtractor:
        if self._extractor is None:
            self._extractor = MemoryExtractor()
        return self._extractor

    def light_retrieval(self, query: str, student_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.store.search(query=query, student_id=student_id, top_k=top_k)

    def deep_retrieval(
        self,
        query: str,
        student_id: str,
        triggers: Optional[Dict[str, bool]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        triggers = triggers or {}

        academic = self.store.search(
            query=query,
            student_id=student_id,
            mem_type=MemoryType.ACADEMIC,
            top_k=5
        )

        personal = self.store.search(
            query=query,
            student_id=student_id,
            mem_type=MemoryType.PERSONAL,
            top_k=3
        )

        preferences = self.store.search(
            query=query,
            student_id=student_id,
            mem_type=MemoryType.PREFERENCE,
            top_k=3
        )

        context = [
            {'memory': m, 'score': 1.0}
            for m in self.store.get_recent_context(student_id, limit=3)
        ]

        if triggers.get('emotional_cue'):
            emotional_patterns = self.store.search(
                query=query,
                student_id=student_id,
                mem_type=MemoryType.PREFERENCE,
                top_k=3,
                metadata_filter={'category': 'emotional_response'}
            )
            seen_ids = {r['memory'].id for r in preferences}
            for ep in emotional_patterns:
                if ep['memory'].id not in seen_ids:
                    preferences.append(ep)

        return {
            'academic': academic,
            'personal': personal,
            'preferences': preferences,
            'context': context
        }

    def should_deep_retrieve(
        self,
        current_message: str,
        conversation: List[Dict[str, str]],
        turn_count: int = 0
    ) -> Dict[str, bool]:
        try:
            extractor = self._get_extractor()
            emotion = extractor.detect_emotion(current_message)
        except:
            emotion = None

        triggers = {
            'topic_change': detect_topic_shift(conversation),
            'emotional_cue': emotion is not None,
            'explicit_reference': has_past_reference(current_message),
            'every_n_turns': turn_count > 0 and turn_count % 5 == 0
        }

        return triggers

    def get_personalized_context(
        self,
        student_message: str,
        student_id: str,
        conversation: Optional[List[Dict[str, str]]] = None,
        turn_count: int = 0
    ) -> Dict[str, Any]:
        conversation = conversation or []

        light_results = self.light_retrieval(student_message, student_id)

        triggers = self.should_deep_retrieve(student_message, conversation, turn_count)

        if any(triggers.values()):
            deep_results = self.deep_retrieval(student_message, student_id, triggers)

            return {
                'mode': 'deep',
                'triggers': triggers,
                'academic': deep_results['academic'],
                'personal': deep_results['personal'],
                'preferences': deep_results['preferences'],
                'context': deep_results['context'],
                'all_results': light_results
            }

        return {
            'mode': 'light',
            'triggers': triggers,
            'all_results': light_results,
            'academic': [],
            'personal': [],
            'preferences': [],
            'context': []
        }

    def get_emotional_patterns(self, student_id: str) -> List[Memory]:
        all_prefs = self.store.get_memories_by_student(student_id, MemoryType.PREFERENCE)

        return [
            m for m in all_prefs
            if m.metadata.get('category') == 'emotional_response'
        ]

    def format_for_prompt(self, context: Dict[str, Any]) -> str:
        sections = []

        def format_memories(memories: List[Dict[str, Any]]) -> str:
            if not memories:
                return "None"
            lines = []
            for item in memories[:5]:
                mem = item['memory']
                emotion_str = f" ({mem.metadata.get('emotion')})" if mem.metadata.get('emotion') else ""
                lines.append(f"- {mem.text}{emotion_str}")
            return '\n'.join(lines)

        if context.get('academic'):
            sections.append(f"Academic:\n{format_memories(context['academic'])}")

        if context.get('personal'):
            sections.append(f"Personal:\n{format_memories(context['personal'])}")

        if context.get('preferences'):
            sections.append(f"Preferences:\n{format_memories(context['preferences'])}")

        if context.get('context'):
            sections.append(f"Recent context:\n{format_memories(context['context'])}")

        if not sections:
            if context.get('all_results'):
                sections.append(f"Relevant memories:\n{format_memories(context['all_results'])}")

        if not sections:
            return "No relevant memories found."

        return '\n\n'.join(sections)

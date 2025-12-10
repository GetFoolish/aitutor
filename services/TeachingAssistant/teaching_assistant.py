import asyncio
import time
import logging
from typing import Optional, Dict
from .core.context import SessionState
from .core.context_manager import ContextManager
from .core.event_processor import EventProcessor
from .handlers.event_handler import WebSocketEventHandler
from .handlers.queue_manager import EventQueueManager
from .handlers.injection_manager import InjectionManager
from .skills_manager import SkillsManager
from .Memory.vector_store import MemoryStore
from .Memory.retriever import MemoryRetriever
from .Memory.extractor import MemoryExtractor
from .Memory.consolidator import MemoryConsolidator, SessionClosingCache
from .Memory import get_memory_data_dir
from .greeting_handler import GreetingHandler
from .skills.memory_retrieval_skill import MemoryRetrievalSkill

logger = logging.getLogger(__name__)


class TeachingAssistant:
    def __init__(self, server_url: str = "ws://localhost:8767/ta", tutor_server_url: Optional[str] = None):
        self.queue_manager = EventQueueManager()
        self.context_manager = ContextManager()
        self.injection_manager = InjectionManager(tutor_server_url)
        self.event_handler = WebSocketEventHandler(self.queue_manager, server_url)
        self.skills_manager = SkillsManager()
        self.event_processor = EventProcessor(self.context_manager, self.skills_manager)
        self.session_state = SessionState()
        self.running = False
        
        self.memory_store = MemoryStore()
        self.memory_extractor = MemoryExtractor()
        self.memory_consolidator = MemoryConsolidator(self.memory_store, self.memory_extractor)
        self.greeting_handler = GreetingHandler()
        
        self.memory_retrievers: Dict[str, MemoryRetriever] = {}
        self.closing_caches: Dict[str, SessionClosingCache] = {}
        
        memory_skill = MemoryRetrievalSkill(memory_retriever=None)
        self.skills_manager.register_skill(memory_skill)

    async def start(self, user_id: str, session_id: str) -> Optional[str]:
        self.session_state.start_session(session_id, user_id, time.time())
        self.context_manager.create_context(session_id, user_id, time.time())
        
        memory_retriever = MemoryRetriever(self.memory_store)
        self.memory_retrievers[session_id] = memory_retriever
        
        closing_cache = SessionClosingCache(session_id, user_id)
        self.closing_caches[session_id] = closing_cache
        
        for skill in self.skills_manager.skills:
            if isinstance(skill, MemoryRetrievalSkill):
                skill.memory_retriever = memory_retriever
        
        greeting = self.greeting_handler.start_session(user_id, session_id)
        return greeting

    async def ongoing(self):
        while self.running:
            events = self.queue_manager.dequeue_batch(max_batch_size=10)
            
            if events:
                for event in events:
                    if event.type == 'session_start':
                        await self._handle_session_start(event)
                        continue
                    elif event.type == 'session_end':
                        await self._handle_session_end(event)
                        continue
                    
                    # Process all other events (text, audio, video, etc.)
                    self.context_manager.update_from_event(event)
                    
                    # Extract memories in real-time when we have complete exchanges
                    context = self.context_manager.get_context(event.session_id)
                    closing_cache = self.closing_caches.get(event.session_id)
                    
                    if event.type == 'text' and event.data.get('is_complete'):
                        speaker = event.data.get('speaker')
                        text = event.data.get('text', '')
                        
                        if context and closing_cache:
                            # When we get Adam's response, we have a complete exchange (user + Adam)
                            if speaker == 'adam' and context.last_user_text:
                                logger.info(f"💬 Complete exchange detected - session: {event.session_id}")
                                closing_cache.update_after_exchange(
                                    student_text=context.last_user_text,
                                    ai_text=text,
                                    topic=event.data.get('topic', 'general'),
                                    extractor=self.memory_extractor,
                                    store=self.memory_store
                                )
                            # When we get user text, check if we have previous Adam text for exchange
                            elif speaker == 'user' and context.last_adam_text:
                                logger.info(f"💬 Complete exchange detected - session: {event.session_id}")
                                closing_cache.update_after_exchange(
                                    student_text=text,
                                    ai_text=context.last_adam_text,
                                    topic=event.data.get('topic', 'general'),
                                    extractor=self.memory_extractor,
                                    store=self.memory_store
                                )
                    
                    injections = self.event_processor.process_event(event)
                    
                    for injection in injections:
                        await self.injection_manager.send_to_adam(
                            injection,
                            event.session_id,
                            event.user_id
                        )
            else:
                for session_id, session_data in self.session_state.sessions.items():
                    if not session_data.get('ended', False):
                        context = self.context_manager.get_context(session_id)
                        if context:
                            injections = self.skills_manager.execute_skills(context)
                            for injection in injections:
                                await self.injection_manager.send_to_adam(
                                    injection,
                                    session_id,
                                    session_data['user_id']
                                )
            
            await asyncio.sleep(0.1)

    async def end(self, user_id: str, session_id: str) -> Optional[str]:
        remaining_events = self.queue_manager.dequeue_batch(max_batch_size=100)
        for event in remaining_events:
            if event.session_id == session_id:
                self.context_manager.update_from_event(event)
        
        # Save conversation to file before consolidating
        context = self.context_manager.get_context(session_id)
        if context:
            self._save_conversation(user_id, session_id, context)
        
        closing_cache = self.closing_caches.get(session_id)
        if closing_cache:
            self.memory_consolidator.consolidate_session(user_id, session_id, closing_cache)
            del self.closing_caches[session_id]
        
        memory_retriever = self.memory_retrievers.get(session_id)
        if memory_retriever:
            memory_retriever.clear_session(session_id)
            del self.memory_retrievers[session_id]
        
        self.context_manager.clear_context(session_id)
        self.session_state.end_session(session_id)
        
        closing = self.greeting_handler.end_session(user_id, session_id)
        return closing
    
    def _save_conversation(self, user_id: str, session_id: str, context):
        """Save conversation transcriptions to JSON file"""
        import json
        from datetime import datetime
        
        try:
            data_dir = get_memory_data_dir(user_id) / "conversations"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = data_dir / f"{session_id}.json"
            conversation_data = {
                "session_id": session_id,
                "user_id": user_id,
                "start_time": datetime.fromtimestamp(context.start_time).isoformat(),
                "end_time": datetime.now().isoformat(),
                "turn_count": context.turn_count,
                "turns": context.conversation_turns
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved conversation to {file_path} ({len(context.conversation_turns)} turns)")
        except Exception as e:
            logger.error(f"❌ Error saving conversation: {e}", exc_info=True)

    async def _handle_session_start(self, event):
        greeting = await self.start(event.user_id, event.session_id)
        if greeting:
            await self.injection_manager.send_to_adam(
                greeting,
                event.session_id,
                event.user_id
            )

    async def _handle_session_end(self, event):
        session_data = self.session_state.sessions.get(event.session_id)
        if session_data:
            closing = await self.end(session_data['user_id'], event.session_id)
            if closing:
                await self.injection_manager.send_to_adam(
                    closing,
                    event.session_id,
                    event.user_id
                )

    async def run(self):
        self.running = True
        await self.event_handler.connect()
        await asyncio.gather(
            self.event_handler.listen(),
            self.ongoing()
        )

    async def stop(self):
        self.running = False
        await self.event_handler.disconnect()
        await self.injection_manager.close()


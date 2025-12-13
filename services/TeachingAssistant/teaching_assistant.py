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
        
        # Store MemoryStore instances per user_id
        self.memory_stores: Dict[str, MemoryStore] = {}
        self.memory_extractor = MemoryExtractor()
        # Note: memory_consolidator will be created per user in start() method
        self.memory_consolidators: Dict[str, MemoryConsolidator] = {}
        self.greeting_handler = GreetingHandler()
        
        self.memory_retrievers: Dict[str, MemoryRetriever] = {}
        self.closing_caches: Dict[str, SessionClosingCache] = {}
        
        memory_skill = MemoryRetrievalSkill(memory_retriever=None)
        self.skills_manager.register_skill(memory_skill)
        
        # Set event loop reference in context_manager for non-blocking file I/O
        # This will be set properly in run() method when event loop is available
    
    def _get_or_create_memory_store(self, user_id: str) -> MemoryStore:
        """
        Get or create a MemoryStore instance for a specific user.
        Creates user-specific Pinecone index if it doesn't exist.
        """
        if user_id not in self.memory_stores:
            logger.info(f"🔧 Creating MemoryStore for user: {user_id}")
            self.memory_stores[user_id] = MemoryStore(user_id=user_id)
        return self.memory_stores[user_id]

    async def start(self, user_id: str, session_id: str) -> Optional[str]:
        self.session_state.start_session(session_id, user_id, time.time())
        self.context_manager.create_context(session_id, user_id, time.time())
        
        # Get or create user-specific MemoryStore
        memory_store = self._get_or_create_memory_store(user_id)
        
        # Create user-specific MemoryConsolidator if not exists
        if user_id not in self.memory_consolidators:
            self.memory_consolidators[user_id] = MemoryConsolidator(memory_store, self.memory_extractor)
        
        memory_retriever = MemoryRetriever(memory_store)
        self.memory_retrievers[session_id] = memory_retriever
        
        closing_cache = SessionClosingCache(session_id, user_id)
        self.closing_caches[session_id] = closing_cache
        
        for skill in self.skills_manager.skills:
            if isinstance(skill, MemoryRetrievalSkill):
                skill.memory_retriever = memory_retriever
        
        greeting = self.greeting_handler.start_session(user_id, session_id)
        return greeting

    async def ongoing(self):
        """Main event processing loop with non-blocking operations."""
        while self.running:
            events = self.queue_manager.dequeue_batch(max_batch_size=5)
            
            if events:
                for event in events:
                    if event.type == 'session_start':
                        await self._handle_session_start(event)
                        continue
                    elif event.type == 'session_end':
                        await self._handle_session_end(event)
                        continue
                    
                    self.context_manager.update_from_event(event)
                    
                    if event.type == 'text':
                        speaker = event.data.get('speaker')
                        text = event.data.get('text', '')
                        event_timestamp = event.data.get('timestamp', '')
                        
                        if speaker == 'user':
                            logger.info(f"✅ Received USER turn at {event_timestamp} (length: {len(text)} chars)")
                        elif speaker == 'adam':
                            logger.info(f"✅ Received ADAM turn at {event_timestamp} (length: {len(text)} chars)")
                        
                        context = self.context_manager.get_context(event.session_id)
                        closing_cache = self.closing_caches.get(event.session_id)
                        memory_retriever = self.memory_retrievers.get(event.session_id)
                        
                        if speaker == 'user' and context and text:
                            user_text = text
                            adam_text = context.last_adam_text or ""
                            
                            # Trigger TA-light retrieval (every user turn) - non-blocking
                            if memory_retriever:
                                logger.info(f"🔍 Triggering TA-light retrieval (non-blocking) - session: {event.session_id}, query: {user_text[:50]}...")
                                asyncio.create_task(self._trigger_memory_retrieval_async(
                                    memory_retriever=memory_retriever,
                                    session_id=event.session_id,
                                    user_id=event.user_id,
                                    user_text=user_text,
                                    timestamp=event.timestamp,
                                    adam_text=adam_text
                                ))
                            
                            # Trigger memory extraction (non-blocking)
                            if closing_cache:
                                logger.info(f"💬 Triggering memory extraction (non-blocking) - session: {event.session_id}, text length: {len(user_text)}")
                                asyncio.create_task(self._extract_memories_async(
                                    closing_cache=closing_cache,
                                    user_text=user_text,
                                    adam_text=adam_text,
                                    topic=event.data.get('topic', 'general'),
                                    session_id=event.session_id
                                ))
                    
                    # Process other skills (memory injection happens after async retrieval completes)
                    injections = self.event_processor.process_event(event)
                    
                    for injection in injections:
                        if injection:
                            logger.info(f"💉 Sending injection to Adam (skill-based) - session: {event.session_id}, reason: skill execution, message preview: {injection[:100]}...")
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
                                if injection:
                                    logger.info(f"💉 Sending injection to Adam (skill-based) - session: {session_id}, reason: skill execution, message preview: {injection[:100]}...")
                                    await self.injection_manager.send_to_adam(
                                        injection,
                                        session_id,
                                        session_data['user_id']
                                    )
            
            if not events:
                await asyncio.sleep(0.01)

    async def end(self, user_id: str, session_id: str) -> Optional[str]:
        # Get context FIRST before processing any remaining events
        # This ensures we can save the conversation even if session_end event clears the context
        context = self.context_manager.get_context(session_id)
        
        if context:
            logger.info(f"📝 Ending session {session_id} - Found context with {len(context.conversation_turns)} turns")
        else:
            logger.warning(f"⚠️ Ending session {session_id} - No context found!")
        
        # Process remaining events (but skip session_end to avoid clearing context prematurely)
        remaining_events = self.queue_manager.dequeue_batch(max_batch_size=100)
        for event in remaining_events:
            if event.session_id == session_id and event.type != 'session_end':
                self.context_manager.update_from_event(event)
                # If we processed a text event, update context reference
                if event.type == 'text' and context:
                    context = self.context_manager.get_context(session_id)
        
        # Flush any remaining turn in buffer before saving
        if context:
            context.flush_current_turn()
        
        if context:
            await self._save_conversation_async(user_id, session_id, context)
        else:
            logger.error(f"❌ Cannot save conversation for session {session_id} - context is None")
        
        closing_cache = self.closing_caches.get(session_id)
        if closing_cache:
            # Use user-specific consolidator
            consolidator = self.memory_consolidators.get(user_id)
            if consolidator:
                consolidator.consolidate_session(user_id, session_id, closing_cache)
            else:
                # Fallback: create consolidator if somehow missing
                memory_store = self._get_or_create_memory_store(user_id)
                consolidator = MemoryConsolidator(memory_store, self.memory_extractor)
                consolidator.consolidate_session(user_id, session_id, closing_cache)
            del self.closing_caches[session_id]
        
        memory_retriever = self.memory_retrievers.get(session_id)
        if memory_retriever:
            memory_retriever.clear_session(session_id)
            del self.memory_retrievers[session_id]
        
        self.context_manager.clear_context(session_id)
        self.session_state.end_session(session_id)
        
        closing = self.greeting_handler.end_session(user_id, session_id)
        return closing
    
    async def _save_conversation_async(self, user_id: str, session_id: str, context):
        """Save conversation to file (non-blocking via thread executor)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_conversation_sync, user_id, session_id, context)
    
    def _save_conversation_sync(self, user_id: str, session_id: str, context):
        """Synchronous file save (runs in thread executor)."""
        import os
        import json
        from datetime import datetime
        
        try:
            data_dir = f"Memory/data/{user_id}/conversations"
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = f"{data_dir}/{session_id}.json"
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
            logger.info(f"💉 Sending injection to Adam (session start) - session: {event.session_id}, reason: greeting message, message preview: {greeting[:100]}...")
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
                logger.info(f"💉 Sending injection to Adam (session end) - session: {event.session_id}, reason: closing message, message preview: {closing[:100]}...")
                await self.injection_manager.send_to_adam(
                    closing,
                    event.session_id,
                    event.user_id
                )

    async def run(self):
        """Start service with non-blocking I/O support."""
        self.running = True
        
        loop = asyncio.get_event_loop()
        self.context_manager.set_event_loop(loop)
        
        await self.event_handler.connect()
        await asyncio.gather(
            self.event_handler.listen(),
            self.ongoing()
        )

    async def _trigger_memory_retrieval_async(self, memory_retriever: MemoryRetriever, session_id: str, 
                                               user_id: str, user_text: str, timestamp: float, adam_text: str):
        """Trigger memory retrieval (TA-light and TA-deep) asynchronously and inject memories after completion"""
        try:
            # Run memory retrieval in executor to avoid blocking (Pinecone queries can be slow)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                memory_retriever.on_user_turn,
                session_id,
                user_id,
                user_text,
                timestamp,
                adam_text
            )
            logger.info(f"✅ Memory retrieval completed for session: {session_id}")
            
            # After retrieval completes, get injection and send it
            injection_text = memory_retriever.get_memory_injection(session_id)
            if injection_text:
                logger.info(f"💉 Sending injection to Adam (retrieval-based) - session: {session_id}, reason: memory retrieval completed, message preview: {injection_text[:100]}...")
                await self.injection_manager.send_to_adam(
                    injection_text,
                    session_id,
                    user_id
                )
        except Exception as e:
            logger.error(f"❌ Error in async memory retrieval: {e}", exc_info=True)

    async def _extract_memories_async(self, closing_cache, user_text: str, adam_text: str, topic: str, session_id: str):
        """Extract memories asynchronously without blocking the event loop"""
        try:
            # Get user_id from closing_cache
            user_id = closing_cache.user_id
            
            # Get user-specific memory store
            memory_store = self._get_or_create_memory_store(user_id)
            
            # Run memory extraction in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                closing_cache.update_after_exchange,
                user_text,
                adam_text,
                topic,
                self.memory_extractor,
                memory_store  # Use user-specific store
            )
            logger.info(f"✅ Memory extraction completed for session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Error in async memory extraction: {e}", exc_info=True)

    async def stop(self):
        self.running = False
        await self.event_handler.disconnect()
        await self.injection_manager.close()


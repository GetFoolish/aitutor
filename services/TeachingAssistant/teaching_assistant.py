"""
Teaching Assistant - Enhanced with Memory, Skills, and Event Processing
All session state is stored in MongoDB via SessionManager.
Integrates memory management, skills system, and event-driven processing.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any

from .session_manager import SessionManager
from .core.context_manager import ContextManager
from .core.event_processor import EventProcessor
from .core.config import TeachingAssistantConfig
from .core.decorators import with_retry
from .core.exceptions import MemoryRetrievalError, MemoryConsolidationError, FileOperationError
from .core.file_utils import save_json_file
from .handlers.queue_manager import EventQueueManager
from .handlers.injection_manager import InjectionManager
from .skills_manager import SkillsManager
from .Memory.vector_store import MemoryStore
from .Memory.retriever import MemoryRetriever
from .Memory.extractor import MemoryExtractor
from .Memory.consolidator import MemoryConsolidator, SessionClosingCache

from managers.mongodb_manager import MongoDBManager

from shared.logging_config import get_logger

logger = get_logger(__name__)


class TeachingAssistant:
    """
    TeachingAssistant with memory management, skills, and event processing.
    
    Now includes:
    - Dependency injection for testability
    - Centralized configuration
    - Managed thread pool for blocking I/O
    - Path handling with pathlib
    - Enhanced error handling
    
    Maintains backward compatibility with existing API methods.
    """

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        context_manager: Optional[ContextManager] = None,
        injection_manager: Optional[InjectionManager] = None,
        skills_manager: Optional[SkillsManager] = None,
        config: Optional[TeachingAssistantConfig] = None
    ):
        """
        Initialize TeachingAssistant with dependency injection support.
        
        Args:
            session_manager: Optional SessionManager instance (creates default if None)
            context_manager: Optional ContextManager instance (creates default if None)
            injection_manager: Optional InjectionManager instance (creates default if None)
            skills_manager: Optional SkillsManager instance (creates default if None)
            config: Optional configuration (loads from environment if None)
        """
        # Configuration (load from environment or use default)
        self.config = config or TeachingAssistantConfig.from_env()
        
        # MongoDB client (shared dependency)
        mongo = MongoDBManager()
        
        # Core components (with dependency injection)
        self.session_manager = session_manager or SessionManager(mongo, self.config)
        self.context_manager = context_manager or ContextManager(mongo, self.config)
        self.injection_manager = injection_manager or InjectionManager(self.session_manager, self.config)
        
        # Event processing components
        self.queue_manager = EventQueueManager()
        self.event_processor = EventProcessor(self.context_manager, None)  # Skills added later
        
        # Skills system with dynamic loading
        if skills_manager:
            self.skills_manager = skills_manager
        else:
            skills_dir = Path(__file__).parent / "skills"
            self.skills_manager = SkillsManager(
                skills_dir=str(skills_dir),
                config=self.config
            )
        
        # Memory system
        self.memory_stores: Dict[str, MemoryStore] = {}
        self.memory_extractor = MemoryExtractor()
        self.memory_consolidators: Dict[str, MemoryConsolidator] = {}
        self.memory_retrievers: Dict[str, MemoryRetriever] = {}
        self.closing_caches: Dict[str, SessionClosingCache] = {}
        
        # Memory management - LRU cache for stores
        self._memory_store_access_times: Dict[str, float] = {}
        self._max_memory_stores = 100  # Maximum number of user memory stores to keep in memory
        
        # Thread pool for blocking I/O operations (managed lifecycle)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.io_thread_pool_workers,
            thread_name_prefix=self.config.thread_name_prefix
        )
        
        # Optimization: Cache active sessions to avoid frequent DB polling
        self.active_session_cache = []
        self.last_session_sync_time = 0
        self.last_context_sync_time = 0
        
        # Event processing loop
        self.running = False
        
        # Update event processor with skills manager
        self.event_processor.skills_manager = self.skills_manager
        
        logger.info(
            "[TEACHING_ASSISTANT] Initialized with config-driven architecture, "
            f"thread pool ({self.config.io_thread_pool_workers} workers), and dependency injection"
        )
    
    def _get_greeting_skill(self):
        """Get the greeting skill from skills manager"""
        for skill in self.skills_manager.skills:
            if skill.name == "greeting":
                return skill
        return None

    def start_session(self, user_id: str) -> dict:
        """Start a new session, returns session info (greeting moved to start() method)"""
        session = self.session_manager.create_session(user_id)
        # Greeting is now handled in self.start() to ensure it's memory-aware
        return {
            "session_id": session["session_id"],
            "prompt": "",  # Will be populated by ta.start() in the API layer
            "session_info": self.session_manager.get_session_info(session["session_id"])
        }

    def end_session(self, session_id: str) -> dict:
        """End session, returns closing prompt with stats"""
        session_summary = self.session_manager.end_session(session_id)
        if not session_summary:
            return {
                "prompt": "",
                "session_info": {"session_active": False}
            }

        greeting_skill = self._get_greeting_skill()
        if greeting_skill:
            closing = greeting_skill.get_closing(
                duration_minutes=session_summary.get("duration_minutes", 0),
                questions_answered=session_summary.get("questions_answered", 0)
            )
        else:
            closing = "[SYSTEM PROMPT FOR ADAM]\nThe tutoring session is ending now. Please give the student a warm closing message."
        return {
            "prompt": closing,
            "session_info": session_summary
        }

    def record_question_answered(
        self,
        session_id: str,
        question_id: str,
        is_correct: bool
    ) -> None:
        """Record a question answer"""
        self.session_manager.record_question_answered(session_id, is_correct)

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn"""
        self.session_manager.record_conversation_turn(session_id)

    def check_inactivity(self, session_id: str) -> Optional[str]:
        """Check inactivity and return prompt if needed"""
        if self.session_manager.check_inactivity(session_id):
            greeting_skill = self._get_greeting_skill()
            if greeting_skill:
                prompt = greeting_skill.get_inactivity_prompt()
            else:
                prompt = "[SYSTEM PROMPT FOR ADAM]\nCheck with the student if they're there and if they want to continue."
            self.session_manager.push_instruction(session_id, prompt)
            return prompt
        return None

    def get_session_info(self, session_id: str) -> dict:
        """Get current session info"""
        return self.session_manager.get_session_info(session_id)

    def get_active_session(self, user_id: str) -> Optional[dict]:
        """Get active session for user"""
        return self.session_manager.get_active_session(user_id)

    def push_instruction(self, session_id: str, instruction: str) -> str:
        """Push an instruction to be delivered via SSE"""
        return self.session_manager.push_instruction(session_id, instruction)

    # ============================================================================
    # New Methods for Memory, Skills, and Event Processing
    # ============================================================================

    def _get_or_create_memory_store(self, user_id: str) -> MemoryStore:
        """Get or create MemoryStore for user with LRU eviction"""
        current_time = time.time()
        
        if user_id not in self.memory_stores:
            # Check if we need to evict old stores (LRU)
            if len(self.memory_stores) >= self._max_memory_stores:
                self._evict_oldest_memory_store()
            
            logger.info(f"[TEACHING_ASSISTANT] Creating MemoryStore for user: {user_id}")
            self.memory_stores[user_id] = MemoryStore(user_id=user_id)
        
        # Update access time for LRU
        self._memory_store_access_times[user_id] = current_time
        return self.memory_stores[user_id]
    
    def _evict_oldest_memory_store(self):
        """Evict the least recently used memory store"""
        if not self._memory_store_access_times:
            return
        
        # Find oldest user
        oldest_user = min(self._memory_store_access_times.items(), key=lambda x: x[1])[0]
        
        logger.info(f"[TEACHING_ASSISTANT] Evicting MemoryStore for user {oldest_user} (LRU eviction)")
        
        # Clean up
        if oldest_user in self.memory_stores:
            del self.memory_stores[oldest_user]
        if oldest_user in self._memory_store_access_times:
            del self._memory_store_access_times[oldest_user]
        if oldest_user in self.memory_consolidators:
            del self.memory_consolidators[oldest_user]


    async def start(self, user_id: str, session_id: str) -> Optional[str]:
        """
        Start session with memory and context initialization.
        Called after session is created in MongoDB.
        """
        # Get session to get start_time
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            return None
        
        # Parse start_time from MongoDB datetime
        start_time = session["started_at"]
        if hasattr(start_time, 'timestamp'):
            start_time = start_time.timestamp()
        elif isinstance(start_time, str):
            from datetime import datetime
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
        else:
            start_time = time.time()
        
        # Create context
        self.context_manager.create_context(session_id, user_id, start_time)
        
        # 1. Generate Greeting FIRST (Fast Path)
        # We try to use cached opening data if available, but don't block heavily.
        logger.info(f"[TEACHING_ASSISTANT] Requesting greeting for session {session_id}")
        
        # Get greeting skill from skills manager
        greeting_skill = self._get_greeting_skill()
        if greeting_skill:
            greeting = await greeting_skill.start_session(user_id, session_id)
        else:
            logger.warning("[TEACHING_ASSISTANT] Greeting skill not found, using fallback")
            greeting = "[SYSTEM PROMPT FOR ADAM]\nYou are Adam, an advanced AI Teaching Assistant.\nPlease greet the student warmly."
        
        logger.info(f"[TEACHING_ASSISTANT] Greeting received: {bool(greeting)}, Length: {len(greeting) if greeting else 0}")

        # Also record greeting into conversation context immediately so it's ready
        context = self.context_manager.get_context(session_id)
        if context and greeting:
            ts = context.start_time or time.time()
            context.add_turn(speaker="adam", text=greeting, timestamp=ts)

        # 2. Initialize Memory Components in Background (Async)
        # This prevents pinecone/memory setup from blocking the greeting response.
        asyncio.create_task(self._initialize_memory_components_async(user_id, session_id))

        return greeting

    async def _initialize_memory_components_async(self, user_id: str, session_id: str):
        """Initialize memory components (Pinecone, etc.) in background"""
        try:
            # Initialize memory components
            # Use asyncio.to_thread for MemoryStore creation as it involves blocking network calls
            if user_id not in self.memory_stores:
                logger.info(f"[TEACHING_ASSISTANT] Creating MemoryStore for user: {user_id} (Background)")
                # Offload heavy initialization to thread to avoid blocking event loop
                memory_store = await asyncio.to_thread(MemoryStore, user_id=user_id)
                self.memory_stores[user_id] = memory_store
            else:
                memory_store = self.memory_stores[user_id]
            
            if user_id not in self.memory_consolidators:
                self.memory_consolidators[user_id] = MemoryConsolidator(memory_store, self.memory_extractor)
            
            memory_retriever = MemoryRetriever(memory_store)
            self.memory_retrievers[session_id] = memory_retriever
            
            closing_cache = SessionClosingCache(session_id, user_id)
            self.closing_caches[session_id] = closing_cache
            
            logger.info(f"[TEACHING_ASSISTANT] Background memory initialization complete for session {session_id}")
        except Exception as e:
            logger.error(f"[TEACHING_ASSISTANT] Error in background memory initialization: {e}", exc_info=True)

    async def ongoing(self):
        """Main event processing loop"""
        while self.running:
            # Dequeue batch of events
            events = self.queue_manager.dequeue_batch(max_batch_size=self.config.event_batch_size)
            
            if events:
                for event in events:
                    # Handle session lifecycle events
                    if event.type == 'session_start':
                        # Session initialization and greeting are handled in the API layer
                        # via `ta.start(...)` to avoid double greetings.
                        continue
                    elif event.type == 'session_end':
                        await self._handle_session_end(event)
                        # Force refresh active sessions cache
                        self.last_session_sync_time = 0
                        continue
                    
                    # Update context from event
                    self.context_manager.update_from_event(event)
                    
                    # Process text events for memory
                    if event.type == 'text':
                        speaker = event.data.get('speaker')
                        text = event.data.get('text', '')
                        timestamp = event.timestamp



                        context = self.context_manager.get_context(event.session_id)
                        closing_cache = self.closing_caches.get(event.session_id)
                        memory_retriever = self.memory_retrievers.get(event.session_id)
                        
                        if speaker == 'user' and context and text:
                            user_text = text
                            adam_text = context.last_adam_text or ""
                            
                            # ===== DETAILED LOGGING: Conversation Exchange =====
                            safe_user_text = user_text.encode("utf-8", "replace").decode("utf-8")
                            safe_adam_text = adam_text.encode("utf-8", "replace").decode("utf-8")
                            logger.info("=" * 80)
                            logger.info("[CONVERSATION] New Exchange")
                            logger.info(f"[CONVERSATION] Session: {event.session_id[:20]}... | User: {event.user_id}")
                            logger.info(f"[CONVERSATION] USER >> {safe_user_text}")
                            logger.info(f"[CONVERSATION] ADAM >> {safe_adam_text}")
                            logger.info("=" * 80)
                            # ===================================================
                            
                            # Trigger TA-light retrieval (async) but debounce to avoid
                            # running on every tiny turn in very quick succession.
                            if memory_retriever:
                                # simple debounce: skip if last retrieval was < Ns ago
                                last_rt = context.last_retrieval_time or 0
                                if (timestamp - last_rt) >= self.config.memory_retrieval_debounce:
                                    context.last_retrieval_time = timestamp
                                    asyncio.create_task(self._trigger_memory_retrieval_async(
                                        memory_retriever=memory_retriever,
                                        session_id=event.session_id,
                                        user_id=event.user_id,
                                        user_text=user_text,
                                        timestamp=timestamp,
                                        adam_text=adam_text
                                    ))
                            
                            # Trigger memory extraction (async)
                            if closing_cache:
                                asyncio.create_task(self._extract_memories_async(
                                    closing_cache=closing_cache,
                                    user_text=user_text,
                                    adam_text=adam_text,
                                    topic=event.data.get('topic', 'general'),
                                    session_id=event.session_id
                                ))
                            
                            # Real-time Conversation Saving (Condition 5)
                            # Save the updated context to file immediately to prevent data loss
                            if context:
                                asyncio.create_task(self._save_conversation_async(
                                    event.user_id,
                                    event.session_id,
                                    context
                                ))
                    
                    # Process event through skills
                    injections = self.event_processor.process_event(event)
                    
                    # Send injections, but avoid queueing exact duplicates back-to-back
                    if injections:
                        context = self.context_manager.get_context(event.session_id)
                        last_injected: Optional[str] = getattr(context, "_last_injection", None) if context else None
                        for injection in injections:
                            if not injection:
                                continue
                            if last_injected and injection.strip() == last_injected.strip():
                                continue
                            await self.injection_manager.send_to_adam(
                                injection,
                                event.session_id,
                                event.user_id
                            )
                            if context:
                                setattr(context, "_last_injection", injection.strip())
            # === Optimization: Periodic Maintenance Tasks ===
            now = time.time()

            # 1. Sync dirty contexts to MongoDB (Write-Behind)
            if now - self.last_context_sync_time >= self.config.context_sync_interval:
                self.context_manager.sync_dirty_contexts()
                # Also cleanup stale contexts (TTL enforcement)
                self.context_manager.cleanup_stale_contexts()
                self.last_context_sync_time = now

            # 2. Refresh active session cache periodically (DB Polling Optimization)
            if now - self.last_session_sync_time >= self.config.session_sync_interval:
                self.active_session_cache = self.session_manager.list_active_sessions()
                self.last_session_sync_time = now
                
                # 3. Cleanup orphaned caches (sessions that ended but caches still exist)
                self._cleanup_orphaned_caches()
                
            # Execute skills on cached active sessions (instead of querying DB every loop)
            if not events and self.active_session_cache:
                for session in self.active_session_cache:
                    session_id = session["session_id"]
                    context = self.context_manager.get_context(session_id)
                    if context:
                        injections = self.skills_manager.execute_skills(context)
                        for injection in injections:
                            if injection:
                                await self.injection_manager.send_to_adam(
                                    injection,
                                    session_id,
                                    session["user_id"]
                                )
            
            
            # Continuous processing - yield to event loop to prevent starvation
            if not events:
                await asyncio.sleep(0)  # Yield control without delay
    
    def _cleanup_orphaned_caches(self):
        """Clean up closing caches for sessions that have ended"""
        active_session_ids = {session["session_id"] for session in self.active_session_cache}
        orphaned_sessions = []
        
        for session_id in list(self.closing_caches.keys()):
            if session_id not in active_session_ids:
                orphaned_sessions.append(session_id)
        
        for session_id in orphaned_sessions:
            logger.info(f"[TEACHING_ASSISTANT] Cleaning up orphaned closing cache for session {session_id}")
            del self.closing_caches[session_id]
        
        # Also cleanup memory retrievers for ended sessions
        for session_id in list(self.memory_retrievers.keys()):
            if session_id not in active_session_ids:
                logger.info(f"[TEACHING_ASSISTANT] Cleaning up orphaned memory retriever for session {session_id}")
                self.memory_retrievers[session_id].clear_session(session_id)
                del self.memory_retrievers[session_id]


    async def end(self, user_id: str, session_id: str) -> Optional[str]:
        """End session with memory consolidation"""
        try:
            # 1. Get closing message FIRST (using last generated state)
            # This ensures we don't wait for final consolidation
            logger.info(f"[TEACHING_ASSISTANT] Requesting closing for session {session_id}")
            greeting_skill = self._get_greeting_skill()
            if greeting_skill:
                closing = greeting_skill.end_session(user_id, session_id)
            else:
                logger.warning("[TEACHING_ASSISTANT] Greeting skill not found, using fallback")
                closing = "[SYSTEM PROMPT FOR ADAM]\nThe tutoring session is ending now. Please give the student a warm closing message."
            logger.info(f"[TEACHING_ASSISTANT] Closing received: {bool(closing)}, Length: {len(closing) if closing else 0}")
            
            # Get context before clearing
            context = self.context_manager.get_context(session_id)
            
            if context:
                # Flush any remaining turn
                context.flush_current_turn()
                
                # Save conversation
                await self._save_conversation_async(user_id, session_id, context)
            
            # Consolidate memories (BACKGROUND)
            closing_cache = self.closing_caches.get(session_id)
            if closing_cache:
                consolidator = self.memory_consolidators.get(user_id)
                if consolidator:
                    # Async consolidation - FIRE AND FORGET
                    # Run in background so user doesn't wait
                    asyncio.create_task(consolidator.consolidate_session(user_id, session_id, closing_cache))
                del self.closing_caches[session_id]
            
            # Clean up memory retriever
            memory_retriever = self.memory_retrievers.get(session_id)
            if memory_retriever:
                memory_retriever.clear_session(session_id)
                del self.memory_retrievers[session_id]
            
            # Clear context
            self.context_manager.clear_context(session_id)
            
            return closing
        except Exception as e:
            logger.error(f"[TEACHING_ASSISTANT] Error ending session {session_id}: {e}", exc_info=True)
            return None

    async def _trigger_memory_retrieval_async(self, memory_retriever: MemoryRetriever, session_id: str, 
                                               user_id: str, user_text: str, timestamp: float, adam_text: str):
        """
        Trigger memory retrieval (TA-light and TA-deep) asynchronously and inject memories after completion.
        Uses managed thread pool for blocking Pinecone operations.
        """
        try:
            # Run memory retrieval in managed executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,  # Use managed executor instead of None
                memory_retriever.on_user_turn,
                session_id,
                user_id,
                user_text,
                timestamp,
                adam_text
            )
            logger.info(f"[TEACHING_ASSISTANT] Memory retrieval completed for session: {session_id}")
            
            # After retrieval completes, get injection and send it
            injection_text = memory_retriever.get_memory_injection(session_id)
            if injection_text:
                logger.info(f"[TEACHING_ASSISTANT] Memory injection ready for session: {session_id}")
                await self.injection_manager.send_to_adam(
                    injection_text,
                    session_id,
                    user_id
                )
        except Exception as e:
            # Wrap in specific exception for better error tracking
            raise MemoryRetrievalError(f"Memory retrieval failed for session {session_id}") from e

    async def _extract_memories_async(self, closing_cache, user_text: str, adam_text: str, topic: str, session_id: str):
        """Extract memories asynchronously without blocking the event loop"""
        try:
            # Get user_id from closing_cache
            user_id = closing_cache.user_id
            
            # Get user-specific memory store
            memory_store = self._get_or_create_memory_store(user_id)
            
            # Now native async, await directly
            await closing_cache.update_after_exchange(
                user_text,
                adam_text,
                topic,
                self.memory_extractor,
                memory_store
            )
            logger.debug(f"[TEACHING_ASSISTANT] Memory extraction step completed for session: {session_id}")
        except Exception as e:
            logger.error(f"[TEACHING_ASSISTANT] Error in async memory extraction: {e}", exc_info=True)

    async def _save_conversation_async(self, user_id: str, session_id: str, context):
        """Save conversation to file (non-blocking via managed thread executor)"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,  # Use managed executor
                self._save_conversation_sync,
                user_id,
                session_id,
                context
            )
        except Exception as e:
            raise FileOperationError(f"Failed to save conversation for session {session_id}") from e
    
    def _save_conversation_sync(self, user_id: str, session_id: str, context):
        """
        Synchronous file save (runs in thread executor).
        Now uses pathlib and file_utils for better path handling.
        """
        from datetime import datetime
        
        try:
            # Use pathlib for cross-platform compatibility
            data_dir = self.config.get_conversations_path(user_id)
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
            
            # Use file_utils for consistent error handling
            if save_json_file(file_path, conversation_data):
                logger.debug(f"[TEACHING_ASSISTANT] Saved conversation to {file_path} ({len(context.conversation_turns)} turns)")
            else:
                raise FileOperationError(f"Failed to save conversation to {file_path}")
        except Exception as e:
            logger.error(f"[TEACHING_ASSISTANT] Error saving conversation: {e}", exc_info=True)



    async def _handle_session_end(self, event):
        """Handle session end event"""
        try:
            session = self.session_manager.get_session_by_id(event.session_id)
            if session:
                await self.end(session["user_id"], event.session_id)
        except Exception as e:
             logger.error(f"[TEACHING_ASSISTANT] Error in _handle_session_end: {e}", exc_info=True)

    async def shutdown(self):
        """
        Graceful shutdown of TeachingAssistant.
        Ensures all resources are properly cleaned up.
        """
        logger.info("[TEACHING_ASSISTANT] Initiating graceful shutdown...")
        
        # Stop the event processing loop
        self.running = False
        
        # Wait a moment for ongoing operations to complete
        await asyncio.sleep(0.5)
        
        # Shutdown the thread pool executor
        self._executor.shutdown(wait=True, cancel_futures=False)
        logger.info("[TEACHING_ASSISTANT] Thread pool executor shut down")
        
        logger.info("[TEACHING_ASSISTANT] Shutdown complete")

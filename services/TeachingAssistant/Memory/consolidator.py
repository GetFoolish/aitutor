import os
import sys
import json
import time
import asyncio
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.logging_config import get_logger
from .schema import MemoryType
from .vector_store import MemoryStore
from .extractor import MemoryExtractor
from ..core.decorators import with_retry, with_circuit_breaker, CircuitBreaker
from ..core.exceptions import LLMGenerationError
from services.TeachingAssistant.prompts import (
    get_closing_artifacts_generation_prompt,
    get_goodbye_message_generation_prompt,
    get_next_session_hooks_enhancement_prompt,
    get_next_session_hooks_from_moments_prompt,
    get_personal_relevance_generation_prompt,
    get_welcome_hook_generation_prompt,
    get_suggested_opener_generation_prompt
)

logger = get_logger(__name__)

# Circuit breaker for LLM services
llm_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

class SessionClosingCache:
    # Number of user-adam exchanges to collect before triggering memory generation
    USER_EXCHANGES_FOR_MEMORY_GENERATION = 3
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        # Lock not strictly needed if running in single async event loop task, 
        # but kept for safety if multi-threaded app structure persists.
        # Switched to asyncio.Lock for async context if needed, but here we keep simple logic.
        self._lock = asyncio.Lock()
        self.cache = {
            "new_memories": [],
            "emotional_arc": [],
            "key_moments": [],
            "unfinished_topics": [],
            "topics_covered": [],
            "session_summary": "",
            "goodbye_message": "",
            "next_session_hooks": []
        }
        # Buffer to store exchanges before batch processing
        self.exchange_buffer = []

        # Clear any existing closing cache from previous session
        self.clear_closing_cache()

    
    def clear_closing_cache(self):
        """Clear closing cache file at the start of a new session."""
        try:
            data_dir = f"services/TeachingAssistant/Memory/data/{self.user_id}/memory/TeachingAssistant"
            file_path = f"{data_dir}/TA-closing-retrieval.json"
            
            # Use os.makedirs to ensure directory exists (exist_ok=True)
            os.makedirs(data_dir, exist_ok=True)
            
            # Initialize with empty structure
            closing_data = {
                "session_id": self.session_id,
                "timestamp": time.time(),
                "new_memories": [],
                "emotional_arc": [],
                "key_moments": [],
                "unfinished_topics": [],
                "topics_covered": [],
                "session_summary": "",
                "goodbye_message": "",
                "next_session_hooks": []
            }
            
            # Always overwrite/create the file with empty data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(closing_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cleared closing cache for new session: {self.session_id}")

        except Exception as e:
            logger.error(f"Error clearing closing cache: {e}", exc_info=True)

    async def update_after_exchange(self, student_text: str, ai_text: str, topic: str, extractor: MemoryExtractor, store: MemoryStore):
        """
        Buffer exchanges and extract memories in batches of 3.
        This is called when we receive broadcasts from server.js.
        Thread-safe to avoid race conditions between concurrent updates.
        """
        async with self._lock:
            # Buffer the exchange if we have both sides of the dialogue
            if student_text and ai_text:

                
                current_time = time.time()
                
                # Check for fragmentation/merging with previous exchange
                merged = False
                if self.exchange_buffer:
                    last_exchange = self.exchange_buffer[-1]
                    last_time = last_exchange.get("_timestamp", 0)
                    
                    # If this message arrived very quickly (< 2.0s) after the last one, 
                    # OR if the AI response hasn't happened yet (implying user is still typing in bursts),
                    # we might want to merge.
                    #
                    # Heuristic: If user text is short and rapid, it's likely a fragment.
                    if (current_time - last_time < 2.0):
                        
                        last_exchange["student_text"] += " " + student_text
                        # Update AI text only if new one has content (overwriting empty with content)
                        if ai_text:
                            last_exchange["ai_text"] = ai_text # Update with latest response
                        
                        last_exchange["_timestamp"] = current_time # Reset timer
                        merged = True

                if not merged:
                    self.exchange_buffer.append({
                        "student_text": student_text,
                        "ai_text": ai_text,
                        "topic": topic,
                        "_timestamp": current_time
                    })
                
                # Track topics (simple deduplication)
                if topic and topic not in self.cache["topics_covered"]:
                    self.cache["topics_covered"].append(topic)
                
                logger.debug(
                    "Buffered exchange %s/%s",
                    len(self.exchange_buffer),
                    self.USER_EXCHANGES_FOR_MEMORY_GENERATION,
                )

                # Process batch when we reach the threshold
                if len(self.exchange_buffer) >= self.USER_EXCHANGES_FOR_MEMORY_GENERATION:
                    await self._process_exchange_batch(extractor, store)
            else:
                logger.warning(
                    "Missing text for buffering - student_text: %s, ai_text: %s",
                    bool(student_text),
                    bool(ai_text),
                )
    
    async def _process_exchange_batch(self, extractor: MemoryExtractor, store: MemoryStore):
        """Process buffered exchanges and extract memories."""
        # Caller must hold self._lock (async)
        if not self.exchange_buffer:
            return

        # Filter out exchanges that lost text for some reason
        valid_exchanges = [
            ex for ex in self.exchange_buffer
            if ex.get("student_text") and ex.get("ai_text")
        ]
        if not valid_exchanges:
            logger.info("No valid exchanges to process in batch; clearing buffer")
            self.exchange_buffer.clear()
            return

        batch_size = len(valid_exchanges)
        logger.info("[MEMORY_CONSOLIDATION] Processing batch of %s exchanges for memory extraction", batch_size)
        
        try:
            # Extract memories and analysis from the batch
            # async wrapper for potentially blocking LLM call
            extraction_result = await asyncio.to_thread(
                extractor.extract_memories_batch,
                exchanges=valid_exchanges,
                student_id=self.user_id,
                session_id=self.session_id
            )
            
            # Unpack results
            extracted_memories = extraction_result.get("memories", [])
            emotions = extraction_result.get("emotions", [])
            key_moments = extraction_result.get("key_moments", [])
            unfinished_topics = extraction_result.get("unfinished_topics", [])
            
            # Update cache with analysis data
            self.cache["emotional_arc"].extend(emotions)
            self.cache["key_moments"].extend(key_moments)
            self.cache["unfinished_topics"].extend(unfinished_topics)
            
            # Save extracted memories to store (Pinecone + local)
            if extracted_memories:
                # Count by type before saving
                type_counts = {}
                for mem in extracted_memories:
                    mem_type = mem.type.value
                    type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
                
                logger.info(
                    "[MEMORY_CONSOLIDATION] Saving %s memories to store (breakdown: %s)",
                    len(extracted_memories),
                    type_counts,
                )
                # Async wrapper for vector store save (network I/O)
                await asyncio.to_thread(store.save_memories_batch, extracted_memories)
                
                # CRITICAL FIX: Don't store full Memory objects - just keep statistics
                # Update cache with metadata only to reduce memory footprint
                if "memories_count" not in self.cache:
                    self.cache["memories_count"] = 0
                    self.cache["memories_by_type"] = {}
                
                self.cache["memories_count"] += len(extracted_memories)
                for mem_type, count in type_counts.items():
                    self.cache["memories_by_type"][mem_type] = self.cache["memories_by_type"].get(mem_type, 0) + count
                
                logger.info(
                    "[MEMORY_CONSOLIDATION] Successfully saved %s memories from %s exchanges to Pinecone and local storage",
                    len(extracted_memories),
                    batch_size,
                )
                logger.info(
                    "[MEMORY_CONSOLIDATION] Total session memories: %s (breakdown: %s)",
                    self.cache["memories_count"],
                    self.cache["memories_by_type"]
                )
            else:
                logger.info("[MEMORY_CONSOLIDATION] No memories extracted from batch of %s exchanges", batch_size)
            
            # Clear the buffer after processing
            self.exchange_buffer.clear()
            logger.info("Cleared exchange buffer")
            
            # Trigger regeneration after each batch of 3 exchanges
            # REMOVED THROTTLING: Condition 2 requires this update after every 3 exchanges
            # now = time.time()
            # last_regen = self.cache.get("last_regen_time", 0)
            # if now - last_regen >= 60:
            
            self.cache["last_regen_time"] = time.time()
            logger.info("Triggering closing cache regeneration (async)")
            # Fire and forget task
            asyncio.create_task(self.regenerate_closing_async(extractor))
            
        except Exception as e:
            logger.error(f"Error processing exchange batch: {e}", exc_info=True)
            # Clear buffer even on error to prevent memory buildup
            self.exchange_buffer.clear()
    
    async def flush_remaining_exchanges(self, extractor: MemoryExtractor, store: MemoryStore):
        """Process any remaining exchanges in buffer (called at session end)."""
        async with self._lock:
            if not self.exchange_buffer:
                logger.info("No remaining exchanges to flush")
                return
            
            remaining_count = len(self.exchange_buffer)
            logger.info("Flushing %s remaining exchanges from buffer", remaining_count)
            await self._process_exchange_batch(extractor, store)
        
        # Final regeneration at session end
        logger.info("Final closing cache regeneration at session end")
        await self.regenerate_closing_async(extractor)
    
    async def regenerate_closing_async(self, extractor: MemoryExtractor):
        """Regenerate closing cache content using LLM (non-blocking async)."""
        logger.info("Starting closing cache regeneration (consolidated async)")
        
        try:
            # Prepare context
            topics = ', '.join(self.cache["topics_covered"]) if self.cache["topics_covered"] else "general topics"
            moments = ', '.join(self.cache["key_moments"]) if self.cache["key_moments"] else "None"
            emotions = ' -> '.join(self.cache["emotional_arc"]) if self.cache["emotional_arc"] else "neutral"
            unfinished = self.cache.get("unfinished_topics", [])
            unfinished_str = ', '.join(unfinished) if unfinished else "None"
            current_emotion = self.cache["emotional_arc"][-1] if self.cache["emotional_arc"] else "neutral"

            # Execute LLM call with retry and circuit breaker logic
            data = await self._generate_closing_artifacts_call(
                topics, moments, emotions, current_emotion, unfinished_str
            )
            
            if not data:
                return

            # Update cache
            if data.get("summary"):
                self.cache["session_summary"] = data["summary"]
            if data.get("goodbye"):
                self.cache["goodbye_message"] = data["goodbye"]
            if data.get("hooks"):
                # Merge with actual unfinished topics
                generated_hooks = data["hooks"]
                final_hooks = unfinished[:2] 
                final_hooks.extend(generated_hooks[:3-len(final_hooks)])
                self.cache["next_session_hooks"] = final_hooks[:3]

            logger.info("Closing cache regeneration complete (Consolidated Async)")
            
            # Save closing cache in real-time
            await asyncio.to_thread(self._save_closing_realtime)
            
        except Exception as e:
            logger.error(f"Error in regenerate_closing_async: {e}", exc_info=True)

    @with_circuit_breaker(llm_circuit_breaker, fallback_return=None)
    @with_retry(exceptions=(Exception,), retries=2)
    async def _generate_closing_artifacts_call(self, topics, moments, emotions, current_emotion, unfinished_str):
        """Helper to make the actual LLM call, protected by decorators."""
        from google import genai
        
        prompt = get_closing_artifacts_generation_prompt(
            topics=topics,
            moments=moments,
            emotions=emotions,
            current_emotion=current_emotion,
            unfinished_str=unfinished_str
        )

        def _call_gemini():
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt
            )
            
            # Track token usage for cost calculation
            try:
                from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                extract_and_track_tokens(response, self.session_id, "closing_artifacts_generation")
            except Exception as track_error:
                logger.info(f"Token tracking failed (non-critical): {track_error}")
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())

        # Offload blocking call to thread
        return await asyncio.to_thread(_call_gemini)

    
    def _generate_goodbye_message_sync(self) -> str:
        """Generate goodbye message based on emotional state using LLM (synchronous)."""
        from google import genai
        
        current_emotion = self.cache["emotional_arc"][-1] if self.cache["emotional_arc"] else "neutral"
        moments = ', '.join(self.cache["key_moments"][-3:]) if self.cache["key_moments"] else "None"
        topics = ', '.join(self.cache["topics_covered"]) if self.cache["topics_covered"] else "general topics"
        
        prompt = get_goodbye_message_generation_prompt(current_emotion, moments, topics)
        
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt
            )
            
            # Track token usage for cost calculation
            try:
                from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                extract_and_track_tokens(response, self.session_id, "goodbye_generation")
            except Exception as track_error:
                logger.info(f"Token tracking failed (non-critical): {track_error}")
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Error generating goodbye_message: {e}")
            return ""
    
    def _generate_next_session_hooks_sync(self) -> list:
        """Generate next session hooks based on unfinished topics and key moments."""
        from google import genai
        
        unfinished = self.cache.get("unfinished_topics", [])
        moments = self.cache.get("key_moments", [])
        
        # Base hooks on actual unfinished topics first
        if unfinished:
            hooks = unfinished[:3]
            # Enhance with LLM if needed for better phrasing
            if len(hooks) < 3 and moments:
                summary = self.cache.get("session_summary", "")
                prompt = get_next_session_hooks_enhancement_prompt(
                    unfinished_topics=', '.join(unfinished),
                    key_moments=', '.join(moments[-3:]) if moments else 'None',
                    session_summary=summary if summary else 'Session in progress'
                )
                try:
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-lite",
                        contents=prompt
                    )
                    
                    # Track token usage for cost calculation
                    try:
                        from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                        extract_and_track_tokens(response, self.session_id, "hooks_enhancement")
                    except Exception as track_error:
                        logger.info(f"Token tracking failed (non-critical): {track_error}")
                    
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                    additional = json.loads(text)
                    hooks.extend(additional[:3 - len(hooks)])
                except Exception:
                    pass
            return hooks[:3]
        
        # Fallback: generate from key moments if no unfinished topics
        if moments:
            summary = self.cache.get("session_summary", "")
            topics = ', '.join(self.cache.get("topics_covered", [])) or "general topics"
            prompt = get_next_session_hooks_from_moments_prompt(
                key_moments=', '.join(moments),
                session_summary=summary if summary else 'Session in progress',
                topics_covered=topics
            )
            try:
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt
                )
                
                # Track token usage for cost calculation
                try:
                    from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                    extract_and_track_tokens(response, self.session_id, "hooks_from_moments")
                except Exception as track_error:
                    logger.info(f"Token tracking failed (non-critical): {track_error}")
                
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                return json.loads(text)
            except Exception as e:
                logger.error(f"Error generating next_session_hooks: {e}")
        
        return []
    
    def _save_closing_realtime(self):
        """Save closing cache to JSON file in real-time (called after each regeneration)."""
        try:
            data_dir = f"services/TeachingAssistant/Memory/data/{self.user_id}/memory/TeachingAssistant"
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = f"{data_dir}/TA-closing-retrieval.json"
            
            # Convert Memory objects to dicts for JSON serialization
            cache_copy = self.cache.copy()
            if "new_memories" in cache_copy:
                cache_copy["new_memories"] = [
                    memory.to_dict() if hasattr(memory, 'to_dict') else memory
                    for memory in cache_copy["new_memories"]
                ]
            
            closing_data = {
                "session_id": self.session_id,
                "timestamp": time.time(),
                **cache_copy
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(closing_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Saved closing cache in real-time to %s", file_path)
        except Exception as e:
            logger.error(f"Error saving closing cache in real-time: {e}", exc_info=True)


class MemoryConsolidator:
    def __init__(self, store: MemoryStore, extractor: MemoryExtractor):
        self.store = store
        self.extractor = extractor

    async def consolidate_session(self, user_id: str, session_id: str, closing_cache: SessionClosingCache):
        logger.info("[MEMORY_CONSOLIDATION] Starting session consolidation for session %s, user %s", session_id, user_id)
        
        # Flush any remaining exchanges in buffer (< 3)
        await closing_cache.flush_remaining_exchanges(self.extractor, self.store)
        
        # Get memory statistics (now using count instead of full objects)
        total_memories = closing_cache.cache.get('memories_count', 0)
        memory_counts = closing_cache.cache.get('memories_by_type', {})
        
        logger.info("[MEMORY_CONSOLIDATION] Total memories generated this session: %s (breakdown: %s)", 
                   total_memories, memory_counts)
        logger.info("[MEMORY_CONSOLIDATION] All memories already saved in real-time batches to Pinecone and local storage")

        logger.info(
            "[MEMORY_CONSOLIDATION] Session stats - Emotions: %s, Key moments: %s, Topics covered: %s, Unfinished topics: %s",
            len(closing_cache.cache['emotional_arc']),
            len(closing_cache.cache['key_moments']),
            len(closing_cache.cache['topics_covered']),
            len(closing_cache.cache.get('unfinished_topics', [])),
        )
        
        # Offload file I/O to thread
        await asyncio.to_thread(self._save_closing, user_id, closing_cache)
        
        # Generate opening context (LLM calls inside) in BACKGROUND to avoid blocking session end
        # This ensures the user gets the closing message immediately.
        # It also creates the hook for the next session.
        asyncio.create_task(self._generate_and_save_opening_background(user_id, closing_cache))
        
        # Recalculate session costs now that memory consolidation LLM calls are complete
        # This ensures TA token usage from memory extraction and closing generation are included
        try:
            from services.CostTracking.cost_tracker import CostTracker
            cost_tracker = CostTracker(session_id, user_id)
            cost_tracker.end_session()
            logger.info(f"[COST_TRACKING] Recalculated costs after memory consolidation for session {session_id[:8]}...")
        except Exception as cost_error:
            logger.error(f"[COST_TRACKING] Failed to recalculate costs after consolidation: {cost_error}", exc_info=True)
        
        logger.info("[MEMORY_CONSOLIDATION] Session consolidation complete for %s (Opening context generation running in background)", session_id)

    async def _generate_and_save_opening_background(self, user_id: str, closing_cache: SessionClosingCache):
        """
        Background task to generate and save opening context.
        This runs in parallel after the session is closed.
        """
        try:
            logger.info("Starting background opening context generation for user %s", user_id)
            opening_context = await self._generate_opening_context_async(user_id, closing_cache)
            await asyncio.to_thread(self._save_opening, user_id, opening_context)
            logger.info("Background opening context generation complete for user %s", user_id)
            
            # Final cost recalculation after all opening context LLM calls complete
            # This captures the opening generation tokens (personal_relevance, welcome_hook, suggested_opener)
            try:
                session_id = closing_cache.session_id
                from services.CostTracking.cost_tracker import CostTracker
                cost_tracker = CostTracker(session_id, user_id)
                cost_tracker.end_session()
                logger.info(f"[COST_TRACKING] Final cost recalculation after opening generation for session {session_id[:8]}...")
            except Exception as cost_error:
                logger.error(f"[COST_TRACKING] Failed to recalculate costs after opening generation: {cost_error}", exc_info=True)
        except Exception as e:
            logger.error(f"Error in background opening context generation: {e}", exc_info=True)

    async def _generate_opening_context_async(self, user_id: str, closing_cache: SessionClosingCache) -> dict:
        """Generate personalized opening context for next session using LLM (Async wrapper)."""
        logger.info("Generating opening context (async)")
        # We can implement a similar _generate_opening_context_call protected method 
        # or just wrap the existing logic in to_thread here for simplicity in this step.
        return await asyncio.to_thread(self._generate_opening_context, user_id, closing_cache, closing_cache.session_id)

    def _generate_personal_relevance(self, user_id: str, session_id: str = None) -> str:
        """Generate time-contextual personal relevance string."""
        from google import genai
        from datetime import datetime
        
        personal_memories = self.store.search(
            query="personal information about student schedule hobbies recurring events",
            student_id=user_id,
            mem_type=MemoryType.PERSONAL,
            top_k=5
        )
        
        if not personal_memories:
            return ""
        
        now = datetime.now()
        day_name = now.strftime("%A")
        time_context = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        personal_texts = [m["memory"].text for m in personal_memories[:3]]
        
        prompt = get_personal_relevance_generation_prompt(
            day_name=day_name,
            time_context=time_context,
            personal_texts=', '.join(personal_texts)
        )

        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt
            )
            
            # Track token usage for cost calculation
            if session_id:
                try:
                    from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                    extract_and_track_tokens(response, session_id, "opening_personal_relevance")
                except Exception as track_error:
                    logger.info(f"Token tracking failed (non-critical): {track_error}")
            
            relevance = response.text.strip()
            return relevance if relevance and len(relevance) > 0 else ""
        except Exception as e:
            logger.error(f"❌ Error generating personal_relevance: {e}")
            return ""

    def _generate_opening_context(self, user_id: str, closing_cache: SessionClosingCache, session_id: str = None) -> dict:
        """Generate personalized opening context for next session using LLM."""
        from google import genai
        
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Extract data from closing cache
        session_summary = closing_cache.cache.get("session_summary", "")
        emotional_arc = closing_cache.cache.get("emotional_arc", [])
        key_moments = closing_cache.cache.get("key_moments", [])
        unfinished_topics = closing_cache.cache.get("unfinished_topics", [])
        
        emotional_state_last = emotional_arc[-1] if emotional_arc else "neutral"
        
        # Generate time-contextual personal relevance
        personal_relevance = self._generate_personal_relevance(user_id, session_id)
        
        # Generate welcome_hook - reference specific achievements
        welcome_hook = ""
        if session_summary or key_moments:
            achievement = key_moments[-1] if key_moments else ""
            welcome_hook_prompt = get_welcome_hook_generation_prompt(
                session_summary=session_summary if session_summary else 'Previous session',
                achievement=achievement if achievement else 'Session completed',
                emotional_state_last=emotional_state_last
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=welcome_hook_prompt
                )
                
                # Track token usage for cost calculation
                if session_id:
                    try:
                        from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                        extract_and_track_tokens(response, session_id, "opening_welcome_hook")
                    except Exception as track_error:
                        logger.info(f"Token tracking failed (non-critical): {track_error}")
                
                welcome_hook = response.text.strip()
            except Exception as e:
                logger.error(f"❌ Error generating welcome_hook: {e}")
        
        # Use actual unfinished topics from closing cache
        unfinished_threads = unfinished_topics[:3] if unfinished_topics else []
        
        # Generate suggested_opener
        suggested_opener = ""
        if session_summary or personal_relevance or unfinished_threads:
            opener_prompt = get_suggested_opener_generation_prompt(
                last_session=session_summary if session_summary else 'Previous session completed',
                emotional_state_last=emotional_state_last,
                personal_relevance=personal_relevance if personal_relevance else 'None',
                unfinished_topics=', '.join(unfinished_threads[:2]) if unfinished_threads else 'None'
            )

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=opener_prompt
                )
                
                # Track token usage for cost calculation
                if session_id:
                    try:
                        from services.TeachingAssistant.token_tracker import extract_and_track_tokens
                        extract_and_track_tokens(response, session_id, "opening_suggested_opener")
                    except Exception as track_error:
                        logger.info(f"Token tracking failed (non-critical): {track_error}")
                
                suggested_opener = response.text.strip()
            except Exception as e:
                logger.error(f"❌ Error generating suggested_opener: {e}")
        
        return {
            "welcome_hook": welcome_hook,
            "last_session_summary": session_summary,
            "unfinished_threads": unfinished_threads,
            "personal_relevance": personal_relevance,
            "emotional_state_last": emotional_state_last,
            "suggested_opener": suggested_opener
        }

    def _save_closing(self, user_id: str, closing_cache: SessionClosingCache):
        data_dir = f"services/TeachingAssistant/Memory/data/{user_id}/memory/TeachingAssistant"
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = f"{data_dir}/TA-closing-retrieval.json"
        
        # Convert Memory objects to dicts for JSON serialization
        cache_copy = closing_cache.cache.copy()
        if "new_memories" in cache_copy:
            cache_copy["new_memories"] = [
                memory.to_dict() if hasattr(memory, 'to_dict') else memory
                for memory in cache_copy["new_memories"]
            ]
        
        closing_data = {
            "session_id": closing_cache.session_id,
            "timestamp": time.time(),
            **cache_copy
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(closing_data, f, indent=2, ensure_ascii=False)

    def _save_opening(self, user_id: str, opening_context: dict):
        """Save opening context to MongoDB users collection"""
        from managers.mongodb_manager import mongo_db
        
        try:
            # Add timestamp to opening context (using time.time() to match existing pattern)
            opening_data = {
                "timestamp": time.time(),
                **opening_context
            }
            
            # Update user document with opening_memory field
            # This ensures only one opening memory exists per user (updated on each session close)
            mongo_db.users.update_one(
                {"user_id": user_id},
                {"$set": {"opening_memory": opening_data}}
            )
            
            logger.info(f"[OPENING_MEMORY] Saved opening memory to MongoDB for user {user_id}")
        except Exception as e:
            logger.error(f"[OPENING_MEMORY] Failed to save opening memory to MongoDB: {e}", exc_info=True)

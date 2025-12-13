import os
import json
import time
import logging
from .schema import MemoryType
from .vector_store import MemoryStore
from .extractor import MemoryExtractor

logger = logging.getLogger(__name__)

class SessionClosingCache:
    # Number of user-adam exchanges to collect before triggering memory generation
    USER_EXCHANGES_FOR_MEMORY_GENERATION = 3
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.cache = {
            "new_memories": [],
            "emotional_arc": [],
            "key_moments": [],
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
            
            # Check if file exists
            if os.path.exists(file_path):
                # Initialize with empty structure
                closing_data = {
                    "session_id": self.session_id,
                    "timestamp": time.time(),
                    "new_memories": [],
                    "emotional_arc": [],
                    "key_moments": [],
                    "topics_covered": [],
                    "session_summary": "",
                    "goodbye_message": "",
                    "next_session_hooks": []
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(closing_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"🧹 Cleared closing cache for new session: {self.session_id}")
            else:
                logger.info(f"ℹ️ No existing closing cache to clear for user: {self.user_id}")
        except Exception as e:
            logger.error(f"❌ Error clearing closing cache: {e}", exc_info=True)

    def update_after_exchange(self, student_text: str, ai_text: str, topic: str, extractor: MemoryExtractor, store: MemoryStore):
        """
        Buffer exchanges and extract memories in batches of 3.
        This is called when we receive broadcasts from server.js.
        """
        # Detect emotion
        emotion = extractor.detect_emotion(student_text)
        if emotion:
            self.cache["emotional_arc"].append(emotion)

        # Track key moments
        if "struggle" in student_text.lower() or "difficult" in student_text.lower():
            self.cache["key_moments"].append("struggle")
        if "understand" in student_text.lower() or "got it" in student_text.lower():
            self.cache["key_moments"].append("breakthrough")

        # Track topics
        if topic:
            if topic not in self.cache["topics_covered"]:
                self.cache["topics_covered"].append(topic)

        # Buffer the exchange
        if student_text and ai_text:
            self.exchange_buffer.append({
                "student_text": student_text,
                "ai_text": ai_text,
                "topic": topic or "general"
            })
            logger.info(f"📦 Buffered exchange {len(self.exchange_buffer)}/{self.USER_EXCHANGES_FOR_MEMORY_GENERATION}")
            
            # Process batch when we reach the threshold
            if len(self.exchange_buffer) >= self.USER_EXCHANGES_FOR_MEMORY_GENERATION:
                self._process_exchange_batch(extractor, store)
        else:
            logger.warning(f"⚠️ Missing text for buffering - student_text: {bool(student_text)}, ai_text: {bool(ai_text)}")
    
    def _process_exchange_batch(self, extractor: MemoryExtractor, store: MemoryStore):
        """Process buffered exchanges and extract memories."""
        if not self.exchange_buffer:
            return
        
        batch_size = len(self.exchange_buffer)
        logger.info(f"🔍 Processing batch of {batch_size} exchanges for memory extraction...")
        
        try:
            # Extract memories from the batch
            extracted_memories = extractor.extract_memories_batch(
                exchanges=self.exchange_buffer,
                student_id=self.user_id,
                session_id=self.session_id
            )
            
            # Save extracted memories to store (Pinecone + local)
            if extracted_memories:
                logger.info(f"💾 Saving {len(extracted_memories)} memories from batch to store...")
                store.save_memories_batch(extracted_memories)
                # Also add to cache for session consolidation
                self.cache["new_memories"].extend(extracted_memories)
                logger.info(f"✅ Successfully saved {len(extracted_memories)} memories from {batch_size} exchanges")
            else:
                logger.info(f"ℹ️ No memories extracted from batch of {batch_size} exchanges")
            
            # Clear the buffer after processing
            self.exchange_buffer.clear()
            logger.info("🧹 Cleared exchange buffer")
            
            # Trigger regeneration after each batch of 3 exchanges (async, non-blocking)
            logger.info("🔄 Triggering closing cache regeneration (after 3 exchanges)...")
            import asyncio
            import threading
            try:
                # Try to get the running loop
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(self._regenerate_closing(extractor))
                except RuntimeError:
                    # No running loop - create and run in a new thread
                    def run_async():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(self._regenerate_closing(extractor))
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_async, daemon=True)
                    thread.start()
            except Exception as e:
                logger.error(f"❌ Error creating regeneration task: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"❌ Error processing exchange batch: {e}", exc_info=True)
            # Clear buffer even on error to prevent memory buildup
            self.exchange_buffer.clear()
    
    def flush_remaining_exchanges(self, extractor: MemoryExtractor, store: MemoryStore):
        """Process any remaining exchanges in buffer (called at session end)."""
        if not self.exchange_buffer:
            logger.info("ℹ️ No remaining exchanges to flush")
            return
        
        remaining_count = len(self.exchange_buffer)
        logger.info(f"🚿 Flushing {remaining_count} remaining exchanges from buffer...")
        self._process_exchange_batch(extractor, store)
        
        # Final regeneration at session end (sync to ensure completion)
        logger.info("🔄 Final closing cache regeneration at session end...")
        import asyncio
        try:
            # Run synchronously to ensure completion before session ends
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create task and wait
                task = asyncio.create_task(self._regenerate_closing(extractor))
                # Note: This won't block if loop is already running
            else:
                # If no loop, run synchronously
                loop.run_until_complete(self._regenerate_closing(extractor))
        except Exception as e:
            logger.error(f"❌ Error in final regeneration: {e}", exc_info=True)
    
    async def _regenerate_closing(self, extractor: MemoryExtractor):
        """Regenerate closing cache content using LLM (runs in background after every 3 exchanges)."""
        logger.info("🔄 Starting closing cache regeneration...")
        
        try:
            # Generate session summary
            summary = await self._generate_session_summary()
            if summary:
                self.cache["session_summary"] = summary
                logger.info(f"✅ Generated session_summary: {summary[:100]}...")
            
            # Generate goodbye message
            goodbye = await self._generate_goodbye_message()
            if goodbye:
                self.cache["goodbye_message"] = goodbye
                logger.info(f"✅ Generated goodbye_message: {goodbye[:100]}...")
            
            # Generate next session hooks
            hooks = await self._generate_next_session_hooks()
            if hooks:
                self.cache["next_session_hooks"] = hooks
                logger.info(f"✅ Generated next_session_hooks: {hooks}")
            
            logger.info("✅ Closing cache regeneration complete")
            
            # Save closing cache in real-time
            self._save_closing_realtime()
            
        except Exception as e:
            logger.error(f"❌ Error in _regenerate_closing: {e}", exc_info=True)
    
    async def _generate_session_summary(self) -> str:
        """Generate session summary using LLM."""
        import google.generativeai as genai
        
        topics = ', '.join(self.cache["topics_covered"]) if self.cache["topics_covered"] else "general topics"
        moments = ', '.join(self.cache["key_moments"]) if self.cache["key_moments"] else "None"
        emotions = ' → '.join(self.cache["emotional_arc"]) if self.cache["emotional_arc"] else "neutral"
        
        prompt = f"""Summarize this tutoring session in 1-2 concise sentences.

Topics covered: {topics}
Key moments: {moments}
Emotional journey: {emotions}

Focus on what was learned and how the student felt. Be specific but brief.
Return ONLY the summary, nothing else."""
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Error generating session_summary: {e}")
            return ""  # No fallback - return empty on failure
    
    async def _generate_goodbye_message(self) -> str:
        """Generate goodbye message based on emotional state using LLM."""
        import google.generativeai as genai
        
        current_emotion = self.cache["emotional_arc"][-1] if self.cache["emotional_arc"] else "neutral"
        moments = ', '.join(self.cache["key_moments"][-3:]) if self.cache["key_moments"] else "None"
        topics = ', '.join(self.cache["topics_covered"]) if self.cache["topics_covered"] else "general topics"
        
        prompt = f"""Generate a warm, natural goodbye message for a tutoring session.

Current emotional state: {current_emotion}
Key moments: {moments}
Topics covered: {topics}

Create a brief (1-2 sentences) goodbye that:
- Acknowledges their emotional state
- Encourages them appropriately
- Feels genuine and personal

Return ONLY the goodbye message, nothing else."""
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Error generating goodbye_message: {e}")
            return ""  # No fallback - return empty on failure
    
    async def _generate_next_session_hooks(self) -> list:
        """Generate next session hooks using LLM."""
        import google.generativeai as genai
        
        summary = self.cache.get("session_summary", "")
        moments = ', '.join(self.cache["key_moments"]) if self.cache["key_moments"] else "None"
        topics = ', '.join(self.cache["topics_covered"]) if self.cache["topics_covered"] else "general topics"
        
        prompt = f"""Based on this tutoring session, suggest 2-3 specific topics or questions to explore in the next session.

Session summary: {summary if summary else 'Session in progress'}
Key moments: {moments}
Topics covered: {topics}

Return as a JSON array of strings. Each should be:
- Specific and actionable
- Natural continuation from this session
- Phrased as a topic or question

Example: ["Continue practicing completing the square", "Explore how discriminant relates to graph shape", "Review word problem strategies"]

Return ONLY the JSON array, nothing else."""
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = await model.generate_content_async(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"❌ Error generating next_session_hooks: {e}")
            return []  # No fallback - return empty on failure
    
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
            
            logger.info(f"💾 Saved closing cache in real-time to {file_path}")
        except Exception as e:
            logger.error(f"❌ Error saving closing cache in real-time: {e}", exc_info=True)


class MemoryConsolidator:
    def __init__(self, store: MemoryStore, extractor: MemoryExtractor):
        self.store = store
        self.extractor = extractor

    def consolidate_session(self, user_id: str, session_id: str, closing_cache: SessionClosingCache):
        logger.info(f"🔄 Consolidating session {session_id} for user {user_id}")
        
        # Flush any remaining exchanges in buffer (< 3)
        closing_cache.flush_remaining_exchanges(self.extractor, self.store)
        
        # Note: Memories are already saved in real-time batches, no need to save again
        logger.info(f"ℹ️ All memories already saved in real-time batches")

        logger.info(f"📊 Session stats - Emotions: {len(closing_cache.cache['emotional_arc'])}, Key moments: {len(closing_cache.cache['key_moments'])}, Topics: {len(closing_cache.cache['topics_covered'])}")
        
        self._save_closing(user_id, closing_cache)
        opening_context = self._generate_opening_context(user_id, closing_cache)
        self._save_opening(user_id, opening_context)
        logger.info(f"✅ Session consolidation complete for {session_id}")

    def _generate_opening_context(self, user_id: str, closing_cache: SessionClosingCache) -> dict:
        """Generate personalized opening context for next session using LLM."""
        import google.generativeai as genai
        
        # Initialize model locally for this method to ensure it's available
        # This fixes UnboundLocalError if first block is skipped but later blocks run
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        
        # Get personal memories for relevance
        personal_memories = self.store.search(
            query="personal information about student",
            student_id=user_id,
            mem_type=MemoryType.PERSONAL,
            top_k=5
        )
        
        # Extract data from closing cache
        session_summary = closing_cache.cache.get("session_summary", "")
        emotional_arc = closing_cache.cache.get("emotional_arc", [])
        key_moments = closing_cache.cache.get("key_moments", [])
        topics_covered = closing_cache.cache.get("topics_covered", [])
        next_session_hooks = closing_cache.cache.get("next_session_hooks", [])
        
        emotional_state_last = emotional_arc[-1] if emotional_arc else "neutral"
        personal_relevance_list = [m["memory"].text for m in personal_memories[:3]]
        
        # Generate welcome_hook using LLM
        # Only generate if we have session data, otherwise skip
        if session_summary or key_moments or topics_covered:
            welcome_hook_prompt = f"""Generate a warm, natural welcome message for a student returning to their next tutoring session.

Last session summary: {session_summary if session_summary else 'Session completed'}
Emotional state when they left: {emotional_state_last}
Key moments: {', '.join(key_moments) if key_moments else 'None'}
Topics covered: {', '.join(topics_covered) if topics_covered else 'general topics'}
Personal context: {', '.join(personal_relevance_list) if personal_relevance_list else 'None'}

Create a brief (1-2 sentences), friendly welcome that references their last session naturally. Don't be overly formal.
Return ONLY the welcome message, nothing else."""

            try:
                response = model.generate_content(welcome_hook_prompt)
                welcome_hook = response.text.strip()
            except Exception as e:
                logger.error(f"❌ Error generating welcome_hook: {e}")
                welcome_hook = ""  # No fallback
        else:
            welcome_hook = ""  # No data to generate from
        
        # Generate unfinished_threads from next_session_hooks and key_moments
        unfinished_threads = []
        if next_session_hooks:
            unfinished_threads.extend(next_session_hooks[:3])
        
        # If no hooks and we have session data, generate from key moments
        if not unfinished_threads and (key_moments or topics_covered):
            unfinished_prompt = f"""Based on this tutoring session, suggest 2-3 specific questions or topics to explore in the next session.

Session summary: {session_summary if session_summary else 'Session completed'}
Key moments: {', '.join(key_moments) if key_moments else 'None'}
Topics covered: {', '.join(topics_covered) if topics_covered else 'general topics'}

Return as a JSON array of strings. Each should be a specific, actionable question or topic.
Example: ["Could we review the quadratic formula and practice more examples?", "Let's explore how to apply this concept to word problems."]

Return ONLY the JSON array, nothing else."""

            try:
                response = model.generate_content(unfinished_prompt)
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                unfinished_threads = json.loads(text)
            except Exception as e:
                logger.error(f"❌ Error generating unfinished_threads: {e}")
                unfinished_threads = []  # No fallback
        
        # Generate suggested_opener using LLM
        # Only generate if we have session data
        if session_summary or personal_relevance_list or unfinished_threads:
            opener_prompt = f"""Generate a natural, conversational opening line for an AI tutor to start the next session with this student.

Last session: {session_summary if session_summary else 'Previous session completed'}
Emotional state: {emotional_state_last}
Personal context: {', '.join(personal_relevance_list) if personal_relevance_list else 'None'}
Unfinished topics: {', '.join(unfinished_threads[:2]) if unfinished_threads else 'None'}

Create a warm, natural conversation starter (1-2 sentences) that feels genuine and personal. Reference their last session or personal life if relevant.
Don't be overly formal or robotic. Sound like a friendly tutor who remembers them.

Return ONLY the opener, nothing else."""

            try:
                response = model.generate_content(opener_prompt)
                suggested_opener = response.text.strip()
            except Exception as e:
                logger.error(f"❌ Error generating suggested_opener: {e}")
                suggested_opener = ""  # No fallback
        else:
            suggested_opener = ""  # No data to generate from
        
        return {
            "welcome_hook": welcome_hook,
            "last_session_summary": session_summary,
            "unfinished_threads": unfinished_threads,
            "personal_relevance": personal_relevance_list,
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
        data_dir = f"services/TeachingAssistant/Memory/data/{user_id}/memory/TeachingAssistant"
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = f"{data_dir}/TA-opening-retrieval.json"
        opening_data = {
            "timestamp": time.time(),
            **opening_context
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(opening_data, f, indent=2, ensure_ascii=False)

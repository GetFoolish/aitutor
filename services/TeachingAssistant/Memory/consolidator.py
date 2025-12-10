import os
import json
import time
import logging
from .schema import MemoryType
from .vector_store import MemoryStore
from .extractor import MemoryExtractor
from . import get_memory_data_dir

logger = logging.getLogger(__name__)

class SessionClosingCache:
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

    def update_after_exchange(self, student_text: str, ai_text: str, topic: str, extractor: MemoryExtractor, store: MemoryStore):
        """
        Update cache after each exchange and extract memories in real-time.
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

        # Extract memories in real-time from the exchange
        if student_text and ai_text:
            logger.info("🔍 Starting memory extraction for exchange...")
            extracted_memories = extractor.extract_memories(
                student_text=student_text,
                ai_text=ai_text,
                topic=topic or "general",
                student_id=self.user_id,
                session_id=self.session_id
            )
            
            # Save extracted memories immediately to store (Pinecone + local)
            if extracted_memories:
                logger.info(f"💾 Saving {len(extracted_memories)} memories to store...")
                store.save_memories_batch(extracted_memories)
                # Also add to cache for session consolidation
                self.cache["new_memories"].extend(extracted_memories)
                logger.info(f"✅ Successfully saved {len(extracted_memories)} memories")
            else:
                logger.info("ℹ️ No memories extracted from this exchange (extractor returned empty list)")
        else:
            logger.warning(f"⚠️ Missing text for extraction - student_text: {bool(student_text)}, ai_text: {bool(ai_text)}")

class MemoryConsolidator:
    def __init__(self, store: MemoryStore, extractor: MemoryExtractor):
        self.store = store
        self.extractor = extractor

    def consolidate_session(self, user_id: str, session_id: str, closing_cache: SessionClosingCache):
        logger.info(f"🔄 Consolidating session {session_id} for user {user_id}")
        
        # Save any remaining memories that weren't saved in real-time
        remaining_memories = closing_cache.cache["new_memories"]
        if remaining_memories:
            logger.info(f"💾 Saving {len(remaining_memories)} remaining memories...")
            self.store.save_memories_batch(remaining_memories)
        else:
            logger.info("ℹ️ No remaining memories to save")

        logger.info(f"📊 Session stats - Emotions: {len(closing_cache.cache['emotional_arc'])}, Key moments: {len(closing_cache.cache['key_moments'])}, Topics: {len(closing_cache.cache['topics_covered'])}")
        
        self._save_closing(user_id, closing_cache)
        opening_context = self._generate_opening_context(user_id, closing_cache)
        self._save_opening(user_id, opening_context)
        logger.info(f"✅ Session consolidation complete for {session_id}")

    def _generate_opening_context(self, user_id: str, closing_cache: SessionClosingCache) -> dict:
        personal_memories = self.store.search(
            query="personal information about student",
            student_id=user_id,
            mem_type=MemoryType.PERSONAL,
            top_k=5
        )
        
        return {
            "welcome_hook": "Welcome back!",
            "last_session_summary": closing_cache.cache.get("session_summary", ""),
            "unfinished_threads": [],
            "personal_relevance": [m["memory"].text for m in personal_memories[:3]],
            "emotional_state_last": closing_cache.cache.get("emotional_arc", [])[-1] if closing_cache.cache.get("emotional_arc") else None,
            "suggested_opener": "How can I help you today?"
        }

    def _save_closing(self, user_id: str, closing_cache: SessionClosingCache):
        data_dir = get_memory_data_dir(user_id) / "memory" / "TeachingAssistant"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / "TA-closing-retrieval.json"
        closing_data = {
            "session_id": closing_cache.session_id,
            "timestamp": time.time(),
            **closing_cache.cache
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(closing_data, f, indent=2, ensure_ascii=False)

    def _save_opening(self, user_id: str, opening_context: dict):
        data_dir = get_memory_data_dir(user_id) / "memory" / "TeachingAssistant"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / "TA-opening-retrieval.json"
        opening_data = {
            "timestamp": time.time(),
            **opening_context
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(opening_data, f, indent=2, ensure_ascii=False)


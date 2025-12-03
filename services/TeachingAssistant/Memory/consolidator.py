import os
import json
import time
import threading
import uuid
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

from .schema import Memory, MemoryType
from .vector_store import MemoryStore
from .extractor import MemoryExtractor
from .embeddings import cosine_similarity, get_embeddings_batch

_executor = ThreadPoolExecutor(max_workers=2)


class SessionClosingCache:
    def __init__(self, student_id: str, session_id: Optional[str] = None, consolidator: Optional['MemoryConsolidator'] = None):
        self.student_id = student_id
        self.session_id = session_id
        self.consolidator = consolidator
        self.cache = {
            'session_summary': '',
            'key_moments': [],
            'new_memories': [],
            'emotional_arc': [],
            'next_session_hooks': [],
            'goodbye_message': '',
            'topics_covered': [],
            'start_time': datetime.utcnow().isoformat() + 'Z'
        }
        self._extractor = None

    def _get_extractor(self) -> MemoryExtractor:
        if self._extractor is None:
            self._extractor = MemoryExtractor()
        return self._extractor

    def update_after_exchange(self, student_text: str, ai_text: str, topic: str = 'general') -> None:
        if topic and topic not in self.cache['topics_covered']:
            self.cache['topics_covered'].append(topic)

        try:
            extractor = self._get_extractor()
            emotion = extractor.detect_emotion(student_text)
            if emotion:
                self.cache['emotional_arc'].append(emotion)
        except:
            pass

        key_moment = self._detect_key_moment(student_text, ai_text)
        if key_moment:
            self.cache['key_moments'].append(key_moment)

        self._regenerate_closing()

    def _detect_key_moment(self, student_text: str, ai_text: str) -> Optional[str]:
        if not student_text or len(student_text.strip()) < 10:
            return None

        try:
            extractor = self._get_extractor()
            prompt = f"""Is this student message a KEY MOMENT (breakthrough or struggle)?

Student said: "{student_text}"

Rules:
- Breakthrough: Student shows genuine understanding, excitement about learning, "aha" moment
- Struggle: Student expresses real confusion, frustration, or being stuck
- Return ONLY one of: "breakthrough: [brief description]" or "struggle: [brief description]" or "none"
- Be selective - most messages are NOT key moments

Response (one line only):"""

            model = extractor._get_model()
            response = model.generate_content(prompt)
            result = response.text.strip().lower()

            if result.startswith('breakthrough:'):
                return f"Breakthrough: {result[13:].strip()}"
            elif result.startswith('struggle:'):
                return f"Struggled: {result[9:].strip()}"
            return None
        except:
            return None

    def _regenerate_closing(self) -> None:
        _executor.submit(self._do_regenerate_closing)

    def _do_regenerate_closing(self) -> None:
        arc = self.cache['emotional_arc']
        moments = self.cache['key_moments']
        topics = self.cache['topics_covered']

        if arc:
            last_emotion = arc[-1]
            if last_emotion in ['frustrated', 'confused']:
                self.cache['goodbye_message'] = "We'll pick this up next time - you're closer than you think!"
            elif last_emotion == 'excited':
                self.cache['goodbye_message'] = "Great work today! Can't wait to build on this next time."
            elif last_emotion == 'tired':
                self.cache['goodbye_message'] = "Good effort today! Get some rest and we'll continue fresh next time."
            else:
                self.cache['goodbye_message'] = "Nice session! See you next time."
        else:
            self.cache['goodbye_message'] = "Good session! See you next time."

        hooks = []
        if moments:
            last_moment = moments[-1]
            if 'Breakthrough' in last_moment:
                hooks.append("Build on today's breakthrough")
            elif 'Struggled' in last_moment:
                hooks.append("Revisit what we struggled with")

        if topics:
            hooks.append(f"Continue with {topics[-1]}")

        self.cache['next_session_hooks'] = hooks

        summary_parts = []
        if moments:
            summary_parts.append(f"Key moments: {'; '.join(moments)}")
        if arc and len(arc) > 1:
            summary_parts.append(f"Emotional journey: {' -> '.join(arc[-5:])}")
        if topics and topics != ['general']:
            summary_parts.append(f"Topics: {', '.join(topics)}")

        self.cache['session_summary'] = '. '.join(summary_parts) if summary_parts else ''
        
        if self.consolidator and self.session_id:
            _executor.submit(self._save_closing_to_json)

    def _save_closing_to_json(self) -> None:
        if not self.consolidator or not self.session_id:
            return
        
        try:
            closing_data = self.consolidator._format_closing_for_ta_memory(
                self, self.session_id, self.student_id, None
            )
            data = self.consolidator._load_ta_closing_file()
            
            existing_index = None
            for i, closing in enumerate(data['closings']):
                if closing.get('session_id') == self.session_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                data['closings'][existing_index] = closing_data
            else:
                data['closings'].append(closing_data)
            
            self.consolidator._save_ta_closing_file(data)
        except Exception:
            pass

    def add_memory(self, memory: Memory) -> None:
        self.cache['new_memories'].append(memory)
        if self.consolidator and self.session_id:
            _executor.submit(self._save_closing_to_json)

    def get_instant_closing(self) -> Dict[str, Any]:
        return self.cache.copy()

    def get_closing_prompt(self) -> str:
        return f"""SESSION ENDING:

Emotional journey today: {' -> '.join(self.cache['emotional_arc']) or 'neutral'}
Key moments: {', '.join(self.cache['key_moments']) or 'none'}

GOODBYE MESSAGE:
{self.cache['goodbye_message']}

NEXT SESSION HOOK:
{', '.join(self.cache['next_session_hooks']) or 'Continue where we left off'}

End the conversation warmly, acknowledging their emotional state.
Mention the next session hook to create continuity."""


class OpeningContextCache:
    def __init__(self, storage_path: Optional[str] = None, student_id: Optional[str] = None):
        if storage_path is None:
            if not student_id:
                raise ValueError("student_id is required for OpeningContextCache")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, 'data', student_id, 'memory')

        self.storage_path = storage_path
        self.student_id = student_id
        self.cache_file = os.path.join(storage_path, '.opening_cache.json')
        os.makedirs(storage_path, exist_ok=True)

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        # Disabled: No longer saving to .opening_cache.json
        # Opening context is saved to TA-opening-retrieval.json instead
        pass

    def generate_opening_context(
        self,
        student_id: str,
        closing_cache: SessionClosingCache,
        store: Optional[MemoryStore] = None
    ) -> Dict[str, Any]:
        closing = closing_cache.get_instant_closing()

        # Get personal memories for context
        personal_relevance = ""
        personal_memories = []
        if store:
            personal = store.get_memories_by_student(student_id, MemoryType.PERSONAL, limit=3)
            if personal:
                personal_memories = [p.text for p in personal]
                personal_relevance = personal[0].text

        # Build welcome hook from key moments
        welcome_hook = ""
        if closing['key_moments']:
            last_moment = closing['key_moments'][-1]
            if 'Breakthrough' in last_moment:
                # Extract what the breakthrough was about
                desc = last_moment.replace('Breakthrough:', '').strip()
                welcome_hook = f"Last time you had a breakthrough - {desc}"
            elif 'Struggled' in last_moment:
                desc = last_moment.replace('Struggled:', '').strip()
                welcome_hook = f"Last time we were working through {desc}"

        # Add topic context if no key moment
        if not welcome_hook and closing['topics_covered']:
            topic = closing['topics_covered'][-1]
            if topic != 'general':
                welcome_hook = f"Last time we were working on {topic}"

        emotional_state = closing['emotional_arc'][-1] if closing['emotional_arc'] else 'neutral'

        # Build comprehensive session summary
        summary_parts = []
        if closing['key_moments']:
            summary_parts.append(f"Key moments: {'; '.join(closing['key_moments'])}")
        if closing['emotional_arc'] and len(closing['emotional_arc']) > 1:
            summary_parts.append(f"Emotional journey: {' -> '.join(closing['emotional_arc'][-5:])}")
        elif emotional_state != 'neutral':
            summary_parts.append(f"Student felt: {emotional_state}")
        if closing['topics_covered'] and closing['topics_covered'] != ['general']:
            summary_parts.append(f"Topics covered: {', '.join(closing['topics_covered'])}")
        
        last_session_summary = '. '.join(summary_parts) if summary_parts else closing['session_summary']

        opening_context = {
            'student_id': student_id,
            'welcome_hook': welcome_hook or "Welcome back!",
            'last_session_summary': last_session_summary,
            'unfinished_threads': closing['next_session_hooks'],
            'personal_relevance': personal_relevance,
            'personal_memories': personal_memories,
            'emotional_state_last': emotional_state,
            'topics_last_session': closing['topics_covered'],
            'key_moments_last': closing['key_moments'],
            'suggested_opener': self._generate_opener(
                welcome_hook, personal_relevance, emotional_state, closing
            )
        }

        return opening_context

    def _generate_opener(
        self, 
        welcome_hook: str, 
        personal_relevance: str, 
        emotional_state: str,
        closing: Dict[str, Any]
    ) -> str:
        """Generate a natural, contextual opener for the next session."""
        
        # Start with greeting
        opener = "Hey! "
        
        # Add personal touch if available (but phrase it naturally)
        if personal_relevance:
            # Check if it's a question-worthy personal detail
            if any(word in personal_relevance.lower() for word in ['headache', 'sick', 'tired', 'stressed']):
                opener += f"Hope you're feeling better - you mentioned {personal_relevance.lower()}. "
            elif any(word in personal_relevance.lower() for word in ['game', 'match', 'practice', 'basketball', 'soccer']):
                opener += f"How did things go? "
        
        # Reference last session naturally
        if welcome_hook and welcome_hook != "Welcome back!":
            opener += welcome_hook + ". "

        # Add appropriate call to action based on emotional state
        if emotional_state == 'excited':
            opener += "Ready to keep that momentum going?"
        elif emotional_state in ['frustrated', 'confused']:
            opener += "Let's take a fresh look at things today - sometimes a break helps!"
        elif closing.get('next_session_hooks'):
            hooks = closing['next_session_hooks']
            if 'Revisit what we struggled with' in hooks:
                opener += "Want to tackle what we were working on, or try something new?"
            else:
                opener += "What would you like to work on today?"
        else:
            opener += "What would you like to work on today?"

        return opener.strip()


class MemoryConsolidator:
    def __init__(self, store: Optional[MemoryStore] = None, student_id: Optional[str] = None):
        self.store = store or MemoryStore(student_id=student_id)
        self.student_id = student_id or (store.student_id if store and hasattr(store, 'student_id') else None)
        self._closing_file_lock = threading.Lock()
        self._opening_file_lock = threading.Lock()

    def _get_ta_closing_filepath(self, student_id: Optional[str] = None) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        student_id = student_id or self.student_id
        if not student_id:
            raise ValueError("student_id is required for TA file paths")
        ta_dir = os.path.join(base_dir, 'data', student_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-closing-retrieval.json')

    def _load_ta_closing_file(self) -> Dict[str, Any]:
        filepath = self._get_ta_closing_filepath(self.student_id)
        
        if not os.path.exists(filepath):
            initial_data = {
                "closings": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or 'closings' not in data:
                    data = {"closings": [], "last_updated": None}
                return data
        except (json.JSONDecodeError, IOError) as e:
            backup_path = filepath + '.backup'
            if os.path.exists(filepath):
                try:
                    os.rename(filepath, backup_path)
                except:
                    pass
            
            initial_data = {
                "closings": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data

    def _save_ta_closing_file(self, data: Dict[str, Any]) -> None:
        filepath = self._get_ta_closing_filepath(self.student_id)
        data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        with self._closing_file_lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except IOError as e:
                raise IOError(f"Failed to save TA-closing-retrieval.json: {e}")

    def _get_ta_opening_filepath(self, student_id: Optional[str] = None) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        student_id = student_id or self.student_id
        if not student_id:
            raise ValueError("student_id is required for TA file paths")
        ta_dir = os.path.join(base_dir, 'data', student_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-opening-retrieval.json')

    def _load_ta_opening_file(self) -> Dict[str, Any]:
        filepath = self._get_ta_opening_filepath(self.student_id)
        
        if not os.path.exists(filepath):
            initial_data = {
                "openings": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or 'openings' not in data:
                    data = {"openings": [], "last_updated": None}
                return data
        except (json.JSONDecodeError, IOError) as e:
            backup_path = filepath + '.backup'
            if os.path.exists(filepath):
                try:
                    os.rename(filepath, backup_path)
                except:
                    pass
            
            initial_data = {
                "openings": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data

    def _save_ta_opening_file(self, data: Dict[str, Any]) -> None:
        filepath = self._get_ta_opening_filepath(self.student_id)
        data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        with self._opening_file_lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except IOError as e:
                raise IOError(f"Failed to save TA-opening-retrieval.json: {e}")

    def _format_opening_for_ta_memory(
        self,
        opening_context: Dict[str, Any],
        session_id: str,
        user_id: str,
        generation_time_ms: float
    ) -> Dict[str, Any]:
        opening_id = f"opening_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        return {
            "opening_id": opening_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "generation_time_ms": round(generation_time_ms, 2),
            "welcome_hook": opening_context.get('welcome_hook', ''),
            "last_session_summary": opening_context.get('last_session_summary', ''),
            "unfinished_threads": opening_context.get('unfinished_threads', []),
            "personal_relevance": opening_context.get('personal_relevance', ''),
            "emotional_state_last": opening_context.get('emotional_state_last', 'neutral'),
            "suggested_opener": opening_context.get('suggested_opener', ''),
            "key_moments_last": opening_context.get('key_moments_last', []),
            "topics_last_session": opening_context.get('topics_last_session', []),
            "personal_memories": opening_context.get('personal_memories', []),
            "status": "success"
        }

    def _format_closing_for_ta_memory(
        self,
        closing_cache: SessionClosingCache,
        session_id: str,
        user_id: str,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        closing = closing_cache.get_instant_closing()
        closing_id = f"closing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        session_duration_seconds = None
        if closing.get('start_time') and end_time:
            try:
                start_str = closing['start_time'].replace('Z', '')
                end_str = end_time.replace('Z', '')
                start_dt = datetime.fromisoformat(start_str)
                end_dt = datetime.fromisoformat(end_str)
                duration = (end_dt - start_dt).total_seconds()
                session_duration_seconds = int(duration) if duration > 0 else None
            except:
                pass
        
        return {
            "closing_id": closing_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "session_duration_seconds": session_duration_seconds,
            "session_summary": closing.get('session_summary', ''),
            "key_moments": closing.get('key_moments', []),
            "emotional_arc": closing.get('emotional_arc', []),
            "topics_covered": closing.get('topics_covered', []),
            "goodbye_message": closing.get('goodbye_message', ''),
            "next_session_hooks": closing.get('next_session_hooks', []),
            "new_memories_count": len(closing.get('new_memories', [])),
            "status": "success"
        }

    def consolidate_session(self, student_id: str, closing_cache: SessionClosingCache) -> Dict[str, Any]:
        new_memories = closing_cache.cache['new_memories']

        saved_ids = []
        if new_memories:
            saved_ids = self.store.save_memories_batch(new_memories)

        merged_count = self._merge_duplicates(student_id)

        closing = closing_cache.get_instant_closing()

        has_meaningful_content = (
            closing['key_moments'] or
            (closing['emotional_arc'] and len(closing['emotional_arc']) > 1) or
            (closing['topics_covered'] and closing['topics_covered'] != ['general'])
        )

        if has_meaningful_content:
            summary_parts = []
            if closing['key_moments']:
                summary_parts.append(f"Key moments: {'; '.join(closing['key_moments'])}")
            if closing['emotional_arc']:
                summary_parts.append(f"Student felt: {closing['emotional_arc'][-1]}")
            if closing['topics_covered'] and closing['topics_covered'] != ['general']:
                summary_parts.append(f"Covered: {', '.join(closing['topics_covered'])}")

            if summary_parts:
                metadata = {'session_end': True}
                if closing['emotional_arc']:
                    metadata['emotion'] = closing['emotional_arc'][-1]
                if closing['topics_covered']:
                    metadata['next_topic'] = closing['topics_covered'][-1]

                context_memory = Memory(
                    student_id=student_id,
                    type=MemoryType.CONTEXT,
                    text='. '.join(summary_parts),
                    importance=0.8,
                    session_id=closing_cache.session_id,
                    metadata=metadata
                )
                self.store.save_memory(context_memory)

        opening_cache = OpeningContextCache(student_id=student_id)
        generation_start = time.time()
        opening = opening_cache.generate_opening_context(student_id, closing_cache, self.store)
        generation_time_ms = (time.time() - generation_start) * 1000

        opening_saved = False
        try:
            opening_data = self._format_opening_for_ta_memory(
                opening, closing_cache.session_id or 'unknown', student_id, generation_time_ms
            )
            data = self._load_ta_opening_file()
            data['openings'].append(opening_data)
            self._save_ta_opening_file(data)
            opening_saved = True
        except Exception as e:
            import traceback
            error_msg = f"Failed to save opening retrieval for session {closing_cache.session_id}: {e}"
            try:
                import sys
                print(f"[ERROR] {error_msg}", file=sys.stderr)
                traceback.print_exc()
            except:
                pass

        return {
            'memories_saved': len(saved_ids),
            'duplicates_merged': merged_count,
            'opening_generated': True,
            'opening_saved': opening_saved,
            'saved_ids': saved_ids
        }

    def _merge_duplicates(self, student_id: str, similarity_threshold: float = 0.9) -> int:
        merged_count = 0

        for mem_type in MemoryType:
            memories = self.store.get_memories_by_student(student_id, mem_type)

            if len(memories) < 2:
                continue

            texts = [m.text for m in memories]
            embeddings = get_embeddings_batch(texts)

            to_delete = set()
            for i, mem1 in enumerate(memories):
                if mem1.id in to_delete:
                    continue

                for j, mem2 in enumerate(memories[i+1:], i+1):
                    if mem2.id in to_delete:
                        continue

                    sim = cosine_similarity(embeddings[i], embeddings[j])
                    if sim >= similarity_threshold:
                        if mem1.importance >= mem2.importance:
                            to_delete.add(mem2.id)
                        else:
                            to_delete.add(mem1.id)
                        merged_count += 1

            for mem_id in to_delete:
                self.store.delete_memory(mem_id, student_id)

        return merged_count


class ConversationWatcher:
    def __init__(
        self,
        conversations_base_path: Optional[str] = None,
        poll_interval: float = 2.0,
        verbose: bool = True
    ):
        if conversations_base_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            conversations_base_path = os.path.join(base_dir, 'data')

        self.conversations_base_path = conversations_base_path
        self.verbose = verbose

        self._processed_turns: Dict[str, int] = {}
        self._session_caches: Dict[str, SessionClosingCache] = {}
        self._completed_sessions: Set[str] = set()
        self._exchange_buffers: Dict[str, List[Dict[str, Any]]] = {}
        self._user_turn_counts: Dict[str, int] = {}
        self._processed_exchange_ids: Dict[str, Set[str]] = {}
        self._batch_size: int = 3

        self._student_stores: Dict[str, MemoryStore] = {}
        self.extractor = MemoryExtractor()
        self._student_consolidators: Dict[str, MemoryConsolidator] = {}
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            try:
                print(f"[{timestamp}] [MEMORY] {message}")
            except UnicodeEncodeError:
                safe_msg = message.encode('ascii', 'replace').decode('ascii')
                print(f"[{timestamp}] [MEMORY] {safe_msg}")

    def _get_student_store(self, student_id: str) -> MemoryStore:
        """Get or create MemoryStore for a specific student_id."""
        if student_id not in self._student_stores:
            self._student_stores[student_id] = MemoryStore(student_id=student_id)
        return self._student_stores[student_id]
    
    def _get_student_consolidator(self, student_id: str) -> 'MemoryConsolidator':
        """Get or create MemoryConsolidator for a specific student_id."""
        if student_id not in self._student_consolidators:
            store = self._get_student_store(student_id)
            self._student_consolidators[student_id] = MemoryConsolidator(store, student_id=student_id)
        return self._student_consolidators[student_id]

    def _process_exchange(
        self,
        session_id: str,
        user_id: str,
        user_text: str,
        adam_text: str,
        cache: SessionClosingCache,
        exchange_id: str,
        turn_index: int
    ) -> None:
        try:
            preview = user_text[:50]
        except:
            preview = "[text]"
        self.log(f"Buffering exchange: \"{preview}...\"")

        cache.update_after_exchange(user_text, adam_text, 'general')

        batch = None
        with self._lock:
            exchange_data = {
                "exchange_id": exchange_id,
                "user_text": user_text,
                "ai_text": adam_text,
                "turn_index": turn_index,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
            self._exchange_buffers[session_id].append(exchange_data)
            self._user_turn_counts[session_id] += 1

            if self._user_turn_counts[session_id] >= self._batch_size:
                batch = self._exchange_buffers[session_id][-self._batch_size:]
                self._exchange_buffers[session_id] = []
                self._user_turn_counts[session_id] = 0

        # Only submit batch if it's ready (batch_size reached)
        if batch:
            _executor.submit(
                self._extract_and_save_memories_batch,
                session_id, user_id, batch, cache
            )

    def _extract_and_save_memories_batch(
        self,
        session_id: str,
        user_id: str,
        exchanges: List[Dict[str, Any]],
        cache: SessionClosingCache
    ) -> None:
        try:
            self.log(f"Batch extracting memories from {len(exchanges)} exchanges")
            
            combined_student_text = "\n\n".join([
                f"Exchange {i+1}:\nStudent: {ex['user_text']}\nAI: {ex.get('ai_text', '')}"
                for i, ex in enumerate(exchanges)
            ])
            
            combined_ai_text = "\n\n".join([
                ex.get('ai_text', '') for ex in exchanges
            ])

            memories = self.extractor.extract_memories(
                student_text=combined_student_text,
                ai_text=combined_ai_text,
                topic='general',
                student_id=user_id,
                session_id=session_id
            )

            if memories:
                self.log(f"Extracted {len(memories)} memories from batch")
                # Get student-specific store
                store = self._get_student_store(user_id)
                for mem in memories:
                    self.log(f"  - [{mem.type.value}] {mem.text[:50]}...")
                    cache.add_memory(mem)
                    store.save_memory(mem)
            else:
                self.log("No memories extracted from batch")

        except Exception as e:
            self.log(f"Batch extraction error: {e}")

    def _finalize_session(self, session_id: str, user_id: str, cache: SessionClosingCache, end_time: Optional[str] = None, consolidator: Optional['MemoryConsolidator'] = None) -> None:
        self.log(f"Session ended: {session_id}")

        # Get student-specific consolidator if not provided
        if consolidator is None:
            consolidator = self._get_student_consolidator(user_id)

        with self._lock:
            remaining_exchanges = self._exchange_buffers.get(session_id, [])
            if remaining_exchanges:
                self.log(f"Processing {len(remaining_exchanges)} remaining exchanges")
                _executor.submit(
                    self._extract_and_save_memories_batch,
                    session_id, user_id, remaining_exchanges, cache
                )

        try:
            result = consolidator.consolidate_session(user_id, cache)
            opening_status = "saved" if result.get('opening_saved', False) else "failed"
            self.log(f"Consolidated: {result['memories_saved']} saved, {result['duplicates_merged']} merged, opening {opening_status}")
        except Exception as e:
            self.log(f"Consolidation error: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")

        try:
            closing_data = consolidator._format_closing_for_ta_memory(
                cache, session_id, user_id, end_time
            )
            data = consolidator._load_ta_closing_file()
            
            existing_index = None
            for i, closing in enumerate(data['closings']):
                if closing.get('session_id') == session_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                data['closings'][existing_index] = closing_data
            else:
                data['closings'].append(closing_data)
            
            consolidator._save_ta_closing_file(data)
            
            key_moments_count = len(closing_data.get('key_moments', []))
            emotional_arc_count = len(closing_data.get('emotional_arc', []))
            topics_count = len(closing_data.get('topics_covered', []))
            duration = closing_data.get('session_duration_seconds')
            
            duration_str = f"{duration} seconds" if duration else "unknown"
            self.log(f"Closing updated: key_moments={key_moments_count}, emotional_arc={emotional_arc_count}, topics={topics_count}, duration={duration_str}")
            self.log(f"Updated TA-closing-retrieval.json (closing_id: {closing_data['closing_id']})")
        except Exception as e:
            self.log(f"Error saving closing data: {e}")
            self.log(f"Traceback: {traceback.format_exc()}")
            # Re-raise to ensure the error is visible to the API endpoint
            raise

        # Note: Opening context is already saved in consolidate_session(), no need to save again here

        self._completed_sessions.add(session_id)

        with self._lock:
            if session_id in self._session_caches:
                del self._session_caches[session_id]
            if session_id in self._processed_turns:
                del self._processed_turns[session_id]
            if session_id in self._exchange_buffers:
                del self._exchange_buffers[session_id]
            if session_id in self._user_turn_counts:
                del self._user_turn_counts[session_id]
            if session_id in self._processed_exchange_ids:
                del self._processed_exchange_ids[session_id]

    def on_session_start(self, session_id: str, user_id: str) -> None:
        """Handle real-time session start event."""
        consolidator = self._get_student_consolidator(user_id)
        if session_id not in self._session_caches:
            self._session_caches[session_id] = SessionClosingCache(user_id, session_id, consolidator)
            self.log(f"New session started: {session_id} (user: {user_id})")
        
        # Initialize buffers for this session
        if session_id not in self._exchange_buffers:
            self._exchange_buffers[session_id] = []
        if session_id not in self._user_turn_counts:
            self._user_turn_counts[session_id] = 0
        if session_id not in self._processed_exchange_ids:
            self._processed_exchange_ids[session_id] = set()
    
    def on_turn(self, session_id: str, user_id: str, user_text: str, adam_text: str, timestamp: str) -> None:
        """Handle real-time conversation turn event."""
        if session_id not in self._session_caches:
            self.on_session_start(session_id, user_id)
        
        cache = self._session_caches[session_id]
        exchange_id = f"{session_id}_{timestamp}"
        
        # Check if already processed
        if exchange_id in self._processed_exchange_ids.get(session_id, set()):
            return
        
        with self._lock:
            self._processed_exchange_ids[session_id].add(exchange_id)
        
        self._process_exchange(
            session_id, user_id, user_text, adam_text, cache, exchange_id, 0
        )
    
    def on_session_end(self, session_id: str, user_id: str, end_time: str) -> None:
        """Handle real-time session end event."""
        if session_id in self._completed_sessions:
            return
        
        if session_id not in self._session_caches:
            self.log(f"Warning: Session {session_id} ended but never started")
            return
        
        cache = self._session_caches[session_id]
        consolidator = self._get_student_consolidator(user_id)
        self._finalize_session(session_id, user_id, cache, end_time, consolidator)

import os
import json
import time
import threading
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
    def __init__(self, student_id: str, session_id: Optional[str] = None):
        self.student_id = student_id
        self.session_id = session_id
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

    def add_memory(self, memory: Memory) -> None:
        self.cache['new_memories'].append(memory)

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
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'memory')

        self.storage_path = storage_path
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
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    def store_opening(self, student_id: str, opening_context: Dict[str, Any]) -> None:
        cache = self._load_cache()
        cache[student_id] = {
            **opening_context,
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
        self._save_cache(cache)

    def get_opening(self, student_id: str) -> Optional[Dict[str, Any]]:
        cache = self._load_cache()
        return cache.get(student_id)

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

        self.store_opening(student_id, opening_context)

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

    def build_opening_prompt(self, student_id: str) -> Optional[str]:
        """Build a prompt injection for the LLM at session start."""
        opening = self.get_opening(student_id)
        if not opening:
            return None

        # Format personal memories if available
        personal_context = ""
        if opening.get('personal_memories'):
            personal_context = "\n".join(f"  - {m}" for m in opening['personal_memories'])
        else:
            personal_context = opening.get('personal_relevance', 'None')

        # Format key moments
        key_moments = ""
        if opening.get('key_moments_last'):
            key_moments = "\n".join(f"  - {m}" for m in opening['key_moments_last'])
        else:
            key_moments = "None"

        return f"""=== RETURNING STUDENT - SESSION CONTEXT ===

LAST SESSION SUMMARY:
{opening.get('last_session_summary', 'No previous session data')}

EMOTIONAL STATE (when they left): {opening.get('emotional_state_last', 'unknown')}

KEY MOMENTS FROM LAST SESSION:
{key_moments}

UNFINISHED THREADS TO CONTINUE:
{', '.join(opening.get('unfinished_threads', [])) or 'None - start fresh'}

PERSONAL DETAILS YOU KNOW:
{personal_context}

SUGGESTED OPENER (use naturally, don't read verbatim):
"{opening.get('suggested_opener', 'Welcome back!')}"

INSTRUCTIONS:
- Greet them warmly, acknowledging you remember them
- Reference last session ONLY if it feels natural
- If they struggled last time, be encouraging
- If they had a breakthrough, build on that excitement
- Use personal details subtly (don't say "I remember you said...")
- Let them guide what they want to work on today

=== END SESSION CONTEXT ==="""


class MemoryConsolidator:
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

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

        opening_cache = OpeningContextCache()
        opening = opening_cache.generate_opening_context(student_id, closing_cache, self.store)

        return {
            'memories_saved': len(saved_ids),
            'duplicates_merged': merged_count,
            'opening_generated': True,
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
        conversations_path: Optional[str] = None,
        poll_interval: float = 2.0,
        verbose: bool = True
    ):
        if conversations_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            conversations_path = os.path.join(base_dir, 'data', 'conversations')

        self.conversations_path = conversations_path
        self.poll_interval = poll_interval
        self.verbose = verbose

        self._processed_turns: Dict[str, int] = {}
        self._session_caches: Dict[str, SessionClosingCache] = {}
        self._completed_sessions: Set[str] = set()

        self.store = MemoryStore()
        self.extractor = MemoryExtractor()
        self.consolidator = MemoryConsolidator(self.store)

        self._running = False
        self._thread: Optional[threading.Thread] = None

    def log(self, message: str) -> None:
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            try:
                print(f"[{timestamp}] [MEMORY] {message}")
            except UnicodeEncodeError:
                safe_msg = message.encode('ascii', 'replace').decode('ascii')
                print(f"[{timestamp}] [MEMORY] {safe_msg}")

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        self.log("ConversationWatcher started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.log("ConversationWatcher stopped")

    def _watch_loop(self) -> None:
        while self._running:
            try:
                self._process_conversations()
            except Exception as e:
                self.log(f"Error in watch loop: {e}")

            time.sleep(self.poll_interval)

    def _process_conversations(self) -> None:
        if not os.path.exists(self.conversations_path):
            return

        for filename in os.listdir(self.conversations_path):
            if not filename.endswith('.json'):
                continue

            session_id = filename[:-5]

            if session_id in self._completed_sessions:
                continue

            filepath = os.path.join(self.conversations_path, filename)
            self._process_session(session_id, filepath)

    def _process_session(self, session_id: str, filepath: str) -> None:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            self.log(f"Error reading {session_id}: {e}")
            return

        turns = session_data.get('turns', [])
        user_id = session_data.get('user_id', 'anonymous')
        last_processed = self._processed_turns.get(session_id, -1)

        if session_id not in self._session_caches:
            self._session_caches[session_id] = SessionClosingCache(user_id, session_id)
            self.log(f"New session: {session_id} (user: {user_id})")

        cache = self._session_caches[session_id]

        new_turns_processed = 0
        i = last_processed + 1

        while i < len(turns):
            turn = turns[i]

            if turn.get('speaker') == 'user':
                user_texts = []
                while i < len(turns) and turns[i].get('speaker') == 'user':
                    text = turns[i].get('text', '').strip()
                    if text and text != '<noise>':
                        user_texts.append(text)
                    i += 1

                adam_text = ''
                if i < len(turns) and turns[i].get('speaker') == 'adam':
                    adam_text = turns[i].get('text', '')
                    i += 1

                user_text = ' '.join(user_texts)

                if user_text:
                    self._process_exchange(session_id, user_id, user_text, adam_text, cache)
                    new_turns_processed += 1
            else:
                i += 1

        self._processed_turns[session_id] = len(turns) - 1

        if session_data.get('end_time'):
            self._finalize_session(session_id, user_id, cache)

    def _process_exchange(
        self,
        session_id: str,
        user_id: str,
        user_text: str,
        adam_text: str,
        cache: SessionClosingCache
    ) -> None:
        try:
            preview = user_text[:50]
        except:
            preview = "[text]"
        self.log(f"Processing exchange: \"{preview}...\"")

        cache.update_after_exchange(user_text, adam_text, 'general')

        _executor.submit(
            self._extract_and_save_memories,
            session_id, user_id, user_text, adam_text, cache
        )

    def _extract_and_save_memories(
        self,
        session_id: str,
        user_id: str,
        user_text: str,
        adam_text: str,
        cache: SessionClosingCache
    ) -> None:
        try:
            memories = self.extractor.extract_memories(
                student_text=user_text,
                ai_text=adam_text,
                topic='general',
                student_id=user_id,
                session_id=session_id
            )

            if memories:
                self.log(f"Extracted {len(memories)} memories")
                for mem in memories:
                    self.log(f"  - [{mem.type.value}] {mem.text[:50]}...")
                    cache.add_memory(mem)
                    self.store.save_memory(mem)
            else:
                self.log("No memories extracted (exchange not memorable)")
        except Exception as e:
            self.log(f"Extraction error: {e}")

    def _finalize_session(self, session_id: str, user_id: str, cache: SessionClosingCache) -> None:
        self.log(f"Session ended: {session_id}")

        try:
            result = self.consolidator.consolidate_session(user_id, cache)
            self.log(f"Consolidated: {result['memories_saved']} saved, {result['duplicates_merged']} merged")
        except Exception as e:
            self.log(f"Consolidation error: {e}")

        self._completed_sessions.add(session_id)

        if session_id in self._session_caches:
            del self._session_caches[session_id]
        if session_id in self._processed_turns:
            del self._processed_turns[session_id]

    def process_existing_sessions(self) -> Dict[str, Any]:
        results = {
            'sessions_processed': 0,
            'memories_extracted': 0,
            'errors': []
        }

        if not os.path.exists(self.conversations_path):
            return results

        for filename in sorted(os.listdir(self.conversations_path)):
            if not filename.endswith('.json'):
                continue

            session_id = filename[:-5]
            filepath = os.path.join(self.conversations_path, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                if not session_data.get('end_time'):
                    continue

                user_id = session_data.get('user_id', 'anonymous')
                turns = session_data.get('turns', [])

                self.log(f"Processing session: {session_id}")

                cache = SessionClosingCache(user_id, session_id)

                i = 0
                while i < len(turns):
                    turn = turns[i]

                    if turn.get('speaker') == 'user':
                        user_texts = []
                        while i < len(turns) and turns[i].get('speaker') == 'user':
                            text = turns[i].get('text', '').strip()
                            if text and text != '<noise>':
                                user_texts.append(text)
                            i += 1

                        adam_text = ''
                        if i < len(turns) and turns[i].get('speaker') == 'adam':
                            adam_text = turns[i].get('text', '')
                            i += 1

                        user_text = ' '.join(user_texts)

                        if user_text:
                            self._process_exchange(session_id, user_id, user_text, adam_text, cache)
                            results['memories_extracted'] += len(cache.cache['new_memories'])
                    else:
                        i += 1

                self.consolidator.consolidate_session(user_id, cache)
                results['sessions_processed'] += 1

            except Exception as e:
                results['errors'].append(f"{session_id}: {str(e)}")
                self.log(f"Error processing {session_id}: {e}")

        return results


def run_memory_watcher():
    print("=" * 60)
    print("Memory Watcher - Starting")
    print("=" * 60)

    watcher = ConversationWatcher(verbose=True)

    print("\nProcessing existing sessions...")
    results = watcher.process_existing_sessions()
    print(f"Processed {results['sessions_processed']} sessions")
    print(f"Extracted {results['memories_extracted']} memories")
    if results['errors']:
        print(f"Errors: {len(results['errors'])}")

    print("\nWatching for new conversations...")
    print("Press Ctrl+C to stop.\n")

    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        watcher.stop()


if __name__ == "__main__":
    run_memory_watcher()

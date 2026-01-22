"""
Memory Retriever - Conversation-aware memory retrieval with light/deep strategies
Based on v4 teaching-assistant branch implementation

Features:
- Light retrieval: Real-time per-turn retrieval
- Deep retrieval: Periodic (every 3 min) comprehensive retrieval
- Contextual query generation using LLM
- Reflection layer for synthesizing instructions
"""

import os
import sys
import json
import time
import threading
from typing import Dict, List, Set, Optional
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

# Try to use shared logging config for colored output
try:
    from shared.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Try Gemini for LLM calls
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .schema import Memory, MemoryType
from .vector_store import MemoryStore


class MemoryRetriever:
    """
    Manages conversation history and memory retrieval for tutoring sessions.

    Implements a two-tier retrieval strategy:
    - Light retrieval: On every user turn, contextually optimized
    - Deep retrieval: Every 3+ minutes, synthesizes themes across conversation
    """

    MAX_HISTORY_PER_SESSION = 10
    MAX_TOTAL_SESSIONS = 50
    MAX_INJECTED_IDS = 100

    def __init__(self, store: MemoryStore):
        self.store = store
        self._conversation_history: Dict[str, List[dict]] = {}
        self._turn_counts: Dict[str, int] = {}
        self._session_retrievals: Dict[str, dict] = {}
        self._injected_memory_ids: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()
        self._session_access_times: Dict[str, float] = {}

        # Initialize Gemini if available
        self._llm_enabled = False
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self._gemini_client = genai.Client(api_key=gemini_key)
                self._gemini_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self._llm_enabled = True
                logger.info(f"[MEMORY_RETRIEVER] Initialized with Gemini ({self._gemini_model_name})")
            except Exception as e:
                logger.warning(f"[MEMORY_RETRIEVER] Gemini init failed: {e}")

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call Gemini LLM"""
        if not self._llm_enabled:
            return None

        try:
            response = self._gemini_client.models.generate_content(
                model=self._gemini_model_name,
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'max_output_tokens': 500
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"[MEMORY_RETRIEVER] LLM call failed: {e}")
            return None

    def on_user_turn(
        self,
        session_id: str,
        user_id: str,
        user_text: str,
        timestamp: float,
        tutor_text: str = ""
    ):
        """
        Process a user turn and trigger retrieval.

        Args:
            session_id: Current session ID
            user_id: Student/user ID
            user_text: User's message
            timestamp: Message timestamp
            tutor_text: Previous tutor response (for context)
        """
        with self._lock:
            # Initialize session if needed
            if session_id not in self._conversation_history:
                if len(self._conversation_history) >= self.MAX_TOTAL_SESSIONS:
                    self._cleanup_oldest_session()

                self._conversation_history[session_id] = []
                self._turn_counts[session_id] = 0
                self._session_retrievals[session_id] = {
                    "light": [],
                    "deep": {},
                    "last_deep_time": time.time()
                }
                self._injected_memory_ids[session_id] = set()

            # Update access time
            self._session_access_times[session_id] = time.time()
            self._turn_counts[session_id] += 1

            # Add to conversation history
            self._conversation_history[session_id].append({
                "speaker": "user",
                "text": user_text,
                "timestamp": timestamp
            })
            if tutor_text:
                self._conversation_history[session_id].append({
                    "speaker": "tutor",
                    "text": tutor_text,
                    "timestamp": timestamp
                })

        # Maintain rolling window
        if len(self._conversation_history[session_id]) > self.MAX_HISTORY_PER_SESSION:
            self._conversation_history[session_id] = \
                self._conversation_history[session_id][-self.MAX_HISTORY_PER_SESSION:]

        # Trim injected IDs
        if len(self._injected_memory_ids[session_id]) > self.MAX_INJECTED_IDS:
            ids_list = list(self._injected_memory_ids[session_id])
            self._injected_memory_ids[session_id] = set(ids_list[-self.MAX_INJECTED_IDS:])

        # Analyze retrieval context
        retrieval_analysis = self._analyze_retrieval_context(user_text, tutor_text)
        should_retrieve = retrieval_analysis.get("need_retrieval", True)
        search_query = retrieval_analysis.get("retrieval_query", user_text)

        # Light retrieval
        light_results = []
        if should_retrieve:
            logger.info(f"[MEMORY_RETRIEVER] Light retrieval for session {session_id}")
            try:
                light_results = self.store.search(
                    query=search_query,
                    student_id=user_id,
                    top_k=10,
                    exclude_session_id=session_id
                )
                logger.info(f"[MEMORY_RETRIEVER] Found {len(light_results)} memories")
            except Exception as e:
                logger.error(f"[MEMORY_RETRIEVER] Light retrieval error: {e}")

        with self._lock:
            self._session_retrievals[session_id]["light"] = light_results

        # Save retrieval results
        self._save_retrieval(session_id, user_id, "light", light_results)

        # Check for deep retrieval (every 3 minutes)
        current_time = time.time()
        session_data = self._session_retrievals.get(session_id)
        if session_data:
            last_deep = session_data.get("last_deep_time", 0)
            if current_time - last_deep >= 180:
                self._do_deep_retrieval(session_id, user_id)
                with self._lock:
                    if session_id in self._session_retrievals:
                        self._session_retrievals[session_id]["last_deep_time"] = current_time

    def _cleanup_oldest_session(self):
        """Remove least recently used session"""
        if not self._session_access_times:
            return

        oldest = min(self._session_access_times.items(), key=lambda x: x[1])[0]
        logger.info(f"[MEMORY_RETRIEVER] Cleaning up session {oldest}")

        for store in [
            self._conversation_history,
            self._turn_counts,
            self._session_retrievals,
            self._injected_memory_ids,
            self._session_access_times
        ]:
            if oldest in store:
                del store[oldest]

    def _analyze_retrieval_context(self, user_text: str, tutor_text: str) -> dict:
        """Analyze if retrieval is needed and generate optimized query"""
        if not user_text or not user_text.strip():
            return {"need_retrieval": False, "retrieval_query": ""}

        fallback = {"need_retrieval": True, "retrieval_query": user_text}

        if not self._llm_enabled:
            return fallback

        try:
            prompt = f"""You are a RAG optimizer for an AI tutor.

Previous AI: "{tutor_text[:500] if tutor_text else 'Startup/Greeting'}"
User Input: "{user_text[:500]}"

TASK 1: Should we retrieve memories?
- FALSE if: Simple acknowledgment (ok, got it, thanks), greetings, rhetorical questions
- TRUE if: Questions, confusion, preferences, personal disclosures, domain terms

TASK 2: If TRUE, generate a keyword-focused search query.
- REMOVE: "student says", "user wants"
- FOCUS: Core concepts, entities, specific gaps

Return JSON:
{{"need_retrieval": true/false, "retrieval_query": "string"}}"""

            result_text = self._call_llm(prompt)
            if not result_text:
                return fallback

            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            if "need_retrieval" in result:
                if not result.get("retrieval_query"):
                    result["retrieval_query"] = user_text
                return result

        except Exception as e:
            logger.warning(f"[MEMORY_RETRIEVER] Context analysis failed: {e}")

        return fallback

    def _do_deep_retrieval(self, session_id: str, user_id: str):
        """Perform deep retrieval across all memory types"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with self._lock:
            history = self._conversation_history.get(session_id, [])
            recent_turns = list(history[-10:]) if len(history) >= 10 else list(history)

        conversation_text = " ".join([turn["text"] for turn in recent_turns])

        # Generate optimized deep query
        deep_query = self._analyze_deep_retrieval_context(conversation_text)

        if not deep_query or not deep_query.strip():
            return

        logger.info(f"[MEMORY_RETRIEVER] Deep retrieval for session {session_id}")

        deep_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_type = {
                executor.submit(
                    self.store.search,
                    query=deep_query,
                    student_id=user_id,
                    mem_type=mem_type,
                    top_k=5 if mem_type == MemoryType.ACADEMIC else 3,
                    exclude_session_id=session_id
                ): mem_type
                for mem_type in MemoryType
            }

            for future in as_completed(future_to_type):
                mem_type = future_to_type[future]
                try:
                    results = future.result()
                    deep_results[mem_type.value] = results
                except Exception as e:
                    logger.error(f"[MEMORY_RETRIEVER] Deep retrieval error for {mem_type.value}: {e}")
                    deep_results[mem_type.value] = []

        with self._lock:
            self._session_retrievals[session_id]["deep"] = deep_results

        self._save_retrieval(session_id, user_id, "deep", deep_results)

    def _analyze_deep_retrieval_context(self, conversation_text: str) -> str:
        """Generate search query for deep retrieval"""
        if not self._llm_enabled:
            return conversation_text

        try:
            prompt = f"""You are a Knowledge Synthesizer for an AI Tutor.
Analyze conversation history to generate a Deep Search Query.

Context: "{conversation_text[:2000]}"

GOAL: Identify underlying themes and patterns for long-term memory search.

GENERATE a single search string combining:
- Academic Concept
- Type of Struggle/Interaction
- Potential Personal Connections

Example:
Context: "I just don't get why t is negative. It's like the ball is going underground."
Good Query: "negative variables logic physics trajectory misconceptions analogies"

Return JSON:
{{"deep_query": "string"}}"""

            result_text = self._call_llm(prompt)
            if not result_text:
                return conversation_text

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            return result.get("deep_query", conversation_text)

        except Exception as e:
            logger.warning(f"[MEMORY_RETRIEVER] Deep context analysis failed: {e}")
            return conversation_text

    def get_memory_injection(self, session_id: str) -> Optional[str]:
        """
        Get synthesized instruction from retrieved memories.

        Returns:
            Instruction string for the tutor, or None if no relevant memories
        """
        if session_id not in self._session_retrievals:
            return None

        with self._lock:
            retrievals = self._session_retrievals.get(session_id, {})
            light_results = list(retrievals.get("light", []))
            deep_results = retrievals.get("deep", {}).copy()
            injected_ids = self._injected_memory_ids.get(session_id, set())

        # Collect un-injected memories
        memories_to_inject = []
        for result in light_results:
            mem_id = result["memory"].id
            if mem_id not in injected_ids:
                memories_to_inject.append(result)
                injected_ids.add(mem_id)

        for mem_type_value, results in deep_results.items():
            for result in results:
                mem_id = result["memory"].id
                if mem_id not in injected_ids:
                    memories_to_inject.append(result)
                    injected_ids.add(mem_id)

        if not memories_to_inject:
            logger.info("[REFLECTION LAYER] FALSE - No new memories available for injection")
            return None

        # Get conversation context
        conversation_context = ""
        if session_id in self._conversation_history:
            recent_turns = self._conversation_history[session_id][-3:]
            conversation_context = "\n".join([
                f"{t['speaker']}: {t['text']}" for t in recent_turns
            ])

        # Synthesize instruction
        instruction = self._synthesize_instruction(memories_to_inject, conversation_context)

        if not instruction:
            return None

        # Clear retrieval results
        with self._lock:
            if session_id in self._session_retrievals:
                self._session_retrievals[session_id]["light"] = []
                self._session_retrievals[session_id]["deep"] = {}

        return f"""[SYSTEM INSTRUCTION]

{instruction}

Note: This instruction is based on retrieved memories from previous sessions.
Apply it naturally without explicitly mentioning these memories to the student."""

    def _synthesize_instruction(self, memories: list, conversation_context: str) -> Optional[str]:
        """Use LLM to synthesize memories into actionable instruction"""
        if not memories or not self._llm_enabled:
            return None

        memory_texts = [f"- {m['memory'].text}" for m in memories]
        memories_str = "\n".join(memory_texts)

        prompt = f"""You are a reflection layer for an AI tutor system.

Retrieved Memories:
{memories_str}

Recent Conversation:
{conversation_context}

TASK: Synthesize these memories into a SINGLE actionable instruction.
- Only return an instruction if memories are highly relevant
- Make it specific and actionable
- Focus on HOW the tutor should adapt

Return ONLY the instruction text, or "NONE" if not relevant.

Examples:
- "Student prefers visual diagrams - use a visual approach"
- "Student struggled with negative numbers - check understanding first"
- "Student gets frustrated with algebra - provide encouragement"
"""

        try:
            result = self._call_llm(prompt)
            if result and result.strip().upper() != "NONE":
                return result.strip()
        except Exception as e:
            logger.error(f"[MEMORY_RETRIEVER] Synthesis failed: {e}")

        return None

    def _save_retrieval(self, session_id: str, user_id: str, retrieval_type: str, results):
        """Save retrieval results to JSON file"""
        try:
            data_dir = Path(f"services/TeachingAssistant/Memory/data/{user_id}/memory/TeachingAssistant")
            data_dir.mkdir(parents=True, exist_ok=True)

            file_path = data_dir / f"TA-{retrieval_type}-retrieval.json"
            retrievals = []
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        retrievals = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    retrievals = []

            # Format results
            if isinstance(results, list):
                results_data = [
                    {"memory": r["memory"].to_dict(), "score": r["score"]}
                    for r in results
                ]
            elif isinstance(results, dict):
                results_data = {}
                for mem_type, mem_results in results.items():
                    results_data[mem_type] = [
                        {"memory": r["memory"].to_dict(), "score": r["score"]}
                        for r in mem_results
                    ]
            else:
                results_data = []

            retrievals.append({
                "session_id": session_id,
                "timestamp": time.time(),
                "results": results_data
            })

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(retrievals, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[MEMORY_RETRIEVER] Save retrieval failed: {e}")

    def clear_session(self, session_id: str):
        """Clear all data for a session"""
        for store in [
            self._conversation_history,
            self._turn_counts,
            self._session_retrievals,
            self._injected_memory_ids,
            self._session_access_times
        ]:
            if session_id in store:
                del store[session_id]

    def get_conversation_history(self, session_id: str) -> List[dict]:
        """Get conversation history for a session"""
        return self._conversation_history.get(session_id, [])

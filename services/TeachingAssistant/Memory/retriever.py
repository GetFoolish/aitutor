import os
import json
import time
import threading
import uuid
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from .schema import Memory, MemoryType
from .vector_store import MemoryStore
from .extractor import detect_topic_shift, has_past_reference, MemoryExtractor

QUERY_GENERATION_PROMPT = """Analyze the recent conversation between a student and AI tutor. Generate a concise search query that captures the main topics and context being discussed.

The query should:
- Focus on the primary topics/subjects being discussed
- Include key details that would help find relevant memories
- Be concise (1-3 sentences maximum)
- Prioritize the overall conversation theme over the most recent message

Recent Conversation:
{conversation}

Current User Message: {current_message}

Generate a search query that best represents what memories should be retrieved based on this conversation context.

Return only the query text, no explanations or additional text."""


class MemoryRetriever:
    def __init__(self, store: Optional[MemoryStore] = None, student_id: Optional[str] = None):
        self.store = store or MemoryStore(student_id=student_id)
        self.student_id = student_id or (store.student_id if store and hasattr(store, 'student_id') else None)
        self._extractor = None
        self.watcher: Optional['MemoryRetrievalWatcher'] = None
        # Track conversation history and turn counts for real-time events
        self._conversation_history: Dict[str, List[Dict[str, str]]] = {}
        self._turn_counts: Dict[str, int] = {}
        self._history_limit: int = 15
        self._lock = threading.Lock()

    def _get_extractor(self) -> MemoryExtractor:
        if self._extractor is None:
            self._extractor = MemoryExtractor()
        return self._extractor

    def _generate_conversation_query(
        self,
        conversation: List[Dict[str, str]],
        current_message: str
    ) -> str:
        if not conversation:
            return current_message
        
        conversation_text = "\n".join([
            f"{turn.get('speaker', 'unknown').title()}: {turn.get('text', '')}"
            for turn in conversation[-10:]
        ])
        
        prompt = QUERY_GENERATION_PROMPT.format(
            conversation=conversation_text,
            current_message=current_message
        )
        
        try:
            extractor = self._get_extractor()
            model = extractor._get_model()
            response = model.generate_content(prompt)
            generated_query = response.text.strip()
            
            if generated_query and len(generated_query) > 10:
                return generated_query
        except Exception as e:
            pass
        
        fallback_query = " ".join([
            turn.get('text', '') for turn in conversation[-5:]
            if turn.get('speaker') == 'user'
        ]) + " " + current_message
        
        return fallback_query.strip() or current_message

    def light_retrieval(
        self, 
        query: str, 
        student_id: str, 
        top_k: int = 5,
        exclude_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self.store.search(
            query=query, 
            student_id=student_id, 
            top_k=top_k,
            exclude_session_id=exclude_session_id
        )

    def deep_retrieval(
        self,
        query: str,
        student_id: str,
        triggers: Optional[Dict[str, bool]] = None,
        exclude_session_id: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        triggers = triggers or {}
        
        if conversation:
            search_query = self._generate_conversation_query(conversation, query)
        else:
            search_query = query

        academic = self.store.search(
            query=search_query,
            student_id=student_id,
            mem_type=MemoryType.ACADEMIC,
            top_k=5,
            exclude_session_id=exclude_session_id
        )

        personal = self.store.search(
            query=search_query,
            student_id=student_id,
            mem_type=MemoryType.PERSONAL,
            top_k=3,
            exclude_session_id=exclude_session_id
        )

        preferences = self.store.search(
            query=search_query,
            student_id=student_id,
            mem_type=MemoryType.PREFERENCE,
            top_k=3,
            exclude_session_id=exclude_session_id
        )

        context = [
            {'memory': m, 'score': 1.0}
            for m in self.store.get_recent_context(student_id, limit=3)
        ]

        if triggers.get('emotional_cue'):
            emotional_patterns = self.store.search(
                query=search_query,
                student_id=student_id,
                mem_type=MemoryType.PREFERENCE,
                top_k=3,
                metadata_filter={'category': 'emotional_response'},
                exclude_session_id=exclude_session_id
            )
            seen_ids = {r['memory'].id for r in preferences}
            for ep in emotional_patterns:
                if ep['memory'].id not in seen_ids:
                    preferences.append(ep)

        return {
            'academic': academic,
            'personal': personal,
            'preferences': preferences,
            'context': context,
            'generated_query': search_query if conversation else None
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
        turn_count: int = 0,
        exclude_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        conversation = conversation or []

        light_results = self.light_retrieval(
            student_message, 
            student_id,
            exclude_session_id=exclude_session_id
        )

        triggers = self.should_deep_retrieve(student_message, conversation, turn_count)

        if any(triggers.values()):
            deep_results = self.deep_retrieval(
                student_message, 
                student_id, 
                triggers,
                exclude_session_id=exclude_session_id,
                conversation=conversation
            )

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

    # TA-light-retrieval.json file management methods
    def _get_ta_memory_filepath(self, student_id: Optional[str] = None) -> str:
        """Get the path to TA-light-retrieval.json file."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        student_id = student_id or self.student_id
        if not student_id:
            raise ValueError("student_id is required for TA file paths")
        ta_dir = os.path.join(base_dir, 'data', student_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-light-retrieval.json')

    def _get_ta_deep_memory_filepath(self, student_id: Optional[str] = None) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        student_id = student_id or self.student_id
        if not student_id:
            raise ValueError("student_id is required for TA file paths")
        ta_dir = os.path.join(base_dir, 'data', student_id, 'memory', 'TeachingAssistant')
        os.makedirs(ta_dir, exist_ok=True)
        return os.path.join(ta_dir, 'TA-deep-retrieval.json')

    def _load_ta_memory_file(self, student_id: Optional[str] = None) -> Dict[str, Any]:
        """Load TA-light-retrieval.json file, creating it if it doesn't exist."""
        filepath = self._get_ta_memory_filepath(student_id)
        
        if not os.path.exists(filepath):
            initial_data = {
                "retrievals": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or 'retrievals' not in data:
                    data = {"retrievals": [], "last_updated": None}
                return data
        except (json.JSONDecodeError, IOError) as e:
            backup_path = filepath + '.backup'
            if os.path.exists(filepath):
                try:
                    os.rename(filepath, backup_path)
                except:
                    pass
            
            initial_data = {
                "retrievals": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data

    def _load_ta_deep_memory_file(self, student_id: Optional[str] = None) -> Dict[str, Any]:
        filepath = self._get_ta_deep_memory_filepath(student_id)
        
        if not os.path.exists(filepath):
            initial_data = {
                "retrievals": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or 'retrievals' not in data:
                    data = {"retrievals": [], "last_updated": None}
                return data
        except (json.JSONDecodeError, IOError) as e:
            backup_path = filepath + '.backup'
            if os.path.exists(filepath):
                try:
                    os.rename(filepath, backup_path)
                except:
                    pass
            
            initial_data = {
                "retrievals": [],
                "last_updated": None
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data

    def _save_ta_memory_file(self, data: Dict[str, Any], student_id: Optional[str] = None) -> None:
        """Save data to TA-light-retrieval.json file (thread-safe)."""
        filepath = self._get_ta_memory_filepath(student_id)
        data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise IOError(f"Failed to save TA-light-retrieval.json: {e}")

    def _save_ta_deep_memory_file(self, data: Dict[str, Any], student_id: Optional[str] = None) -> None:
        filepath = self._get_ta_deep_memory_filepath(student_id)
        data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise IOError(f"Failed to save TA-deep-retrieval.json: {e}")

    def _format_retrieval_for_ta_memory(
        self,
        retrieval_results: List[Dict[str, Any]],
        student_message: str,
        user_id: str,
        session_id: str,
        retrieval_time_ms: float
    ) -> Dict[str, Any]:
        """Format retrieval results for TA-light-retrieval.json structure."""
        retrieval_id = f"ret_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        memories_list = []
        for result in retrieval_results:
            mem = result.get('memory')
            score = result.get('score', 0.0)
            
            memory_data = {
                "memory_id": mem.id,
                "type": mem.type.value,
                "text": mem.text,
                "score": float(score),
                "importance": float(mem.importance),
                "timestamp": mem.timestamp.isoformat() + 'Z',
                "metadata": mem.metadata.copy() if mem.metadata else {}
            }
            
            if mem.session_id:
                memory_data["session_id"] = mem.session_id
            
            memories_list.append(memory_data)
        
        return {
            "retrieval_id": retrieval_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "student_message": student_message,
            "query_embedding_generated": True,
            "pinecone_query_params": {
                "student_id": user_id,
                "top_k": 10
            },
            "results": {
                "total_found": len(memories_list),
                "memories": memories_list
            },
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "status": "success"
        }

    def _format_deep_retrieval_for_ta_memory(
        self,
        deep_results: Dict[str, List[Dict[str, Any]]],
        student_message: str,
        user_id: str,
        session_id: str,
        triggers: Dict[str, bool],
        retrieval_time_ms: float
    ) -> Dict[str, Any]:
        retrieval_id = f"deep_ret_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        def format_memories(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
            memories_list = []
            for result in memories:
                mem = result.get('memory')
                score = result.get('score', 0.0)
                
                memory_data = {
                    "memory_id": mem.id,
                    "type": mem.type.value,
                    "text": mem.text,
                    "score": float(score),
                    "importance": float(mem.importance),
                    "timestamp": mem.timestamp.isoformat() + 'Z',
                    "metadata": mem.metadata.copy() if mem.metadata else {}
                }
                
                if mem.session_id:
                    memory_data["session_id"] = mem.session_id
                
                memories_list.append(memory_data)
            
            return {
                "total_found": len(memories_list),
                "memories": memories_list
            }
        
        result_dict = {
            "retrieval_id": retrieval_id,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "student_message": student_message,
            "triggers": triggers.copy(),
            "query_embedding_generated": True,
            "pinecone_query_params": {
                "student_id": user_id,
                "academic_top_k": 5,
                "personal_top_k": 3,
                "preferences_top_k": 3,
                "context_limit": 3
            },
            "results": {
                "academic": format_memories(deep_results.get('academic', [])),
                "personal": format_memories(deep_results.get('personal', [])),
                "preferences": format_memories(deep_results.get('preferences', [])),
                "context": format_memories(deep_results.get('context', []))
            },
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "status": "success"
        }
        
        if deep_results.get('generated_query'):
            result_dict["generated_query"] = deep_results['generated_query']
            result_dict["original_message"] = student_message
        
        return result_dict

    # Watcher integration methods
    def start_retrieval_watcher(self, poll_interval: float = 1.0, verbose: bool = True) -> None:
        """Start the memory retrieval watcher."""
        if self.watcher is not None:
            return
        
        self.watcher = MemoryRetrievalWatcher(
            retriever=self,
            poll_interval=poll_interval,
            verbose=verbose
        )

    def stop_retrieval_watcher(self) -> None:
        """Stop the memory retrieval watcher."""
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher = None

    def on_user_turn(
        self,
        session_id: str,
        user_id: str,
        user_text: str,
        timestamp: str,
        adam_text: str = ""
    ) -> None:
        """Handle real-time user turn event for memory retrieval."""
        try:
            preview = user_text[:50] + "..." if len(user_text) > 50 else user_text
        except:
            preview = "[text]"
        
        verbose = self.watcher.verbose if self.watcher else True
        if verbose:
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            try:
                print(f"[{timestamp_str}] [RETRIEVAL] New user turn (real-time): session_id={session_id}, user_id={user_id}")
                print(f"[{timestamp_str}] [RETRIEVAL] Query: \"{preview}\"")
            except UnicodeEncodeError:
                safe_msg = preview.encode('ascii', 'replace').decode('ascii')
                print(f"[{timestamp_str}] [RETRIEVAL] Query: \"{safe_msg}\"")
        
        start_time = time.time()
        
        try:
            retrieval_results = self.light_retrieval(
                query=user_text,
                student_id=user_id,
                top_k=10,
                exclude_session_id=session_id
            )
            retrieval_time_ms = (time.time() - start_time) * 1000
            
            if verbose:
                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp_str}] [RETRIEVAL] Found {len(retrieval_results)} memories")
            
            retrieval_data = self._format_retrieval_for_ta_memory(
                retrieval_results=retrieval_results,
                student_message=user_text,
                user_id=user_id,
                session_id=session_id,
                retrieval_time_ms=retrieval_time_ms
            )
            
            # Save to file (for read/backup purposes only)
            if self.watcher:
                self.watcher._save_retrieval_to_file(retrieval_data, user_id)
                if verbose:
                    timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp_str}] [RETRIEVAL] Saved to TA-light-retrieval.json (retrieval_id: {retrieval_data['retrieval_id']})")
            
            # Get conversation history for deep retrieval check
            with self._lock:
                if session_id not in self._conversation_history:
                    self._conversation_history[session_id] = []
                if session_id not in self._turn_counts:
                    self._turn_counts[session_id] = 0
                
                conversation = self._conversation_history[session_id].copy()
                turn_count = self._turn_counts[session_id]
                
                # Update conversation history
                self._conversation_history[session_id].append({
                    "speaker": "user",
                    "text": user_text
                })
                if adam_text:
                    self._conversation_history[session_id].append({
                        "speaker": "adam",
                        "text": adam_text
                    })
                
                # Limit history size
                if len(self._conversation_history[session_id]) > self._history_limit:
                    self._conversation_history[session_id] = self._conversation_history[session_id][-self._history_limit:]
                
                self._turn_counts[session_id] = turn_count + 1
            
            # Check for deep retrieval triggers
            triggers = self.should_deep_retrieve(
                current_message=user_text,
                conversation=conversation,
                turn_count=turn_count + 1
            )
            
            if any(triggers.values()):
                active_triggers = [k for k, v in triggers.items() if v]
                if verbose:
                    timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp_str}] [RETRIEVAL] Deep retrieval triggered: {', '.join(active_triggers)}")
                
                deep_start_time = time.time()
                
                try:
                    deep_results = self.deep_retrieval(
                        query=user_text,
                        student_id=user_id,
                        triggers=triggers,
                        exclude_session_id=session_id,
                        conversation=conversation
                    )
                    deep_retrieval_time_ms = (time.time() - deep_start_time) * 1000
                    
                    academic_count = len(deep_results.get('academic', []))
                    personal_count = len(deep_results.get('personal', []))
                    preferences_count = len(deep_results.get('preferences', []))
                    context_count = len(deep_results.get('context', []))
                    
                    if verbose:
                        timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp_str}] [RETRIEVAL] Deep found: academic={academic_count}, personal={personal_count}, preferences={preferences_count}, context={context_count}")
                    
                    deep_retrieval_data = self._format_deep_retrieval_for_ta_memory(
                        deep_results=deep_results,
                        student_message=user_text,
                        user_id=user_id,
                        session_id=session_id,
                        triggers=triggers,
                        retrieval_time_ms=deep_retrieval_time_ms
                    )
                    
                    # Save to file (for read/backup purposes only)
                    if self.watcher:
                        self.watcher._save_deep_retrieval_to_file(deep_retrieval_data, user_id)
                        if verbose:
                            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp_str}] [RETRIEVAL] Deep saved to TA-deep-retrieval.json (retrieval_id: {deep_retrieval_data['retrieval_id']})")
                    
                except Exception as deep_error:
                    deep_retrieval_time_ms = (time.time() - deep_start_time) * 1000
                    if verbose:
                        timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp_str}] [RETRIEVAL] Error during deep retrieval: {deep_error}")
                    
                    error_data = {
                        "retrieval_id": f"deep_ret_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                        "session_id": session_id,
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                        "student_message": user_text,
                        "triggers": triggers.copy(),
                        "query_embedding_generated": False,
                        "pinecone_query_params": {
                            "student_id": user_id,
                            "academic_top_k": 5,
                            "personal_top_k": 3,
                            "preferences_top_k": 3,
                            "context_limit": 3
                        },
                        "results": {
                            "academic": {"total_found": 0, "memories": []},
                            "personal": {"total_found": 0, "memories": []},
                            "preferences": {"total_found": 0, "memories": []},
                            "context": {"total_found": 0, "memories": []}
                        },
                        "retrieval_time_ms": round(deep_retrieval_time_ms, 2),
                        "status": "error",
                        "error_message": str(deep_error)
                    }
                    
                    try:
                        if self.watcher:
                            self.watcher._save_deep_retrieval_to_file(error_data, user_id)
                    except Exception as save_error:
                        if verbose:
                            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp_str}] [RETRIEVAL] Failed to save deep error to file: {save_error}")
            
        except Exception as e:
            retrieval_time_ms = (time.time() - start_time) * 1000
            if verbose:
                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp_str}] [RETRIEVAL] Error during retrieval: {e}")
            
            error_data = {
                "retrieval_id": f"ret_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "student_message": user_text,
                "query_embedding_generated": False,
                "pinecone_query_params": {
                    "student_id": user_id,
                    "top_k": 10
                },
                "results": {
                    "total_found": 0,
                    "memories": []
                },
                "retrieval_time_ms": round(retrieval_time_ms, 2),
                "status": "error",
                "error_message": str(e)
            }
            
            try:
                if self.watcher:
                    self.watcher._save_retrieval_to_file(error_data, user_id)
            except Exception as save_error:
                if verbose:
                    timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{timestamp_str}] [RETRIEVAL] Failed to save error to file: {save_error}")
    
    def clear_session_history(self, session_id: str) -> None:
        """Clear conversation history for a session (called on session end)."""
        with self._lock:
            if session_id in self._conversation_history:
                del self._conversation_history[session_id]
            if session_id in self._turn_counts:
                del self._turn_counts[session_id]


class MemoryRetrievalWatcher:
    """
    This class is kept for backward compatibility and file saving methods only.
    Watches conversation files and triggers lightweight memory retrieval
    when new user turns are detected. Saves results to TA-light-retrieval.json.
    """
    
    def __init__(
        self,
        retriever: MemoryRetriever,
        conversations_base_path: Optional[str] = None,
        poll_interval: float = 1.0,
        verbose: bool = True
    ):
        self.retriever = retriever
        
        if conversations_base_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            conversations_base_path = os.path.join(base_dir, 'data')
        
        self.conversations_base_path = conversations_base_path
        self.verbose = verbose
        self._lock = threading.Lock()
    
    def log(self, message: str) -> None:
        """Log a message with timestamp."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            try:
                print(f"[{timestamp}] [RETRIEVAL] {message}")
            except UnicodeEncodeError:
                safe_msg = message.encode('ascii', 'replace').decode('ascii')
                print(f"[{timestamp}] [RETRIEVAL] {safe_msg}")
    
    def stop(self) -> None:
        """Stop the watcher (no-op since file polling is disabled, kept for API compatibility)."""
        if self.verbose:
            self.log("MemoryRetrievalWatcher stop called (no-op, using real-time events)")
    
    def _save_retrieval_to_file(self, retrieval_data: Dict[str, Any], student_id: Optional[str] = None) -> None:
        """Save retrieval data to TA-light-retrieval.json file."""
        try:
            data = self.retriever._load_ta_memory_file(student_id)
            data['retrievals'].append(retrieval_data)
            self.retriever._save_ta_memory_file(data, student_id)
        except Exception as e:
            self.log(f"Failed to save retrieval to file: {e}")

    def _save_deep_retrieval_to_file(self, retrieval_data: Dict[str, Any], student_id: Optional[str] = None) -> None:
        try:
            data = self.retriever._load_ta_deep_memory_file(student_id)
            data['retrievals'].append(retrieval_data)
            self.retriever._save_ta_deep_memory_file(data, student_id)
        except Exception as e:
            self.log(f"Failed to save deep retrieval to file: {e}")

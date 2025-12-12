import os
import json
import time
from typing import Dict, List, Set, Optional
from .schema import Memory, MemoryType
from .vector_store import MemoryStore

class MemoryRetriever:
    def __init__(self, store: MemoryStore):
        self.store = store
        self._conversation_history: Dict[str, List[dict]] = {}
        self._turn_counts: Dict[str, int] = {}
        self._session_retrievals: Dict[str, dict] = {}
        self._injected_memory_ids: Dict[str, Set[str]] = {}

    def on_user_turn(self, session_id: str, user_id: str, user_text: str, 
                     timestamp: float, adam_text: str = ""):
        if session_id not in self._conversation_history:
            self._conversation_history[session_id] = []
            self._turn_counts[session_id] = 0
            self._session_retrievals[session_id] = {"light": [], "deep": {}}
            self._injected_memory_ids[session_id] = set()

        self._turn_counts[session_id] += 1
        self._conversation_history[session_id].append({
            "speaker": "user",
            "text": user_text,
            "timestamp": timestamp
        })
        if adam_text:
            self._conversation_history[session_id].append({
                "speaker": "adam",
                "text": adam_text,
                "timestamp": timestamp
            })

        if len(self._conversation_history[session_id]) > 15:
            self._conversation_history[session_id] = self._conversation_history[session_id][-15:]

        light_results = self.store.search(
            query=user_text,
            student_id=user_id,
            top_k=10,
            exclude_session_id=session_id
        )
        self._session_retrievals[session_id]["light"] = light_results
        self._save_retrieval(session_id, user_id, "light", light_results)

        current_time = time.time()
        last_deep = self._session_retrievals[session_id].get("last_deep_time", 0)
        if current_time - last_deep >= 180:
            self._do_deep_retrieval(session_id, user_id)
            self._session_retrievals[session_id]["last_deep_time"] = current_time

    def _do_deep_retrieval(self, session_id: str, user_id: str):
        history = self._conversation_history.get(session_id, [])
        recent_turns = history[-10:] if len(history) >= 10 else history
        conversation_text = " ".join([turn["text"] for turn in recent_turns])
        
        deep_results = {}
        for mem_type in MemoryType:
            results = self.store.search(
                query=conversation_text,
                student_id=user_id,
                mem_type=mem_type,
                top_k=5 if mem_type == MemoryType.ACADEMIC else 3,
                exclude_session_id=session_id
            )
            deep_results[mem_type.value] = results
        
        self._session_retrievals[session_id]["deep"] = deep_results
        self._save_retrieval(session_id, user_id, "deep", deep_results)
    
    def get_memory_injection(self, session_id: str) -> Optional[str]:
        if session_id not in self._session_retrievals:
            return None
            
        retrievals = self._session_retrievals[session_id]
        injected_ids = self._injected_memory_ids[session_id]
        
        memories_to_inject = []
        for result in retrievals.get("light", []):
            mem_id = result["memory"].id
            if mem_id not in injected_ids:
                memories_to_inject.append(result)
                injected_ids.add(mem_id)

        for mem_type in MemoryType:
            for result in retrievals.get("deep", {}).get(mem_type.value, []):
                mem_id = result["memory"].id
                if mem_id not in injected_ids:
                    memories_to_inject.append(result)
                    injected_ids.add(mem_id)
        
        if not memories_to_inject:
            return None
        
        memories_by_type = {}
        for result in memories_to_inject:
            mem_type = result["memory"].type.value
            if mem_type not in memories_by_type:
                memories_by_type[mem_type] = []
            memories_by_type[mem_type].append(result["memory"])

        formatted_parts = []
        type_names = {
            "academic": "Academic Memories",
            "personal": "Personal Memories",
            "preference": "Preference Memories",
            "context": "Context Memories"
        }

        for mem_type, mems in memories_by_type.items():
            formatted_parts.append(f"{type_names.get(mem_type, mem_type.title())}:")
            for mem in mems:
                emotion = mem.metadata.get("emotion", "")
                emotion_str = f" (emotion: {emotion})" if emotion else ""
                formatted_parts.append(f"- {mem.text}{emotion_str}")

        formatted_memories = "\n".join(formatted_parts)

        injection_text = f"""{{{{FOR THIS NEXT RESPONSE ONLY, USE THESE RELEVANT MEMORIES TO GUIDE YOUR RESPONSE. DO NOT MENTION THESE MEMORIES EXPLICITLY IN YOUR PUBLIC RESPONSE. TREAT THESE AS INTERNAL CONTEXT ONLY:

{formatted_memories}

Use these memories naturally to personalize your response. Do not reference them directly or say "I remember" or "based on our previous conversation". Just use the information naturally as if you already know it.
}}}}"""
        
        return injection_text
    
    def _save_retrieval(self, session_id: str, user_id: str, retrieval_type: str, results: List[dict]):
        data_dir = f"Memory/data/{user_id}/memory/TeachingAssistant"
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = f"{data_dir}/TA-{retrieval_type}-retrieval.json"
        retrievals = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                retrievals = json.load(f)
        
        retrieval_data = {
            "session_id": session_id,
            "timestamp": time.time(),
            "results": [{"memory": r["memory"].to_dict(), "score": r["score"]} for r in results]
        }
        retrievals.append(retrieval_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(retrievals, f, indent=2, ensure_ascii=False)

    def clear_session(self, session_id: str):
        if session_id in self._conversation_history:
            del self._conversation_history[session_id]
        if session_id in self._turn_counts:
            del self._turn_counts[session_id]
        if session_id in self._session_retrievals:
            del self._session_retrievals[session_id]
        if session_id in self._injected_memory_ids:
            del self._injected_memory_ids[session_id]
    

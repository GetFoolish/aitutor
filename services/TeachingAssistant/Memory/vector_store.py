import os
import json
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from .schema import Memory, MemoryType
from .embeddings import get_embedding, get_query_embedding, EMBEDDING_DIMENSION

load_dotenv()

_pc = None
_index = None


def _get_pinecone_index():
    global _pc, _index
    if _index is None:
        from pinecone import Pinecone
        _pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_name = os.getenv("PINECONE_INDEX_NAME")
        _index = _pc.Index(index_name)
    return _index


class MemoryStore:
    def __init__(self, storage_path: Optional[str] = None, student_id: Optional[str] = None):
        if storage_path is None:
            if not student_id:
                raise ValueError("student_id is required for MemoryStore")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, 'data', student_id, 'memory')

        self.storage_path = storage_path
        self.student_id = student_id
        os.makedirs(self.storage_path, exist_ok=True)
        self._lock = threading.Lock()
        self._index = None

        for mem_type in MemoryType:
            filepath = self._get_filepath(mem_type)
            if not os.path.exists(filepath):
                self._save_file(mem_type, [])

    def _get_index(self):
        if self._index is None:
            self._index = _get_pinecone_index()
        return self._index

    def _get_filepath(self, mem_type: MemoryType) -> str:
        return os.path.join(self.storage_path, f"{mem_type.value}.json")

    def _load_file(self, mem_type: MemoryType) -> List[Dict[str, Any]]:
        filepath = self._get_filepath(mem_type)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_file(self, mem_type: MemoryType, memories: List[Dict[str, Any]]) -> None:
        filepath = self._get_filepath(mem_type)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)

    def _build_pinecone_metadata(self, memory: Memory) -> Dict[str, Any]:
        metadata = {
            "student_id": memory.student_id,
            "type": memory.type.value,
            "text": memory.text,
            "importance": memory.importance,
            "timestamp": memory.timestamp.isoformat() + 'Z',
        }
        if memory.session_id:
            metadata["session_id"] = memory.session_id
        for key, value in memory.metadata.items():
            if value is not None:
                metadata[key] = value
        return metadata

    def save_memory(self, memory: Memory) -> str:
        embedding = get_embedding(memory.text)

        index = self._get_index()
        metadata = self._build_pinecone_metadata(memory)

        namespace = memory.type.value
        index.upsert(
            vectors=[{
                "id": memory.id,
                "values": embedding,
                "metadata": metadata
            }],
            namespace=namespace
        )

        with self._lock:
            memories = self._load_file(memory.type)
            memories = [m for m in memories if m.get('id') != memory.id]
            memories.append(memory.to_dict())
            self._save_file(memory.type, memories)

        return memory.id

    def save_memories_batch(self, memories: List[Memory]) -> List[str]:
        if not memories:
            return []

        texts = [m.text for m in memories]
        from .embeddings import get_embeddings_batch
        embeddings = get_embeddings_batch(texts)

        mem_embeddings = dict(zip([m.id for m in memories], embeddings))

        index = self._get_index()
        by_namespace: Dict[str, List[Dict]] = {}

        for mem in memories:
            ns = mem.type.value
            if ns not in by_namespace:
                by_namespace[ns] = []

            metadata = self._build_pinecone_metadata(mem)

            by_namespace[ns].append({
                "id": mem.id,
                "values": mem_embeddings[mem.id],
                "metadata": metadata
            })

        for ns, vectors in by_namespace.items():
            index.upsert(vectors=vectors, namespace=ns)

        by_type: Dict[MemoryType, List[Memory]] = {}
        for mem in memories:
            if mem.type not in by_type:
                by_type[mem.type] = []
            by_type[mem.type].append(mem)

        ids = []
        with self._lock:
            for mem_type, type_memories in by_type.items():
                existing = self._load_file(mem_type)
                new_ids = {m.id for m in type_memories}
                existing = [m for m in existing if m.get('id') not in new_ids]

                for mem in type_memories:
                    existing.append(mem.to_dict())
                    ids.append(mem.id)

                self._save_file(mem_type, existing)

        return ids

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        for mem_type in MemoryType:
            memories = self._load_file(mem_type)
            for m in memories:
                if m.get('id') == memory_id:
                    return Memory.from_dict(m)
        return None

    def get_memories_by_student(
        self,
        student_id: str,
        mem_type: Optional[MemoryType] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        results = []
        types_to_search = [mem_type] if mem_type else list(MemoryType)

        for t in types_to_search:
            memories = self._load_file(t)
            for m in memories:
                if m.get('student_id') == student_id:
                    results.append(Memory.from_dict(m))

        results.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def search(
        self,
        query: str,
        student_id: str,
        mem_type: Optional[MemoryType] = None,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        exclude_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query_embedding = get_query_embedding(query)

        index = self._get_index()

        filter_dict = {}
        if metadata_filter:
            for key, value in metadata_filter.items():
                if isinstance(value, dict) and any(op in value for op in ["$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin"]):
                    filter_dict[key] = value
                else:
                   filter_dict[key] = {"$eq": value}
        
        if exclude_session_id:
            filter_dict["session_id"] = {"$ne": exclude_session_id}

        if mem_type:
            namespaces = [mem_type.value]
        else:
            namespaces = [t.value for t in MemoryType]

        all_matches = []
        for ns in namespaces:
            try:
                results = index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    namespace=ns,
                    filter=filter_dict if filter_dict else None,
                    include_metadata=True
                )
                all_matches.extend(results.matches)
            except Exception:
                continue

        all_matches.sort(key=lambda x: x.score, reverse=True)
        all_matches = all_matches[:top_k]

        candidates = []
        for match in all_matches:
            meta = match.metadata
            mem_data = {
                "id": match.id,
                "student_id": meta.get("student_id", student_id),
                "type": meta.get("type", "context"),
                "text": meta.get("text", ""),
                "importance": meta.get("importance", 0.5),
                "timestamp": meta.get("timestamp", datetime.utcnow().isoformat() + 'Z'),
                "metadata": {}
            }
            if meta.get("session_id"):
                mem_data["session_id"] = meta.get("session_id")

            for key in ['emotion', 'valence', 'category', 'topic', 'trigger', 'response', 'resolution', 'session_end', 'next_topic']:
                if meta.get(key):
                    mem_data["metadata"][key] = meta.get(key)

            candidates.append({
                'memory': Memory.from_dict(mem_data),
                'score': match.score
            })

        return candidates

    def delete_memory(self, memory_id: str, student_id: Optional[str] = None, mem_type: Optional[MemoryType] = None) -> bool:
        if student_id:
            try:
                index = self._get_index()
                if mem_type:
                    index.delete(ids=[memory_id], namespace=mem_type.value)
                else:
                    for t in MemoryType:
                        try:
                            index.delete(ids=[memory_id], namespace=t.value)
                        except Exception:
                            continue
            except Exception:
                pass

        with self._lock:
            for mt in MemoryType:
                memories = self._load_file(mt)
                original_len = len(memories)
                memories = [m for m in memories if m.get('id') != memory_id]

                if len(memories) < original_len:
                    self._save_file(mt, memories)
                    return True
        return False

    def get_recent_context(self, student_id: str, limit: int = 3) -> List[Memory]:
        """Get recent context memories from Pinecone, sorted by timestamp."""
        # Use a neutral query to get all context memories for this student
        # We'll sort by timestamp in Python
        query_embedding = get_query_embedding("context session summary")
        
        index = self._get_index()
        
        # Filter by student_id and type=context
        filter_dict = {
            "student_id": {"$eq": student_id},
            "type": {"$eq": "context"}
        }
        
        try:
            # Query Pinecone for context memories
            # Get more results than needed to ensure we have recent ones
            results = index.query(
                vector=query_embedding,
                top_k=min(limit * 5, 20),  # Get more to sort by timestamp
                namespace=MemoryType.CONTEXT.value,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Convert to Memory objects and sort by timestamp
            memories = []
            for match in results.matches:
                meta = match.metadata
                mem_data = {
                    "id": match.id,
                    "student_id": meta.get("student_id", student_id),
                    "type": meta.get("type", "context"),
                    "text": meta.get("text", ""),
                    "importance": meta.get("importance", 0.5),
                    "timestamp": meta.get("timestamp", datetime.utcnow().isoformat() + 'Z'),
                    "metadata": {}
                }
                if meta.get("session_id"):
                    mem_data["session_id"] = meta.get("session_id")
                
                # Copy metadata fields
                for key in ['emotion', 'valence', 'category', 'topic', 'trigger', 'response', 'resolution', 'session_end', 'next_topic']:
                    if meta.get(key):
                        mem_data["metadata"][key] = meta.get(key)
                
                try:
                    memory = Memory.from_dict(mem_data)
                    memories.append(memory)
                except Exception:
                    continue
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda x: x.timestamp, reverse=True)
            
            return memories[:limit]
            
        except Exception:
            # Fallback: return empty list if Pinecone query fails
            return []

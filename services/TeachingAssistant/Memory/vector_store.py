import os
import json
import logging
from typing import List, Optional, Dict
from pinecone import Pinecone
from dotenv import load_dotenv
from .schema import Memory, MemoryType
from .embeddings import get_embeddings_batch
from . import get_memory_data_dir

load_dotenv()

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, index_name: str = None):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", "aitutor-memories")
        self.index = self.pc.Index(self.index_name)

    def save_memory(self, memory: Memory):
        logger.info(f"💾 Saving single memory: {memory.type.value} - {memory.text[:50]}...")
        try:
            embedding = get_embeddings_batch([memory.text])[0]
            self.index.upsert(
                vectors=[{
                    "id": memory.id,
                    "values": embedding,
                    "metadata": {
            "student_id": memory.student_id,
            "type": memory.type.value,
            "text": memory.text,
            "importance": memory.importance,
                        "timestamp": memory.timestamp.isoformat(),
                        "session_id": memory.session_id,
                        **memory.metadata
                    }
                }],
                namespace=memory.type.value
            )
            logger.info(f"✅ Saved to Pinecone (namespace: {memory.type.value})")
            self._save_to_local(memory)
            logger.info(f"✅ Saved to local file")
        except Exception as e:
            logger.error(f"❌ Error saving memory: {e}", exc_info=True)
            raise

    def save_memories_batch(self, memories: List[Memory]):
        if not memories:
            logger.warning("⚠️ save_memories_batch called with empty list")
            return

        logger.info(f"💾 Saving batch of {len(memories)} memories to Pinecone and local storage")

        memories_by_type = {}
        for mem in memories:
            if mem.type not in memories_by_type:
                memories_by_type[mem.type] = []
            memories_by_type[mem.type].append(mem)

        for mem_type, mems in memories_by_type.items():
            logger.info(f"📦 Processing {len(mems)} {mem_type.value} memories...")
            texts = [m.text for m in mems]
            
            try:
                embeddings = get_embeddings_batch(texts)

                vectors = [{
                    "id": mem.id,
                    "values": emb,
                    "metadata": {
                        "student_id": mem.student_id,
                        "type": mem.type.value,
                        "text": mem.text,
                        "importance": mem.importance,
                        "timestamp": mem.timestamp.isoformat(),
                        "session_id": mem.session_id,
                        **mem.metadata
                    }
                } for mem, emb in zip(mems, embeddings)]

                self.index.upsert(vectors=vectors, namespace=mem_type.value)
                logger.info(f"✅ Saved {len(vectors)} vectors to Pinecone (namespace: {mem_type.value})")
            except Exception as e:
                logger.error(f"❌ Error saving {mem_type.value} memories to Pinecone: {e}", exc_info=True)
                raise

        for mem in memories:
            try:
                self._save_to_local(mem)
            except Exception as e:
                logger.error(f"❌ Error saving memory {mem.id} to local file: {e}", exc_info=True)
        
        logger.info(f"✅ Successfully saved all {len(memories)} memories")

    def search(self, query: str, student_id: str, mem_type: Optional[MemoryType] = None, 
               top_k: int = 10, exclude_session_id: Optional[str] = None) -> List[Dict]:
        from .embeddings import get_query_embedding
        
        query_embedding = get_query_embedding(query)
        filter_dict = {"student_id": {"$eq": student_id}}
        
        if exclude_session_id:
            filter_dict["session_id"] = {"$ne": exclude_session_id}

        namespaces = [mem_type.value] if mem_type else [mt.value for mt in MemoryType]

        results = []
        for namespace in namespaces:
            response = self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                namespace=namespace,
                filter=filter_dict
                )
            for match in response.matches:
                # Skip matches with missing metadata
                if not match.metadata:
                    continue
                results.append({
                    "memory": Memory.from_dict(match.metadata),
                    "score": match.score
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _save_to_local(self, memory: Memory):
        data_dir = get_memory_data_dir(memory.student_id) / "memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / f"{memory.type.value}.json"
        memories = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                memories = json.load(f)
        
        memories.append(memory.to_dict())
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)
        


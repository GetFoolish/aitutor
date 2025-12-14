import os
import json
import logging
import time
import re
from typing import List, Optional, Dict
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from .schema import Memory, MemoryType
from .embeddings import get_embeddings_batch

load_dotenv()

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, user_id: str = None, index_name: str = None):
        """
        Initialize MemoryStore with user-specific index.
        
        Args:
            user_id: User ID to create/get index named "memory_{user_id}"
            index_name: Optional override for index name (for backward compatibility)
        """
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Determine index name: user_id-based or provided or env or default
        if user_id:
            # Sanitize user_id for Pinecone index name (must be lowercase alphanumeric with hyphens only)
            sanitized_user_id = self._sanitize_index_name(user_id)
            self.index_name = f"memory-{sanitized_user_id}"
            logger.info(f"📦 Using user-specific index: {self.index_name} (from user_id: {user_id})")
        elif index_name:
            self.index_name = index_name
            logger.info(f"📦 Using provided index: {self.index_name}")
        else:
            # Fallback to env or default (for backward compatibility)
            self.index_name = os.getenv("PINECONE_INDEX_NAME", "aitutor-memories")
            logger.info(f"📦 Using default index: {self.index_name}")
        
        # Check if index exists, create if not
        self._ensure_index_exists()
        
        self.index = self.pc.Index(self.index_name)
    
    def _sanitize_index_name(self, user_id: str) -> str:
        """
        Sanitize user_id to be valid for Pinecone index names.
        Pinecone index names must be lowercase alphanumeric characters or hyphens (-).
        Underscores are NOT allowed, so we replace them with hyphens.
        """
        # Convert to lowercase and replace invalid characters (including underscores) with hyphens
        sanitized = re.sub(r'[^a-z0-9-]', '-', user_id.lower())
        # Replace underscores with hyphens (Pinecone doesn't allow underscores)
        sanitized = sanitized.replace('_', '-')
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Ensure it's not empty
        if not sanitized:
            sanitized = "anonymous"
        return sanitized
    
    def _ensure_index_exists(self):
        """Check if index exists, create it if it doesn't."""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"📦 Index '{self.index_name}' not found. Creating new index for user...")
                
                # Get embedding dimension from env or default to 1024
                dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
                
                # Get cloud and region from env or use defaults
                cloud = os.getenv("PINECONE_CLOUD", "aws")  # "aws" or "gcp"
                region = os.getenv("PINECONE_REGION", "us-east-1")
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=cloud,
                        region=region
                    )
                )
                
                # Wait for index to be ready
                logger.info(f"⏳ Waiting for index '{self.index_name}' to be ready...")
                max_wait_time = 300  # 5 minutes max wait
                start_time = time.time()
                
                while True:
                    try:
                        index_info = self.pc.describe_index(self.index_name)
                        if index_info.status.get('ready', False):
                            logger.info(f"✅ Index '{self.index_name}' is ready!")
                            break
                        
                        elapsed = time.time() - start_time
                        if elapsed > max_wait_time:
                            raise TimeoutError(f"Index '{self.index_name}' did not become ready within {max_wait_time} seconds")
                        
                        time.sleep(2)
                    except Exception as e:
                        elapsed = time.time() - start_time
                        if elapsed > max_wait_time:
                            raise TimeoutError(f"Error waiting for index: {e}")
                        logger.warning(f"⚠️ Waiting for index... ({e})")
                        time.sleep(2)
            else:
                logger.info(f"✅ Index '{self.index_name}' already exists - using existing index")
                
        except Exception as e:
            logger.error(f"❌ Error checking/creating index: {e}", exc_info=True)
            raise

    def save_memory(self, memory: Memory):
        logger.info(f"💾 Saving single memory: {memory.type.value} - {memory.text[:50]}...")
        try:
            embedding = get_embeddings_batch([memory.text])[0]
            # Filter out None/null values from metadata (Pinecone doesn't accept null values)
            clean_metadata = {k: v for k, v in memory.metadata.items() if v is not None}
            
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
                        **clean_metadata
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

                vectors = []
                for mem, emb in zip(mems, embeddings):
                    # Filter out None/null values from metadata (Pinecone doesn't accept null values)
                    clean_metadata = {k: v for k, v in mem.metadata.items() if v is not None}
                    
                    vectors.append({
                        "id": mem.id,
                        "values": emb,
                        "metadata": {
                            "student_id": mem.student_id,
                            "type": mem.type.value,
                            "text": mem.text,
                            "importance": mem.importance,
                            "timestamp": mem.timestamp.isoformat(),
                            "session_id": mem.session_id,
                            **clean_metadata
                        }
                    })

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
        
        logger.info(f"🔍 Searching in index: {self.index_name} for student_id: {student_id}, query: {query[:50]}...")
        
        query_embedding = get_query_embedding(query)
        filter_dict = {"student_id": {"$eq": student_id}}
        
        if exclude_session_id:
            filter_dict["session_id"] = {"$ne": exclude_session_id}

        namespaces = [mem_type.value] if mem_type else [mt.value for mt in MemoryType]
        logger.info(f"   Searching namespaces: {namespaces}, top_k: {top_k}, filter: {filter_dict}")

        results = []
        for namespace in namespaces:
            try:
                response = self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace,
                    filter=filter_dict,
                    include_metadata=True
                )
                logger.info(f"   Namespace '{namespace}': Found {len(response.matches)} matches")
                for i, match in enumerate(response.matches):
                    # Skip matches with missing metadata
                    if not match.metadata:
                        logger.warning(f"   Match {i} in namespace '{namespace}' has no metadata, skipping")
                        continue

                    try:
                        # Reconstruct metadata structure for Memory.from_dict()
                        # Pinecone stores flattened metadata (emotion, valence, etc. at top level)
                        # But Memory.from_dict() expects nested structure with 'metadata' dict
                        metadata_dict = match.metadata.copy()
                        
                        # Extract nested metadata fields (emotion, valence, category, topic, etc.)
                        # These are stored at top level in Pinecone but should be in nested 'metadata' dict
                        nested_metadata = {}
                        memory_fields = {'id', 'type', 'text', 'importance', 'student_id', 'session_id', 'timestamp'}
                        
                        for key, value in list(metadata_dict.items()):
                            if key not in memory_fields:
                                nested_metadata[key] = value
                                metadata_dict.pop(key)
                        
                        # Add nested metadata dict
                        metadata_dict['metadata'] = nested_metadata
                        
                        memory = Memory.from_dict(metadata_dict)
                        results.append({
                            "memory": memory,
                            "score": match.score
                        })
                        logger.debug(f"   ✅ Converted match {i}: {memory.text[:50]}... (score: {match.score:.3f})")
                    except Exception as e:
                        logger.error(f"   ❌ Error converting match {i} in namespace '{namespace}': {e}", exc_info=True)
                        logger.error(f"   Metadata keys: {list(match.metadata.keys())}")
                        continue
            except Exception as e:
                logger.error(f"❌ Error searching namespace '{namespace}' in index '{self.index_name}': {e}", exc_info=True)

        results.sort(key=lambda x: x["score"], reverse=True)
        final_results = results[:top_k]
        logger.info(f"✅ Search complete: Returning {len(final_results)} results from index '{self.index_name}'")
        return final_results

    def _save_to_local(self, memory: Memory):
        data_dir = f"services/TeachingAssistant/Memory/data/{memory.student_id}/memory"
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = f"{data_dir}/{memory.type.value}.json"
        memories = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                memories = json.load(f)
        
        # Check for duplicate memory ID before appending
        memory_dict = memory.to_dict()
        existing_ids = {m.get('id') for m in memories if isinstance(m, dict)}
        
        if memory_dict['id'] not in existing_ids:
            memories.append(memory_dict)
        else:
            # Update existing memory instead of duplicating
            for i, m in enumerate(memories):
                if isinstance(m, dict) and m.get('id') == memory_dict['id']:
                    memories[i] = memory_dict
                    break
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)

    def clear_all_memories(self, user_id: str) -> bool:
        """
        Clear all memories for a user from both Pinecone and local storage.

        Args:
            user_id: User ID whose memories should be cleared

        Returns:
            True if successful, False otherwise
        """
        import shutil

        logger.info(f"🧹 Clearing all memories for user: {user_id}")

        # Clear Pinecone - delete all vectors in all namespaces
        try:
            for mem_type in MemoryType:
                namespace = mem_type.value
                try:
                    # Delete all vectors in namespace by using delete with filter
                    self.index.delete(
                        filter={"student_id": {"$eq": user_id}},
                        namespace=namespace
                    )
                    logger.info(f"   ✅ Cleared Pinecone namespace: {namespace}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Error clearing namespace {namespace}: {e}")
            logger.info(f"✅ Cleared all Pinecone data for user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Error clearing Pinecone data: {e}", exc_info=True)
            return False

        # Clear local storage
        try:
            local_data_dir = f"services/TeachingAssistant/Memory/data/{user_id}"
            if os.path.exists(local_data_dir):
                shutil.rmtree(local_data_dir)
                logger.info(f"✅ Cleared local data directory: {local_data_dir}")
            else:
                logger.info(f"ℹ️ No local data directory found for user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Error clearing local data: {e}", exc_info=True)
            return False

        logger.info(f"🧹 Successfully cleared all memories for user: {user_id}")
        return True



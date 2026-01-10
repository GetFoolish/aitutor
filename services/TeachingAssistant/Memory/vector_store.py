"""
Vector Store - Pinecone-based memory storage with deduplication
Based on v4 teaching-assistant branch implementation

Features:
- Intelligent deduplication using semantic similarity
- Multi-factor scoring (similarity, recency, importance)
- User-specific indexes
- Local JSON backup
"""

import os
import sys
import json
import time
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Import Pinecone
try:
    from pinecone import Pinecone, ServerlessSpec
    from pinecone.exceptions import PineconeApiException
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("[MEMORY_STORE] Pinecone not installed")

from .schema import Memory, MemoryType
from .embeddings import get_embeddings_batch, get_query_embedding, get_embedding_dimension


@dataclass
class MemoryConfig:
    """
    Configuration for memory deduplication and retrieval scoring.
    All parameters are loaded from environment variables with sensible defaults.
    """
    # Deduplication settings
    similarity_threshold: float = 0.92
    min_word_count: int = 3

    # Junk word filter
    junk_words: set = None

    # Scoring weights (must sum to ~1.0)
    weight_similarity: float = 0.6
    weight_recency: float = 0.3
    weight_importance: float = 0.1

    # Recency calculation
    recency_decay_hours: float = 24.0
    max_counter_for_frequency: int = 10

    def __post_init__(self):
        """Load configuration from environment variables."""
        self.similarity_threshold = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.92"))
        self.min_word_count = int(os.getenv("MEMORY_MIN_WORD_COUNT", "3"))

        # Junk words
        junk_words_str = os.getenv(
            "MEMORY_JUNK_WORDS",
            "y,yes,no,okay,ok,yeah,nope,yep,sure,fine,k"
        )
        self.junk_words = {word.strip().lower() for word in junk_words_str.split(",")}

        # Scoring weights
        self.weight_similarity = float(os.getenv("MEMORY_WEIGHT_SIMILARITY", "0.6"))
        self.weight_recency = float(os.getenv("MEMORY_WEIGHT_RECENCY", "0.3"))
        self.weight_importance = float(os.getenv("MEMORY_WEIGHT_IMPORTANCE", "0.1"))

        # Recency parameters
        self.recency_decay_hours = float(os.getenv("MEMORY_RECENCY_DECAY_HOURS", "24.0"))
        self.max_counter_for_frequency = int(os.getenv("MEMORY_MAX_COUNTER_FREQUENCY", "10"))

        # Validate weights
        total_weight = self.weight_similarity + self.weight_recency + self.weight_importance
        if not (0.99 <= total_weight <= 1.01):
            logger.warning(
                f"[MEMORY_CONFIG] Weights sum to {total_weight:.3f}, not 1.0. "
                f"sim={self.weight_similarity}, rec={self.weight_recency}, imp={self.weight_importance}"
            )


class MemoryStore:
    """
    Pinecone-based memory store with intelligent deduplication.

    Features:
    - User-specific indexes (memory-{user_id})
    - Semantic deduplication with configurable threshold
    - Multi-factor scoring for retrieval
    - Local JSON backup
    """

    def __init__(self, user_id: str = None, index_name: str = None):
        """
        Initialize MemoryStore.

        Args:
            user_id: User ID for user-specific index (memory-{user_id})
            index_name: Optional override for index name
        """
        self.config = MemoryConfig()
        self.enabled = False

        if not PINECONE_AVAILABLE:
            logger.error("[MEMORY_STORE] Pinecone not available")
            return

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.error("[MEMORY_STORE] PINECONE_API_KEY not set")
            return

        try:
            self.pc = Pinecone(api_key=api_key)

            # Determine index name
            if user_id:
                sanitized_user_id = self._sanitize_index_name(user_id)
                self.index_name = f"memory-{sanitized_user_id}"
            elif index_name:
                self.index_name = index_name
            else:
                self.index_name = os.getenv("PINECONE_INDEX_NAME", "student-memories")

            self._ensure_index_exists()
            self.index = self.pc.Index(self.index_name)
            self.enabled = True

            logger.info(f"[MEMORY_STORE] Initialized with index: {self.index_name}")

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Initialization failed: {e}")

    def _sanitize_index_name(self, user_id: str) -> str:
        """Sanitize user_id for Pinecone index name"""
        sanitized = re.sub(r'[^a-z0-9-]', '-', user_id.lower())
        sanitized = sanitized.replace('_', '-')
        sanitized = re.sub(r'-+', '-', sanitized)
        sanitized = sanitized.strip('-')
        return sanitized if sanitized else "anonymous"

    def _ensure_index_exists(self):
        """Create index if it doesn't exist"""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                dimension = get_embedding_dimension()
                cloud = os.getenv("PINECONE_CLOUD", "aws")
                region = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

                logger.info(f"[MEMORY_STORE] Creating index '{self.index_name}' (dim={dimension})")

                try:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=dimension,
                        metric="cosine",
                        spec=ServerlessSpec(cloud=cloud, region=region)
                    )
                except PineconeApiException as e:
                    if e.status == 409:
                        logger.info(f"[MEMORY_STORE] Index created by another process")
                    else:
                        raise

                # Wait for index to be ready
                max_wait = 300
                start = time.time()
                while True:
                    try:
                        info = self.pc.describe_index(self.index_name)
                        if info.status.get('ready', False):
                            break
                        if time.time() - start > max_wait:
                            raise TimeoutError("Index not ready")
                        time.sleep(2)
                    except Exception:
                        if time.time() - start > max_wait:
                            raise
                        time.sleep(2)

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Error ensuring index: {e}")
            raise

    def _find_duplicate_memory(self, memory: Memory) -> Optional[Dict]:
        """Search for duplicate memory using semantic similarity"""
        if not self.enabled:
            return None

        try:
            embedding = get_embeddings_batch([memory.text])[0]
            if not embedding:
                return None

            response = self.index.query(
                vector=embedding,
                top_k=1,
                namespace=memory.type.value,
                filter={"student_id": {"$eq": memory.student_id}},
                include_metadata=True
            )

            if not response.matches:
                return None

            top_match = response.matches[0]
            if top_match.score >= self.config.similarity_threshold:
                logger.info(
                    f"[DEDUP] Duplicate found (score: {top_match.score:.3f}): "
                    f"'{top_match.metadata.get('text', '')[:50]}...'"
                )
                return {
                    "id": top_match.id,
                    "score": top_match.score,
                    "metadata": top_match.metadata
                }

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Dedup check failed: {e}")

        return None

    def _calculate_recency_score(self, counter: int, first_epoch: float, last_epoch: float) -> float:
        """Calculate recency score combining time and frequency"""
        current_time = time.time()
        hours_since_last = (current_time - last_epoch) / 3600.0
        time_factor = 1.0 / (1.0 + (hours_since_last / self.config.recency_decay_hours))
        frequency_factor = min(counter / float(self.config.max_counter_for_frequency), 1.0)
        return (time_factor * 0.5) + (frequency_factor * 0.5)

    def save_memory(self, memory: Memory) -> bool:
        """
        Save a memory with intelligent deduplication.

        Returns:
            True if saved successfully
        """
        if not self.enabled:
            return False

        try:
            # Check for duplicates
            duplicate = self._find_duplicate_memory(memory)

            if duplicate:
                # Update existing memory
                existing_metadata = duplicate["metadata"]
                old_counter = existing_metadata.get('counter', 1)
                first_epoch = existing_metadata.get('first_epoch', memory.first_epoch)
                new_importance = max(
                    existing_metadata.get('importance', 0.5),
                    memory.importance
                )

                clean_metadata = {k: v for k, v in memory.metadata.items() if v is not None}

                self.index.update(
                    id=duplicate["id"],
                    set_metadata={
                        "student_id": memory.student_id,
                        "type": memory.type.value,
                        "text": memory.text,
                        "importance": new_importance,
                        "timestamp": memory.timestamp.isoformat(),
                        "session_id": memory.session_id,
                        "counter": old_counter + 1,
                        "first_epoch": first_epoch,
                        "last_epoch": memory.last_epoch,
                        **clean_metadata
                    },
                    namespace=memory.type.value
                )
                logger.info(f"[MEMORY_STORE] Updated memory (counter: {old_counter + 1})")
            else:
                # Create new memory
                embedding = get_embeddings_batch([memory.text])[0]
                if not embedding:
                    return False

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
                            "counter": memory.counter,
                            "first_epoch": memory.first_epoch,
                            "last_epoch": memory.last_epoch,
                            **clean_metadata
                        }
                    }],
                    namespace=memory.type.value
                )
                logger.info(f"[MEMORY_STORE] Created new memory: {memory.type.value}")

            # Backup to local file
            self._save_to_local(memory)
            return True

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Save failed: {e}")
            return False

    def save_memories_batch(self, memories: List[Memory]) -> int:
        """
        Save a batch of memories with deduplication.

        Returns:
            Number of successfully saved memories
        """
        if not self.enabled or not memories:
            return 0

        success_count = 0
        for memory in memories:
            if self.save_memory(memory):
                success_count += 1

        logger.info(f"[MEMORY_STORE] Batch saved {success_count}/{len(memories)} memories")
        return success_count

    def search(
        self,
        query: str,
        student_id: str,
        mem_type: Optional[MemoryType] = None,
        top_k: int = 10,
        exclude_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for memories with multi-factor scoring.

        Args:
            query: Search query text
            student_id: Student to search for
            mem_type: Optional memory type filter
            top_k: Number of results
            exclude_session_id: Session to exclude

        Returns:
            List of results with memory and scores
        """
        if not self.enabled:
            return []

        try:
            query_embedding = get_query_embedding(query)
            if not query_embedding:
                return []

            filter_dict = {"student_id": {"$eq": student_id}}
            if exclude_session_id:
                filter_dict["session_id"] = {"$ne": exclude_session_id}

            namespaces = [mem_type.value] if mem_type else [mt.value for mt in MemoryType]
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

                    for match in response.matches:
                        if not match.metadata:
                            continue

                        try:
                            # Reconstruct Memory from metadata
                            metadata_dict = match.metadata.copy()
                            nested_metadata = {}
                            memory_fields = {
                                'id', 'type', 'text', 'importance', 'student_id',
                                'session_id', 'timestamp', 'counter', 'first_epoch', 'last_epoch'
                            }
                            for key, value in list(metadata_dict.items()):
                                if key not in memory_fields:
                                    nested_metadata[key] = value
                                    metadata_dict.pop(key)
                            metadata_dict['metadata'] = nested_metadata

                            memory = Memory.from_dict(metadata_dict)
                            results.append({
                                "memory": memory,
                                "vector_similarity": match.score
                            })
                        except Exception as e:
                            logger.error(f"[MEMORY_STORE] Error converting match: {e}")

                except Exception as e:
                    logger.error(f"[MEMORY_STORE] Error searching namespace '{namespace}': {e}")

            # Calculate final scores
            for result in results:
                memory = result["memory"]
                vector_similarity = result["vector_similarity"]
                recency_score = self._calculate_recency_score(
                    getattr(memory, 'counter', 1),
                    getattr(memory, 'first_epoch', time.time()),
                    getattr(memory, 'last_epoch', time.time())
                )
                importance_score = memory.importance

                final_score = (
                    (vector_similarity * self.config.weight_similarity) +
                    (recency_score * self.config.weight_recency) +
                    (importance_score * self.config.weight_importance)
                )

                result["recency_score"] = recency_score
                result["importance_score"] = importance_score
                result["final_score"] = final_score
                result["score"] = final_score

            # Sort by final score
            results.sort(key=lambda x: x["final_score"], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Search failed: {e}")
            return []

    def delete_memory(self, memory_id: str, namespace: str = None) -> bool:
        """Delete a memory by ID"""
        if not self.enabled:
            return False

        try:
            if namespace:
                self.index.delete(ids=[memory_id], namespace=namespace)
            else:
                # Delete from all namespaces
                for mem_type in MemoryType:
                    self.index.delete(ids=[memory_id], namespace=mem_type.value)
            return True
        except Exception as e:
            logger.error(f"[MEMORY_STORE] Delete failed: {e}")
            return False

    def delete_student_memories(self, student_id: str) -> bool:
        """Delete all memories for a student"""
        if not self.enabled:
            return False

        try:
            for mem_type in MemoryType:
                self.index.delete(
                    filter={"student_id": {"$eq": student_id}},
                    namespace=mem_type.value
                )
            logger.info(f"[MEMORY_STORE] Deleted all memories for student: {student_id}")
            return True
        except Exception as e:
            logger.error(f"[MEMORY_STORE] Delete student memories failed: {e}")
            return False

    def _save_to_local(self, memory: Memory):
        """Save memory to local JSON file for backup"""
        try:
            data_dir = Path(f"services/TeachingAssistant/Memory/data/{memory.student_id}/memory")
            data_dir.mkdir(parents=True, exist_ok=True)

            file_path = data_dir / f"{memory.type.value}.json"
            memories = []
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    memories = json.load(f)

            memory_dict = memory.to_dict()
            existing_ids = {m.get('id') for m in memories if isinstance(m, dict)}

            if memory_dict['id'] not in existing_ids:
                memories.append(memory_dict)
            else:
                for i, m in enumerate(memories):
                    if isinstance(m, dict) and m.get('id') == memory_dict['id']:
                        memories[i] = memory_dict
                        break

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memories, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[MEMORY_STORE] Local save failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if not self.enabled:
            return {"enabled": False}

        try:
            stats = self.index.describe_index_stats()
            return {
                "enabled": True,
                "index_name": self.index_name,
                "total_vector_count": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "namespaces": stats.get("namespaces", {}),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}

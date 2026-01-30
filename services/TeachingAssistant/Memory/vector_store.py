"""
MongoDB Vector Store - MongoDB Atlas-based memory storage with vector search

Replaces Pinecone with MongoDB Atlas Vector Search.
Uses the same embeddings module (Gemini/OpenAI) for generating vectors.

Features:
- Intelligent deduplication using semantic similarity
- Multi-factor scoring (similarity, recency, importance)
- User-specific collections or namespaces
- No additional service dependencies (uses existing MongoDB)
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

# Import MongoDB
try:
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("[MONGODB_VECTOR_STORE] pymongo not installed")

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


class MemoryStore:
    """
    MongoDB-based memory store with vector search.

    Features:
    - Uses MongoDB Atlas Vector Search for semantic similarity
    - Same interface as Pinecone MemoryStore
    - Intelligent deduplication
    - Multi-factor scoring for retrieval
    """

    def __init__(self, user_id: str = None, collection_name: str = None):
        """
        Initialize MongoDBMemoryStore.

        Args:
            user_id: User ID for filtering (stored in documents)
            collection_name: Optional override for collection name
        """
        self.config = MemoryConfig()
        self.enabled = False
        self.user_id = user_id

        if not MONGODB_AVAILABLE:
            logger.error("[MONGODB_VECTOR_STORE] pymongo not available")
            return

        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            logger.error("[MONGODB_VECTOR_STORE] MONGODB_URI not set")
            return

        try:
            self.client = MongoClient(mongodb_uri)
            self.db_name = os.getenv("MONGODB_MEMORY_DB", "ai_tutor")
            self.db = self.client[self.db_name]

            # Collection name - single collection for all memories
            self.collection_name = collection_name or os.getenv("MONGODB_MEMORY_COLLECTION", "memories")
            self.collection = self.db[self.collection_name]

            # Ensure indexes
            self._ensure_indexes()

            self.enabled = True
            self.embedding_dimension = get_embedding_dimension()

            logger.info(f"[MONGODB_VECTOR_STORE] Initialized with collection: {self.collection_name} (dim={self.embedding_dimension})")

        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Initialization failed: {e}")

    def _ensure_indexes(self):
        """Create necessary indexes for efficient queries"""
        try:
            # Standard indexes for filtering
            self.collection.create_index("student_id")
            self.collection.create_index("type")
            self.collection.create_index([("student_id", 1), ("type", 1)])
            self.collection.create_index("session_id")

            # Note: Vector search index must be created in MongoDB Atlas UI or via Atlas API
            # The index should be named "vector_index" and configured for the "embedding" field
            logger.info("[MONGODB_VECTOR_STORE] Standard indexes ensured")

        except Exception as e:
            logger.warning(f"[MONGODB_VECTOR_STORE] Index creation warning: {e}")

    def _check_vector_search_available(self) -> bool:
        """Check if vector search is available (Atlas feature)"""
        try:
            # Try a simple vector search to see if it's available
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": [0.0] * self.embedding_dimension,
                        "numCandidates": 1,
                        "limit": 1
                    }
                }
            ]
            list(self.collection.aggregate(pipeline))
            return True
        except OperationFailure as e:
            if "vector search" in str(e).lower() or "not found" in str(e).lower():
                logger.warning("[MONGODB_VECTOR_STORE] Vector search index not configured. Using fallback search.")
                return False
            return False
        except Exception:
            return False

    def _find_duplicate_memory(self, memory: Memory) -> Optional[Dict]:
        """Search for duplicate memory using semantic similarity"""
        if not self.enabled:
            return None

        try:
            embedding = get_embeddings_batch([memory.text])[0]
            if not embedding:
                return None

            # Try vector search first
            try:
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "vector_index",
                            "path": "embedding",
                            "queryVector": embedding,
                            "numCandidates": 10,
                            "limit": 1,
                            "filter": {
                                "student_id": memory.student_id,
                                "type": memory.type.value
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "text": 1,
                            "student_id": 1,
                            "type": 1,
                            "importance": 1,
                            "counter": 1,
                            "first_epoch": 1,
                            "last_epoch": 1,
                            "score": {"$meta": "vectorSearchScore"}
                        }
                    }
                ]

                results = list(self.collection.aggregate(pipeline))

                if results and results[0].get("score", 0) >= self.config.similarity_threshold:
                    match = results[0]
                    logger.info(
                        f"[DEDUP] Duplicate found (score: {match['score']:.3f}): "
                        f"'{match.get('text', '')[:50]}...'"
                    )
                    return {
                        "id": str(match["_id"]),
                        "score": match["score"],
                        "metadata": match
                    }

            except OperationFailure:
                # Vector search not available, use text-based fallback
                existing = self.collection.find_one({
                    "student_id": memory.student_id,
                    "type": memory.type.value,
                    "text": memory.text
                })
                if existing:
                    return {
                        "id": str(existing["_id"]),
                        "score": 1.0,
                        "metadata": existing
                    }

        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Dedup check failed: {e}")

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

                self.collection.update_one(
                    {"_id": existing_metadata["_id"]},
                    {"$set": {
                        "importance": new_importance,
                        "timestamp": memory.timestamp.isoformat(),
                        "session_id": memory.session_id,
                        "counter": old_counter + 1,
                        "last_epoch": memory.last_epoch,
                        **{k: v for k, v in memory.metadata.items() if v is not None}
                    }}
                )
                logger.info(f"[MONGODB_VECTOR_STORE] Updated memory (counter: {old_counter + 1})")
            else:
                # Create new memory
                embedding = get_embeddings_batch([memory.text])[0]
                if not embedding:
                    logger.warning("[MONGODB_VECTOR_STORE] Failed to generate embedding")
                    return False

                doc = {
                    "memory_id": memory.id,
                    "student_id": memory.student_id,
                    "type": memory.type.value,
                    "text": memory.text,
                    "embedding": embedding,
                    "importance": memory.importance,
                    "timestamp": memory.timestamp.isoformat(),
                    "session_id": memory.session_id,
                    "counter": memory.counter,
                    "first_epoch": memory.first_epoch,
                    "last_epoch": memory.last_epoch,
                    **{k: v for k, v in memory.metadata.items() if v is not None}
                }

                self.collection.insert_one(doc)
                logger.info(f"[MONGODB_VECTOR_STORE] Created new memory: {memory.type.value}")

            # Backup to local file
            self._save_to_local(memory)
            return True

        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Save failed: {e}")
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

        logger.info(f"[MONGODB_VECTOR_STORE] Batch saved {success_count}/{len(memories)} memories")
        return success_count

    def search(
        self,
        query: str = None,
        query_text: str = None,  # Alias for compatibility
        student_id: str = None,
        mem_type: Optional[MemoryType] = None,
        top_k: int = 10,
        exclude_session_id: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for memories with multi-factor scoring.

        Args:
            query: Search query text
            query_text: Alias for query (for compatibility)
            student_id: Student to search for (uses self.user_id if not provided)
            mem_type: Optional memory type filter
            top_k: Number of results
            exclude_session_id: Session to exclude
            min_importance: Minimum importance threshold

        Returns:
            List of results with memory and scores
        """
        if not self.enabled:
            return []

        # Handle parameter aliases
        query = query or query_text
        student_id = student_id or self.user_id

        if not query or not student_id:
            return []

        try:
            query_embedding = get_query_embedding(query)
            if not query_embedding:
                return []

            # Build filter
            filter_dict = {"student_id": student_id}
            if exclude_session_id:
                filter_dict["session_id"] = {"$ne": exclude_session_id}
            if mem_type:
                filter_dict["type"] = mem_type.value
            if min_importance > 0:
                filter_dict["importance"] = {"$gte": min_importance}

            results = []

            # Try vector search
            try:
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "vector_index",
                            "path": "embedding",
                            "queryVector": query_embedding,
                            "numCandidates": top_k * 10,
                            "limit": top_k * 2,  # Get more to filter
                            "filter": filter_dict
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "memory_id": 1,
                            "text": 1,
                            "student_id": 1,
                            "type": 1,
                            "importance": 1,
                            "timestamp": 1,
                            "session_id": 1,
                            "counter": 1,
                            "first_epoch": 1,
                            "last_epoch": 1,
                            "score": {"$meta": "vectorSearchScore"}
                        }
                    }
                ]

                cursor = self.collection.aggregate(pipeline)

                for doc in cursor:
                    # Apply additional filters that vector search might not support
                    if mem_type and doc.get("type") != mem_type.value:
                        continue

                    results.append({
                        "text": doc.get("text", ""),
                        "type": doc.get("type", "unknown"),
                        "importance": doc.get("importance", 0.5),
                        "timestamp": doc.get("timestamp", ""),
                        "vector_similarity": doc.get("score", 0),
                        "counter": doc.get("counter", 1),
                        "first_epoch": doc.get("first_epoch", time.time()),
                        "last_epoch": doc.get("last_epoch", time.time()),
                    })

            except OperationFailure as e:
                # Vector search not available, fall back to regular query
                logger.warning(f"[MONGODB_VECTOR_STORE] Vector search failed, using fallback: {e}")

                # Type filter
                types_to_search = [mem_type.value] if mem_type else [mt.value for mt in MemoryType]

                for type_value in types_to_search:
                    query_filter = {**filter_dict, "type": type_value}
                    cursor = self.collection.find(query_filter).limit(top_k)

                    for doc in cursor:
                        results.append({
                            "text": doc.get("text", ""),
                            "type": doc.get("type", "unknown"),
                            "importance": doc.get("importance", 0.5),
                            "timestamp": doc.get("timestamp", ""),
                            "vector_similarity": 0.5,  # Default score for fallback
                            "counter": doc.get("counter", 1),
                            "first_epoch": doc.get("first_epoch", time.time()),
                            "last_epoch": doc.get("last_epoch", time.time()),
                        })

            # Calculate final scores
            for result in results:
                vector_similarity = result.get("vector_similarity", 0.5)
                recency_score = self._calculate_recency_score(
                    result.get("counter", 1),
                    result.get("first_epoch", time.time()),
                    result.get("last_epoch", time.time())
                )
                importance_score = result.get("importance", 0.5)

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
            results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Search failed: {e}")
            return []

    def search_similar_memories(
        self,
        query_text: str,
        student_id: str,
        top_k: int = 5,
        min_importance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Alias for search() with common parameters.
        Used by session_manager.retrieve_relevant_memories()
        """
        return self.search(
            query=query_text,
            student_id=student_id,
            top_k=top_k,
            min_importance=min_importance
        )

    def delete_memory(self, memory_id: str, namespace: str = None) -> bool:
        """Delete a memory by ID"""
        if not self.enabled:
            return False

        try:
            result = self.collection.delete_one({"memory_id": memory_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Delete failed: {e}")
            return False

    def delete_student_memories(self, student_id: str) -> bool:
        """Delete all memories for a student"""
        if not self.enabled:
            return False

        try:
            result = self.collection.delete_many({"student_id": student_id})
            logger.info(f"[MONGODB_VECTOR_STORE] Deleted {result.deleted_count} memories for student: {student_id}")
            return True
        except Exception as e:
            logger.error(f"[MONGODB_VECTOR_STORE] Delete student memories failed: {e}")
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
            logger.error(f"[MONGODB_VECTOR_STORE] Local save failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self.enabled:
            return {"enabled": False}

        try:
            # Get total count
            total_count = self.collection.count_documents({})

            # Get count by type
            pipeline = [
                {"$group": {"_id": "$type", "count": {"$sum": 1}}}
            ]
            by_type = {doc["_id"]: doc["count"] for doc in self.collection.aggregate(pipeline)}

            # Get count for current user if set
            user_count = 0
            if self.user_id:
                user_count = self.collection.count_documents({"student_id": self.user_id})

            return {
                "enabled": True,
                "collection_name": self.collection_name,
                "total_memories": total_count,
                "user_memories": user_count,
                "by_type": by_type,
                "embedding_dimension": self.embedding_dimension,
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


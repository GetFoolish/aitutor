"""
Pinecone Client for Semantic Memory Search
Based on the Cognitive Memory Pipeline architecture

This module handles:
- Vector embeddings for memories (Gemini or OpenAI)
- Semantic search for "find similar moments"
- Upsert/delete operations for memory management

Supports: Google Gemini embeddings (primary) and OpenAI (fallback)
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

# Try Gemini for embeddings (primary)
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Fallback to OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PineconeClient:
    """
    Singleton Pinecone client for semantic memory search.

    Uses Gemini or OpenAI embeddings to convert memory text into vectors,
    then stores and queries them in Pinecone for semantic similarity.
    """

    _instance = None
    _initialized = False

    # Default configuration (can be overridden by env vars)
    DEFAULT_INDEX_NAME = "student-memories"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PineconeClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.enabled = False
        self.pc = None
        self.index = None
        self.embedding_provider = None
        self.gemini_client = None
        self.gemini_model = None
        self.openai_client = None
        self.embedding_dimension = 768  # Default for Gemini

        # Get configuration from environment
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", self.DEFAULT_INDEX_NAME)

        if not PINECONE_AVAILABLE:
            logger.warning("[PINECONE] pinecone-client not installed. Semantic search disabled.")
            self._initialized = True
            return

        if not pinecone_api_key:
            logger.warning("[PINECONE] PINECONE_API_KEY not set. Semantic search disabled.")
            self._initialized = True
            return

        # Try to initialize embedding provider
        if not self._init_embedding_provider():
            logger.warning("[PINECONE] No embedding provider available. Semantic search disabled.")
            self._initialized = True
            return

        try:
            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_api_key)

            # Get or create index
            self._ensure_index()

            self.enabled = True
            logger.info(
                f"[PINECONE] Initialized with {self.embedding_provider} embeddings, "
                f"index '{self.index_name}' (dim={self.embedding_dimension})"
            )

        except Exception as e:
            logger.error(f"[PINECONE] Failed to initialize: {e}")

        self._initialized = True

    def _init_embedding_provider(self) -> bool:
        """Initialize embedding provider (Gemini or OpenAI)"""

        # Try Gemini first
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                # Use text-embedding model
                self.gemini_model = "models/text-embedding-004"
                self.embedding_provider = "gemini"
                self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
                logger.info(f"[PINECONE] Using Gemini embeddings (dim={self.embedding_dimension})")
                return True
            except Exception as e:
                logger.warning(f"[PINECONE] Gemini embedding init failed: {e}")

        # Fallback to OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                self.embedding_provider = "openai"
                self.embedding_dimension = 1536  # text-embedding-3-small
                logger.info("[PINECONE] Using OpenAI embeddings (dim=1536)")
                return True
            except Exception as e:
                logger.warning(f"[PINECONE] OpenAI embedding init failed: {e}")

        return False

    def _ensure_index(self):
        """Ensure the Pinecone index exists"""
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"[PINECONE] Creating index '{self.index_name}' (dim={self.embedding_dimension})...")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
                )
            )

        self.index = self.pc.Index(self.index_name)

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if not self.embedding_provider:
            return None

        try:
            if self.embedding_provider == "gemini":
                result = self.gemini_client.models.embed_content(
                    model=self.gemini_model,
                    contents=text
                )
                return result.embeddings[0].values

            elif self.embedding_provider == "openai" and self.openai_client:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding

        except Exception as e:
            logger.error(f"[PINECONE] Failed to generate embedding: {e}")
            return None

    def _get_query_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for query (may use different task type)"""
        if not self.embedding_provider:
            return None

        try:
            if self.embedding_provider == "gemini":
                result = self.gemini_client.models.embed_content(
                    model=self.gemini_model,
                    contents=text
                )
                return result.embeddings[0].values

            elif self.embedding_provider == "openai" and self.openai_client:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding

        except Exception as e:
            logger.error(f"[PINECONE] Failed to generate query embedding: {e}")
            return None

    def upsert_memory(
        self,
        memory_id: str,
        student_id: str,
        text: str,
        memory_type: str,
        importance: float,
        emotion: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Upsert a memory into Pinecone.

        Args:
            memory_id: Unique identifier for the memory
            student_id: Student this memory belongs to
            text: The memory text to embed
            memory_type: Type of memory (personal, academic, etc.)
            importance: Importance score (0-1)
            emotion: Associated emotion
            timestamp: When the memory was created
            session_id: Session where memory was extracted
            tags: Additional tags for filtering

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Generate embedding
            embedding = self._get_embedding(text)
            if not embedding:
                return False

            # Prepare metadata
            metadata = {
                "student_id": student_id,
                "text": text[:1000],  # Pinecone metadata limit
                "memory_type": memory_type,
                "importance": importance,
                "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            }

            if emotion:
                metadata["emotion"] = emotion
            if session_id:
                metadata["session_id"] = session_id
            if tags:
                metadata["tags"] = tags

            # Upsert to Pinecone
            self.index.upsert(
                vectors=[{
                    "id": memory_id,
                    "values": embedding,
                    "metadata": metadata
                }]
            )

            logger.debug(f"[PINECONE] Upserted memory {memory_id}")
            return True

        except Exception as e:
            logger.error(f"[PINECONE] Failed to upsert memory {memory_id}: {e}")
            return False

    def upsert_memories_batch(self, memories: List[Dict[str, Any]]) -> int:
        """
        Batch upsert multiple memories.

        Args:
            memories: List of memory dicts with keys:
                - id, student_id, text, memory_type, importance
                - Optional: emotion, timestamp, session_id, tags

        Returns:
            Number of successfully upserted memories
        """
        if not self.enabled:
            return 0

        success_count = 0
        vectors = []

        for memory in memories:
            try:
                embedding = self._get_embedding(memory["text"])
                if not embedding:
                    continue

                metadata = {
                    "student_id": memory["student_id"],
                    "text": memory["text"][:1000],
                    "memory_type": memory.get("memory_type", "personal"),
                    "importance": memory.get("importance", 0.5),
                    "timestamp": memory.get("timestamp", datetime.utcnow().isoformat()),
                }

                if memory.get("emotion"):
                    metadata["emotion"] = memory["emotion"]
                if memory.get("session_id"):
                    metadata["session_id"] = memory["session_id"]
                if memory.get("tags"):
                    metadata["tags"] = memory["tags"]

                vectors.append({
                    "id": memory["id"],
                    "values": embedding,
                    "metadata": metadata
                })

            except Exception as e:
                logger.error(f"[PINECONE] Failed to prepare memory {memory.get('id')}: {e}")

        if vectors:
            try:
                # Batch upsert (Pinecone handles up to 100 at a time)
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    self.index.upsert(vectors=batch)
                    success_count += len(batch)

                logger.info(f"[PINECONE] Batch upserted {success_count} memories")
            except Exception as e:
                logger.error(f"[PINECONE] Batch upsert failed: {e}")

        return success_count

    def search_similar_memories(
        self,
        query_text: str,
        student_id: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        emotion_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories.

        Args:
            query_text: Text to find similar memories for
            student_id: Student to search memories for
            top_k: Number of results to return
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            emotion_filter: Filter by emotion

        Returns:
            List of matching memories with similarity scores
        """
        if not self.enabled:
            return []

        try:
            # Generate query embedding
            query_embedding = self._get_query_embedding(query_text)
            if not query_embedding:
                return []

            # Build filter
            filter_dict = {"student_id": {"$eq": student_id}}

            if memory_type:
                filter_dict["memory_type"] = {"$eq": memory_type}

            if min_importance > 0:
                filter_dict["importance"] = {"$gte": min_importance}

            if emotion_filter:
                filter_dict["emotion"] = {"$eq": emotion_filter}

            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )

            # Format results
            memories = []
            for match in results.get("matches", []):
                memories.append({
                    "id": match["id"],
                    "similarity_score": match["score"],
                    "text": match["metadata"].get("text", ""),
                    "memory_type": match["metadata"].get("memory_type"),
                    "emotion": match["metadata"].get("emotion"),
                    "importance": match["metadata"].get("importance", 0.5),
                    "timestamp": match["metadata"].get("timestamp"),
                    "session_id": match["metadata"].get("session_id"),
                })

            logger.debug(f"[PINECONE] Found {len(memories)} similar memories for student {student_id}")
            return memories

        except Exception as e:
            logger.error(f"[PINECONE] Search failed: {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a single memory from Pinecone"""
        if not self.enabled:
            return False

        try:
            self.index.delete(ids=[memory_id])
            logger.debug(f"[PINECONE] Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"[PINECONE] Failed to delete memory {memory_id}: {e}")
            return False

    def delete_student_memories(self, student_id: str) -> bool:
        """Delete all memories for a student"""
        if not self.enabled:
            return False

        try:
            self.index.delete(
                filter={"student_id": {"$eq": student_id}}
            )
            logger.info(f"[PINECONE] Deleted all memories for student {student_id}")
            return True
        except Exception as e:
            logger.error(f"[PINECONE] Failed to delete student memories: {e}")
            return False

    def get_index_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        if not self.enabled:
            return {"enabled": False}

        try:
            stats = self.index.describe_index_stats()
            return {
                "enabled": True,
                "embedding_provider": self.embedding_provider,
                "index_name": self.index_name,
                "total_vector_count": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", self.embedding_dimension),
                "index_fullness": stats.get("index_fullness", 0),
            }
        except Exception as e:
            logger.error(f"[PINECONE] Failed to get stats: {e}")
            return {"enabled": True, "error": str(e)}


# Singleton instance
pinecone_client = PineconeClient()

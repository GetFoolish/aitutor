import os
import sys
import json
import time
import re
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from dataclasses import dataclass
from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import PineconeApiException
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.logging_config import get_logger
from .schema import Memory, MemoryType
from .embeddings import get_embeddings_batch

load_dotenv()

logger = get_logger(__name__)


@dataclass
class MemoryConfig:
    """
    Configuration for memory deduplication and retrieval scoring.
    All parameters are loaded from environment variables with sensible defaults.
    """
    # Deduplication settings
    similarity_threshold: float = 0.92  # Cosine similarity threshold for duplicates (0.0-1.0)
    min_word_count: int = 3  # Minimum words required to save a memory
    
    # Junk word filter (common single-word responses that shouldn't be saved)
    junk_words: set = None
    
    # Scoring weights for retrieval (must sum to ~1.0)
    weight_similarity: float = 0.6  # Vector similarity weight
    weight_recency: float = 0.3     # Recency weight
    weight_importance: float = 0.1  # Importance weight
    
    # Recency calculation parameters
    recency_decay_hours: float = 24.0  # Hours over which recency decays to 50%
    max_counter_for_frequency: int = 10  # Max counter value for frequency normalization
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        # Deduplication settings
        
        self.similarity_threshold = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.92"))
        self.min_word_count = int(os.getenv("MEMORY_MIN_WORD_COUNT", "3"))
        
        # Junk words from env or use defaults
        junk_words_str = os.getenv("MEMORY_JUNK_WORDS", "y,yes,no,okay,ok,yeah,nope,yep,sure,fine,k")
        self.junk_words = {word.strip().lower() for word in junk_words_str.split(",")}
        
        # Scoring weights
        self.weight_similarity = float(os.getenv("MEMORY_WEIGHT_SIMILARITY", "0.6"))
        self.weight_recency = float(os.getenv("MEMORY_WEIGHT_RECENCY", "0.3"))
        self.weight_importance = float(os.getenv("MEMORY_WEIGHT_IMPORTANCE", "0.1"))
        
        # Recency parameters
        self.recency_decay_hours = float(os.getenv("MEMORY_RECENCY_DECAY_HOURS", "24.0"))
        self.max_counter_for_frequency = int(os.getenv("MEMORY_MAX_COUNTER_FREQUENCY", "10"))
        
        # Validate weights sum to approximately 1.0
        total_weight = self.weight_similarity + self.weight_recency + self.weight_importance
        if not (0.99 <= total_weight <= 1.01):
            logger.warning(
                f"Memory scoring weights sum to {total_weight:.3f}, not 1.0. "
                f"This may affect score interpretation. Weights: "
                f"similarity={self.weight_similarity}, recency={self.weight_recency}, "
                f"importance={self.weight_importance}"
            )
        
        logger.info(
            f"[MEMORY_CONFIG] Loaded configuration: "
            f"similarity_threshold={self.similarity_threshold}, "
            f"min_words={self.min_word_count}, "
            f"weights=(sim:{self.weight_similarity}, rec:{self.weight_recency}, imp:{self.weight_importance})"
        )


class MemoryStore:
    def __init__(self, user_id: str = None, index_name: str = None):
        """
        Initialize MemoryStore with user-specific index.
        
        Args:
            user_id: User ID to create/get index named "memory_{user_id}"
            index_name: Optional override for index name (for backward compatibility)
        """
        # Initialize configuration
        self.config = MemoryConfig()
        
        # Validate Pinecone API key
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key or api_key == "":
            logger.error("PINECONE_API_KEY not set. Memory system will not function.")
            logger.error("Please set PINECONE_API_KEY environment variable. See SETUP.md for instructions.")
            raise ValueError("PINECONE_API_KEY environment variable is required for memory functionality")
        
        self.pc = Pinecone(api_key=api_key)
        
        # Determine index name: user_id-based or provided or env or default
        if user_id:
            # Sanitize user_id for Pinecone index name (must be lowercase alphanumeric with hyphens only)
            sanitized_user_id = self._sanitize_index_name(user_id)
            self.index_name = f"memory-{sanitized_user_id}"
            logger.info(f"Using user-specific index: {self.index_name} (from user_id: {user_id})")
        elif index_name:
            self.index_name = index_name
            logger.info(f"Using provided index: {self.index_name}")
        else:
            # Fallback to env or default (for backward compatibility)
            self.index_name = os.getenv("PINECONE_INDEX_NAME", "aitutor-memories")
            logger.info(f"Using default index: {self.index_name}")
        
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
                logger.info(f"Index '{self.index_name}' not found. Creating new index for user...")
                
                # Get embedding dimension from env or default to 1024
                dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
                
                # Get cloud and region from env or use defaults
                cloud = os.getenv("PINECONE_CLOUD", "aws")  # "aws" or "gcp"
                region = os.getenv("PINECONE_REGION", "us-east-1")
                
                try:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=dimension,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud=cloud,
                            region=region
                        )
                    )
                except PineconeApiException as e:
                    # Handle race condition: another process created the index simultaneously
                    if e.status == 409:
                        logger.info(f"Index '{self.index_name}' was created by another process (409 Conflict). Continuing...")
                    else:
                        raise
                
                # Wait for index to be ready
                logger.info(f"Waiting for index '{self.index_name}' to be ready...")
                max_wait_time = 300  # 5 minutes max wait
                start_time = time.time()
                
                while True:
                    try:
                        index_info = self.pc.describe_index(self.index_name)
                        if index_info.status.get('ready', False):
                            logger.info(f"Index '{self.index_name}' is ready")
                            break
                        
                        elapsed = time.time() - start_time
                        if elapsed > max_wait_time:
                            raise TimeoutError(f"Index '{self.index_name}' did not become ready within {max_wait_time} seconds")
                        
                        time.sleep(2)
                    except Exception as e:
                        elapsed = time.time() - start_time
                        if elapsed > max_wait_time:
                            raise TimeoutError(f"Error waiting for index: {e}")
                        logger.warning(f"Waiting for index... ({e})")
                        time.sleep(2)
            else:
                logger.info(f"Index '{self.index_name}' already exists - using existing index")
                
        except Exception as e:
            logger.error(f"❌ Error checking/creating index: {e}", exc_info=True)
            raise



    def _find_duplicate_memory(self, memory: Memory) -> Optional[Dict]:
        """
        Search for a duplicate memory using semantic similarity.
        
        Args:
            memory: The memory to check for duplicates
            
        Returns:
            Dict containing duplicate info (id, score, metadata) if found, None otherwise
        """
        try:
            # Get embedding for the new memory
            embedding = get_embeddings_batch([memory.text])[0]
            
            # Query Pinecone for most similar memory
            response = self.index.query(
                vector=embedding,
                top_k=1,  # Only get the most similar one
                namespace=memory.type.value,
                filter={"student_id": {"$eq": memory.student_id}},
                include_metadata=True
            )
            
            # Check if any results found
            if not response.matches or len(response.matches) == 0:
                logger.debug(f"[DEDUP] No existing memories found for comparison")
                return None
            
            top_match = response.matches[0]
            similarity_score = top_match.score
            
            # Log the comparison
            existing_text = top_match.metadata.get('text', '')[:80]
            logger.debug(
                f"[DEDUP] Similarity check: new='{memory.text[:80]}...' vs "
                f"existing='{existing_text}...' → score={similarity_score:.3f}"
            )
            
            # Check if similarity exceeds threshold
            if similarity_score >= self.config.similarity_threshold:
                logger.info(
                    f"[DEDUP] Duplicate detected (score: {similarity_score:.3f} >= {self.config.similarity_threshold}): "
                    f"'{existing_text}...'"
                )
                return {
                    "id": top_match.id,
                    "score": similarity_score,
                    "metadata": top_match.metadata
                }
            else:
                logger.debug(
                    f"[DEDUP] Not a duplicate (score: {similarity_score:.3f} < {self.config.similarity_threshold})"
                )
                return None
                
        except Exception as e:
            logger.error(f"❌ Error checking for duplicate memory: {e}", exc_info=True)
            # Return None to allow new memory creation on error
            return None

    def _calculate_recency_score(self, counter: int, first_epoch: float, last_epoch: float) -> float:
        """
        Calculate recency score from memory statistics.
        
        Combines two factors:
        1. Time-based: How recently was this memory last seen?
        2. Frequency-based: How often is this memory reinforced?
        
        Args:
            counter: Number of times memory was reinforced
            first_epoch: Unix timestamp when memory was first created
            last_epoch: Unix timestamp when memory was last seen
            
        Returns:
            Recency score (0.0 to 1.0)
        """
        current_time = time.time()
        
        # Time-based recency (decays over time)
        hours_since_last = (current_time - last_epoch) / 3600.0
        # Decay to 50% after recency_decay_hours
        time_factor = 1.0 / (1.0 + (hours_since_last / self.config.recency_decay_hours))
        
        # Frequency-based recency (more reinforcements = more important)
        frequency_factor = min(counter / float(self.config.max_counter_for_frequency), 1.0)
        
        # Combine both: 50% time-based, 50% frequency-based
        recency_score = (time_factor * 0.5) + (frequency_factor * 0.5)
        
        return recency_score

    def save_memory(self, memory: Memory):
        """
        Save a memory with intelligent deduplication.
        
        Algorithm:
        1. Filter junk inputs (short text, common words)
        2. Search for semantically similar existing memories
        3. If duplicate found (similarity >= threshold), update existing memory
        4. Otherwise, create new memory
        
        Args:
            memory: Memory object to save
        """
        logger.info(f"[SAVE] Processing memory: {memory.type.value} - '{memory.text[:50]}...'")
        

        
        try:
            # Step 2: Check for duplicates
            duplicate = self._find_duplicate_memory(memory)
            
            if duplicate:
                # UPDATE existing memory
                existing_id = duplicate["id"]
                existing_metadata = duplicate["metadata"]
                old_counter = existing_metadata.get('counter', 1)
                first_epoch = existing_metadata.get('first_epoch', memory.first_epoch)
                old_importance = existing_metadata.get('importance', 0.5)
                
                # Keep the higher importance score
                new_importance = max(old_importance, memory.importance)
                
                logger.info(
                    f"[DEDUP] Updating existing memory (ID: {existing_id[:8]}..., counter: {old_counter} -> {old_counter + 1})"
                )
                
                # Filter out None/null values from metadata
                clean_metadata = {k: v for k, v in memory.metadata.items() if v is not None}
                
                # Update metadata only (don't regenerate embedding)
                self.index.update(
                    id=existing_id,
                    set_metadata={
                        "student_id": memory.student_id,
                        "type": memory.type.value,
                        "text": memory.text,  # Update to latest version
                        "importance": new_importance,
                        "timestamp": memory.timestamp.isoformat(),
                        "session_id": memory.session_id,
                        "counter": old_counter + 1,
                        "first_epoch": first_epoch,  # Keep original
                        "last_epoch": memory.last_epoch,  # Update to current
                        **clean_metadata
                    },
                    namespace=memory.type.value
                )
                
                logger.info(
                    f"[DEDUP] Updated memory: counter={old_counter + 1}, "
                    f"importance={old_importance:.2f}→{new_importance:.2f}, "
                    f"similarity={duplicate['score']:.3f}"
                )
            else:
                # CREATE new memory
                logger.info(f"[NEW] Creating new memory (no duplicate found)")
                
                embedding = get_embeddings_batch([memory.text])[0]
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
                
                logger.info(
                    f"[NEW] Created new memory in Pinecone (namespace: {memory.type.value}, "
                    f"importance: {memory.importance:.2f})"
                )
            
            # Save to local file for backup
            self._save_to_local(memory)
            logger.debug(f"[SAVE] Saved to local file")
            
        except Exception as e:
            logger.error(f"❌ Error saving memory: {e}", exc_info=True)
            raise

    def save_memories_batch(self, memories: List[Memory]):
        """
        Save a batch of memories with intelligent deduplication.
        
        This method processes each memory through save_memory() to ensure:
        1. Duplicate detection runs for each memory
        2. Counters are updated for duplicates
        3. Only unique memories are created
        
        Args:
            memories: List of Memory objects to save
        """
        if not memories:
            logger.warning("[MEMORY_STORE] save_memories_batch called with empty list")
            return

        # Count by type
        type_counts = {}
        for mem in memories:
            mem_type = mem.type.value
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1

        logger.info(
            "[MEMORY_STORE] Processing batch of %s memories with deduplication (breakdown: %s)", 
            len(memories), type_counts
        )

        # Statistics tracking
        stats = {
            "processed": 0,
            "filtered": 0,
            "duplicates_updated": 0,
            "new_created": 0,
            "errors": 0
        }

        # Process each memory individually to apply deduplication
        for i, mem in enumerate(memories, 1):
            try:

                
                # Check for duplicates
                duplicate = self._find_duplicate_memory(mem)
                
                if duplicate:
                    # UPDATE existing memory
                    existing_id = duplicate["id"]
                    existing_metadata = duplicate["metadata"]
                    old_counter = existing_metadata.get('counter', 1)
                    first_epoch = existing_metadata.get('first_epoch', mem.first_epoch)
                    old_importance = existing_metadata.get('importance', 0.5)
                    new_importance = max(old_importance, mem.importance)
                    
                    logger.info(
                        f"[BATCH {i}/{len(memories)}] [DEDUP] Updating memory (ID: {existing_id[:8]}..., "
                        f"counter: {old_counter} -> {old_counter + 1}, similarity: {duplicate['score']:.3f})"
                    )
                    
                    # Filter metadata
                    clean_metadata = {k: v for k, v in mem.metadata.items() if v is not None}
                    
                    # Update metadata only
                    self.index.update(
                        id=existing_id,
                        set_metadata={
                            "student_id": mem.student_id,
                            "type": mem.type.value,
                            "text": mem.text,
                            "importance": new_importance,
                            "timestamp": mem.timestamp.isoformat(),
                            "session_id": mem.session_id,
                            "counter": old_counter + 1,
                            "first_epoch": first_epoch,
                            "last_epoch": mem.last_epoch,
                            **clean_metadata
                        },
                        namespace=mem.type.value
                    )
                    
                    stats["duplicates_updated"] += 1
                else:
                    # CREATE new memory
                    logger.info(
                        f"[BATCH {i}/{len(memories)}] [NEW] Creating memory: "
                        f"[{mem.type.value}] (importance: {mem.importance:.2f}) - '{mem.text[:60]}...'"
                    )
                    
                    embedding = get_embeddings_batch([mem.text])[0]
                    clean_metadata = {k: v for k, v in mem.metadata.items() if v is not None}
                    
                    self.index.upsert(
                        vectors=[{
                            "id": mem.id,
                            "values": embedding,
                            "metadata": {
                                "student_id": mem.student_id,
                                "type": mem.type.value,
                                "text": mem.text,
                                "importance": mem.importance,
                                "timestamp": mem.timestamp.isoformat(),
                                "session_id": mem.session_id,
                                "counter": mem.counter,
                                "first_epoch": mem.first_epoch,
                                "last_epoch": mem.last_epoch,
                                **clean_metadata
                            }
                        }],
                        namespace=mem.type.value
                    )
                    
                    stats["new_created"] += 1
                
                # Save to local file
                self._save_to_local(mem)
                stats["processed"] += 1
                
            except Exception as e:
                logger.error(
                    f"[BATCH {i}/{len(memories)}] ❌ Error processing memory: {e}", 
                    exc_info=True
                )
                stats["errors"] += 1
        
        # Log final statistics
        logger.info(
            f"[MEMORY_STORE] Batch complete: {stats['processed']} processed, "
            f"{stats['new_created']} created, {stats['duplicates_updated']} updated, "
            f"{stats['filtered']} filtered, {stats['errors']} errors"
        )

    def search(self, query: str, student_id: str, mem_type: Optional[MemoryType] = None, 
               top_k: int = 10, exclude_session_id: Optional[str] = None) -> List[Dict]:
        from .embeddings import get_query_embedding
        
        # Sanitize query snippet for console encodings that may not support all Unicode
        snippet = (query or "")[:50]
        safe_snippet = snippet.encode("ascii", "ignore").decode("ascii", "ignore")
        
        query_embedding = get_query_embedding(query)
        filter_dict = {"student_id": {"$eq": student_id}}
        
        if exclude_session_id:
            filter_dict["session_id"] = {"$ne": exclude_session_id}

        namespaces = [mem_type.value] if mem_type else [mt.value for mt in MemoryType]
        
        results = []
        namespace_counts = {}
        
        for namespace in namespaces:
            try:
                response = self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace,
                    filter=filter_dict,
                    include_metadata=True
                )
                namespace_counts[namespace] = len(response.matches)
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
                        memory_fields = {'id', 'type', 'text', 'importance', 'student_id', 'session_id', 'timestamp', 'counter', 'first_epoch', 'last_epoch'}
                        
                        for key, value in list(metadata_dict.items()):
                            if key not in memory_fields:
                                nested_metadata[key] = value
                                metadata_dict.pop(key)
                        
                        # Add nested metadata dict
                        metadata_dict['metadata'] = nested_metadata
                        
                        memory = Memory.from_dict(metadata_dict)
                        results.append({
                            "memory": memory,
                            "vector_similarity": match.score  # Store original vector similarity
                        })
                        logger.debug(f"   ✅ Converted match {i}: {memory.text[:50]}... (similarity: {match.score:.3f})")
                    except Exception as e:
                        logger.error(f"   ❌ Error converting match {i} in namespace '{namespace}': {e}", exc_info=True)
                        logger.error(f"   Metadata keys: {list(match.metadata.keys())}")
                        continue
            except Exception as e:
                logger.error(f"❌ Error searching namespace '{namespace}' in index '{self.index_name}': {e}", exc_info=True)

        # Calculate final scores using 3-factor system
        # Log condensed search summary
        total_found = len(results)
        namespace_summary = ", ".join([f"{ns}: {count}" for ns, count in namespace_counts.items() if count > 0])
        logger.info(
            "[MEMORY_STORE] Searched %s (namespaces: %s) → Found %s candidates (%s) → Returning top %s after scoring",
            self.index_name,
            len(namespaces),
            total_found,
            namespace_summary if namespace_summary else "none",
            min(top_k, total_found)
        )
        
        for result in results:
            memory = result["memory"]
            vector_similarity = result["vector_similarity"]
            
            # Calculate recency score
            counter = getattr(memory, 'counter', 1)
            first_epoch = getattr(memory, 'first_epoch', time.time())
            last_epoch = getattr(memory, 'last_epoch', time.time())
            recency_score = self._calculate_recency_score(counter, first_epoch, last_epoch)
            
            # Get importance score
            importance_score = memory.importance
            
            # Calculate final score with configurable weights
            final_score = (
                (vector_similarity * self.config.weight_similarity) +
                (recency_score * self.config.weight_recency) +
                (importance_score * self.config.weight_importance)
            )
            
            # Store all scores
            result["recency_score"] = recency_score
            result["importance_score"] = importance_score
            result["final_score"] = final_score
            result["score"] = final_score  # For backward compatibility
            
            logger.debug(
                f"[SCORING] '{memory.text[:40]}...': "
                f"sim={vector_similarity:.3f}, rec={recency_score:.3f}, imp={importance_score:.3f} "
                f"→ final={final_score:.3f} (counter={counter})"
            )
        
        # Sort by final score instead of just vector similarity
        results.sort(key=lambda x: x["final_score"], reverse=True)
        final_results = results[:top_k]
        
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





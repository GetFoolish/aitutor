"""
Embeddings Module - Generate text embeddings for semantic search
Supports: Google Gemini (primary), Pinecone Inference (fallback), OpenAI (fallback)

Based on v4 teaching-assistant branch implementation with Gemini support.
"""

import os
import logging
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Try Gemini first (primary)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Fallback to Pinecone inference
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

# Fallback to OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Global state for embedding provider
_embedding_provider = None
_gemini_model = None
_pinecone_client = None
_openai_client = None
_embedding_dimension = 768  # Default for Gemini


def _init_embedding_provider():
    """Initialize the embedding provider (called once)"""
    global _embedding_provider, _gemini_model, _pinecone_client, _openai_client, _embedding_dimension

    if _embedding_provider is not None:
        return

    # Try Gemini first
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=gemini_key)
            _gemini_model = "models/text-embedding-004"
            _embedding_provider = "gemini"
            _embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
            logger.info(f"[EMBEDDINGS] Using Gemini embeddings (dim={_embedding_dimension})")
            return
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Gemini init failed: {e}")

    # Fallback to Pinecone inference
    pinecone_key = os.getenv("PINECONE_API_KEY")
    if pinecone_key and PINECONE_AVAILABLE:
        try:
            _pinecone_client = Pinecone(api_key=pinecone_key)
            _embedding_provider = "pinecone"
            _embedding_dimension = 1024  # multilingual-e5-large
            logger.info("[EMBEDDINGS] Using Pinecone inference embeddings (dim=1024)")
            return
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] Pinecone init failed: {e}")

    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and OPENAI_AVAILABLE:
        try:
            _openai_client = OpenAI(api_key=openai_key)
            _embedding_provider = "openai"
            _embedding_dimension = 1536  # text-embedding-3-small
            logger.info("[EMBEDDINGS] Using OpenAI embeddings (dim=1536)")
            return
        except Exception as e:
            logger.warning(f"[EMBEDDINGS] OpenAI init failed: {e}")

    logger.error("[EMBEDDINGS] No embedding provider available!")
    _embedding_provider = "none"


def get_embedding_dimension() -> int:
    """Get the embedding dimension for the current provider"""
    _init_embedding_provider()
    return _embedding_dimension


def get_query_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for a query text.
    Uses task_type="retrieval_query" for Gemini.

    Args:
        text: Query text to embed

    Returns:
        List of floats representing the embedding, or None on error
    """
    _init_embedding_provider()

    if not text or not text.strip():
        logger.warning("[EMBEDDINGS] Empty text provided for query embedding")
        return None

    try:
        if _embedding_provider == "gemini":
            result = genai.embed_content(
                model=_gemini_model,
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']

        elif _embedding_provider == "pinecone" and _pinecone_client:
            result = _pinecone_client.inference.embed(
                model="multilingual-e5-large",
                inputs=[text],
                parameters={"input_type": "query"}
            )
            return result[0]["values"]

        elif _embedding_provider == "openai" and _openai_client:
            response = _openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

    except Exception as e:
        logger.error(f"[EMBEDDINGS] Failed to generate query embedding: {e}")
        return None

    return None


def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a batch of texts.
    Uses task_type="retrieval_document" for Gemini.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings (or None for failed embeddings)
    """
    _init_embedding_provider()

    if not texts:
        return []

    # Filter out empty texts
    valid_texts = [t for t in texts if t and t.strip()]
    if not valid_texts:
        return [None] * len(texts)

    try:
        if _embedding_provider == "gemini":
            embeddings = []
            for text in texts:
                if not text or not text.strip():
                    embeddings.append(None)
                    continue
                try:
                    result = genai.embed_content(
                        model=_gemini_model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f"[EMBEDDINGS] Failed to embed text: {e}")
                    embeddings.append(None)
            return embeddings

        elif _embedding_provider == "pinecone" and _pinecone_client:
            result = _pinecone_client.inference.embed(
                model="multilingual-e5-large",
                inputs=valid_texts,
                parameters={"input_type": "passage"}
            )
            # Map back to original indices
            embeddings = []
            valid_idx = 0
            for text in texts:
                if text and text.strip():
                    embeddings.append(result[valid_idx]["values"])
                    valid_idx += 1
                else:
                    embeddings.append(None)
            return embeddings

        elif _embedding_provider == "openai" and _openai_client:
            response = _openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=valid_texts
            )
            # Map back to original indices
            embeddings = []
            valid_idx = 0
            for text in texts:
                if text and text.strip():
                    embeddings.append(response.data[valid_idx].embedding)
                    valid_idx += 1
                else:
                    embeddings.append(None)
            return embeddings

    except Exception as e:
        logger.error(f"[EMBEDDINGS] Failed to generate batch embeddings: {e}")
        return [None] * len(texts)

    return [None] * len(texts)


def get_document_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for a document/passage text.
    Alias for single-text batch embedding.

    Args:
        text: Document text to embed

    Returns:
        List of floats representing the embedding, or None on error
    """
    result = get_embeddings_batch([text])
    return result[0] if result else None

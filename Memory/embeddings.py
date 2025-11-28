"""
Embeddings Module - Pinecone inference API for embeddings.
Embeddings are generated using Pinecone's model and stored only in Pinecone.
No local embedding cache is maintained.
"""

import os
from typing import List
import numpy as np
from dotenv import load_dotenv

load_dotenv()

_pc = None
EMBEDDING_MODEL = "multilingual-e5-large"
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))


def _get_pinecone_client():
    global _pc
    if _pc is None:
        from pinecone import Pinecone
        _pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return _pc


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding using Pinecone's inference API.
    Embedding is stored in Pinecone when memory is saved, not locally.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION
    
    text = text.strip()
    
    pc = _get_pinecone_client()
    response = pc.inference.embed(
        model=EMBEDDING_MODEL,
        inputs=[text],
        parameters={"input_type": "passage"}
    )
    embedding_list = response.data[0].values
    
    return embedding_list


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings in batch using Pinecone's inference API.
    Embeddings are stored in Pinecone when memories are saved, not locally.
    """
    if not texts:
        return []
    
    # Filter out empty texts and prepare for batch embedding
    texts_to_embed = []
    indices_to_embed = []
    results = [None] * len(texts)
    
    for i, text in enumerate(texts):
        if not text or not text.strip():
            results[i] = [0.0] * EMBEDDING_DIMENSION
            continue
        
        texts_to_embed.append(text.strip())
        indices_to_embed.append(i)
    
    if texts_to_embed:
        pc = _get_pinecone_client()
        response = pc.inference.embed(
            model=EMBEDDING_MODEL,
            inputs=texts_to_embed,
            parameters={"input_type": "passage"}
        )
        
        for idx, emb_data in zip(indices_to_embed, response.data):
            embedding_list = emb_data.values
            results[idx] = embedding_list
    
    return results


def get_query_embedding(text: str) -> List[float]:
    """
    Generate query embedding using Pinecone's inference API.
    Used for searching memories in Pinecone.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION
    
    text = text.strip()
    
    pc = _get_pinecone_client()
    response = pc.inference.embed(
        model=EMBEDDING_MODEL,
        inputs=[text],
        parameters={"input_type": "query"}
    )
    embedding_list = response.data[0].values
    
    return embedding_list


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))

"""
Embedding Client

Handles text embedding generation for RAG using SentenceTransformers.
Supports batch embedding for efficient indexing of guideline documents.
"""

import os
from typing import List, Optional
from functools import lru_cache

# Prevent PyTorch/tokenizers thread deadlocks on Windows
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


class EmbeddingClient:
    """
    Client for generating text embeddings.

    Uses SentenceTransformers for local embedding generation.
    Default model: all-MiniLM-L6-v2 (fast, good quality for semantic search)
    Alternative: text-embedding-3-large via OpenAI API
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.

        Args:
            model_name: SentenceTransformer model name or path
        """
        import torch
        torch.set_num_threads(1)

        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.embedding_dim


# Singleton instance
_client: Optional[EmbeddingClient] = None


def get_embedding_client(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingClient:
    """
    Get or create the embedding client singleton.
    
    Args:
        model_name: Model to use (only used on first call)
        
    Returns:
        EmbeddingClient instance
    """
    global _client
    if _client is None:
        _client = EmbeddingClient(model_name)
    return _client

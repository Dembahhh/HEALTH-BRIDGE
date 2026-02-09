"""
Embedding Client

Handles text embedding generation for RAG using FastEmbed.
Supports batch embedding for efficient indexing of guideline documents.
"""

from typing import List, Optional, Generator
import numpy as np
from fastembed import TextEmbedding


class EmbeddingClient:
    """
    Client for generating text embeddings using FastEmbed.

    Uses light-weight ONNX-based models (no PyTorch required).
    Default model: BAAI/bge-small-en-v1.5 (fast, high performance)
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        """
        Initialize the embedding model.

        Args:
            model_name: FastEmbed model name
        """
        self.model = TextEmbedding(model_name=model_name)
        self.model_name = model_name
        # FastEmbed doesn't expose dimension directly, but BGE-small is 384
        # We can infer it from a dummy embedding if needed, or hardcode known models
        self.embedding_dim = 384

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        # embed returns a generator of numpy arrays
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (handled internally by FastEmbed)
            
        Returns:
            List of embedding vectors
        """
        embeddings = list(self.model.embed(texts, batch_size=batch_size))
        return [e.tolist() for e in embeddings]

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.embedding_dim


# Singleton instance
_client: Optional[EmbeddingClient] = None


def get_embedding_client(model_name: str = "BAAI/bge-small-en-v1.5") -> EmbeddingClient:
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

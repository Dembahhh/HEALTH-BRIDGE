"""
Vector Retriever

Handles vector search over guideline documents using ChromaDB.
Implements the RAG retrieval layer as specified:
- Vector search with metadata filters (condition, topic)
- Returns top-k relevant chunks
- Supports pre-filtering by condition/topic
"""

from typing import List, Dict, Any, Optional
import os

from app.config.settings import settings
from app.core.rag.embeddings import get_embedding_client
from app.core.rag.chunker import Chunk


class VectorRetriever:
    """
    Retrieves relevant chunks from the vector store using ChromaDB.
    
    As per spec:
    - Uses vector search over guideline corpus
    - Supports metadata filters (e.g., topic="activity", condition="hypertension")
    - Returns top-k relevant chunks
    """

    def __init__(
        self,
        collection_name: str = "guidelines",
        persist_directory: Optional[str] = None,
    ):
        """
        Initialize the retriever with ChromaDB.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory for persistent storage (ignored in HTTP mode)
        """
        from app.core.chroma_client import get_chroma_client

        self.client = get_chroma_client()

        self.collection_name = collection_name

        # We provide our own embeddings, so give ChromaDB a no-op
        # function to prevent it from loading its default model (which
        # hangs on Windows due to onnxruntime/PyTorch conflicts).
        from chromadb.utils.embedding_functions import EmbeddingFunction

        class _NoOpEmbedding(EmbeddingFunction):
            def __init__(self):
                pass  # Required by newer ChromaDB

            def name(self) -> str:
                return "noop_embedding"

            def __call__(self, input):
                return [[0.0] * 384 for _ in input]

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Health guideline documents for NCD prevention",
                "hnsw:space": "cosine",  # Use cosine similarity
            },
            embedding_function=_NoOpEmbedding(),
        )

        self.embedding_client = get_embedding_client()

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
        """
        # Generate embeddings
        embeddings = self.embedding_client.embed_batch(documents)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def add_chunks(self, chunks: List[Chunk]) -> None:
        """
        Add Chunk objects to the vector store.
        
        Args:
            chunks: List of Chunk objects from the chunker
        """
        if not chunks:
            return
            
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        
        self.add_documents(documents, metadatas, ids)

    def search(
        self,
        query: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            where: Optional metadata filters (ChromaDB where clause)
            where_document: Optional document content filters
            
        Returns:
            List of matching documents with metadata and distances
        """
        query_embedding = self.embedding_client.embed(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        
        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                result = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": distance,
                    "relevance_score": max(0.0, 1.0 - distance),  # Clamp to non-negative
                }
                formatted.append(result)
        
        return formatted

    def search_guidelines(
        self,
        query: str,
        condition: Optional[str] = None,
        topic: Optional[str] = None,
        source: Optional[str] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search guidelines with optional filters.
        
        As per spec, retrieval uses metadata filters to reduce search space.
        
        Args:
            query: Search query
            condition: Filter by condition (hypertension, diabetes, general_ncd)
            topic: Filter by topic (diet, activity, red_flags, sdoh)
            source: Filter by source (WHO, MoH)
            k: Number of results
            
        Returns:
            List of relevant guideline chunks
        """
        # Build filter list for ChromaDB
        filters = []
        if condition:
            filters.append({"condition": condition})
        if topic:
            filters.append({"topic": topic})
        if source:
            filters.append({"source": source})

        # ChromaDB requires $and wrapper for multiple filters
        if len(filters) > 1:
            where_clause = {"$and": filters}
        elif len(filters) == 1:
            where_clause = filters[0]
        else:
            where_clause = None

        return self.search(query, k=k, where=where_clause)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
        }

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self.client.delete_collection(self.collection_name)

    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        # Get all IDs and delete them
        all_data = self.collection.get()
        if all_data["ids"]:
            self.collection.delete(ids=all_data["ids"])


# Singleton instance
_retriever: Optional[VectorRetriever] = None


def get_retriever(collection_name: str = "guidelines") -> VectorRetriever:
    """
    Get or create the retriever singleton.
    
    Args:
        collection_name: Collection name (only used on first call)
        
    Returns:
        VectorRetriever instance
    """
    global _retriever
    if _retriever is None:
        _retriever = VectorRetriever(collection_name)
    return _retriever

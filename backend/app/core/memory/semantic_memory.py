import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from datetime import datetime
import os

# Use a persistent path for ChromaDB
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_memory")

class SemanticMemory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        from app.core.rag.embeddings import get_embedding_client
        
        # Wrapper to make our EmbeddingClient compatible with Chroma
        class ChromaEmbeddingWrapper(embedding_functions.EmbeddingFunction):
            def __call__(self, input: List[str]) -> List[List[float]]:
                client = get_embedding_client()
                return client.embed_batch(input)

        self.embedding_fn = ChromaEmbeddingWrapper()

        self.collection = self.client.get_or_create_collection(
            name="user_memories",
            embedding_function=self.embedding_fn
        )

    def store_memory(self, user_id: str, text: str, metadata: Dict) -> str:
        """Stores a memory snippet with deduplication.

        Checks for existing memories with the same user_id and type
        that are semantically similar (distance < 0.15). If a near-duplicate
        exists, the old one is replaced with the new text.
        """
        import uuid

        # Enforce user_id in metadata
        metadata["user_id"] = user_id
        metadata["timestamp"] = metadata.get("timestamp", datetime.now().isoformat())
        mem_type = metadata.get("type", "unknown")

        # Deduplication: check for near-identical memories of the same type
        try:
            existing = self.collection.query(
                query_texts=[text],
                n_results=1,
                where={"$and": [{"user_id": user_id}, {"type": mem_type}]}
            )
            if (existing["documents"]
                    and existing["documents"][0]
                    and existing["distances"]
                    and existing["distances"][0][0] < 0.15):
                # Near-duplicate found — replace it
                old_id = existing["ids"][0][0]
                self.collection.delete(ids=[old_id])
        except Exception:
            pass  # If dedup check fails, proceed with normal insert

        memory_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[memory_id]
        )
        return memory_id

    def recall_memories(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        """Retrieves relevant memories for a specific user."""
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where={"user_id": user_id} # Filter by user is CRITICAL
        )
        
        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return memories

    def get_recent_memories(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Gets the most recently added memories (naive implementation via peek/get)."""
        # Chroma's 'get' doesn't strictly sort by time unless we query by metadata.
        # For now, we'll just fetch by user_id.
        results = self.collection.get(
            where={"user_id": user_id},
            limit=limit
        )
        # Convert to list of dicts
        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][i]
                })
        return memories

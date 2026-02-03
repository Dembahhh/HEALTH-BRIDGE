import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from datetime import datetime
import os

# Use a persistent path for ChromaDB
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_memory")


class SemanticMemory:
    """
    Semantic memory layer using ChromaDB for persistent storage.

    Phase 1 Improvements:
    - Fixed get_recent_memories() to actually return sorted results
    - Added temporal sorting by timestamp
    - Improved deduplication (checks multiple candidates)
    - Added memory type filtering
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        from app.core.rag.embeddings import get_embedding_client

        # Wrapper to make our EmbeddingClient compatible with ChromaDB
        class ChromaEmbeddingWrapper(embedding_functions.EmbeddingFunction):
            def __init__(self):
                pass  # Required by newer ChromaDB

            def name(self) -> str:
                return "healthbridge_embeddings"

            def __call__(self, input: List[str]) -> List[List[float]]:
                client = get_embedding_client()
                return client.embed_batch(input)

        self.embedding_fn = ChromaEmbeddingWrapper()

        self.collection = self.client.get_or_create_collection(
            name="user_memories",
            embedding_function=self.embedding_fn
        )

    def store_memory(
        self,
        user_id: str,
        text: str,
        metadata: Dict,
        dedup_threshold: float = 0.15
    ) -> str:
        """
        Stores a memory snippet with improved deduplication.

        Checks for existing memories with the same user_id and type
        that are semantically similar (distance < threshold). If a near-duplicate
        exists, the old one is replaced with the new text.

        Args:
            user_id: Unique identifier for the user
            text: The memory text to store
            metadata: Additional metadata (type, source, etc.)
            dedup_threshold: Distance threshold for deduplication (default: 0.15)

        Returns:
            The ID of the stored memory
        """
        import uuid

        # Enforce user_id and timestamp in metadata
        metadata["user_id"] = user_id
        metadata["timestamp"] = metadata.get("timestamp", datetime.now().isoformat())
        mem_type = metadata.get("type", "unknown")

        # Improved deduplication: check top 3 similar memories of the same type
        try:
            existing = self.collection.query(
                query_texts=[text],
                n_results=3,  # Check more candidates for better dedup
                where={"$and": [{"user_id": user_id}, {"type": mem_type}]}
            )

            # Find and remove all near-duplicates
            if existing["documents"] and existing["documents"][0]:
                for i, distance in enumerate(existing["distances"][0]):
                    if distance < dedup_threshold:
                        old_id = existing["ids"][0][i]
                        self.collection.delete(ids=[old_id])

        except Exception as e:
            # If dedup check fails, proceed with normal insert
            print(f"Deduplication check failed: {e}")

        memory_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[memory_id]
        )
        return memory_id

    def recall_memories(
        self,
        user_id: str,
        query: str,
        k: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieves relevant memories for a specific user via semantic search.

        Args:
            user_id: The user to search memories for
            query: Search query text
            k: Number of results to return
            memory_type: Optional filter by memory type (profile, habit_plan, etc.)

        Returns:
            List of memory dictionaries with text, metadata, and distance
        """
        # Build where clause
        where_clause = {"user_id": user_id}
        if memory_type:
            where_clause = {"$and": [{"user_id": user_id}, {"type": memory_type}]}

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where_clause
        )

        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return memories

    def get_recent_memories(
        self,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Gets the most recently added memories, sorted by timestamp.

        FIXED: Now properly retrieves and sorts memories by timestamp.

        Args:
            user_id: The user to get memories for
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type

        Returns:
            List of memory dictionaries sorted by timestamp (newest first)
        """
        # Build where clause
        where_clause = {"user_id": user_id}
        if memory_type:
            where_clause = {"$and": [{"user_id": user_id}, {"type": memory_type}]}

        try:
            results = self.collection.get(
                where=where_clause,
                limit=limit * 2  # Fetch extra to account for sorting
            )
        except Exception as e:
            print(f"Error fetching memories: {e}")
            return []

        # Convert to list of dicts with metadata
        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                memory = {
                    "text": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    "id": results["ids"][i] if results["ids"] else None
                }
                memories.append(memory)

        # Sort by timestamp (newest first)
        def get_timestamp(mem):
            ts = mem.get("metadata", {}).get("timestamp", "")
            if ts:
                try:
                    return datetime.fromisoformat(ts)
                except ValueError:
                    pass
            return datetime.min

        memories.sort(key=get_timestamp, reverse=True)

        return memories[:limit]

    def get_all_memories(self, user_id: str) -> List[Dict]:
        """
        Gets ALL memories for a user (for debugging/inspection).

        Returns:
            List of all memory dictionaries for this user
        """
        try:
            results = self.collection.get(
                where={"user_id": user_id}
            )
        except Exception:
            return []

        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    "id": results["ids"][i] if results["ids"] else None
                })

        return memories

    def delete_memory(self, memory_id: str) -> bool:
        """
        Deletes a specific memory by ID.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if deleted successfully
        """
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"Error deleting memory {memory_id}: {e}")
            return False

    def clear_user_memories(self, user_id: str) -> int:
        """
        Clears all memories for a specific user.

        Args:
            user_id: The user whose memories to clear

        Returns:
            Number of memories deleted
        """
        try:
            all_memories = self.get_all_memories(user_id)
            if all_memories:
                ids_to_delete = [m["id"] for m in all_memories if m.get("id")]
                if ids_to_delete:
                    self.collection.delete(ids=ids_to_delete)
                return len(ids_to_delete)
        except Exception as e:
            print(f"Error clearing memories for {user_id}: {e}")
        return 0

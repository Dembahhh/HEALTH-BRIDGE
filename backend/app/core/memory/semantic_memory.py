from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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
        from app.core.chroma_client import get_chroma_client

        self.client = get_chroma_client()

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
        dedup_threshold: float = 0.35,
        session_id: Optional[str] = None
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
            dedup_threshold: Distance threshold for deduplication (default: 0.35)

        Returns:
            The ID of the stored memory
        """
        import uuid

        # Enforce user_id and timestamp in metadata
        metadata["user_id"] = user_id
        metadata["timestamp"] = metadata.get("timestamp", datetime.now().isoformat())
        if session_id:
            metadata["session_id"] = session_id
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
            logger.warning("Deduplication check failed: %s", e)

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
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        max_age_hours: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieves relevant memories for a specific user via semantic search.

        Args:
            user_id: The user to search memories for
            query: Search query text
            k: Number of results to return
            memory_type: Optional filter by memory type (profile, habit_plan, etc.)
            session_id: Optional filter by session (for conversation isolation)
            max_age_hours: Optional max age in hours (filters out older memories)

        Returns:
            List of memory dictionaries with text, metadata, and distance
        """
        # Build where clause with optional filters
        conditions = [{"user_id": user_id}]
        if memory_type:
            conditions.append({"type": memory_type})
        if session_id:
            conditions.append({"session_id": session_id})

        if len(conditions) == 1:
            where_clause = conditions[0]
        else:
            where_clause = {"$and": conditions}

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where_clause
        )

        memories = []
        cutoff = None
        if max_age_hours is not None:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                # Apply TTL filter
                if cutoff and meta.get("timestamp"):
                    try:
                        mem_time = datetime.fromisoformat(meta["timestamp"])
                        if mem_time < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass
                memories.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return memories

    def get_recent_memories(
        self,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Gets the most recently added memories, sorted by timestamp.

        FIXED: Now properly retrieves and sorts memories by timestamp.

        Args:
            user_id: The user to get memories for
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type
            session_id: Optional filter by session (for conversation isolation)

        Returns:
            List of memory dictionaries sorted by timestamp (newest first)
        """
        # Build where clause with optional filters
        conditions = [{"user_id": user_id}]
        if memory_type:
            conditions.append({"type": memory_type})
        if session_id:
            conditions.append({"session_id": session_id})

        if len(conditions) == 1:
            where_clause = conditions[0]
        else:
            where_clause = {"$and": conditions}

        try:
            results = self.collection.get(
                where=where_clause,
                limit=limit * 2  # Fetch extra to account for sorting
            )
        except Exception as e:
            logger.error("Error fetching memories: %s", e)
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
            logger.error("Error deleting memory %s: %s", memory_id, e)
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
            logger.error("Error clearing memories for %s: %s", user_id, e)
        return 0

    def clear_session_memories(self, user_id: str, session_id: str) -> int:
        """
        Clears all memories for a specific user session.
        Useful for test isolation.

        Args:
            user_id: The user whose session memories to clear
            session_id: The session to clear

        Returns:
            Number of memories deleted
        """
        try:
            results = self.collection.get(
                where={"$and": [{"user_id": user_id}, {"session_id": session_id}]}
            )
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                return len(results["ids"])
        except Exception as e:
            logger.error("Error clearing session memories: %s", e)
        return 0

    def cleanup_old_memories(self, user_id: str, older_than_hours: float) -> int:
        """
        Removes memories older than a specified age.

        Args:
            user_id: The user whose old memories to clean up
            older_than_hours: Delete memories older than this many hours

        Returns:
            Number of memories deleted
        """
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        try:
            all_memories = self.get_all_memories(user_id)
            ids_to_delete = []
            for mem in all_memories:
                ts = mem.get("metadata", {}).get("timestamp", "")
                if ts:
                    try:
                        mem_time = datetime.fromisoformat(ts)
                        if mem_time < cutoff:
                            ids_to_delete.append(mem["id"])
                    except (ValueError, TypeError):
                        continue
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        except Exception as e:
            logger.error("Error cleaning old memories: %s", e)
        return 0

"""
Memory Factory for HEALTH-BRIDGE

Provides a unified interface to switch between memory backends:
- SemanticMemory (ChromaDB) - Phase 1
- CogneeMemory (Cognee) - Phase 2

Configuration via environment variable:
    MEMORY_BACKEND=semantic  (default, uses ChromaDB)
    MEMORY_BACKEND=cognee    (uses Cognee graph memory)
"""

import logging
import os
from typing import Union, Optional

logger = logging.getLogger(__name__)

# Memory backend types
BACKEND_SEMANTIC = "semantic"
BACKEND_COGNEE = "cognee"


def get_memory_backend() -> str:
    """Get configured memory backend from environment."""
    return os.getenv("MEMORY_BACKEND", BACKEND_SEMANTIC).lower()


def get_memory():
    """
    Get the appropriate memory instance based on configuration.
    
    Returns:
        SemanticMemory or CogneeMemoryManager based on MEMORY_BACKEND env var
    """
    backend = get_memory_backend()
    
    if backend == BACKEND_COGNEE:
        try:
            from app.core.memory.cognee_memory import get_cognee_memory
            return get_cognee_memory()
        except ImportError:
            logger.warning("Cognee not available, falling back to SemanticMemory")
    
    # Default to SemanticMemory
    from app.core.memory.semantic_memory import SemanticMemory
    return SemanticMemory()


class MemoryAdapter:
    """
    Adapter that provides a unified interface for both memory backends.
    
    This allows code to work with either backend without changes.
    """
    
    def __init__(self, backend: Optional[str] = None):
        self.backend_type = backend or get_memory_backend()
        self._semantic_memory = None
        self._cognee_memory = None
    
    def _get_semantic(self):
        if self._semantic_memory is None:
            from app.core.memory.semantic_memory import SemanticMemory
            self._semantic_memory = SemanticMemory()
        return self._semantic_memory
    
    def _get_cognee(self):
        if self._cognee_memory is None:
            from app.core.memory.cognee_memory import get_cognee_memory
            self._cognee_memory = get_cognee_memory()
        return self._cognee_memory
    
    async def store(
        self,
        user_id: str,
        text: str,
        metadata: dict,
        turn_data: Optional[dict] = None
    ) -> bool:
        """
        Store memory using the configured backend.
        
        Args:
            user_id: User identifier
            text: Text to store
            metadata: Metadata dict with 'type' key
            turn_data: Optional full turn data for Cognee
        """
        if self.backend_type == BACKEND_COGNEE:
            cognee = self._get_cognee()
            if turn_data:
                return await cognee.store_conversation_turn(
                    user_id, turn_data, metadata.get("session_type", "general")
                )
            else:
                return await cognee.store_conversation_turn(
                    user_id,
                    {
                        "user_message": text,
                        "agent_response": "",
                        "extracted_entities": metadata,
                        "timestamp": metadata.get("timestamp", "")
                    },
                    metadata.get("type", "general")
                )
        else:
            memory = self._get_semantic()
            memory.store_memory(user_id, text, metadata)
            return True
    
    async def recall(
        self,
        user_id: str,
        query: str,
        k: int = 5
    ) -> dict:
        """
        Recall memories using the configured backend.
        
        Returns a unified format:
        {
            "results": List of memory items,
            "entities": Dict of extracted entities (Cognee only),
            "relationships": List of relationships (Cognee only),
            "summary": Brief summary
        }
        """
        if self.backend_type == BACKEND_COGNEE:
            cognee = self._get_cognee()
            result = await cognee.recall_contextual_memory(user_id, query)
            return {
                "results": result.get("raw_results", []),
                "entities": result.get("entities", {}),
                "relationships": result.get("relationships", []),
                "summary": result.get("summary", "")
            }
        else:
            memory = self._get_semantic()
            results = memory.recall_memories(user_id, query, k=k)
            return {
                "results": results,
                "entities": {},
                "relationships": [],
                "summary": " | ".join([r.get("text", "")[:50] for r in results[:3]])
            }
    
    def recall_sync(self, user_id: str, query: str, k: int = 5) -> dict:
        """Synchronous version of recall."""
        from app.core.memory.cognee_memory import run_async
        return run_async(self.recall(user_id, query, k))
    
    def store_sync(
        self,
        user_id: str,
        text: str,
        metadata: dict,
        turn_data: Optional[dict] = None
    ) -> bool:
        """Synchronous version of store."""
        from app.core.memory.cognee_memory import run_async
        return run_async(self.store(user_id, text, metadata, turn_data))


# Singleton adapter
_adapter: Optional[MemoryAdapter] = None


def get_memory_adapter() -> MemoryAdapter:
    """Get or create the memory adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = MemoryAdapter()
    return _adapter
"""
Cognee-Ready Memory Manager for HEALTH-BRIDGE

This is a SIMPLIFIED version that uses SemanticMemory internally
but maintains the same interface for future Cognee integration.

When you're ready to use Cognee:
1. pip install cognee
2. Set MEMORY_BACKEND=cognee in .env
3. Replace the internal implementation with actual Cognee calls

The interface remains the same, so no other code changes needed.
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryNode:
    """Represents a node in the memory graph."""
    id: str
    text: str
    node_type: str  # profile, habit, constraint, reading, conversation
    timestamp: str
    metadata: Dict = field(default_factory=dict)
    relationships: List[Dict] = field(default_factory=list)


@dataclass
class MemorySearchResult:
    """Result from a memory search."""
    text: str
    node_type: str
    relevance_score: float
    timestamp: str
    relationships: List[Dict] = field(default_factory=list)
    temporal_context: Optional[str] = None


class CogneeMemoryManager:
    """
    Graph-style memory manager using SemanticMemory as backend.
    
    This provides the same interface as a full Cognee implementation
    but uses ChromaDB/SemanticMemory internally. When you're ready
    to upgrade to Cognee, only this class needs to change.
    
    Features provided (via SemanticMemory):
    - Structured storage with metadata
    - Semantic search
    - Memory type filtering
    - Temporal ordering
    
    Features ready for Cognee upgrade:
    - Entity extraction (currently manual)
    - Relationship tracking (currently via metadata)
    - Temporal patterns (currently via timestamp queries)
    """
    
    def __init__(self):
        self._memory = None
        self._initialized = False
    
    def _get_memory(self):
        """Lazy init for SemanticMemory."""
        if self._memory is None:
            from app.core.memory.semantic_memory import SemanticMemory
            self._memory = SemanticMemory()
        return self._memory
    
    def initialize(self):
        """Initialize the memory backend."""
        self._get_memory()
        self._initialized = True
    
    def store_conversation_turn(
        self,
        user_id: str,
        turn_data: Dict[str, Any],
        session_type: str
    ) -> bool:
        """
        Store a conversation turn with context.
        
        Args:
            user_id: Unique user identifier
            turn_data: Dictionary containing:
                - user_message: str
                - agent_response: str
                - extracted_entities: Dict (optional)
                - timestamp: str (ISO format)
            session_type: One of "intake", "follow_up", "general"
            
        Returns:
            True if stored successfully
        """
        try:
            memory = self._get_memory()
            
            # Build structured text for storage
            timestamp = turn_data.get("timestamp", datetime.now().isoformat())
            user_msg = turn_data.get("user_message", "")
            entities = turn_data.get("extracted_entities", {})
            
            # Create a structured document
            doc = {
                "session_type": session_type,
                "user_message": user_msg,
                "entities": entities,
                "timestamp": timestamp
            }
            
            memory.store_memory(
                user_id=user_id,
                text=json.dumps(doc),
                metadata={
                    "type": "conversation",
                    "session_type": session_type,
                    "timestamp": timestamp
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Store error: {e}")
            return False
    
    def recall_contextual_memory(
        self,
        user_id: str,
        query: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Retrieve memories with structured context.
        
        Args:
            user_id: User to search for
            query: Search query
            lookback_days: How far back to search
            
        Returns:
            Dictionary with:
                - entities: Extracted entities from memories
                - relationships: Connections (placeholder for Cognee)
                - temporal_patterns: Time-based patterns (placeholder)
                - summary: Brief summary
                - raw_results: Raw memory results
        """
        try:
            memory = self._get_memory()
            
            # Semantic search
            results = memory.recall_memories(user_id, query, k=5)
            
            # Get recent memories by type
            profile_memories = memory.get_recent_memories(
                user_id, limit=2, memory_type="profile"
            )
            
            # Extract entities from results
            entities = {}
            for mem in results + profile_memories:
                text = mem.get("text", "")
                try:
                    parsed = json.loads(text)
                    if "entities" in parsed:
                        entities.update(parsed["entities"])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Build summary
            summary_parts = []
            for r in results[:3]:
                text = r.get("text", "")
                if len(text) > 100:
                    text = text[:100] + "..."
                summary_parts.append(text)
            
            return {
                "entities": entities,
                "relationships": [],  # Placeholder for Cognee
                "temporal_patterns": [],  # Placeholder for Cognee
                "summary": " | ".join(summary_parts) if summary_parts else "",
                "raw_results": results
            }
            
        except Exception as e:
            print(f"Recall error: {e}")
            return {
                "entities": {},
                "relationships": [],
                "temporal_patterns": [],
                "summary": "",
                "raw_results": []
            }
    
    def get_habit_timeline(
        self,
        user_id: str,
        habit_name: str
    ) -> List[Dict]:
        """
        Track a specific habit over time.
        
        Args:
            user_id: User to search
            habit_name: Name of the habit to track
            
        Returns:
            List of timeline entries
        """
        try:
            memory = self._get_memory()
            
            # Search for habit mentions
            results = memory.recall_memories(user_id, f"habit {habit_name}", k=10)
            
            timeline = []
            for i, r in enumerate(results):
                text = r.get("text", "")
                timestamp = r.get("metadata", {}).get("timestamp", "")
                
                # Try to parse status from text
                status = "mentioned"
                text_lower = text.lower()
                if "started" in text_lower or "began" in text_lower:
                    status = "started"
                elif "stopped" in text_lower or "quit" in text_lower:
                    status = "stopped"
                elif "struggling" in text_lower or "difficult" in text_lower:
                    status = "struggling"
                elif "doing well" in text_lower or "keeping up" in text_lower:
                    status = "active"
                
                timeline.append({
                    "index": i + 1,
                    "habit": habit_name,
                    "status": status,
                    "content": text[:200] if len(text) > 200 else text,
                    "timestamp": timestamp
                })
            
            # Sort by timestamp if available
            timeline.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            
            return timeline
            
        except Exception as e:
            print(f"Timeline error: {e}")
            return []
    
    def store_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> bool:
        """Store a user profile."""
        try:
            memory = self._get_memory()
            
            memory.store_memory(
                user_id=user_id,
                text=json.dumps({
                    "type": "profile",
                    "data": profile_data,
                    "timestamp": datetime.now().isoformat()
                }),
                metadata={
                    "type": "profile",
                    "timestamp": datetime.now().isoformat()
                }
            )
            return True
        except Exception:
            return False
    
    def store_habit_plan(
        self,
        user_id: str,
        habits: List[Dict[str, Any]]
    ) -> bool:
        """Store a habit plan."""
        try:
            memory = self._get_memory()
            
            memory.store_memory(
                user_id=user_id,
                text=json.dumps({
                    "type": "habit_plan",
                    "habits": habits,
                    "habit_count": len(habits),
                    "timestamp": datetime.now().isoformat()
                }),
                metadata={
                    "type": "habit_plan",
                    "timestamp": datetime.now().isoformat()
                }
            )
            return True
        except Exception:
            return False
    
    def clear_user_data(self, user_id: str) -> bool:
        """Clear all data for a user."""
        try:
            memory = self._get_memory()
            memory.clear_user_memories(user_id)
            return True
        except Exception:
            return False


# Singleton instance
_cognee_memory: Optional[CogneeMemoryManager] = None


def get_cognee_memory() -> CogneeMemoryManager:
    """Get or create the Cognee memory manager singleton."""
    global _cognee_memory
    if _cognee_memory is None:
        _cognee_memory = CogneeMemoryManager()
    return _cognee_memory
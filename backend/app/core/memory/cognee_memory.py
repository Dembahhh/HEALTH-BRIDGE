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
import logging
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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

            # Enrich with regex-based entity extraction
            extracted = self._extract_entities(user_msg)
            if extracted:
                entities["auto_extracted"] = extracted

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
            logger.error("Failed to store conversation turn: %s", e)
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
            
            # Extract entities from results (JSON-stored + regex-based)
            entities: Dict[str, Any] = {}
            all_extracted: Dict[str, List[str]] = {}
            all_memories = results + profile_memories

            for mem in all_memories:
                text = mem.get("text", "")
                # Try JSON-stored entities first
                try:
                    parsed = json.loads(text)
                    if "entities" in parsed:
                        entities.update(parsed["entities"])
                except (json.JSONDecodeError, TypeError):
                    pass
                # Regex-based entity extraction on raw text
                extracted = self._extract_entities(text)
                for cat, items in extracted.items():
                    existing = all_extracted.get(cat, [])
                    for item in items:
                        if item not in existing:
                            existing.append(item)
                    all_extracted[cat] = existing

            # Merge regex-extracted entities into result
            if all_extracted:
                entities["extracted"] = all_extracted

            # Build relationships from extracted entities
            relationships = self._build_relationships(all_extracted)

            # Detect temporal patterns from memory timestamps
            temporal_patterns = self._detect_temporal_patterns(all_memories)

            # Build summary
            summary_parts = []
            for r in results[:3]:
                text = r.get("text", "")
                if len(text) > 100:
                    text = text[:100] + "..."
                summary_parts.append(text)

            return {
                "entities": entities,
                "relationships": relationships,
                "temporal_patterns": temporal_patterns,
                "summary": " | ".join(summary_parts) if summary_parts else "",
                "raw_results": results
            }
            
        except Exception as e:
            logger.error("Failed to recall contextual memory: %s", e)
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
                
                status = self._detect_habit_status(text)
                
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
            logger.error("Failed to get habit timeline: %s", e)
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

    # -----------------------------------------------------------------
    # Phase 11: Entity extraction, relationship, and temporal helpers
    # -----------------------------------------------------------------

    # Regex patterns for health entity extraction
    _ENTITY_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "condition": [
            (r"\bhypertension\b", "hypertension"),
            (r"\bhigh\s*blood\s*pressure\b", "hypertension"),
            (r"\bdiabete\w*\b", "diabetes"),
            (r"\bheart\s*(disease|problem|attack|condition|failure)\b", "heart disease"),
            (r"\bcholesterol\b", "high cholesterol"),
            (r"\bstroke\b", "stroke"),
            (r"\bkidney\s*(disease|problem|failure)\b", "kidney disease"),
            (r"\basthma\b", "asthma"),
            (r"\bcopd\b", "COPD"),
            (r"\bobes\w+\b", "obesity"),
        ],
        "demographic": [
            (r"\b(\d{1,3})\s*(?:years?\s*old|y/?o)\b", "age"),
            (r"\b(male|female|man|woman)\b", "sex"),
        ],
        "lifestyle": [
            (r"\bsmok\w+\b", "smoking"),
            (r"\balcohol\b|\bdrink\w*\b", "alcohol"),
            (r"\bexercis\w+\b|\bwalk\w*\b|\bgym\b|\bsport\w*\b", "exercise"),
            (r"\bdiet\w*\b|\bvegetarian\b|\bvegan\b", "diet"),
        ],
        "family": [
            (r"\b(father|mother|dad|mom|parent|brother|sister|grandpa|grandma|uncle|aunt)\b", "family_member"),
        ],
    }

    _HABIT_STATUS_KEYWORDS: Dict[str, List[str]] = {
        "started": ["started", "began", "beginning", "new habit", "just started"],
        "active": ["doing well", "keeping up", "on track", "going great", "improved"],
        "struggling": ["struggling", "difficult", "hard", "failing", "can't keep"],
        "stopped": ["stopped", "quit", "gave up", "abandoned", "no longer"],
        "resumed": ["resumed", "back on", "started again", "picked up again"],
    }

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract health-related entities from text using regex patterns.

        Args:
            text: Raw text to extract entities from.

        Returns:
            Dict mapping entity category to list of matched entity labels.
        """
        entities: Dict[str, List[str]] = {}
        text_lower = text.lower()

        for category, patterns in self._ENTITY_PATTERNS.items():
            found: List[str] = []
            for pattern, label in patterns:
                if re.search(pattern, text_lower):
                    if label not in found:
                        found.append(label)
            if found:
                entities[category] = found

        return entities

    def _detect_habit_status(self, text: str) -> str:
        """Detect the status of a habit from text content.

        Args:
            text: Text describing habit progress.

        Returns:
            One of: "started", "active", "struggling", "stopped",
            "resumed", or "mentioned" as fallback.
        """
        text_lower = text.lower()
        for status, keywords in self._HABIT_STATUS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return status
        return "mentioned"

    def _detect_temporal_patterns(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[str]:
        """Detect temporal patterns from a list of timestamped memories.

        Looks for:
        - Recurring conditions mentioned across sessions
        - Habit adherence trends (improving, declining)
        - Gaps in engagement

        Args:
            memories: List of memory dicts, each with optional ``text``
                and ``metadata.timestamp`` fields.

        Returns:
            List of human-readable pattern descriptions.
        """
        patterns: List[str] = []

        # Collect timestamps
        timestamps: List[datetime] = []
        condition_mentions: Dict[str, int] = {}
        habit_statuses: List[Tuple[str, str]] = []  # (timestamp, status)

        for mem in memories:
            text = mem.get("text", "")
            ts_str = mem.get("metadata", {}).get("timestamp", "")

            # Parse timestamp
            ts = None
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

            # Count condition mentions
            entities = self._extract_entities(text)
            for cond in entities.get("condition", []):
                condition_mentions[cond] = condition_mentions.get(cond, 0) + 1

            # Track habit statuses
            status = self._detect_habit_status(text)
            if status != "mentioned" and ts_str:
                habit_statuses.append((ts_str, status))

        # Pattern: recurring conditions
        for cond, count in condition_mentions.items():
            if count >= 2:
                patterns.append(
                    f"{cond} mentioned {count} times across sessions"
                )

        # Pattern: engagement gaps
        if len(timestamps) >= 2:
            timestamps.sort()
            max_gap = max(
                (timestamps[i + 1] - timestamps[i]).days
                for i in range(len(timestamps) - 1)
            )
            if max_gap > 14:
                patterns.append(
                    f"Engagement gap of {max_gap} days detected"
                )

        # Pattern: habit trend
        if len(habit_statuses) >= 2:
            recent = [s for _, s in sorted(habit_statuses)[-3:]]
            positive = {"active", "started", "resumed"}
            negative = {"struggling", "stopped"}
            if all(s in positive for s in recent):
                patterns.append("Positive habit adherence trend")
            elif all(s in negative for s in recent):
                patterns.append("Declining habit adherence trend")

        return patterns

    def _build_relationships(
        self,
        entities: Dict[str, List[str]],
    ) -> List[str]:
        """Build simple relationship descriptions from extracted entities.

        For example, if both a family member and a condition are found,
        infer a family history relationship.

        Args:
            entities: Output of ``_extract_entities``.

        Returns:
            List of relationship description strings.
        """
        relationships: List[str] = []

        family_members = entities.get("family", [])
        conditions = entities.get("condition", [])
        lifestyle_factors = entities.get("lifestyle", [])

        # Family-condition relationships
        for member in family_members:
            for cond in conditions:
                relationships.append(
                    f"Family history: {member} linked to {cond}"
                )

        # Lifestyle-condition relationships
        for factor in lifestyle_factors:
            for cond in conditions:
                relationships.append(
                    f"Lifestyle factor '{factor}' relevant to {cond}"
                )

        return relationships


# Singleton instance
_cognee_memory: Optional[CogneeMemoryManager] = None


def get_cognee_memory() -> CogneeMemoryManager:
    """Get or create the Cognee memory manager singleton."""
    global _cognee_memory
    if _cognee_memory is None:
        _cognee_memory = CogneeMemoryManager()
    return _cognee_memory
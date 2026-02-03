"""
Conversation State Management for HEALTH-BRIDGE

Tracks conversation context across multiple turns and sessions.
Replaces the simple list that was reset after each crew run.

Phase 3 Implementation:
- Tracks collected fields with confidence levels
- Identifies implied information from context
- Marks ambiguous responses needing clarification
- Detects urgent symptoms
- Maintains history across sessions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import json


class FieldConfidence(Enum):
    """Confidence level for extracted fields."""
    HIGH = "high"           # Explicitly stated: "I am 45 years old"
    MEDIUM = "medium"       # Clearly implied: "mid-40s" -> ~45
    LOW = "low"             # Inferred: "retired" -> likely 60+
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass
class ExtractedField:
    """A field extracted from conversation."""
    name: str
    value: Any
    confidence: FieldConfidence
    source_message: str
    turn_number: int
    clarifying_question: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence.value,
            "turn": self.turn_number
        }


@dataclass 
class ConversationState:
    """
    Tracks conversation state across multiple turns.
    
    Replaces the simple list approach with rich context tracking.
    """
    session_type: str = "general"
    user_id: str = ""
    
    # Message history
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Extracted information
    collected_fields: Dict[str, ExtractedField] = field(default_factory=dict)
    implied_fields: Dict[str, str] = field(default_factory=dict)
    ambiguous_fields: List[str] = field(default_factory=list)
    
    # Tracking
    turn_count: int = 0
    sessions_completed: int = 0
    last_question_field: Optional[str] = None
    urgent_flags: List[str] = field(default_factory=list)
    
    # Timestamps
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_user_message(self, message: str) -> int:
        """Add a user message and increment turn count."""
        self.turn_count += 1
        self.messages.append({
            "role": "user",
            "content": message,
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now().isoformat()
        return self.turn_count
    
    def add_agent_message(self, message: str, question_field: Optional[str] = None):
        """Add an agent message."""
        self.messages.append({
            "role": "agent",
            "content": message,
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat()
        })
        self.last_question_field = question_field
        self.last_activity = datetime.now().isoformat()
    
    def set_field(
        self,
        name: str,
        value: Any,
        confidence: FieldConfidence,
        source_message: str,
        clarifying_question: Optional[str] = None
    ):
        """Set an extracted field value."""
        self.collected_fields[name] = ExtractedField(
            name=name,
            value=value,
            confidence=confidence,
            source_message=source_message,
            turn_number=self.turn_count,
            clarifying_question=clarifying_question
        )
        
        # Remove from ambiguous if present
        if name in self.ambiguous_fields:
            self.ambiguous_fields.remove(name)
    
    def set_implied(self, name: str, value: str, reason: str):
        """Set an implied field with reasoning."""
        self.implied_fields[name] = f"{value} (inferred: {reason})"
    
    def mark_ambiguous(self, name: str, clarifying_question: str):
        """Mark a field as needing clarification."""
        if name not in self.ambiguous_fields:
            self.ambiguous_fields.append(name)
        
        if name in self.collected_fields:
            self.collected_fields[name].clarifying_question = clarifying_question
            self.collected_fields[name].confidence = FieldConfidence.NEEDS_CLARIFICATION
    
    def add_urgent_flag(self, symptom: str):
        """Flag an urgent symptom."""
        if symptom not in self.urgent_flags:
            self.urgent_flags.append(symptom)
    
    def get_user_messages(self) -> List[str]:
        """Get all user messages as strings."""
        return [m["content"] for m in self.messages if m["role"] == "user"]
    
    def get_combined_input(self) -> str:
        """Get all user messages combined."""
        return " ".join(self.get_user_messages())
    
    def get_recent_messages(self, max_turns: int = 5) -> List[str]:
        """Get recent user messages."""
        user_msgs = self.get_user_messages()
        return user_msgs[-max_turns:]
    
    def get_field_value(self, name: str) -> Optional[Any]:
        """Get value of a collected field."""
        if name in self.collected_fields:
            return self.collected_fields[name].value
        return None
    
    def has_field(self, name: str) -> bool:
        """Check if field has been collected."""
        return name in self.collected_fields
    
    def get_detected_fields_dict(self) -> Dict[str, bool]:
        """Get dict of field names to detected status (for compatibility)."""
        all_fields = ["age", "sex", "conditions", "family_history", 
                      "smoking", "alcohol", "diet", "activity", "constraints"]
        return {f: self.has_field(f) for f in all_fields}
    
    def get_fields_needing_clarification(self) -> List[ExtractedField]:
        """Get fields needing clarification."""
        return [
            f for f in self.collected_fields.values()
            if f.confidence == FieldConfidence.NEEDS_CLARIFICATION
        ]
    
    def complete_session(self):
        """Mark session complete."""
        self.sessions_completed += 1
        self.messages.append({
            "role": "system",
            "content": f"[SESSION {self.sessions_completed} COMPLETE]",
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat()
        })
    
    def has_urgent_symptoms(self) -> bool:
        """Check for urgent symptoms."""
        return len(self.urgent_flags) > 0
    
    def count_collected_fields(self) -> int:
        """Count fields with HIGH or MEDIUM confidence."""
        return sum(
            1 for f in self.collected_fields.values()
            if f.confidence in [FieldConfidence.HIGH, FieldConfidence.MEDIUM]
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "session_type": self.session_type,
            "user_id": self.user_id,
            "turn_count": self.turn_count,
            "sessions_completed": self.sessions_completed,
            "collected_fields": {k: v.to_dict() for k, v in self.collected_fields.items()},
            "implied_fields": self.implied_fields,
            "ambiguous_fields": self.ambiguous_fields,
            "urgent_flags": self.urgent_flags,
            "message_count": len(self.messages)
        }
    
    def reset(self):
        """Reset for new session (keeps user_id)."""
        user_id = self.user_id
        session_type = self.session_type
        self.messages = []
        self.collected_fields = {}
        self.implied_fields = {}
        self.ambiguous_fields = []
        self.turn_count = 0
        self.last_question_field = None
        self.urgent_flags = []
        self.started_at = datetime.now().isoformat()
        self.user_id = user_id
        self.session_type = session_type
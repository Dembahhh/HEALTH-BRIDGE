"""
Session Manager for HEALTH-BRIDGE

Orchestrates all Phase 1-4 components into a unified session flow:
- Conversation state tracking (Phase 3)
- LLM-based extraction (Phase 3)
- Pattern detection (Phase 4)
- Intervention generation (Phase 4)
- Memory persistence (Phase 1-2)

This is the main entry point for the chat interface.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import tracked
from app.services.conversation_state import ConversationState, FieldConfidence
from app.services.input_collector import InputCollector

logger = logging.getLogger(__name__)
from app.services.llm_extractor import get_extractor, FullExtractionResult
from app.services.question_generator import get_question_generator
from app.services.pattern_detector import get_pattern_detector, DetectedPattern
from app.services.intervention_engine import get_intervention_engine, Intervention


@dataclass
class SessionResult:
    """Result of processing a user message."""
    # Response to show user
    response: str
    
    # Session state
    ready_for_crew: bool
    session_type: str
    turn_count: int
    
    # Extracted data
    collected_fields: Dict[str, Any]
    implied_fields: Dict[str, str]
    
    # Patterns and interventions (for follow-up sessions)
    patterns: List[Dict] = field(default_factory=list)
    interventions: List[Dict] = field(default_factory=list)
    
    # Flags
    has_urgent_symptoms: bool = False
    urgent_symptoms: List[str] = field(default_factory=list)
    session_complete: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "response": self.response,
            "ready_for_crew": self.ready_for_crew,
            "session_type": self.session_type,
            "turn_count": self.turn_count,
            "collected_fields": self.collected_fields,
            "implied_fields": self.implied_fields,
            "patterns": self.patterns,
            "interventions": self.interventions,
            "has_urgent_symptoms": self.has_urgent_symptoms,
            "urgent_symptoms": self.urgent_symptoms,
            "session_complete": self.session_complete
        }


class SessionManager:
    """
    Manages a complete conversation session.
    
    Coordinates:
    - Input collection and validation
    - Field extraction (LLM or regex)
    - Pattern detection (for follow-ups)
    - Intervention generation
    - Memory storage
    
    Usage:
        manager = SessionManager(user_id="user123", session_type="intake")
        
        # Process each message
        result = manager.process_message("I am 45 years old male")
        print(result.response)
        
        if result.ready_for_crew:
            # Run the CrewAI pipeline
            crew_result = run_crew(result.collected_fields)
            manager.complete_session(crew_result)
    """
    
    def __init__(
        self,
        user_id: str,
        session_type: str = "intake",
        user_habits: List[str] = None,
        use_llm: bool = True
    ):
        """
        Initialize session manager.
        
        Args:
            user_id: Unique user identifier
            session_type: One of "intake", "follow_up", "general"
            user_habits: For follow-up, list of user's existing habits
            use_llm: Whether to use LLM extraction (False for testing)
        """
        self.user_id = user_id
        self.session_type = session_type
        self.user_habits = user_habits or []
        
        # Initialize components
        self.state = ConversationState(
            session_type=session_type,
            user_id=user_id
        )
        self.collector = InputCollector(use_llm=use_llm)
        self.extractor = get_extractor(use_llm=use_llm)
        self.question_gen = get_question_generator()
        self.pattern_detector = get_pattern_detector()
        self.intervention_engine = get_intervention_engine()
        
        # Session tracking
        self.patterns_detected: List[DetectedPattern] = []
        self.interventions_generated: List[Intervention] = []
        self.crew_result = None
        self._welcome_shown = False
    
    def get_welcome_message(self) -> str:
        """Get the initial welcome message for this session."""
        welcome, field = self.question_gen.get_welcome_message(
            self.session_type, 
            self.user_habits
        )
        self.state.last_question_field = field
        self._welcome_shown = True
        return welcome
    
    @tracked(name="process_message", tags=["session"])
    def process_message(self, message: str) -> SessionResult:
        """
        Process a user message and return appropriate response.

        This is the main entry point for each conversation turn.

        Args:
            message: User's message

        Returns:
            SessionResult with response and state information
        """
        # Add message to state
        self.state.add_user_message(message)
        
        # Extract fields from message
        extraction = self.extractor.extract_all(
            message=message,
            context=self.state.get_recent_messages(5),
            last_question_field=self.state.last_question_field
        )
        
        # Process extraction results
        self._process_extraction(extraction, message)
        
        # Check for urgent symptoms
        if self.state.has_urgent_symptoms():
            return self._handle_urgent_symptoms()

        # Assess readiness using existing state (avoids redundant re-extraction)
        assessment = self._assess_readiness()

        if assessment["ready"]:
            return self._prepare_for_crew(assessment)
        else:
            return self._continue_collection(assessment)
    
    def _process_extraction(self, extraction: FullExtractionResult, source_message: str):
        """Process extraction results into conversation state."""
        # Add extracted fields
        for name, result in extraction.fields.items():
            confidence = (
                FieldConfidence.HIGH if result.confidence >= 0.8 else
                FieldConfidence.MEDIUM if result.confidence >= 0.5 else
                FieldConfidence.LOW
            )
            
            if result.needs_clarification:
                confidence = FieldConfidence.NEEDS_CLARIFICATION
                self.state.mark_ambiguous(name, result.clarifying_question or "")
            
            self.state.set_field(
                name=name,
                value=result.value,
                confidence=confidence,
                source_message=source_message,
                clarifying_question=result.clarifying_question
            )
        
        # Add implied fields
        for field_name, value in extraction.implied.items():
            self.state.set_implied(field_name, value, "context")
        
        # Add urgent symptoms
        for symptom in extraction.urgent_symptoms:
            self.state.add_urgent_flag(symptom)
    
    def _assess_readiness(self) -> Dict:
        """Assess readiness using the existing conversation state.

        This avoids the redundant re-extraction that ``self.collector.assess()``
        performs by working directly with fields already stored in ``self.state``.

        Returns:
            Dict with ``ready`` bool and supporting metadata.
        """
        from app.services.input_collector import (
            INTAKE_MIN_FIELDS,
            INTAKE_MAX_TURNS,
            FOLLOW_UP_MIN_QUESTIONS,
            FOLLOW_UP_MAX_TURNS,
            GENERAL_MIN_LENGTH,
        )

        fields_collected = self.state.count_collected_fields()
        turn = self.state.turn_count
        combined = self.state.get_combined_input()

        if self.session_type == "intake":
            has_critical = self.state.has_critical_fields()
            enough = has_critical and fields_collected >= INTAKE_MIN_FIELDS
            safety_valve = turn >= INTAKE_MAX_TURNS

            if enough or safety_valve:
                return {
                    "ready": True,
                    "combined_input": combined,
                    "detected_fields": self.state.get_detected_fields_dict(),
                    "turn": turn,
                    "collected_values": {
                        k: v.value for k, v in self.state.collected_fields.items()
                    },
                    "implied_fields": self.state.implied_fields,
                }
            return {
                "ready": False,
                "detected_fields": self.state.get_detected_fields_dict(),
                "turn": turn,
            }

        if self.session_type == "follow_up":
            enough = fields_collected >= FOLLOW_UP_MIN_QUESTIONS
            safety_valve = turn >= FOLLOW_UP_MAX_TURNS
            long_enough = len(combined.split()) >= 20

            if enough or safety_valve or long_enough:
                return {
                    "ready": True,
                    "combined_input": combined,
                    "detected_fields": self.state.get_detected_fields_dict(),
                    "turn": turn,
                }
            return {
                "ready": False,
                "detected_fields": self.state.get_detected_fields_dict(),
                "turn": turn,
            }

        # General session
        has_question = bool(
            re.search(r"\?|how|what|why|when|can|should|is it", combined, re.IGNORECASE)
        )
        has_topic = bool(
            re.search(
                r"\b(diet|exercise|blood\s*pressure|diabetes|hypertension|heart|weight|habit|health|symptom)\w*\b",
                combined,
                re.IGNORECASE,
            )
        )
        long_enough = len(combined.strip()) >= GENERAL_MIN_LENGTH

        if (has_question or has_topic or long_enough) or turn >= 2:
            return {
                "ready": True,
                "combined_input": combined,
                "detected_fields": {"has_question": has_question, "has_topic": has_topic},
                "turn": turn,
            }
        return {
            "ready": False,
            "detected_fields": {},
            "turn": turn,
        }

    def _handle_urgent_symptoms(self) -> SessionResult:
        """Handle detection of urgent symptoms."""
        symptoms = self.state.urgent_flags
        symptoms_str = ", ".join(symptoms)
        
        response = f"""⚠️ **IMPORTANT**: You mentioned {symptoms_str}. These could be signs of a serious condition.

**Please seek immediate medical attention:**
- Go to your nearest emergency room, OR
- Call emergency services (911 / your local emergency number)

Do not wait to see if symptoms improve. Your health is the priority.

Once you've received medical care, we can continue with your health plan."""
        
        return SessionResult(
            response=response,
            ready_for_crew=False,
            session_type=self.session_type,
            turn_count=self.state.turn_count,
            collected_fields={k: v.value for k, v in self.state.collected_fields.items()},
            implied_fields=self.state.implied_fields,
            has_urgent_symptoms=True,
            urgent_symptoms=symptoms
        )
    
    def _continue_collection(self, assessment: Dict) -> SessionResult:
        """Continue collecting information."""
        # Get next question
        question, field = self.question_gen.get_next_question(
            self.state, 
            self.session_type
        )
        
        if question:
            self.state.add_agent_message(question, field)
            response = question
        else:
            response = assessment.get("question", "Is there anything else you'd like to share?")
        
        return SessionResult(
            response=response,
            ready_for_crew=False,
            session_type=self.session_type,
            turn_count=self.state.turn_count,
            collected_fields={k: v.value for k, v in self.state.collected_fields.items()},
            implied_fields=self.state.implied_fields
        )
    
    def _prepare_for_crew(self, assessment: Dict) -> SessionResult:
        """Prepare data for crew execution."""
        # For follow-up sessions, detect patterns
        patterns_data = []
        interventions_data = []
        
        if self.session_type == "follow_up":
            # Detect patterns
            self.patterns_detected = self.pattern_detector.analyze_session(
                self.state.get_user_messages()
            )
            
            # Get habit summary
            habit_summary = self.pattern_detector.get_habit_summary(
                self.state.get_user_messages()
            )
            
            # Generate interventions
            self.interventions_generated = self.intervention_engine.generate_interventions(
                self.patterns_detected,
                habit_summary
            )
            
            patterns_data = [p.to_dict() for p in self.patterns_detected]
            interventions_data = [i.to_dict() for i in self.interventions_generated]
        
        # Build response
        response = self._build_handoff_message()
        
        return SessionResult(
            response=response,
            ready_for_crew=True,
            session_type=self.session_type,
            turn_count=self.state.turn_count,
            collected_fields={k: v.value for k, v in self.state.collected_fields.items()},
            implied_fields=self.state.implied_fields,
            patterns=patterns_data,
            interventions=interventions_data
        )
    
    def _build_handoff_message(self) -> str:
        """Build message when handing off to crew."""
        if self.session_type == "intake":
            return "Thank you for sharing that information! I'm now analyzing your health profile and creating personalized recommendations..."
        elif self.session_type == "follow_up":
            return "Thanks for the update! I'm reviewing your progress and preparing personalized feedback..."
        else:
            return "Let me look into that for you..."
    
    def complete_session(
        self,
        crew_result: Any,
        save_to_memory: bool = True
    ) -> str:
        """
        Complete the session after crew execution.
        
        Args:
            crew_result: Result from CrewAI execution
            save_to_memory: Whether to save session to memory
            
        Returns:
            Final response to show user (crew output + interventions)
        """
        self.crew_result = crew_result
        self.state.complete_session()
        
        # Build final response
        response_parts = []

        # Format crew result into human-readable text (not raw JSON)
        from app.services.response_formatter import ResponseFormatter
        formatted = ResponseFormatter.format_crew_output(crew_result)
        response_parts.append(formatted)
        
        # Add interventions for follow-up sessions
        if self.session_type == "follow_up" and self.interventions_generated:
            intervention_msg = self.intervention_engine.format_intervention_message(
                self.interventions_generated
            )
            if intervention_msg:
                response_parts.append("\n" + intervention_msg)
        
        # Save to memory
        if save_to_memory:
            self._save_to_memory()
        
        return "\n".join(response_parts)
    
    def _save_to_memory(self):
        """Save session data to memory."""
        try:
            from app.core.memory.semantic_memory import SemanticMemory
            memory = SemanticMemory()
            
            # Save collected profile data
            if self.session_type == "intake":
                profile_data = {
                    "type": "profile",
                    "fields": {k: v.value for k, v in self.state.collected_fields.items()},
                    "implied": self.state.implied_fields,
                    "session_date": datetime.now().isoformat()
                }
                memory.store_memory(
                    self.user_id,
                    json.dumps(profile_data),
                    {"type": "profile", "session_type": "intake"}
                )
            
            # Save patterns for follow-up
            if self.patterns_detected:
                patterns_data = {
                    "type": "patterns",
                    "patterns": [p.to_dict() for p in self.patterns_detected],
                    "session_date": datetime.now().isoformat()
                }
                memory.store_memory(
                    self.user_id,
                    json.dumps(patterns_data),
                    {"type": "patterns", "session_type": self.session_type}
                )
            
            # Save conversation summary
            summary = {
                "type": "conversation",
                "session_type": self.session_type,
                "turn_count": self.state.turn_count,
                "fields_collected": list(self.state.collected_fields.keys()),
                "session_date": datetime.now().isoformat()
            }
            memory.store_memory(
                self.user_id,
                json.dumps(summary),
                {"type": "conversation", "session_type": self.session_type}
            )
            
        except Exception as e:
            logger.warning("Failed to save to memory: %s", e)
    
    def get_combined_input(self) -> str:
        """Get combined user input for crew."""
        return self.state.get_combined_input()
    
    def get_collected_fields(self) -> Dict[str, Any]:
        """Get all collected field values."""
        return {k: v.value for k, v in self.state.collected_fields.items()}
    
    def get_patterns_summary(self) -> str:
        """Get a summary of detected patterns for the crew."""
        if not self.patterns_detected:
            return ""
        
        lines = ["Detected patterns from this session:"]
        for pattern in self.patterns_detected[:3]:
            lines.append(f"- {pattern.description} (severity: {pattern.severity.value})")
        
        return "\n".join(lines)
    
    def get_session_context(self) -> Dict:
        """Get full session context for crew execution."""
        return {
            "user_id": self.user_id,
            "session_type": self.session_type,
            "combined_input": self.get_combined_input(),
            "collected_fields": self.get_collected_fields(),
            "implied_fields": self.state.implied_fields,
            "patterns_summary": self.get_patterns_summary(),
            "previous_habits": self.user_habits,
            "turn_count": self.state.turn_count
        }
    
    def reset(self):
        """Reset session for a new conversation."""
        self.state.reset()
        self.patterns_detected = []
        self.interventions_generated = []
        self.crew_result = None
        self._welcome_shown = False

    def should_run_full_crew(self) -> Tuple[bool, str]:
        """
        Determine if the full agent crew should run, or if we can skip it.

        This prevents wasteful agent calls for:
        - Simple clarification responses
        - Insufficient data for meaningful recommendations
        - Repeated identical requests

        Returns:
            Tuple of (should_run: bool, reason: str)
        """
        # Minimum data thresholds by session type
        min_fields = {
            "intake": 4,      # Need at least age, sex, + 2 lifestyle factors
            "follow_up": 1,   # Need at least some progress update
            "general": 1      # Any question is fine
        }

        collected_count = len(self.state.collected_fields)
        required = min_fields.get(self.session_type, 1)

        # Check 1: Enough data collected?
        if collected_count < required:
            return False, f"Insufficient data: {collected_count}/{required} fields collected"

        # Check 2: For intake, ensure we have critical fields
        if self.session_type == "intake":
            critical_fields = {"age", "sex"}
            collected_names = set(self.state.collected_fields.keys())
            missing_critical = critical_fields - collected_names

            if missing_critical:
                return False, f"Missing critical fields: {missing_critical}"

        # Check 3: For follow-up, ensure there's actual progress to discuss
        if self.session_type == "follow_up":
            messages = self.state.get_user_messages()
            if len(messages) < 2:
                return False, "Need more context for follow-up analysis"

            # Check if messages contain substance (not just "yes/no")
            total_words = sum(len(m.split()) for m in messages)
            if total_words < 10:
                return False, "Responses too brief for meaningful analysis"

        # Check 4: Avoid repeated runs with same data (basic cache check)
        # This is a simple check - in production you'd use a proper cache
        context_hash = hash(frozenset(
            (k, str(v.value)) for k, v in self.state.collected_fields.items()
        ))

        if hasattr(self, '_last_crew_hash') and self._last_crew_hash == context_hash:
            return False, "Data unchanged since last analysis"

        # Mark this hash for next time
        self._last_crew_hash = context_hash

        return True, "Ready for full analysis"

    def get_quick_response(self, reason: str) -> str:
        """
        Generate a quick response when full crew isn't needed.

        Args:
            reason: Why crew was skipped

        Returns:
            Appropriate response message
        """
        if "Insufficient data" in reason:
            return "I need a bit more information before I can provide personalized recommendations. " + \
                   self.question_gen.get_next_question(self.state, self.session_type)[0]

        if "Missing critical" in reason:
            return "To give you accurate health guidance, I'll need to know your age and sex. Could you share those?"

        if "too brief" in reason:
            return "Could you tell me a bit more about how things have been going? " + \
                   "For example, what habits have you been working on, and how are they going?"

        if "unchanged" in reason:
            return "Based on what you've shared, my previous recommendations still apply. " + \
                   "Is there anything specific you'd like me to address or clarify?"

        return "Let me help you with that. Could you tell me more about your question?"


# Factory function
def create_session_manager(
    user_id: str,
    session_type: str = "intake",
    user_habits: List[str] = None,
    use_llm: bool = True
) -> SessionManager:
    """Create a new session manager."""
    return SessionManager(
        user_id=user_id,
        session_type=session_type,
        user_habits=user_habits,
        use_llm=use_llm
    )
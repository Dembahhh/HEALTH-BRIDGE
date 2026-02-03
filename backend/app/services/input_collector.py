"""
Multi-turn Input Collector for HEALTH-BRIDGE

Phase 3 Implementation:
- Uses LLM-based extraction instead of regex
- Tracks conversation state across turns
- Handles clarifications and implied information
- Detects urgent symptoms

Maintains backward compatibility with existing API.
"""

import re
from typing import Dict, List, Optional
from app.services.conversation_state import ConversationState, FieldConfidence
from app.services.llm_extractor import get_extractor, LLMExtractor
from app.services.question_generator import get_question_generator, QuestionGenerator


# Thresholds
INTAKE_MIN_FIELDS = 6
INTAKE_MAX_TURNS = 12
FOLLOW_UP_MIN_QUESTIONS = 3
FOLLOW_UP_MAX_TURNS = 7
GENERAL_MIN_LENGTH = 15


class InputCollector:
    """
    Guides users through providing sufficient information before running
    the CrewAI pipeline.
    
    Phase 3: Now uses LLM extraction with regex fallback.
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize collector.
        
        Args:
            use_llm: Whether to use LLM extraction (False for testing)
        """
        self.extractor: LLMExtractor = get_extractor(use_llm=use_llm)
        self.question_gen: QuestionGenerator = get_question_generator()
        
        # State tracking (for stateful usage)
        self._states: Dict[str, ConversationState] = {}
    
    def get_or_create_state(
        self,
        user_id: str,
        session_type: str = "intake"
    ) -> ConversationState:
        """Get or create conversation state for a user."""
        key = f"{user_id}_{session_type}"
        if key not in self._states:
            self._states[key] = ConversationState(
                session_type=session_type,
                user_id=user_id
            )
        return self._states[key]
    
    def assess(
        self,
        messages: List[str],
        session_type: str,
        user_habits: Optional[List[str]] = None,
    ) -> Dict:
        """
        Assess whether accumulated messages contain enough info.
        
        This is the main API - maintains backward compatibility.
        
        Args:
            messages: List of user messages collected so far
            session_type: One of "intake", "follow_up", "general"
            user_habits: For follow_up, list of user's existing habits
            
        Returns:
            dict with ready, combined_input/question, detected_fields, turn
        """
        # Create a temporary state for this assessment
        state = ConversationState(session_type=session_type)
        
        # Process each message
        for i, msg in enumerate(messages):
            state.add_user_message(msg)
            
            # Extract fields from this message
            context = messages[:i] if i > 0 else None
            last_field = state.last_question_field
            
            extraction = self.extractor.extract_all(msg, context, last_field)
            
            # Add urgent symptoms
            for symptom in extraction.urgent_symptoms:
                state.add_urgent_flag(symptom)
            
            # Add extracted fields
            for name, result in extraction.fields.items():
                confidence = FieldConfidence.HIGH if result.confidence >= 0.8 else \
                            FieldConfidence.MEDIUM if result.confidence >= 0.5 else \
                            FieldConfidence.LOW
                
                if result.needs_clarification:
                    confidence = FieldConfidence.NEEDS_CLARIFICATION
                
                state.set_field(
                    name=name,
                    value=result.value,
                    confidence=confidence,
                    source_message=msg,
                    clarifying_question=result.clarifying_question
                )
            
            # Add implied fields
            for field, value in extraction.implied.items():
                state.set_implied(field, value, "context")
        
        # Assess by session type
        if session_type == "intake":
            return self._assess_intake(state)
        elif session_type == "follow_up":
            return self._assess_follow_up(state, user_habits or [])
        else:
            return self._assess_general(state)
    
    def assess_message(
        self,
        message: str,
        state: ConversationState,
        user_habits: Optional[List[str]] = None
    ) -> Dict:
        """
        Assess a single new message with existing state.
        
        More efficient for multi-turn conversations.
        """
        # Add message to state
        state.add_user_message(message)
        
        # Extract from this message
        context = state.get_recent_messages(5)
        extraction = self.extractor.extract_all(
            message, 
            context[:-1] if len(context) > 1 else None,
            state.last_question_field
        )
        
        # Process extraction
        for symptom in extraction.urgent_symptoms:
            state.add_urgent_flag(symptom)
        
        for name, result in extraction.fields.items():
            confidence = FieldConfidence.HIGH if result.confidence >= 0.8 else \
                        FieldConfidence.MEDIUM if result.confidence >= 0.5 else \
                        FieldConfidence.LOW
            
            if result.needs_clarification:
                confidence = FieldConfidence.NEEDS_CLARIFICATION
            
            state.set_field(name, result.value, confidence, message, result.clarifying_question)
        
        for field, value in extraction.implied.items():
            state.set_implied(field, value, "context")
        
        # Assess
        if state.session_type == "intake":
            return self._assess_intake(state)
        elif state.session_type == "follow_up":
            return self._assess_follow_up(state, user_habits or [])
        else:
            return self._assess_general(state)
    
    def get_welcome_question(
        self,
        session_type: str,
        user_habits: Optional[List[str]] = None,
    ) -> str:
        """Get the initial welcome question."""
        welcome, _ = self.question_gen.get_welcome_message(session_type, user_habits)
        return welcome
    
    def _assess_intake(self, state: ConversationState) -> Dict:
        """Assess intake session."""
        
        fields_collected = state.count_collected_fields()
        turn = state.turn_count
        
        # Check if ready
        enough_fields = fields_collected >= INTAKE_MIN_FIELDS
        safety_valve = turn >= INTAKE_MAX_TURNS
        has_urgent = state.has_urgent_symptoms()
        
        if has_urgent:
            # Get urgent response
            question, _ = self.question_gen.get_next_question(state, "intake")
            return {
                "ready": False,
                "question": question,
                "detected_fields": state.get_detected_fields_dict(),
                "turn": turn,
                "urgent": True,
                "urgent_symptoms": state.urgent_flags
            }
        
        if enough_fields or safety_valve:
            return {
                "ready": True,
                "combined_input": state.get_combined_input(),
                "detected_fields": state.get_detected_fields_dict(),
                "turn": turn,
                "collected_values": {k: v.value for k, v in state.collected_fields.items()},
                "implied_fields": state.implied_fields
            }
        
        # Get next question
        question, field = self.question_gen.get_next_question(state, "intake")
        
        if question is None:
            # No more questions but not enough fields - use fallback
            question = "Is there anything else about your health you'd like to share?"
        
        state.add_agent_message(question, field)
        
        return {
            "ready": False,
            "question": question,
            "detected_fields": state.get_detected_fields_dict(),
            "turn": turn,
            "next_field": field
        }
    
    def _assess_follow_up(
        self,
        state: ConversationState,
        user_habits: List[str]
    ) -> Dict:
        """Assess follow-up session."""
        
        fields_collected = state.count_collected_fields()
        turn = state.turn_count
        combined = state.get_combined_input()
        
        # Check readiness
        enough_answers = fields_collected >= FOLLOW_UP_MIN_QUESTIONS
        safety_valve = turn >= FOLLOW_UP_MAX_TURNS
        long_enough = len(combined.split()) >= 20
        
        if enough_answers or safety_valve or long_enough:
            return {
                "ready": True,
                "combined_input": combined,
                "detected_fields": state.get_detected_fields_dict(),
                "turn": turn
            }
        
        # Get next question
        question, field = self.question_gen.get_next_question(state, "follow_up")
        
        if question is None:
            question = "Is there anything else you'd like to share about your progress?"
        
        state.add_agent_message(question, field)
        
        return {
            "ready": False,
            "question": question,
            "detected_fields": state.get_detected_fields_dict(),
            "turn": turn
        }
    
    def _assess_general(self, state: ConversationState) -> Dict:
        """Assess general/educational session."""
        
        combined = state.get_combined_input()
        turn = state.turn_count
        
        # Check if we have enough for a general query
        has_question = bool(re.search(r"\?|how|what|why|when|can|should|is it", combined, re.IGNORECASE))
        has_topic = bool(re.search(
            r"\b(diet|exercise|blood\s*pressure|diabetes|hypertension|heart|weight|habit|health|symptom)\w*\b",
            combined,
            re.IGNORECASE
        ))
        long_enough = len(combined.strip()) >= GENERAL_MIN_LENGTH
        
        if (has_question or has_topic or long_enough) or turn >= 2:
            return {
                "ready": True,
                "combined_input": combined,
                "detected_fields": {"has_question": has_question, "has_topic": has_topic},
                "turn": turn,
            }
        
        if turn == 0:
            question = (
                "Hi! I can help answer health questions about diet, exercise, "
                "blood pressure, diabetes, and healthy habits.\n\n"
                "What would you like to know? For example:\n"
                "  • \"What foods should I avoid for high blood pressure?\"\n"
                "  • \"How much exercise do I need per week?\"\n"
                "  • \"What are warning signs of a stroke?\""
            )
        else:
            question = (
                "Could you be more specific about what you'd like to know?\n"
                "Try asking a question like \"How can I lower my blood pressure naturally?\""
            )
        
        return {
            "ready": False,
            "question": question,
            "detected_fields": {},
            "turn": turn,
        }
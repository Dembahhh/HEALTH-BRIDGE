"""
Smart Question Generator for HEALTH-BRIDGE

Generates contextual follow-up questions based on:
- What's already been collected
- What needs clarification
- User's risk profile
- Conversation flow

Phase 3 Implementation:
- Adaptive question ordering
- Acknowledges previous responses
- Skips irrelevant questions based on context
- Handles urgent symptom escalation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.services.conversation_state import ConversationState, FieldConfidence


@dataclass
class FieldConfig:
    """Configuration for a data collection field."""
    name: str
    question: str
    priority: int  # 1 = highest priority
    order: int     # Default order
    clarifying_questions: List[str]
    skip_if_age_over: Optional[int] = None  # Skip if user is older than this


# Field configurations for intake
FIELD_CONFIGS: Dict[str, FieldConfig] = {
    "age": FieldConfig(
        name="age",
        question="How old are you?",
        priority=1,
        order=1,
        clarifying_questions=["Could you tell me your exact age?"]
    ),
    "sex": FieldConfig(
        name="sex", 
        question="Are you male or female?",
        priority=1,
        order=2,
        clarifying_questions=[]
    ),
    "conditions": FieldConfig(
        name="conditions",
        question='Do you have any existing health conditions like hypertension, diabetes, or heart disease? (You can say "none" if not)',
        priority=1,
        order=3,
        clarifying_questions=[
            "Are you currently taking any medication for this?",
            "How long have you had this condition?"
        ]
    ),
    "family_history": FieldConfig(
        name="family_history",
        question='Does anyone in your family have hypertension, diabetes, or heart disease?',
        priority=2,
        order=4,
        clarifying_questions=["Which family member, and what condition?"]
    ),
    "smoking": FieldConfig(
        name="smoking",
        question="Do you smoke? (yes / no / quit)",
        priority=2,
        order=5,
        clarifying_questions=["How many cigarettes per day?"],
        skip_if_age_over=75
    ),
    "alcohol": FieldConfig(
        name="alcohol",
        question="Do you drink alcohol? (no / occasionally / regularly)",
        priority=2,
        order=6,
        clarifying_questions=["About how many drinks per week?"]
    ),
    "diet": FieldConfig(
        name="diet",
        question='What does your typical diet look like? (e.g., "mostly rice and vegetables")',
        priority=2,
        order=7,
        clarifying_questions=["How much salt do you typically use in cooking?"]
    ),
    "activity": FieldConfig(
        name="activity",
        question='How physically active are you? (e.g., "sedentary", "walk daily", "exercise 3x/week")',
        priority=2,
        order=8,
        clarifying_questions=["What type of exercise and how often?"]
    ),
    "constraints": FieldConfig(
        name="constraints",
        question='Are there any constraints that might affect your health habits? (e.g., "long work hours", "limited food access") Or say "none"',
        priority=3,
        order=9,
        clarifying_questions=[]
    ),
}

# Acknowledgment templates
ACKNOWLEDGMENTS = [
    "Thanks for sharing that!",
    "Got it, thank you.",
    "I've noted that.",
    "Thanks! That helps.",
    "Understood.",
    "Great, thanks.",
]

# Urgent symptom response
URGENT_RESPONSE = """⚠️ **IMPORTANT**: You mentioned {symptoms}. These could be signs of a serious condition.

**Please seek immediate medical attention:**
- Go to your nearest emergency room, OR
- Call emergency services (911 / your local emergency number)

Do not wait to see if symptoms improve. Your health is the priority.

Once you've received medical care, we can continue with your health plan."""


class QuestionGenerator:
    """Generates contextual questions for health data collection."""
    
    def __init__(self):
        self.configs = FIELD_CONFIGS
        self._ack_index = 0
    
    def get_next_question(
        self,
        state: ConversationState,
        session_type: str = "intake"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the next question to ask.
        
        Args:
            state: Current conversation state
            session_type: Type of session
            
        Returns:
            Tuple of (question_text, field_name) or (None, None) if done
        """
        # Handle urgent symptoms first
        if state.has_urgent_symptoms():
            symptoms = ", ".join(state.urgent_flags)
            return (URGENT_RESPONSE.format(symptoms=symptoms), None)
        
        if session_type == "intake":
            return self._get_intake_question(state)
        elif session_type == "follow_up":
            return self._get_followup_question(state)
        else:
            return (None, None)
    
    def _get_intake_question(
        self,
        state: ConversationState
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get next intake question."""
        
        # Check for fields needing clarification first
        needs_clarification = state.get_fields_needing_clarification()
        if needs_clarification:
            field = needs_clarification[0]
            if field.clarifying_question:
                q = f"I need a bit more detail: {field.clarifying_question}"
                return (q, field.name)
        
        # Get prioritized list of missing fields
        missing = self._get_missing_fields(state)
        
        if not missing:
            return (None, None)
        
        field_name = missing[0]
        config = self.configs[field_name]
        
        # Build question with acknowledgment
        question = config.question
        
        if state.turn_count > 0:
            ack = self._build_acknowledgment(state)
            if ack:
                question = f"{ack}\n\n{question}"
        
        return (question, field_name)
    
    def _get_missing_fields(self, state: ConversationState) -> List[str]:
        """Get list of missing fields sorted by priority."""
        missing = []
        
        # Get user's age for skip logic
        user_age = state.get_field_value("age")
        
        for name, config in self.configs.items():
            # Skip if already collected
            if state.has_field(name):
                continue
            
            # Skip if age-based skip applies
            if config.skip_if_age_over and user_age:
                try:
                    if int(user_age) > config.skip_if_age_over:
                        continue
                except (ValueError, TypeError):
                    pass
            
            missing.append((config.priority, config.order, name))
        
        # Sort by priority, then order
        missing.sort(key=lambda x: (x[0], x[1]))
        
        return [name for _, _, name in missing]
    
    def _build_acknowledgment(self, state: ConversationState) -> str:
        """Build acknowledgment for previous response."""
        
        # Find fields collected in this turn
        recent = [
            f.name.replace("_", " ")
            for f in state.collected_fields.values()
            if f.turn_number == state.turn_count
        ]
        
        if recent:
            if len(recent) == 1:
                return f"Thanks! I've noted your {recent[0]}."
            else:
                return f"Thanks! I've noted your {', '.join(recent[:-1])} and {recent[-1]}."
        
        # Check for implied fields
        if state.implied_fields:
            return "Got it, thanks for that context."
        
        # Generic acknowledgment
        ack = ACKNOWLEDGMENTS[self._ack_index % len(ACKNOWLEDGMENTS)]
        self._ack_index += 1
        return ack
    
    def _get_followup_question(
        self,
        state: ConversationState
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get next follow-up session question."""
        
        followup_fields = [
            ("habits_followed", "Which habits from your plan have you been able to follow?"),
            ("habits_struggled", "Have you stopped or struggled with any habits? Which ones and why?"),
            ("health_readings", "Have you had any recent health readings like blood pressure or weight?"),
            ("barriers", "Are you facing any challenges or barriers to following your plan?"),
            ("feelings", "How are you feeling overall — any symptoms or concerns?"),
        ]
        
        for field_name, question in followup_fields:
            if not state.has_field(field_name):
                if state.turn_count > 0:
                    ack = ACKNOWLEDGMENTS[self._ack_index % len(ACKNOWLEDGMENTS)]
                    self._ack_index += 1
                    return (f"{ack}\n\n{question}", field_name)
                return (question, field_name)
        
        return (None, None)
    
    def get_welcome_message(
        self,
        session_type: str,
        user_habits: List[str] = None
    ) -> Tuple[str, Optional[str]]:
        """Get welcome message for session start."""
        
        if session_type == "intake":
            first_field = "age"
            question = self.configs["age"].question
            welcome = (
                "Welcome! I'm here to help assess your health profile and "
                "create a personalized wellness plan.\n\n"
                f"Let's start: {question}"
            )
            return (welcome, first_field)
        
        elif session_type == "follow_up":
            if user_habits:
                habits_str = "\n".join(f"  • {h}" for h in user_habits[:4])
                welcome = (
                    f"Welcome back! Last time we set up these habits for you:\n"
                    f"{habits_str}\n\n"
                    f"How have things been going? Which habits have you been able to follow?"
                )
            else:
                welcome = (
                    "Welcome back! Let's check in on your progress.\n\n"
                    "Which habits from your plan have you been able to follow?"
                )
            return (welcome, "habits_followed")
        
        else:
            welcome = (
                "Hi! I can help answer health questions about diet, exercise, "
                "blood pressure, diabetes, and healthy habits.\n\n"
                "What would you like to know?"
            )
            return (welcome, None)


# Singleton
_generator: Optional[QuestionGenerator] = None


def get_question_generator() -> QuestionGenerator:
    """Get or create question generator singleton."""
    global _generator
    if _generator is None:
        _generator = QuestionGenerator()
    return _generator
"""
Multi-turn input collector for HealthBridge agent sessions.

Guides users through providing sufficient information before running
the full CrewAI pipeline. Asks one question at a time and waits for
user responses. This avoids wasting LLM tokens on vague input.

Usage:
    collector = InputCollector()
    result = collector.assess(["I'm 45 male"], "intake")
    if not result["ready"]:
        print(result["question"])  # single question to ask
    else:
        run_crew(result["combined_input"])
"""

import re
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Field definitions per session type
# ---------------------------------------------------------------------------

INTAKE_FIELDS = {
    "age": {
        "patterns": [
            r"\b(\d{1,3})\s*(year|yr|y\.?o\.?)",
            r"\bage\b[:\s]*(\d{1,3})",
            r"\b(?:i'?m|i am|am)\s*(\d{2})\b",
            r"\b(\d{2})\s*(year|yr)s?\s*old\b",
        ],
        "question": "How old are you?",
        "priority": 1,
        "order": 1,
    },
    "sex": {
        "patterns": [
            r"\b(male|female|man|woman|boy|girl)\b",
            r"\bsex[:\s]*(m|f|male|female)\b",
        ],
        "question": "Are you male or female?",
        "priority": 1,
        "order": 2,
    },
    "conditions": {
        "patterns": [
            r"\b(hypertension|diabetes|diabetic|high\s*blood\s*pressure|heart|cholesterol)\b",
            r"\b(diagnosed|condition|suffer|have)\b.*\b(disease|illness)\b",
            r"\bno\s+(known\s+)?(condition|disease|illness)\b",
            r"\bhealthy\b",
        ],
        "question": "Do you have any existing health conditions? (e.g., hypertension, diabetes, heart disease — or \"none\")",
        "priority": 1,
        "order": 3,
    },
    "family_history": {
        "patterns": [
            r"\b(father|mother|parent|family|brother|sister|sibling)\b.*\b(history|had|has|have|diabete|hypertension|heart|stroke|pressure)\b",
            r"\b(history|diabete|hypertension|heart|stroke|pressure)\b.*\b(father|mother|parent|family|brother|sister)\b",
            r"\bfamily\s+history\b",
            r"\b(inherit|genetic|hereditary)\w*\b",
            r"\bno\s+family\s+history\b",
        ],
        "question": "Does anyone in your family have hypertension, diabetes, or heart disease? (e.g., \"my father had hypertension\" or \"no family history\")",
        "priority": 2,
        "order": 4,
    },
    "smoking": {
        "patterns": [
            r"\b(smok|cigarette|tobacco|nicotine)\w*\b",
            r"\b(don'?t|do not|never)\s+smoke\b",
            r"\bnon[\s-]?smoker\b",
        ],
        "question": "Do you smoke? (yes/no, or how often)",
        "priority": 2,
        "order": 5,
    },
    "alcohol": {
        "patterns": [
            r"\b(alcohol|drink|beer|wine|spirit|liquor)\w*\b",
            r"\b(don'?t|do not|never)\s+drink\b",
            r"\bteetotal\w*\b",
        ],
        "question": "Do you drink alcohol? (no / occasionally / regularly)",
        "priority": 2,
        "order": 6,
    },
    "diet": {
        "patterns": [
            r"\b(eat|food|diet|vegetable|fruit|meat|fish|ugali|chapati|rice|bread|sugar|salt|soda|processed)\w*\b",
            r"\b(vegetarian|vegan|pescatarian)\b",
            r"\b(healthy|unhealthy|junk|fast\s*food)\b",
        ],
        "question": "What does your typical diet look like? (e.g., \"mostly rice and vegetables\" or \"lots of processed food\")",
        "priority": 2,
        "order": 7,
    },
    "activity": {
        "patterns": [
            r"\b(exercise|walk|run|gym|sport|active|sedentary|jog|swim|cycle|workout)\w*\b",
            r"\b(don'?t|do not|never)\s+(exercise|move|walk)\b",
            r"\b(sit|desk)\s*(all\s*day|job)\b",
        ],
        "question": "How physically active are you? (e.g., \"sedentary\", \"walk 30 min daily\", \"exercise 3x/week\")",
        "priority": 2,
        "order": 8,
    },
    "constraints": {
        "patterns": [
            r"\b(can'?t|cannot|unable|difficult|hard|no\s+access|expensive|afford)\b",
            r"\b(work|job|shift|night|schedule)\b.*\b(long|busy|irregular)\b",
            r"\b(unsafe|flood|rain|danger)\b",
            r"\b(budget|money|cost)\b",
            r"\bno\s+constraints?\b",
        ],
        "question": "Are there any constraints that might affect your health habits? (e.g., \"long work hours\", \"limited food access\", \"unsafe to walk outside\" — or \"none\")",
        "priority": 3,
        "order": 9,
    },
}

FOLLOW_UP_QUESTIONS = [
    {
        "id": "habits_followed",
        "question": "Which habits from your plan have you been able to follow?",
        "patterns": [
            r"\b(follow|kept|doing|did|stick|stuck|maintain)\w*\b",
            r"\b(habit|plan|routine|goal)\w*\b",
            r"\b(walk|exercise|eat|diet|water|sleep|meditat)\w*\b",
        ],
    },
    {
        "id": "habits_stopped",
        "question": "Have you stopped or struggled with any habits? Which ones and why?",
        "patterns": [
            r"\b(stop|quit|skip|miss|fail|struggle|hard|difficult|couldn'?t)\w*\b",
            r"\b(gave\s+up|dropped|abandoned)\b",
        ],
    },
    {
        "id": "new_habits",
        "question": "Have you started any new healthy habits on your own?",
        "patterns": [
            r"\b(new|start|began|added|also|extra)\w*\b.*\b(habit|routine|exercise|diet)\w*\b",
            r"\b(habit|routine)\w*\b.*\b(new|start|began|added)\w*\b",
        ],
    },
    {
        "id": "health_readings",
        "question": "Have you had any recent health readings? (blood pressure, weight, blood sugar)",
        "patterns": [
            r"\b(blood\s*pressure|bp|sugar|glucose|weight|bmi|reading|measure)\b",
            r"\b\d{2,3}/\d{2,3}\b",  # BP format
            r"\b\d{2,3}\s*(kg|lb|pound)\b",  # weight
        ],
    },
    {
        "id": "barriers",
        "question": "Are you facing any challenges or barriers to following your plan?",
        "patterns": [
            r"\b(barrier|challenge|problem|issue|block|obstacle)\w*\b",
            r"\b(rain|flood|unsafe|expensive|busy|tired|sick|injury)\b",
            r"\b(can'?t|cannot|unable)\b",
        ],
    },
    {
        "id": "feelings",
        "question": "How are you feeling overall — any symptoms or concerns?",
        "patterns": [
            r"\b(feel|feeling|felt)\w*\b",
            r"\b(symptom|pain|ache|dizzy|tired|fatigue|headache|chest)\w*\b",
            r"\b(better|worse|same|fine|good|bad)\b",
        ],
    },
]

# Thresholds
INTAKE_MIN_FIELDS = 4  # Minimum fields to have before running crew
INTAKE_MAX_TURNS = 8   # Safety valve: run crew after this many turns
FOLLOW_UP_MIN_QUESTIONS = 2  # Minimum follow-up questions answered
FOLLOW_UP_MAX_TURNS = 5
GENERAL_MIN_LENGTH = 15


# ---------------------------------------------------------------------------
# InputCollector
# ---------------------------------------------------------------------------

class InputCollector:
    """
    Guides users through providing sufficient information before running
    the full CrewAI crew pipeline. Asks one question at a time.

    Designed to be used by both the CLI and the API route.
    """

    def assess(
        self,
        messages: List[str],
        session_type: str,
        user_habits: Optional[List[str]] = None,
    ) -> Dict:
        """
        Assess whether accumulated messages contain enough info to run the crew.

        Args:
            messages: List of user messages collected so far (may be empty).
            session_type: One of "intake", "follow_up", "general".
            user_habits: For follow_up sessions, list of user's existing habits
                         from their plan (to ask about specifically).

        Returns:
            dict with keys:
              - ready (bool): True if the crew should run.
              - combined_input (str): Merged text to pass to the crew (if ready).
              - question (str): The next question to ask the user (if not ready).
              - detected_fields (dict): Which fields were found.
              - turn (int): How many messages have been collected.
        """
        combined = " ".join(messages)
        turn = len(messages)

        if session_type == "intake":
            return self._assess_intake(combined, turn)
        elif session_type == "follow_up":
            return self._assess_follow_up(combined, turn, user_habits or [])
        else:
            return self._assess_general(combined, turn)

    def get_welcome_question(
        self,
        session_type: str,
        user_habits: Optional[List[str]] = None,
    ) -> str:
        """Get the initial welcome question for a session type."""
        result = self.assess([], session_type, user_habits)
        return result.get("question", "How can I help you today?")

    # ------------------------------------------------------------------
    # Intake — ask one question at a time
    # ------------------------------------------------------------------

    def _assess_intake(self, combined: str, turn: int) -> Dict:
        detected = {}
        missing_by_order = []

        for field, config in INTAKE_FIELDS.items():
            found = any(
                re.search(p, combined, re.IGNORECASE) for p in config["patterns"]
            )
            detected[field] = found
            if not found:
                missing_by_order.append((config["order"], field, config))

        # Sort by order to ask questions in logical sequence
        missing_by_order.sort(key=lambda x: x[0])
        fields_found = sum(1 for v in detected.values() if v)

        # Check if ready
        enough_fields = fields_found >= INTAKE_MIN_FIELDS
        safety_valve = turn >= INTAKE_MAX_TURNS

        if enough_fields or safety_valve:
            return {
                "ready": True,
                "combined_input": combined,
                "detected_fields": detected,
                "turn": turn,
            }

        # --- Build the next question ---
        if turn == 0:
            # First interaction: warm welcome + first question
            first_q = missing_by_order[0][2]["question"] if missing_by_order else "How old are you?"
            question = (
                "Welcome! I'm here to help assess your health profile and "
                "create a personalized plan.\n\n"
                f"Let's start: {first_q}"
            )
        else:
            # Acknowledge what we got, then ask the next missing field
            detected_names = [f.replace("_", " ") for f, v in detected.items() if v]
            if detected_names:
                ack = f"Thanks! I've noted your {', '.join(detected_names[-2:])}.\n\n"
            else:
                ack = ""

            if missing_by_order:
                next_q = missing_by_order[0][2]["question"]
                question = f"{ack}{next_q}"
            else:
                question = f"{ack}Is there anything else you'd like to add about your health?"

        return {
            "ready": False,
            "question": question,
            "detected_fields": detected,
            "turn": turn,
        }

    # ------------------------------------------------------------------
    # Follow-up — ask about specific habits
    # ------------------------------------------------------------------

    def _assess_follow_up(
        self,
        combined: str,
        turn: int,
        user_habits: List[str],
    ) -> Dict:
        detected = {}
        questions_answered = 0

        for item in FOLLOW_UP_QUESTIONS:
            found = any(
                re.search(p, combined, re.IGNORECASE) for p in item["patterns"]
            )
            detected[item["id"]] = found
            if found:
                questions_answered += 1

        # Check if ready
        enough_answers = questions_answered >= FOLLOW_UP_MIN_QUESTIONS
        safety_valve = turn >= FOLLOW_UP_MAX_TURNS
        long_enough = len(combined.split()) >= 20

        if enough_answers or safety_valve or long_enough:
            return {
                "ready": True,
                "combined_input": combined,
                "detected_fields": detected,
                "turn": turn,
            }

        # --- Build the next question ---
        if turn == 0:
            # First interaction: personalized welcome
            if user_habits:
                habits_list = ", ".join(user_habits[:3])
                if len(user_habits) > 3:
                    habits_list += f" (and {len(user_habits) - 3} more)"
                question = (
                    f"Welcome back! Last time we set up these habits for you:\n"
                    f"  {habits_list}\n\n"
                    f"How have things been going? Which habits have you been able to follow?"
                )
            else:
                question = (
                    "Welcome back! Let's check in on your progress.\n\n"
                    "Which habits from your plan have you been able to follow?"
                )
        else:
            # Find next unanswered question
            next_question = None
            for item in FOLLOW_UP_QUESTIONS:
                if not detected.get(item["id"]):
                    next_question = item["question"]
                    break

            if next_question:
                # Acknowledge and ask next
                if questions_answered > 0:
                    question = f"Got it, thanks for sharing.\n\n{next_question}"
                else:
                    question = next_question
            else:
                question = "Is there anything else you'd like to share about your progress?"

        return {
            "ready": False,
            "question": question,
            "detected_fields": detected,
            "turn": turn,
        }

    # ------------------------------------------------------------------
    # General / educational — just need a clear question
    # ------------------------------------------------------------------

    def _assess_general(self, combined: str, turn: int) -> Dict:
        # For general, we just need a reasonable question/topic
        has_question = bool(re.search(r"\?|how|what|why|when|can|should|is it", combined, re.IGNORECASE))
        has_topic = bool(re.search(
            r"\b(diet|exercise|blood\s*pressure|diabetes|hypertension|heart|weight|habit|health|symptom|warning|sign)\w*\b",
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
                "  - \"What foods should I avoid for high blood pressure?\"\n"
                "  - \"How much exercise do I need per week?\"\n"
                "  - \"What are warning signs of a stroke?\""
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

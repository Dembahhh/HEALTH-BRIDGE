"""
Task Definitions

Each function returns a CrewAI Task bound to a specific agent.
Tasks use output_pydantic for structured, validated output.
"""

from crewai import Task
from .models import Profile, RiskAssessment, Constraints, HabitPlan, SafetyReview


def intake_task(agent, user_input: str, user_id: str, memory_context: str = "") -> Task:
    return Task(
        description=(
            f"Analyze the following user input and extract a health profile.\n"
            f"User said: '{user_input}'\n\n"
            f"Extract: age, sex, weight category, activity level, diet pattern, "
            f"family history, smoking status, and alcohol habits.\n\n"
            f"CONSTRAINTS:\n"
            f"- Extract ONLY what the user explicitly stated or clearly implied.\n"
            f"- Do NOT infer conditions, risk factors, or lifestyle details not mentioned.\n"
            f"- If a field is completely missing, use 'unknown'.\n"
            f"- Do NOT fill 'family_history' unless the user mentions relatives' health.\n"
            f"- Do NOT assume diet patterns from cultural background.\n"
            f"\n{memory_context}"
        ),
        agent=agent,
        expected_output="Structured Profile JSON matching the schema with ONLY user-provided data",
        output_pydantic=Profile
    )


def risk_assessment_task(agent, context_tasks: list, memory_context: str = "") -> Task:
    return Task(
        description=(
            "Using the user's Profile from the previous task, estimate "
            "hypertension and diabetes risk bands based on WHO guidelines.\n\n"
            "INSTRUCTIONS:\n"
            "1. Use the 'Retrieve Guidelines' tool with condition='hypertension' "
            "AND condition='diabetes' to get relevant risk tables.\n"
            "2. ONLY cite risk factors that appear in the retrieved guidelines.\n"
            "3. If no guideline supports a claim, do NOT include it.\n"
            "4. Map user data to risk bands: low, moderate, or high.\n"
            "5. For each key_driver, reference the specific guideline that supports it.\n\n"
            "CONSTRAINTS:\n"
            "- Do NOT diagnose. Only estimate risk bands.\n"
            "- Do NOT invent statistics or percentages.\n"
            "- If data is missing, state 'insufficient data' rather than guessing.\n"
            f"\n{memory_context}"
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Structured RiskAssessment JSON matching the schema",
        output_pydantic=RiskAssessment
    )


def context_sdoh_task(agent, user_input: str, user_id: str, memory_context: str = "") -> Task:
    return Task(
        description=(
            f"Analyze the user's input for social and environmental constraints.\n"
            f"User said: '{user_input}'\n"
            f"Identify: exercise safety, food access, time constraints, financial band.\n"
            f"Use user_id '{user_id}' when saving constraints or recalling memories.\n"
            f"\n{memory_context}"
        ),
        agent=agent,
        expected_output="Structured Constraints JSON matching the schema",
        output_pydantic=Constraints
    )


def habit_plan_task(agent, user_id: str, context_tasks: list) -> Task:
    return Task(
        description=(
            "Create a realistic 4-week tiny-habit plan based on the Risk Assessment "
            "and SDOH Constraints from previous tasks.\n\n"
            "RULES:\n"
            "- Include exactly 1-3 habits.\n"
            "- Each habit MUST have: action, frequency, trigger, rationale.\n"
            "- Habits must be affordable and accessible for the user's financial_band.\n"
            "- Habits must be safe given the user's exercise_safety constraints.\n"
            "- Do NOT recommend gym memberships, expensive supplements, or equipment.\n"
            "- Base rationale on retrieved guidelines, not general knowledge.\n\n"
            "EXAMPLE OUTPUT:\n"
            '{"duration_weeks": 4, "focus_areas": ["Reduce salt intake", '
            '"Increase daily movement"], "habits": [{"action": "Walk for 15 minutes", '
            '"frequency": "Daily", "trigger": "After dinner, before sitting down", '
            '"rationale": "Regular walking helps lower blood pressure (WHO guidelines)"}], '
            '"motivational_message": "Small steps lead to big changes!"}\n\n'
            f"Use user_id '{user_id}' when recalling user memories for personalization."
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Structured HabitPlan JSON matching the schema",
        output_pydantic=HabitPlan
    )


def safety_review_task(agent, context_tasks: list) -> Task:
    return Task(
        description=(
            "Review the Habit Plan from the previous task for safety.\n"
            "Check for: diagnostic claims, medication/dosage advice, "
            "missing escalation for dangerous symptoms.\n"
            "Use the 'Retrieve Guidelines' tool to verify red flag handling. "
            "Consider using topic='red_flags' to find clinical safety guidance.\n\n"
            "CRITICAL: You MUST always include the complete habit plan in your "
            "revised_response field, formatted as a friendly user-facing message.\n"
            "- If the plan is safe, copy it into revised_response as clear, "
            "readable text (not JSON) with the habits, frequencies, triggers, "
            "and a motivational closing.\n"
            "- If parts are unsafe, rewrite those parts and include the corrected "
            "full plan in revised_response.\n"
            "- NEVER leave revised_response as null or empty."
        ),
        agent=agent,
        context=context_tasks,
        expected_output=(
            "SafetyReview JSON with is_safe boolean, any flagged_issues, and "
            "the COMPLETE habit plan as user-friendly text in revised_response."
        ),
        output_pydantic=SafetyReview
    )

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
            f"User said: '{user_input}'\n"
            f"Extract: age, sex, weight category, activity level, diet pattern, "
            f"family history, smoking status, and alcohol habits.\n"
            f"If any field is missing, make a reasonable assumption and note it.\n"
            f"\n{memory_context}"
        ),
        agent=agent,
        expected_output="Structured Profile JSON matching the schema",
        output_pydantic=Profile
    )


def risk_assessment_task(agent, context_tasks: list, memory_context: str = "") -> Task:
    return Task(
        description=(
            "Using the user's Profile from the previous task, estimate "
            "hypertension and diabetes risk bands based on WHO guidelines.\n"
            "Use the 'Retrieve Guidelines' tool to look up relevant risk tables. "
            "You can specify condition='hypertension' or condition='diabetes' to focus your search.\n"
            "Do NOT diagnose. Only estimate risk bands: low, moderate, or high.\n"
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
            "and SDOH Constraints from previous tasks.\n"
            "Keep habits small, affordable, and safe for the user's context.\n"
            f"Use user_id '{user_id}' when recalling user memories for personalization.\n"
            "Include 1-3 habits max with clear triggers and rationale."
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
            "Consider using topic='red_flags' to find clinical safety guidance.\n"
            "If the plan is safe, return it as-is. If not, rewrite the unsafe parts."
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Safety review with revised response if needed",
        output_pydantic=SafetyReview
    )

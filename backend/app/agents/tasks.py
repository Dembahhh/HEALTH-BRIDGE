"""
Task Definitions

Each function returns a CrewAI Task bound to a specific agent.
Tasks use output_pydantic for structured, validated output.
Includes grounding constraints and citation requirements.
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
            f"Analyze the nuance in the user's description. While you should not invent data, "
            f"you should carefully extract implications from their daily routine or comments. "
            f"If a field is completely missing, use 'unknown'. "
            f"Use 'unknown' for categorical literals only as a last resort.\n"
            f"\n"
            f"GROUNDING RULES:\n"
            f"- ONLY extract information that the user explicitly stated or strongly implied.\n"
            f"- Do NOT invent statistics, percentages, or risk numbers.\n"
            f"- Do NOT assume lifestyle details not mentioned by the user.\n"
            f"- If unsure about a field, set it to 'unknown' rather than guessing.\n"
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
            "hypertension and diabetes risk bands based on WHO guidelines.\n"
            "Use the 'Retrieve Guidelines' tool to look up relevant risk tables. "
            "You can specify condition='hypertension' or condition='diabetes' to focus your search.\n"
            "Do NOT diagnose. Only estimate risk bands: low, moderate, or high.\n"
            "\n"
            "GROUNDING RULES:\n"
            "- ONLY cite risk factors that appear in the retrieved guidelines.\n"
            "- Do NOT invent statistics, percentages, or relative risk numbers.\n"
            "- Base your explanation strictly on the user's profile data and retrieved evidence.\n"
            "- If the guidelines don't cover a specific factor, say so rather than guessing.\n"
            "\n"
            "CITATION RULES:\n"
            "- For each risk factor you mention, include a citation from the retrieved guideline.\n"
            "- Populate the 'citations' field with source_id, source_name, text_snippet, "
            "condition, and topic for each guideline chunk you reference.\n"
            "\n"
            "EXAMPLE OUTPUT (for reference only — use the user's actual data):\n"
            '{\n'
            '  "hypertension_risk": "moderate",\n'
            '  "diabetes_risk": "low",\n'
            '  "key_drivers": ["family history of hypertension", "sedentary lifestyle"],\n'
            '  "explanation": "Based on your family history and current activity level...",\n'
            '  "citations": [{"source_id": "who-htn-001", "source_name": "WHO Hypertension Guidelines", '
            '"text_snippet": "Family history increases risk by...", "condition": "hypertension", "topic": "risk_factors"}]\n'
            '}\n'
            f"\n{memory_context}"
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Structured RiskAssessment JSON with citations from retrieved guidelines",
        output_pydantic=RiskAssessment
    )


def context_sdoh_task(agent, user_input: str, user_id: str, memory_context: str = "") -> Task:
    return Task(
        description=(
            f"Analyze the user's input for social and environmental constraints.\n"
            f"User said: '{user_input}'\n"
            f"Identify: exercise safety, food access, time constraints, financial band.\n"
            f"Use user_id '{user_id}' when saving constraints or recalling memories.\n"
            f"\n"
            f"GROUNDING RULES:\n"
            f"- ONLY report constraints the user mentioned or strongly implied.\n"
            f"- Do NOT assume income level, food access, or safety conditions.\n"
            f"- If a constraint is not mentioned, describe it as 'not specified' rather than assuming.\n"
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
            "Include 1-3 habits max with clear triggers and rationale.\n"
            "\n"
            "GROUNDING RULES:\n"
            "- Habits MUST respect the user's SDOH constraints (budget, safety, time, food access).\n"
            "- Do NOT recommend expensive foods, gym memberships, or activities "
            "that conflict with the user's constraints.\n"
            "- Do NOT invent statistics about habit effectiveness.\n"
            "- Use the 'Retrieve Guidelines' tool if you need evidence for a recommendation.\n"
            "\n"
            "CITATION RULES:\n"
            "- If you reference a guideline for a habit recommendation, include it in 'citations'.\n"
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Structured HabitPlan JSON with practical habits and citations",
        output_pydantic=HabitPlan
    )


def safety_review_task(agent, context_tasks: list) -> Task:
    return Task(
        description=(
            "Review the response from the previous task for safety.\n"
            "Check for: diagnostic claims, medication/dosage advice, "
            "missing escalation for dangerous symptoms.\n"
            "Use the 'Retrieve Guidelines' tool to verify red flag handling. "
            "Consider using topic='red_flags' to find clinical safety guidance.\n"
            "\n"
            "CRITICAL: You MUST always include the complete habit plan from the "
            "previous task in your revised_response, even if no safety edits are needed. "
            "If the content is safe, copy the habit plan text into revised_response verbatim. "
            "If not safe, rewrite ONLY the unsafe parts while preserving the rest.\n"
            "The revised_response field must NEVER be null or empty.\n"
            "\n"
            "GROUNDING RULES:\n"
            "- Do NOT add medical claims, diagnoses, or statistics not in the original plan.\n"
            "- Do NOT invent safety concerns that aren't supported by guidelines.\n"
            "- Only flag issues that are genuinely dangerous or misleading.\n"
            "\n"
            "FORMATTING: When writing revised_response, use natural flowing paragraphs. "
            "Do NOT use bullet points, numbered lists, asterisks, or markdown bold/italic. "
            "Use short paragraphs (2-4 sentences) separated by blank lines. "
            "Keep a warm, conversational tone.\n"
            "\n"
            "CITATION RULES:\n"
            "- Preserve all citations from previous tasks.\n"
            "- If you add safety guidance from retrieved guidelines, include those citations too.\n"
        ),
        agent=agent,
        context=context_tasks,
        expected_output="Safety review with complete revised_response (never null) and preserved citations",
        output_pydantic=SafetyReview
    )

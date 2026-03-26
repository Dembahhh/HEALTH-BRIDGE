"""
Screening service module.

This module provides services related to the screening process,
including integration with AI components for generating summaries.
"""

import asyncio
from typing import Any, Dict, List

from crewai import Crew, Process, Task

from app.agents.agents import HealthBridgeAgents
from app.agents.models import HabitPlan, SafetyReview


async def generate_screening_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a clinical summary and habit plan using the AI agent pipeline.
    
    Args:
        context: A dictionary containing the screening context, including
            patient vitals, classifications, and practitioner notes.
            
    Returns:
        A dictionary with "summary", "referrals", and "habit_plan".
    """
    # TODO: The existing crew setup in app/agents/tasks.py and app/agents/crew.py
    # is deeply coupled to chat-based intake (expecting raw `user_input` to extract a Profile).
    # To properly run the full (Risk -> SDOH -> Habit -> Safety) pipeline for a clinical
    # screening, we need:
    # 1. A dedicated `screening_crew()` in crew.py.
    # 2. Structured tasks in tasks.py that accept BP/Glucose classifications natively
    #    rather than extracting them from user text.
    # For now, as per instruction, we bypass the early pipeline and call the Habit Coach
    # and Safety agents directly with the rich clinical context provided by the screening.
    
    agents = HealthBridgeAgents()
    coach = agents.habit_coach_agent()
    safety = agents.safety_policy_agent()

    # 1. Build a structured prompt/input from the context
    patient_info = (
        f"Name: {context.get('patient_name', 'Unknown')}\n"
        f"Age: {context.get('patient_age', 'Unknown')}\n"
        f"Sex: {context.get('patient_sex', 'Unknown')}\n"
    )
    
    bp_dict = context.get('bp_classification') or {}
    bp_info = f"Blood Pressure: {bp_dict.get('label', 'Unknown')} (Severity: {bp_dict.get('severity', 'Unknown')})"
    
    glucose_dict = context.get('glucose_classification')
    glucose_info = "Glucose: Not tested"
    if glucose_dict:
        glucose_info = f"Glucose: {glucose_dict.get('label', 'Unknown')} (Severity: {glucose_dict.get('severity', 'Unknown')})"

    practitioner = context.get('practitioner_role', 'Practitioner')
    notes = context.get('notes', 'None')

    structured_prompt = (
        f"You are reviewing a patient screening conducted by a {practitioner}.\n\n"
        f"## Patient Profile\n{patient_info}\n\n"
        f"## Clinical Classifications\n{bp_info}\n{glucose_info}\n\n"
        f"## Practitioner Notes\n{notes}\n\n"
        f"Based on this clinical screening, create a realistic 4-week tiny-habit plan. "
        f"Keep habits small, affordable, and safe. Since we bypassed the SDOH agent, assume "
        f"typical low-resource constraints unless notes specify otherwise.\n"
        f"Include 1-3 habits max with clear triggers and rationale."
    )

    # 2. Create ad-hoc tasks using existing agents
    t_plan = Task(
        description=structured_prompt,
        agent=coach,
        expected_output="Structured HabitPlan JSON matching the schema.",
        output_pydantic=HabitPlan,
    )

    t_safety = Task(
        description=(
            "Review the habit plan from the previous task for clinical safety.\n"
            "Ensure no diagnostic claims or medication dosing advice is present.\n"
            "If safe, copy the plan verbatim into revised_response. If unsafe, rewrite only the unsafe parts.\n"
            "CRITICAL: revised_response must never be empty."
        ),
        agent=safety,
        context=[t_plan],
        expected_output="Structured SafetyReview JSON with a safe habit plan.",
        output_pydantic=SafetyReview,
    )

    # 3. Trigger the agent pipeline (mini-crew)
    crew = Crew(
        agents=[coach, safety],
        tasks=[t_plan, t_safety],
        process=Process.sequential,
        verbose=True
    )
    
    # Run the crew in a thread since kickoff is blocking
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, crew.kickoff)
    
    # 4. Extract and format the return dict
    try:
        safety_review: SafetyReview = result.pydantic
        habit_plan_str = safety_review.revised_response or str(result.raw)
        flagged_issues = safety_review.flagged_issues
    except Exception:
        habit_plan_str = str(result.raw)
        flagged_issues = []

    referrals: List[str] = []
    if flagged_issues:
        referrals.append("Safety flagging notes: " + "; ".join(flagged_issues))
        referrals.append("Immediate clinical follow-up recommended based on safety review.")
        
    summary_text = (
        f"Screening Summary for {context.get('patient_name', 'Patient')}\n"
        f"-----------------------------------------\n"
        f"{bp_info}\n{glucose_info}\n\n"
        f"Clinical Notes: {notes}"
    )

    return {
        "summary": summary_text,
        "referrals": referrals,
        "habit_plan": habit_plan_str
    }


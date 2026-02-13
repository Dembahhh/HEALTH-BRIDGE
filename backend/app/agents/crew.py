"""
Crew Assembly

Assembles agents and tasks into Crews for different session types.
Includes ParallelIntakeOrchestrator for concurrent Risk + SDOH execution.
"""

import os
from crewai import Crew, Process, Task
from .agents import HealthBridgeAgents
from . import tasks
from .models import RiskAssessment, Constraints, HabitPlan, SafetyReview
from app.config.settings import settings

_verbose = os.getenv("AGENT_VERBOSE", "false").lower() == "true"


class HealthBridgeCrew:
    def __init__(self):
        self._agents = HealthBridgeAgents()

    # Monkey-patch to disable CrewAI's local SQLite storage (fixes disk full error)
    def _disable_crew_storage(self, crew_instance: Crew):
        if hasattr(crew_instance, '_task_output_handler'):
            class DummyStorage:
                def add(self, *args, **kwargs): pass
                def reset(self): pass
                def delete_all(self): pass
            
            # Replace the handler's storage with a dummy that does nothing
            if hasattr(crew_instance._task_output_handler, 'storage'):
                crew_instance._task_output_handler.storage = DummyStorage()
        return crew_instance

    def intake_crew(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """Full intake session: profile -> risk -> constraints -> plan -> safety."""

        # Agents
        intake = self._agents.intake_agent()
        risk = self._agents.risk_guideline_agent()
        context = self._agents.context_sdoh_agent()
        coach = self._agents.habit_coach_agent()
        safety = self._agents.safety_policy_agent()

        # Tasks (chained via context)
        t_intake = tasks.intake_task(intake, user_input, user_id, memory_context)
        t_risk = tasks.risk_assessment_task(risk, context_tasks=[t_intake], memory_context=memory_context)
        t_context = tasks.context_sdoh_task(context, user_input, user_id, memory_context)
        t_plan = tasks.habit_plan_task(coach, user_id, context_tasks=[t_risk, t_context])
        t_safety = tasks.safety_review_task(safety, context_tasks=[t_plan])

        return Crew(
            agents=[intake, risk, context, coach, safety],
            tasks=[t_intake, t_risk, t_context, t_plan, t_safety],
            process=Process.sequential,
            verbose=_verbose,
            tracing=settings.TRACING_ENABLED,
        )

    def follow_up_crew(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """Follow-up session: recall -> constraints update -> revised plan -> safety."""

        context = self._agents.context_sdoh_agent()
        coach = self._agents.habit_coach_agent()
        safety = self._agents.safety_policy_agent()

        t_context = tasks.context_sdoh_task(context, user_input, user_id, memory_context)
        t_plan = tasks.habit_plan_task(coach, user_id, context_tasks=[t_context])
        t_safety = tasks.safety_review_task(safety, context_tasks=[t_plan])

        return Crew(
            agents=[context, coach, safety],
            tasks=[t_context, t_plan, t_safety],
            process=Process.sequential,
            verbose=_verbose,
            tracing=settings.TRACING_ENABLED,
        )

    def general_crew(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """General questions: risk lookup -> safety check.

        When memory_context includes a '## Your Health Profile' section, the
        agent will reference the user's personal data to give a personalized
        answer instead of generic advice.
        """

        risk = self._agents.risk_guideline_agent()
        safety = self._agents.safety_policy_agent()

        t_risk = tasks.risk_assessment_task(risk, context_tasks=[], memory_context=memory_context)
        t_safety = tasks.safety_review_task(safety, context_tasks=[t_risk])

        # Build a profile-aware task description
        profile_instruction = ""
        if "## Your Health Profile" in memory_context:
            profile_instruction = (
                "IMPORTANT: The user has a health profile on file (included below). "
                "You MUST reference their specific profile data (age, BMI, family history, "
                "lifestyle factors, constraints) when answering. Do NOT give generic advice. "
                "Personalize your answer to THEIR situation.\n\n"
            )

        t_risk.description = (
            f"The user asked: '{user_input}'\n\n"
            f"{profile_instruction}"
            f"Use the 'Retrieve Guidelines' tool to find relevant information.\n"
            f"Provide an educational, non-diagnostic answer.\n\n"
            f"RESPONSE FORMAT: Write in natural, flowing paragraphs. Do NOT use bullet points, "
            f"numbered lists, asterisks, or markdown bold/italic formatting. Use short paragraphs "
            f"(2-4 sentences each) separated by blank lines. Weave profile data naturally into "
            f"sentences. Keep a warm, conversational tone.\n"
            f"\n{memory_context}"
        )

        return Crew(
            agents=[risk, safety],
            tasks=[t_risk, t_safety],
            process=Process.sequential,
            verbose=_verbose,
            tracing=settings.TRACING_ENABLED
        )


class ParallelIntakeOrchestrator:
    """Splits intake pipeline into 3 stages for parallel Risk + SDOH execution.

    Stage 1 (sequential): Intake -> Profile extraction
    Stage 2 (parallel):   Risk assessment + SDOH constraints (independent)
    Stage 3 (sequential): Habit plan -> Safety review

    Usage:
        orch = ParallelIntakeOrchestrator()
        profile_result = orch.stage1_intake(user_input, user_id, ctx).kickoff()
        # run stage2_risk and stage2_sdoh concurrently
        risk, sdoh = await asyncio.gather(
            loop.run_in_executor(None, orch.stage2_risk(profile_str, ctx).kickoff),
            loop.run_in_executor(None, orch.stage2_sdoh(user_input, user_id, ctx).kickoff),
        )
        final = orch.stage3_plan_safety(risk_str, sdoh_str, user_id).kickoff()
    """

    def __init__(self):
        self._agents = HealthBridgeAgents()

    def stage1_intake(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """Stage 1: Extract user profile from input."""
        intake = self._agents.intake_agent()
        t_intake = tasks.intake_task(intake, user_input, user_id, memory_context)
        return Crew(
            agents=[intake],
            tasks=[t_intake],
            process=Process.sequential,
            verbose=_verbose,
        )

    def stage2_risk(self, profile_output: str, memory_context: str = "") -> Crew:
        """Stage 2a: Risk assessment based on extracted profile."""
        risk = self._agents.risk_guideline_agent()
        t_risk = Task(
            description=(
                f"Using the following user profile, estimate hypertension and "
                f"diabetes risk bands based on WHO guidelines.\n"
                f"User Profile:\n{profile_output}\n\n"
                f"Use the 'Retrieve Guidelines' tool to look up relevant risk tables. "
                f"You can specify condition='hypertension' or condition='diabetes' to focus your search.\n"
                f"Do NOT diagnose. Only estimate risk bands: low, moderate, or high.\n"
                f"\n{memory_context}"
            ),
            agent=risk,
            expected_output="Structured RiskAssessment JSON matching the schema",
            output_pydantic=RiskAssessment,
        )
        return Crew(
            agents=[risk],
            tasks=[t_risk],
            process=Process.sequential,
            verbose=_verbose,
        )

    def stage2_sdoh(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """Stage 2b: SDOH constraints analysis (independent of profile)."""
        context = self._agents.context_sdoh_agent()
        t_context = tasks.context_sdoh_task(context, user_input, user_id, memory_context)
        return Crew(
            agents=[context],
            tasks=[t_context],
            process=Process.sequential,
            verbose=_verbose,
        )

    def stage3_plan_safety(
        self, risk_output: str, sdoh_output: str, user_id: str
    ) -> Crew:
        """Stage 3: Generate habit plan + safety review using combined results."""
        coach = self._agents.habit_coach_agent()
        safety = self._agents.safety_policy_agent()

        t_plan = Task(
            description=(
                f"Create a realistic 4-week tiny-habit plan based on the following:\n\n"
                f"## Risk Assessment\n{risk_output}\n\n"
                f"## SDOH Constraints\n{sdoh_output}\n\n"
                f"Keep habits small, affordable, and safe for the user's context.\n"
                f"Use user_id '{user_id}' when recalling user memories for personalization.\n"
                f"Include 1-3 habits max with clear triggers and rationale."
            ),
            agent=coach,
            expected_output="Structured HabitPlan JSON matching the schema",
            output_pydantic=HabitPlan,
        )
        t_safety = tasks.safety_review_task(safety, context_tasks=[t_plan])

        return Crew(
            agents=[coach, safety],
            tasks=[t_plan, t_safety],
            process=Process.sequential,
            verbose=_verbose,
        )

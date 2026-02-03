"""
Crew Assembly

Assembles agents and tasks into Crews for different session types.
"""

from crewai import Crew, Process
from .agents import HealthBridgeAgents
from . import tasks


class HealthBridgeCrew:
    def __init__(self):
        self._agents = HealthBridgeAgents()

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
            verbose=True
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
            verbose=True
        )

    def general_crew(self, user_input: str, user_id: str, memory_context: str = "") -> Crew:
        """General questions: risk lookup -> safety check."""

        risk = self._agents.risk_guideline_agent()
        safety = self._agents.safety_policy_agent()

        t_risk = tasks.risk_assessment_task(risk, context_tasks=[], memory_context=memory_context)
        t_safety = tasks.safety_review_task(safety, context_tasks=[t_risk])

        # Override descriptions for general questions
        t_risk.description = (
            f"The user asked: '{user_input}'\n"
            f"Use the 'Retrieve Guidelines' tool to find relevant information.\n"
            f"Provide an educational, non-diagnostic answer.\n"
            f"\n{memory_context}"
        )

        return Crew(
            agents=[risk, safety],
            tasks=[t_risk, t_safety],
            process=Process.sequential,
            verbose=True,
            tracing=True
        )

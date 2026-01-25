from crewai import Crew, Task, Process
from app.agents.agents import HealthBridgeAgents
from app.agents.models import Profile, RiskAssessment, Constraints, HabitPlan, SafetyReview
from typing import Dict, Any

class ChatService:
    def __init__(self):
        self.agents = HealthBridgeAgents()

    def run_intake_session(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        Runs the full intake -> plan flow. 
        In a real production app, this would be broken down or state-managed.
        For now, we run the full chain on the initial input.
        """
        
        # Instantiate Agents
        intake_agent = self.agents.intake_agent()
        risk_agent = self.agents.risk_guideline_agent()
        context_agent = self.agents.context_sdoh_agent()
        habit_agent = self.agents.habit_coach_agent()
        safety_agent = self.agents.safety_policy_agent()

        # Define Tasks
        # 1. Intake
        task_intake = Task(
            description=f"Analyze the user input: '{user_input}'. Extract age, sex, activity level, etc. If missing, make reasonable assumptions or note as missing.",
            agent=intake_agent,
            expected_output="Structured Profile JSON"
        )

        # 2. Risk
        task_risk = Task(
            description="Based on the Profile, estimate hypertension/diabetes risk bands using WHO guidelines.",
            agent=risk_agent,
            context=[task_intake],
            expected_output="Structured RiskAssessment JSON"
        )

        # 3. Context - includes user_id for memory tools
        task_context = Task(
            description=(
                f"Analyze the user input '{user_input}' for social/environmental constraints (money, time, safety). "
                f"Use user_id '{{user_id}}' when saving constraints or recalling memories."
            ),
            agent=context_agent,
            expected_output="Structured Constraints JSON"
        )

        # 4. Plan - includes user_id for memory recall
        task_plan = Task(
            description=(
                "Create a 4-week tiny habit plan based on Risk and Constraints. Keep it very simple. "
                "Use user_id '{user_id}' when recalling user memories for personalization."
            ),
            agent=habit_agent,
            context=[task_risk, task_context],
            expected_output="Structured HabitPlan JSON"
        )

        # 5. Safety
        task_safety = Task(
            description="Review the Habit Plan. Ensure no diagnosis claims. Ensure safety.",
            agent=safety_agent,
            context=[task_plan],
            expected_output="Final safe response text"
        )

        # Create Crew
        health_crew = Crew(
            agents=[intake_agent, risk_agent, context_agent, habit_agent, safety_agent],
            tasks=[task_intake, task_risk, task_context, task_plan, task_safety],
            process=Process.sequential,
            verbose=True
        )

        # Kickoff with user_id input for interpolation
        result = health_crew.kickoff(inputs={"user_id": user_id})
        return result

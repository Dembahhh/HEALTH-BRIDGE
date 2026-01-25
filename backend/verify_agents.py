import os
os.environ["OPENAI_API_KEY"] = "sk-proj-dummy-key-for-testing-agents-initialization-only"
from app.agents.agents import HealthBridgeAgents


def test_agents():
    agents = HealthBridgeAgents()
    
    print("Initializing Intake Agent...")
    intake = agents.intake_agent()
    print(f"Success: {intake.role}")

    print("Initializing Risk Agent...")
    risk = agents.risk_guideline_agent()
    print(f"Success: {risk.role}")

    print("Initializing Context Agent...")
    context = agents.context_sdoh_agent()
    print(f"Success: {context.role}")

    print("Initializing Habit Agent...")
    habit = agents.habit_coach_agent()
    print(f"Success: {habit.role}")

    print("Initializing Safety Agent...")
    safety = agents.safety_policy_agent()
    print(f"Success: {safety.role}")

if __name__ == "__main__":
    test_agents()

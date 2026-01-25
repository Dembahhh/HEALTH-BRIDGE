from crewai import Agent, LLM
from .models import Profile, RiskAssessment, Constraints, HabitPlan, SafetyReview
from .tools import retrieve_guidelines, recall_memory, save_constraint

class HealthBridgeAgents:
    def __init__(self):
        # Configure Gemini LLM for all agents
        self.llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7
        )
    def intake_agent(self):
        return Agent(
            role='Intake Specialist',
            goal='Collect a minimal but sufficient health profile from the user',
            backstory=(
                "You are an empathetic health intake assistant. Your job is to ask simple, "
                "culturally relevant questions to understand a user's health context "
                "(age, activity, diet, history) without being overwhelming."
            ),
            allow_delegation=False,
            verbose=True,
            llm=self.llm
        )

    def risk_guideline_agent(self):
        return Agent(
            role='Medical Guideline Researcher',
            goal='Estimate health risk bands based on WHO and local guidelines',
            backstory=(
                "You are a strict, guideline-focused researcher. You do NOT diagnose. "
                "You look at the user's profile and compare it against established "
                "risk tables for hypertension and diabetes to estimate a risk band."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[retrieve_guidelines],
            llm=self.llm
        )

    def context_sdoh_agent(self):
        return Agent(
            role='Social Context Analyst',
            goal='Identify environmental and social constraints that affect health behavior',
            backstory=(
                "You understand the reality of life in low-resource settings. "
                "You look for constraints like 'unsafe to walk at night', 'cannot afford gym', "
                "or 'works double shifts'. You ensure advice is grounded in reality."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[save_constraint, recall_memory],
            llm=self.llm
        )

    def habit_coach_agent(self):
        return Agent(
            role='Behavioral Health Coach',
            goal='Design a realistic 4-week tiny-habit plan',
            backstory=(
                "You are a motivating and practical coach. You take the medical risk "
                "and the social constraints, and you craft a plan that is 'tiny' enough "
                "to succeed. You never suggest things the user cannot afford or do safely."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[recall_memory],
            llm=self.llm
        )

    def safety_policy_agent(self):
        return Agent(
            role='Clinical Safety Officer',
            goal='Ensure all advice is safe, non-diagnostic, and appropriate',
            backstory=(
                "You are the final checkpoint. You scan outgoing messages for red flags: "
                "diagnostic claims ('You have diabetes'), dosage advice, or missing escalation "
                "for dangerous symptoms. You rewrite anything unsafe."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[retrieve_guidelines],
            llm=self.llm
        )

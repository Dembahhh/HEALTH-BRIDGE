import os
from crewai import Agent, LLM
# from .models import Profile, RiskAssessment, Constraints, HabitPlan, SafetyReview  # TODO: Use with output_pydantic
from .tools import retrieve_guidelines, recall_memory, save_constraint

class HealthBridgeAgents:
    def __init__(self):
        # Configure LLM from environment
        provider = os.getenv("LLM_PROVIDER", "github")
        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
        temperature = float(os.getenv("LLM_TEMPERATURE", "1.0"))
        
        # Support for different providers
        api_key = None
        base_url = None
        
        if provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = os.getenv("GITHUB_BASE_URL", "https://models.github.ai/inference")
        elif provider == "azure":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")

        self.llm = LLM(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url
        )
    def intake_agent(self):
        return Agent(
            role='Intake Specialist',
            goal='Collect a minimal but sufficient health profile (age, sex, BMI category, activity, diet, history, smoking/alcohol)',
            backstory=(
                "You are an empathetic health intake assistant specialized in African contexts. "
                "Your job is to identify a user's health profile by asking simple, culturally relevant questions. "
                "You must collect: age, sex, rough weight/BMI category, activity level, diet patterns, "
                "family history of hypertension/diabetes, smoking status, and alcohol consumption."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[],
            llm=self.llm
        )

    def risk_guideline_agent(self):
        return Agent(
            role='Medical Guideline Researcher',
            goal='Estimate hypertension and diabetes risk bands based on WHO and MoH guidelines',
            backstory=(
                "You are a strict, guideline-focused researcher. You do NOT diagnose. "
                "You use RAG to search WHO and Ministry of Health guidelines to compare "
                "user profiles against established risk tables. You output ESTIMATED risk bands "
                "(low, moderate, high) and identify key drivers like family history or salt intake."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[retrieve_guidelines],
            llm=self.llm
        )

    def context_sdoh_agent(self):
        return Agent(
            role='Social Context Analyst',
            goal='Identify environmental (SDOH) constraints: food access, exercise safety, time, and finance',
            backstory=(
                "You understand the reality of life in low-resource African settings. "
                "You look for Social Determinants of Health (SDOH) like neighborhood safety for exercise, "
                "access to fresh vs processed food, time constraints due to long work shifts, "
                "and financial limitations for clinic visits or healthy food. "
                "You ensure all advice is grounded in these real-world constraints."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[save_constraint, recall_memory],
            llm=self.llm
        )

    def habit_coach_agent(self):
        return Agent(
            role='Behavioral Health Coach',
            goal='Design realistic 4-week tiny-habit plans based on risk, context, and past memory',
            backstory=(
                "You are a motivating and practical coach. You design 4-week plans with 1-3 tiny habits "
                "that are small enough to succeed. You take the medical risk and social constraints "
                "into account. You use semantic memory to recall what worked or failed in the past "
                "and adapt the plan accordingly. You focus on simple triggers and motivational framing."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[recall_memory],
            llm=self.llm
        )

    def safety_policy_agent(self):
        return Agent(
            role='Clinical Safety Officer',
            goal='Enforce safety rules: no diagnosis, no dosing, and clear clinician escalation',
            backstory=(
                "You are the final checkpoint for safety. You scan responses for diagnostic claims "
                "('You have diabetes'), medication dosage advice, or missing escalation for red-flag "
                "symptoms (e.g. chest pain, blurred vision). You ensure the language is firm but "
                "non-alarming, always recommending in-person clinical care when necessary."
            ),
            allow_delegation=False,
            verbose=True,
            tools=[retrieve_guidelines],
            llm=self.llm
        )

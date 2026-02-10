import logging
from crewai import Agent, LLM
from app.config.settings import settings
from .tools import retrieve_guidelines, recall_memory, save_constraint

logger = logging.getLogger(__name__)


class HealthBridgeAgents:
    def __init__(self):
        # Read configuration from the validated Settings singleton
        provider = settings.LLM_PROVIDER
        model = settings.LLM_MODEL
        temperature = settings.LLM_TEMPERATURE

        # Verbosity control
        self._verbose = settings.DEBUG

        # Support for different providers
        api_key = None
        base_url = None

        if provider == "groq":
            api_key = settings.GROQ_API_KEY
            base_url = "https://api.groq.com/openai/v1"
            if model == "openai/gpt-4o-mini":
                model = "llama-3.3-70b-versatile"
        elif provider == "gemini":
            api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        elif provider == "github":
            api_key = settings.GITHUB_TOKEN
            base_url = settings.GITHUB_BASE_URL
        elif provider == "azure":
            api_key = settings.AZURE_OPENAI_API_KEY
        elif provider == "openai":
            api_key = settings.OPENAI_API_KEY

        # Validate API key is present
        if not api_key:
            env_var_map = {
                "groq": "GROQ_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "github": "GITHUB_TOKEN",
                "azure": "AZURE_OPENAI_API_KEY",
                "openai": "OPENAI_API_KEY",
            }
            expected_var = env_var_map.get(provider, "UNKNOWN")
            raise ValueError(
                f"No API key found for provider '{provider}'. "
                f"Set the {expected_var} environment variable in .env"
            )

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
            verbose=self._verbose,
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
            verbose=self._verbose,
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
            verbose=self._verbose,
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
            verbose=self._verbose,
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
            verbose=self._verbose,
            tools=[retrieve_guidelines],
            llm=self.llm
        )

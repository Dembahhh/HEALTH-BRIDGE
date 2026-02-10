"""
Chat Orchestrator

Bridges the API layer with SessionManager + ChatService.
Manages per-session state and routes messages through the multi-agent pipeline.
Fetches user HealthProfile for personalized responses and classifies question types.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from uuid import uuid4

from app.models.profile import HealthProfile
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Thread pool for blocking CrewAI calls
_executor = ThreadPoolExecutor(max_workers=3)


class ChatOrchestrator:
    """
    Manages active chat sessions and routes messages through
    the SessionManager (multi-turn collection) and ChatService (crew execution).
    """

    def __init__(self):
        from app.services.chat import ChatService
        self._sessions: Dict[str, SessionManager] = {}
        self._chat_service = ChatService()

    def _get_or_create_session(
        self, user_id: str, session_id: str, session_type: str
    ) -> SessionManager:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionManager(
                user_id=user_id,
                session_type=session_type,
                use_llm=True,
            )
        return self._sessions[session_id]

    # ------------------------------------------------------------------
    # Profile & Question Classification
    # ------------------------------------------------------------------

    @staticmethod
    def _build_profile_summary(profile: HealthProfile) -> str:
        """Format a HealthProfile object as a readable summary string.

        Only includes fields the user has explicitly provided (non-None).
        This prevents the LLM from treating default values as user-provided data.
        """
        parts = ["## Your Health Profile"]

        if profile.age_band:
            parts.append(f"- Age group: {profile.age_band}")
        if profile.sex:
            parts.append(f"- Sex: {profile.sex}")
        if profile.bmi_category is not None:
            parts.append(f"- BMI category: {profile.bmi_category}")
        if profile.activity_level is not None:
            parts.append(f"- Activity level: {profile.activity_level}")
        if profile.diet_pattern is not None:
            parts.append(f"- Diet pattern: {profile.diet_pattern}")
        if profile.smoking_status is not None:
            parts.append(f"- Smoking status: {profile.smoking_status}")
        if profile.alcohol_consumption is not None:
            parts.append(f"- Alcohol consumption: {profile.alcohol_consumption}")
        if profile.family_history_hypertension is not None:
            parts.append(
                f"- Family history of hypertension: "
                f"{'Yes' if profile.family_history_hypertension else 'No'}"
            )
        if profile.family_history_diabetes is not None:
            parts.append(
                f"- Family history of diabetes: "
                f"{'Yes' if profile.family_history_diabetes else 'No'}"
            )

        if profile.risk_bands:
            parts.append(f"- Risk assessment: {profile.risk_bands}")
        if profile.top_risk_factors:
            parts.append(f"- Top risk factors: {', '.join(profile.top_risk_factors)}")

        if profile.constraints:
            c = profile.constraints
            if c.exercise_safety is not None:
                parts.append(f"- Exercise safety: {c.exercise_safety}")
            if c.income_band is not None:
                parts.append(f"- Income band: {c.income_band}")
            if c.food_access is not None:
                parts.append(f"- Food access: {c.food_access}")
            if c.time_availability is not None:
                parts.append(f"- Time availability: {c.time_availability}")
            if c.additional_notes:
                parts.append(f"- Additional notes: {c.additional_notes}")

        # If only the header was added, the user has no profile data yet
        if len(parts) == 1:
            return ""

        return "\n".join(parts)

    @staticmethod
    async def _fetch_profile_summary(user_id: str) -> str:
        """Fetch the user's HealthProfile and return a formatted summary string."""
        try:
            profile = await HealthProfile.find_one(HealthProfile.user_id == user_id)
            if not profile:
                return ""
            return ChatOrchestrator._build_profile_summary(profile)
        except Exception as e:
            logger.warning("Failed to fetch profile for user %s: %s", user_id, e)
            return ""

    @staticmethod
    async def _fetch_profile_and_history(
        user_id: str, history_limit: int = 10
    ) -> tuple:
        """Fetch profile summary, conversation history, and the profile object itself.

        Returns:
            (summary_str, history_list, profile_object_or_None)
        """
        try:
            profile = await HealthProfile.find_one(HealthProfile.user_id == user_id)
            if not profile:
                return ("", [], None)
            summary = ChatOrchestrator._build_profile_summary(profile)
            history = profile.get_history_for_llm(max_entries=history_limit)
            return (summary, history, profile)
        except Exception as e:
            logger.warning("Failed to fetch profile+history for user %s: %s", user_id, e)
            return ("", [], None)

    @staticmethod
    def _classify_question(message: str) -> str:
        """Classify user question to select the right response strategy.

        Returns one of: emergency, risk_assessment, personalized,
        lifestyle, general_health.
        """
        text = message.lower()

        # Emergency / urgent symptoms
        emergency_terms = [
            "chest pain", "can't breathe", "cannot breathe",
            "blurred vision", "stroke", "fainting", "severe headache",
            "numbness", "paralysis", "heart attack",
        ]
        if any(t in text for t in emergency_terms):
            return "emergency"

        # Personal risk assessment (needs profile)
        risk_terms = [
            "my risk", "my chances", "am i at risk", "risk for",
            "risk of", "likely to get", "probability", "susceptible",
            "predisposed", "using my profile", "based on my",
            "according to my", "do i have risk", "what are my risk",
        ]
        if any(t in text for t in risk_terms):
            return "risk_assessment"

        # Profile-based personalized questions
        personal_terms = [
            "for me", "should i", "my health", "my diet", "my exercise",
            "my condition", "my situation", "recommend for me",
            "personalize", "specific to me", "in my case", "given my",
            "based on my profile", "my body",
        ]
        if any(t in text for t in personal_terms):
            return "personalized"

        # Lifestyle / habit questions
        lifestyle_terms = [
            "how to exercise", "what to eat", "diet plan", "meal plan",
            "workout", "lose weight", "gain weight", "sleep better",
            "reduce stress", "habit", "routine", "food",
        ]
        if any(t in text for t in lifestyle_terms):
            return "lifestyle"

        # Default: general health education
        return "general_health"

    @staticmethod
    def _build_system_prompt(question_type: str, profile_summary: str) -> str:
        """Build a system prompt tailored to the question type and user profile."""
        base = (
            "You are a friendly, knowledgeable health coach for preventive health "
            "(hypertension and type 2 diabetes) in African settings. "
            "NEVER diagnose or prescribe medication. "
            "If the user describes urgent symptoms (chest pain, stroke signs), "
            "tell them to seek emergency care immediately.\n\n"
        )

        # Formatting rules applied to every response
        formatting = (
            "RESPONSE FORMAT RULES (follow strictly):\n"
            "- Write in natural, flowing paragraphs. Do NOT use bullet points, "
            "numbered lists, asterisks, or markdown bold/italic formatting.\n"
            "- Use short paragraphs (2-4 sentences each) separated by blank lines.\n"
            "- When mentioning the user's profile data, weave it naturally into "
            "sentences rather than listing it.\n"
            "- Keep a warm, conversational tone as if speaking to the user face-to-face.\n"
            "- End with a brief encouraging closing thought or next step.\n\n"
        )

        if question_type == "emergency":
            return base + formatting + (
                "The user may be describing urgent symptoms. "
                "Prioritize their safety. Tell them to seek immediate medical attention. "
                "Be calm but firm. Do NOT provide medical diagnosis."
            )

        if question_type == "risk_assessment" and profile_summary:
            return base + formatting + (
                "The user is asking about their personal health risks. "
                "Use their health profile below to provide a PERSONALIZED risk assessment. "
                "Reference their specific profile data (age, BMI, family history, lifestyle) "
                "when explaining risk factors. Be specific about which of THEIR factors "
                "increase or decrease risk. Do NOT give generic advice.\n\n"
                f"{profile_summary}\n\n"
                "Cover the following in natural paragraphs (not as a list):\n"
                "- Start by acknowledging their specific profile factors relevant to the question.\n"
                "- Discuss which of their factors increase risk and why.\n"
                "- Mention which of their factors are protective.\n"
                "- Offer personalized, actionable recommendations based on their constraints.\n"
                "- Close by recommending professional consultation for a definitive assessment."
            )

        if question_type == "personalized" and profile_summary:
            return base + formatting + (
                "The user is asking for personalized health advice. "
                "Use their health profile below to tailor your response. "
                "Reference their specific situation, constraints, and history. "
                "Make recommendations practical given their SDOH constraints.\n\n"
                f"{profile_summary}\n\n"
                "Always tie your advice back to their specific profile data."
            )

        if question_type == "lifestyle":
            if profile_summary:
                return base + formatting + (
                    "The user is asking about lifestyle and habits. "
                    "Use their health profile below to personalize your advice. "
                    "Consider their activity level, diet pattern, time availability, "
                    "and food access when making recommendations.\n\n"
                    f"{profile_summary}\n\n"
                    "Give practical, affordable, and culturally relevant suggestions."
                )
            return base + formatting + (
                "The user is asking about lifestyle and habits. "
                "Give practical, affordable, and culturally relevant suggestions "
                "for preventive health in African settings."
            )

        # general_health - educational
        if profile_summary:
            return base + formatting + (
                "The user is asking a general health question. "
                "Provide educational information and, where relevant, "
                "relate it to their personal profile below.\n\n"
                f"{profile_summary}\n\n"
                "Give concise, evidence-based answers."
            )

        return base + formatting + "Give concise, practical, culturally sensitive advice."

    # ------------------------------------------------------------------
    # Message Processing
    # ------------------------------------------------------------------

    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        session_type: str = "general",
    ) -> Dict:
        """
        Process a user message through the full multi-agent pipeline.

        Flow:
        1. SessionManager collects info across turns
        2. When ready, ChatService runs the CrewAI crew
        3. Returns the final response

        Returns:
            dict with 'content' and optional 'agent_name'
        """
        manager = self._get_or_create_session(user_id, session_id, session_type)

        # Run SessionManager.process_message (blocking LLM extraction)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, manager.process_message, message
        )

        if result.has_urgent_symptoms:
            return {"content": result.response, "agent_name": "safety"}

        if not result.ready_for_crew:
            # Still collecting info - return the follow-up question
            return {"content": result.response, "agent_name": "collector"}

        # Ready for crew execution
        context = manager.get_session_context()
        combined_input = context["combined_input"]
        detected_fields = context["collected_fields"]
        crew_session_type = context["session_type"]

        # Fetch profile + history for personalized crew context
        profile_summary, _conv_history, profile = await self._fetch_profile_and_history(user_id)

        crew_result = await loop.run_in_executor(
            _executor,
            self._chat_service.run_session,
            combined_input,
            user_id,
            crew_session_type,
            detected_fields,
            [message],
            profile_summary,
        )

        # Complete the session in the manager
        final_response = manager.complete_session(crew_result)

        # Persist conversation entry on the profile
        try:
            if profile is None:
                profile = HealthProfile(user_id=user_id)
            profile.append_conversation(message, final_response, "crew")
            await profile.save()
        except Exception as save_err:
            logger.warning("Failed to save conversation history (crew): %s", save_err)

        # Clean up finished session
        self._sessions.pop(session_id, None)

        return {"content": final_response, "agent_name": "crew"}

    async def quick_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> Dict:
        """
        Quick single-turn response via a direct LLM call (no crew pipeline).

        Targets 2-5s response time instead of 30-60s for a full crew run.
        Fetches the user's HealthProfile and classifies the question type
        to deliver personalized, context-aware responses.
        Injects cross-session conversation history for continuity.
        """
        loop = asyncio.get_event_loop()

        try:
            # Fetch profile, conversation history, and classify question
            profile_summary, conv_history, profile = await self._fetch_profile_and_history(user_id)
            question_type = self._classify_question(message)

            logger.info(
                "Quick message: user=%s question_type=%s has_profile=%s history_len=%d",
                user_id, question_type, bool(profile_summary), len(conv_history) // 2,
            )

            response = await loop.run_in_executor(
                _executor,
                self._direct_llm_call,
                message,
                user_id,
                profile_summary,
                question_type,
                conv_history,
            )

            # Persist conversation entry on the profile
            try:
                if profile is None:
                    # First-time user — create a new HealthProfile with this exchange
                    profile = HealthProfile(user_id=user_id)
                profile.append_conversation(message, response, question_type)
                await profile.save()
            except Exception as save_err:
                logger.warning("Failed to save conversation history: %s", save_err)

            return {"content": response, "agent_name": f"quick:{question_type}"}
        except Exception as e:
            logger.error("Quick message error: %s", e, exc_info=True)
            return {
                "content": "I'm sorry, I had trouble processing that. Could you try rephrasing your question?",
                "agent_name": "system",
            }

    @staticmethod
    def _direct_llm_call(
        message: str,
        user_id: str,
        profile_summary: str = "",
        question_type: str = "general_health",
        conversation_history: list = None,
    ) -> str:
        """Single LLM call with profile-aware, question-typed system prompt and conversation history."""
        import os

        provider = os.getenv("LLM_PROVIDER", "github")

        system_prompt = ChatOrchestrator._build_system_prompt(
            question_type, profile_summary
        )

        if provider == "gemini":
            return ChatOrchestrator._gemini_call(message, system_prompt, conversation_history)
        else:
            return ChatOrchestrator._openai_compatible_call(
                message, system_prompt, provider, conversation_history
            )

    @staticmethod
    def _gemini_call(
        message: str, system_prompt: str, conversation_history: list = None
    ) -> str:
        """Direct Gemini call via the new google.genai SDK with optional conversation history."""
        import os
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)

        # Build contents list: history entries + current message
        # Gemini uses "model" instead of "assistant"
        contents = []
        if conversation_history:
            for msg in conversation_history:
                role = "model" if msg["role"] == "assistant" else msg["role"]
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])],
                ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=message)],
        ))

        logger.info(
            "[Gemini] Sending request to gemini-2.0-flash-lite (history=%d msgs)...",
            len(contents) - 1,
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
                max_output_tokens=1024,
            ),
        )

        text = response.text
        logger.info("[Gemini] Response received (%d chars)", len(text))
        return text

    @staticmethod
    def _openai_compatible_call(
        message: str, system_prompt: str, provider: str, conversation_history: list = None
    ) -> str:
        """Fallback for OpenAI-compatible providers (GitHub, OpenAI) with optional conversation history."""
        import os
        import httpx

        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
            # Groq doesn't have OpenAI models — force a compatible model
            if model.startswith("openai/") or model.startswith("gpt"):
                model = "llama-3.3-70b-versatile"
        elif provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = os.getenv("GITHUB_BASE_URL", "https://models.github.ai/inference")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = "https://api.openai.com/v1"
        else:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GITHUB_TOKEN")
            base_url = os.getenv("GITHUB_BASE_URL", "https://models.github.ai/inference")

        # Build messages: system → history → current user message
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        logger.info(
            "[%s] Sending request to %s (history=%d msgs)...",
            provider.upper(), model, len(messages) - 2,
        )

        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.4,
                "max_tokens": 1024,
                "messages": messages,
            },
            timeout=25.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        logger.info("[%s] Response received (%d chars)", provider.upper(), len(text))
        return text

    def remove_session(self, session_id: str):
        """Remove a session from the in-memory cache."""
        self._sessions.pop(session_id, None)


# Singleton
_orchestrator: Optional[ChatOrchestrator] = None


def get_orchestrator() -> ChatOrchestrator:
    """Get the singleton ChatOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator()
    return _orchestrator

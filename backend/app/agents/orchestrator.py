"""
Chat Orchestrator

Bridges the API layer with SessionManager + ChatService.
Manages per-session state and routes messages through the multi-agent pipeline.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.session_manager import SessionManager
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

# Thread pool for blocking CrewAI calls
_executor = ThreadPoolExecutor(max_workers=3)


class ChatOrchestrator:
    """
    Manages active chat sessions and routes messages through
    the SessionManager (multi-turn collection) and ChatService (crew execution).
    """

    def __init__(self):
        self._sessions: Dict[str, SessionManager] = {}
        self._chat_service = ChatService()
        # Per-session conversation history for quick chat (keeps last N exchanges)
        self._quick_history: Dict[str, List[dict]] = {}

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

    @staticmethod
    def _classify_intent(message: str) -> str:
        """Classify user intent to route to quick or full pipeline.
        
        Returns:
            'quick' for simple questions (educational, FAQs)
            'full' for complex requests (intake, risk assessment, habit planning)
        """
        text = message.lower().strip()
        
        # Full pipeline signals — personal health data or action requests
        full_signals = [
            "i am", "i'm", "years old", "my age", "my weight", "i smoke",
            "i drink", "my diet", "family history", "assess me", "check my risk",
            "create a plan", "habit plan", "my health", "i weigh", "bmi",
            "follow up", "follow-up", "progress", "update my", "check in",
        ]
        
        # Quick signals — educational, simple questions
        quick_signals = [
            "what is", "what are", "how does", "tell me about", "explain",
            "define", "difference between", "why is", "can you", "should i",
            "is it", "how to", "tips for", "benefits of",
        ]
        
        if any(signal in text for signal in full_signals):
            return "full"
        if any(signal in text for signal in quick_signals):
            return "quick"
        
        # Default: if message is short (<20 words), quick; otherwise full
        if len(text.split()) < 20:
            return "quick"
        return "full"

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

        crew_result = await loop.run_in_executor(
            _executor,
            self._chat_service.run_session,
            combined_input,
            user_id,
            crew_session_type,
            detected_fields,
            [message],
        )

        # Complete the session in the manager
        final_response = manager.complete_session(crew_result)

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
        Now includes conversation history and memory recall for context.
        """
        loop = asyncio.get_event_loop()

        # Get or create conversation history for this session
        history = self._quick_history.get(session_id, [])

        try:
            response = await loop.run_in_executor(
                _executor, self._direct_llm_call, message, user_id, history
            )
            # Save to history (keep last 10 exchanges = 20 messages)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            self._quick_history[session_id] = history[-20:]

            return {"content": response, "agent_name": "quick"}
        except Exception as e:
            logger.error("Quick message error: %s", e, exc_info=True)
            return {
                "content": "I'm sorry, I had trouble processing that. Could you try rephrasing your question?",
                "agent_name": "system",
            }

    @staticmethod
    def _direct_llm_call(
        message: str, user_id: str, history: List[dict] = None
    ) -> str:
        """Single LLM call via httpx — no CrewAI overhead.

        Includes:
        - Memory recall for user context (profile, past habits)
        - Conversation history for multi-turn continuity
        """
        import os
        import httpx

        provider = os.getenv("LLM_PROVIDER", "github")
        model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

        if provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            base_url = os.getenv("GITHUB_BASE_URL", "https://models.github.ai/inference")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = "https://api.openai.com/v1"
        else:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GITHUB_TOKEN")
            base_url = os.getenv("GITHUB_BASE_URL", "https://models.github.ai/inference")

        # Recall relevant memories for personalisation
        memory_context = ""
        try:
            from app.core.memory.semantic_memory import SemanticMemory
            mem = SemanticMemory()
            recent = mem.recall_memories(user_id, message, k=3)
            if recent:
                snippets = [m["text"][:120] for m in recent]
                memory_context = (
                    "\n\nUser history (use this to personalise your response):\n"
                    + "\n".join(f"- {s}" for s in snippets)
                )
        except Exception as exc:
            logger.debug("Memory recall skipped in quick chat: %s", exc)

        system_prompt = (
            "You are a friendly, knowledgeable health coach for preventive health "
            "(hypertension and type 2 diabetes) in African settings. "
            "Give concise, practical, culturally sensitive advice. "
            "NEVER diagnose or prescribe medication. "
            "If the user describes urgent symptoms (chest pain, stroke signs), "
            "tell them to seek emergency care immediately."
            + memory_context
        )

        # Build messages array with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            # Include last 5 exchanges (10 messages) for context
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})

        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.3,
                "max_tokens": 1024,
                "messages": messages,
            },
            timeout=25.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

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

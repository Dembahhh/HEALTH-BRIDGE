from opik import track
from app.agents.crew import HealthBridgeCrew
from app.services.input_collector import InputCollector
from typing import Dict, Any, List
import json
import re


class ChatServiceResult:
    """Structured result from chat service."""

    def __init__(self, raw_result, user_id: str):
        self.raw_result = str(raw_result)
        self.user_id = user_id

        # Extract structured data from pydantic output if available
        self.pydantic_output = getattr(raw_result, 'pydantic', None)
        self.habits = self._extract_habits()

    def _extract_habits(self) -> list:
        """Extract habits from structured output or raw text."""
        # If SafetyReview pydantic output is available
        if self.pydantic_output and hasattr(self.pydantic_output, 'revised_response'):
            pass

        # Try JSON extraction from raw text
        json_match = re.search(r'\{[\s\S]*"habits"[\s\S]*\}', self.raw_result)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "habits" in data:
                    return data["habits"]
            except json.JSONDecodeError:
                pass

        # Fallback: extract bullet points
        habits = []
        for line in self.raw_result.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•')) and len(line) > 10:
                habit_text = line.lstrip('-*• ').strip()
                if any(w in habit_text.lower() for w in ['walk', 'eat', 'drink', 'sleep', 'exercise', 'reduce', 'add', 'avoid']):
                    habits.append({
                        "title": habit_text[:50],
                        "description": habit_text,
                        "frequency": "daily",
                        "category": "general",
                        "difficulty": "easy"
                    })
        return habits[:3]

    def __str__(self):
        return self.raw_result


class ChatService:
    def __init__(self):
        self.crew = HealthBridgeCrew()
        self._memory = None
        self.collector = InputCollector()

    def assess_input(
        self,
        messages: List[str],
        session_type: str,
        user_habits: List[str] = None,
    ) -> Dict:
        """Check if accumulated input is sufficient before running the crew.

        Args:
            messages: List of user messages collected so far.
            session_type: One of "intake", "follow_up", "general".
            user_habits: For follow_up sessions, list of user's existing habits.

        Returns a dict with ``ready`` (bool), and either ``combined_input``
        (when ready) or ``question`` (the next question to ask when not ready).
        """
        return self.collector.assess(messages, session_type, user_habits)

    def _get_memory(self):
        """Lazy initialization for SemanticMemory."""
        if self._memory is None:
            from app.core.memory.semantic_memory import SemanticMemory
            self._memory = SemanticMemory()
        return self._memory

    def _recall_context(self, user_id: str, user_input: str) -> str:
        """
        Pre-flight memory recall: fetch recent memories relevant to this session.
        Returns a formatted string for injection into crew inputs.
        """
        try:
            memory = self._get_memory()
            # Semantic search: find memories relevant to current input
            relevant = memory.recall_memories(user_id, user_input, k=5)
            # Also get recent memories regardless of query
            recent = memory.get_recent_memories(user_id, limit=5)

            # Deduplicate by text content
            seen_texts = set()
            all_memories: List[str] = []
            for m in relevant + recent:
                text = m.get("text", "")
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    mem_type = m.get("metadata", {}).get("type", "unknown")
                    all_memories.append(f"[{mem_type}] {text}")

            if not all_memories:
                return ""

            return "User memory context:\n" + "\n".join(all_memories[:8])
        except Exception:
            return ""

    @staticmethod
    def _detect_session_type(user_input: str, has_profile_memory: bool) -> str:
        """Classify session intent from the user's first message.

        Rules:
        - If the message contains personal health data (age, weight, smoking, etc.)
          and there is no existing profile memory -> intake
        - If the user references progress, updates, or past habits -> follow_up
        - Otherwise -> general (educational question)
        """
        text = user_input.lower()

        intake_signals = [
            "i am", "i'm", "years old", "my age", "my weight", "i smoke",
            "i drink", "my diet", "family history", "i weigh", "bmi",
            "my health", "assess me", "check my risk", "new here",
        ]
        followup_signals = [
            "update", "follow up", "follow-up", "progress", "last time",
            "my plan", "how am i doing", "check in", "check-in",
            "still struggling", "been doing", "changed my", "went well",
        ]

        if any(s in text for s in followup_signals):
            return "follow_up"
        if any(s in text for s in intake_signals) and not has_profile_memory:
            return "intake"
        return "general"

    @track
    def run_session(self, user_input: str, user_id: str, session_type: str = "intake") -> ChatServiceResult:
        """
        Run the appropriate crew based on session type.
        """
        # Supervisor pre-processing: recall memory context
        memory_context = self._recall_context(user_id, user_input)

        # Auto-detect session type if the caller passed the default
        if session_type == "general":
            has_profile = "[profile]" in memory_context
            session_type = self._detect_session_type(user_input, has_profile)

        if session_type == "intake":
            crew = self.crew.intake_crew(user_input, user_id, memory_context)
        elif session_type == "follow_up":
            crew = self.crew.follow_up_crew(user_input, user_id, memory_context)
        else:
            crew = self.crew.general_crew(user_input, user_id, memory_context)

        result = crew.kickoff(inputs={"user_id": user_id})

        # Post-processing: save key outputs to semantic memory
        self._save_session_memories(result, user_id, session_type)

        return ChatServiceResult(raw_result=result, user_id=user_id)

    def _save_session_memories(self, result, user_id: str, session_type: str):
        """Save profile and habit plan to semantic memory after crew completes."""
        try:
            memory = self._get_memory()
            raw = str(result)

            if session_type == "intake":
                # Save a profile summary from the crew output
                pydantic_out = getattr(result, "pydantic", None)
                if pydantic_out and hasattr(pydantic_out, "revised_response"):
                    # SafetyReview is the last task output
                    profile_summary = raw[:300]
                else:
                    profile_summary = raw[:300]
                memory.store_memory(user_id, profile_summary, {"type": "profile"})

            # Save habit plan summary if present in output
            if "habits" in raw.lower() or "habit" in raw.lower():
                # Extract a short plan summary (first 300 chars)
                plan_summary = raw[:300] if len(raw) > 300 else raw
                memory.store_memory(user_id, plan_summary, {"type": "habit_plan"})

        except Exception:
            pass  # Memory save is best-effort; don't break the session

    # Backward compatibility
    def run_intake_session(self, user_input: str, user_id: str) -> ChatServiceResult:
        return self.run_session(user_input, user_id, session_type="intake")

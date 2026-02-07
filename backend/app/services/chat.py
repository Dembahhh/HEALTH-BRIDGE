import asyncio
import concurrent.futures
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from opik import track

from app.agents.crew import HealthBridgeCrew, ParallelIntakeOrchestrator
from app.services.input_collector import InputCollector

logger = logging.getLogger(__name__)


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
    """
    Service layer for managing chat sessions with HealthBridge agents.
    
    Phase 1 Improvements:
    - Structured memory storage (full context, not truncated)
    - Entity extraction from conversations
    - Session state tracking
    - Improved memory recall with type filtering
    """
    
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
        
        IMPROVED: Now retrieves memories by type and provides structured context.
        
        Returns a formatted string for injection into crew inputs.
        """
        try:
            memory = self._get_memory()
            
            # Semantic search: find memories relevant to current input
            relevant = memory.recall_memories(user_id, user_input, k=5)
            
            # Get recent memories by type for more structured context
            recent_profile = memory.get_recent_memories(user_id, limit=2, memory_type="profile")
            recent_habits = memory.get_recent_memories(user_id, limit=2, memory_type="habit_plan")
            recent_conversation = memory.get_recent_memories(user_id, limit=3, memory_type="conversation")

            # Deduplicate by text content
            seen_texts = set()
            all_memories: List[str] = []
            
            # Add typed memories first (more structured)
            for m in recent_profile:
                text = m.get("text", "")
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    all_memories.append(f"[profile] {text}")
            
            for m in recent_habits:
                text = m.get("text", "")
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    all_memories.append(f"[habit_plan] {text}")
            
            for m in recent_conversation:
                text = m.get("text", "")
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    all_memories.append(f"[conversation] {text}")
            
            # Add semantically relevant memories
            for m in relevant:
                text = m.get("text", "")
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    mem_type = m.get("metadata", {}).get("type", "unknown")
                    all_memories.append(f"[{mem_type}] {text}")

            if not all_memories:
                return ""

            return "User memory context:\n" + "\n".join(all_memories[:10])
        except Exception as e:
            print(f"Memory recall error: {e}")
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

    def _extract_entities_from_input(self, user_input: str, detected_fields: Dict) -> Dict:
        """
        Extract structured entities from user input.
        
        This provides better context than raw text for memory storage.
        
        Args:
            user_input: The combined user input text
            detected_fields: Fields detected by InputCollector
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {
            "detected_fields": detected_fields,
            "word_count": len(user_input.split()),
            "has_numbers": bool(re.search(r'\d+', user_input)),
        }
        
        # Extract age if present
        age_match = re.search(r'\b(\d{1,3})\s*(year|yr|y\.?o\.?|years?\s*old)', user_input, re.IGNORECASE)
        if age_match:
            entities["age"] = int(age_match.group(1))
        
        # Extract sex if present
        sex_match = re.search(r'\b(male|female|man|woman)\b', user_input, re.IGNORECASE)
        if sex_match:
            entities["sex"] = sex_match.group(1).lower()
        
        # Extract conditions mentioned
        conditions = []
        condition_patterns = [
            (r'\bhypertension\b', 'hypertension'),
            (r'\bdiabete\w*\b', 'diabetes'),
            (r'\bhigh\s*blood\s*pressure\b', 'high blood pressure'),
            (r'\bheart\s*(disease|problem|condition)\b', 'heart disease'),
            (r'\bcholesterol\b', 'high cholesterol'),
        ]
        for pattern, condition in condition_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                conditions.append(condition)
        if conditions:
            entities["conditions_mentioned"] = conditions
        
        return entities

    @track
    def run_session(
        self,
        user_input: str,
        user_id: str,
        session_type: str = "intake",
        detected_fields: Optional[Dict] = None,
        conversation_history: Optional[List[str]] = None,
        use_cognee: bool = True,
    ) -> ChatServiceResult:
        """
        Run the appropriate crew based on session type.

        Supports:
        - Cognee graph memory when MEMORY_BACKEND=cognee
        - Parallel Risk+SDOH execution when PARALLEL_CREW=true (intake only)
        """
        # Check if Cognee should be used
        use_cognee_memory = use_cognee and os.getenv("MEMORY_BACKEND", "semantic").lower() == "cognee"

        # Supervisor pre-processing: recall memory context
        if use_cognee_memory:
            memory_context = self._recall_rich_context(user_id, user_input, session_type)
        else:
            memory_context = self._recall_context(user_id, user_input)

        # Auto-detect session type if the caller passed the default
        if session_type == "general":
            has_profile = "[profile]" in memory_context or "## User Profile" in memory_context
            session_type = self._detect_session_type(user_input, has_profile)

        # Parallel execution for intake when enabled
        use_parallel = os.getenv("PARALLEL_CREW", "false").lower() == "true"

        if session_type == "intake" and use_parallel:
            result = self._run_parallel_intake(user_input, user_id, memory_context)
        elif session_type == "intake":
            crew = self.crew.intake_crew(user_input, user_id, memory_context)
            result = crew.kickoff(inputs={"user_id": user_id})
        elif session_type == "follow_up":
            crew = self.crew.follow_up_crew(user_input, user_id, memory_context)
            result = crew.kickoff(inputs={"user_id": user_id})
        else:
            crew = self.crew.general_crew(user_input, user_id, memory_context)
            result = crew.kickoff(inputs={"user_id": user_id})

        # Post-processing: save key outputs to memory
        if use_cognee_memory:
            self._save_to_cognee(
                result=result,
                user_id=user_id,
                session_type=session_type,
                user_input=user_input,
                detected_fields=detected_fields or {},
                conversation_history=conversation_history or []
            )

        # Always save to semantic memory as backup
        self._save_session_memories_structured(
            result=result,
            user_id=user_id,
            session_type=session_type,
            user_input=user_input,
            detected_fields=detected_fields or {},
            conversation_history=conversation_history or []
        )

        return ChatServiceResult(raw_result=result, user_id=user_id)

    def _run_parallel_intake(self, user_input: str, user_id: str, memory_context: str):
        """Run intake with parallel Risk + SDOH execution.

        Stage 1: Intake (profile extraction) - sequential
        Stage 2: Risk + SDOH - parallel via ThreadPoolExecutor
        Stage 3: Plan + Safety - sequential
        """
        orch = ParallelIntakeOrchestrator()

        # Stage 1: Extract profile
        logger.info("Parallel intake: Stage 1 - Profile extraction")
        profile_result = orch.stage1_intake(user_input, user_id, memory_context).kickoff(
            inputs={"user_id": user_id}
        )
        profile_str = str(profile_result)

        # Stage 2: Risk + SDOH in parallel using threads
        logger.info("Parallel intake: Stage 2 - Risk + SDOH (parallel)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            risk_crew = orch.stage2_risk(profile_str, memory_context)
            sdoh_crew = orch.stage2_sdoh(user_input, user_id, memory_context)

            risk_future = executor.submit(risk_crew.kickoff, inputs={"user_id": user_id})
            sdoh_future = executor.submit(sdoh_crew.kickoff, inputs={"user_id": user_id})

            risk_result = risk_future.result()
            sdoh_result = sdoh_future.result()

        risk_str = str(risk_result)
        sdoh_str = str(sdoh_result)

        # Stage 3: Plan + Safety
        logger.info("Parallel intake: Stage 3 - Plan + Safety")
        final_result = orch.stage3_plan_safety(risk_str, sdoh_str, user_id).kickoff(
            inputs={"user_id": user_id}
        )

        return final_result

    def _save_session_memories_structured(
        self,
        result,
        user_id: str,
        session_type: str,
        user_input: str,
        detected_fields: Dict,
        conversation_history: List[str]
    ):
        """
        Save structured session data to semantic memory.
        
        PHASE 1 FIX: Instead of truncating to 300 chars, we now:
        1. Extract and store structured entities
        2. Store full context as JSON
        3. Create separate memory entries for different types of data
        """
        try:
            memory = self._get_memory()
            raw_output = str(result)
            timestamp = datetime.now().isoformat()
            
            # Extract entities from input
            entities = self._extract_entities_from_input(user_input, detected_fields)
            
            if session_type == "intake":
                # Store structured profile data
                profile_data = {
                    "session_type": "intake",
                    "entities": entities,
                    "input_summary": user_input[:500] if len(user_input) > 500 else user_input,
                    "output_summary": self._extract_key_points(raw_output),
                    "timestamp": timestamp
                }
                
                profile_text = json.dumps(profile_data, indent=2)
                memory.store_memory(
                    user_id, 
                    profile_text, 
                    {
                        "type": "profile",
                        "session_type": session_type,
                        "timestamp": timestamp
                    }
                )
            
            # Store habit plan if present in output
            if "habit" in raw_output.lower():
                habits_extracted = self._extract_habits_from_output(raw_output)
                if habits_extracted:
                    habit_data = {
                        "session_type": session_type,
                        "habits": habits_extracted,
                        "timestamp": timestamp
                    }
                    
                    habit_text = json.dumps(habit_data, indent=2)
                    memory.store_memory(
                        user_id,
                        habit_text,
                        {
                            "type": "habit_plan",
                            "session_type": session_type,
                            "timestamp": timestamp
                        }
                    )
            
            # Store conversation summary (for multi-turn context)
            if conversation_history:
                conversation_data = {
                    "session_type": session_type,
                    "turn_count": len(conversation_history),
                    "messages": conversation_history[-5:],  # Last 5 messages
                    "detected_fields": detected_fields,
                    "timestamp": timestamp
                }
                
                conversation_text = json.dumps(conversation_data, indent=2)
                memory.store_memory(
                    user_id,
                    conversation_text,
                    {
                        "type": "conversation",
                        "session_type": session_type,
                        "timestamp": timestamp
                    }
                )

        except Exception as e:
            print(f"Memory save error: {e}")
            # Memory save is best-effort; don't break the session

    def _extract_key_points(self, output: str, max_points: int = 5) -> List[str]:
        """Extract key bullet points from agent output."""
        key_points = []
        
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                clean_line = re.sub(r'^[-*•\d.)\s]+', '', line).strip()
                if len(clean_line) > 10:
                    key_points.append(clean_line)
                    if len(key_points) >= max_points:
                        break
        
        return key_points

    def _extract_habits_from_output(self, output: str) -> List[Dict]:
        """Extract habit information from agent output."""
        habits = []
        
        # Try JSON extraction first
        json_match = re.search(r'\{[\s\S]*"habits"[\s\S]*\}', output)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "habits" in data:
                    return data["habits"]
            except json.JSONDecodeError:
                pass
        
        # Fallback: extract bullet points that look like habits
        habit_keywords = ['walk', 'eat', 'drink', 'sleep', 'exercise', 'reduce', 
                         'add', 'avoid', 'limit', 'increase', 'daily', 'weekly']
        
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•')) and len(line) > 10:
                habit_text = line.lstrip('-*• ').strip()
                if any(w in habit_text.lower() for w in habit_keywords):
                    habits.append({
                        "description": habit_text[:200],
                        "extracted_at": datetime.now().isoformat()
                    })
        
        return habits[:5]  # Max 5 habits

    # Legacy method - calls new implementation
    def _save_session_memories(self, result, user_id: str, session_type: str):
        """Legacy wrapper - redirects to structured version."""
        self._save_session_memories_structured(
            result=result,
            user_id=user_id,
            session_type=session_type,
            user_input="",
            detected_fields={},
            conversation_history=[]
        )

    # Backward compatibility
    def run_intake_session(self, user_input: str, user_id: str) -> ChatServiceResult:
        return self.run_session(user_input, user_id, session_type="intake")

    # =========================================================================
    # PHASE 2: Cognee Integration Methods
    # =========================================================================

    def _get_cognee_memory(self):
        """Lazy initialization for CogneeMemoryManager."""
        if not hasattr(self, '_cognee_memory') or self._cognee_memory is None:
            from app.core.memory.cognee_memory import get_cognee_memory
            self._cognee_memory = get_cognee_memory()
        return self._cognee_memory

    async def _recall_rich_context_async(
        self,
        user_id: str,
        user_input: str,
        session_type: str
    ) -> str:
        """
        Enhanced memory recall with graph + temporal reasoning.

        This is the async version that uses Cognee's full capabilities.
        """
        try:
            cognee = self._get_cognee_memory()

            # Cognee provides structured context
            context = await cognee.recall_contextual_memory(
                user_id=user_id,
                query=user_input,
                lookback_days=30 if session_type == "follow_up" else 90
            )

            # Format for agent consumption
            formatted = []

            # User profile / entities
            if context.get("entities"):
                formatted.append("## User Profile")
                for key, val in context["entities"].items():
                    formatted.append(f"- {key}: {val}")

            # Historical patterns
            if context.get("temporal_patterns"):
                formatted.append("\n## Patterns & Trends")
                for pattern in context["temporal_patterns"]:
                    formatted.append(f"- {pattern}")

            # Causal relationships
            if context.get("relationships"):
                formatted.append("\n## Key Insights")
                for rel in context["relationships"][:5]:
                    formatted.append(f"- {rel}")

            # Summary
            if context.get("summary"):
                formatted.append(f"\n## Summary\n{context['summary'][:500]}")

            return "\n".join(formatted) if formatted else ""

        except Exception as e:
            print(f"Rich context recall failed: {e}")
            # Fallback to basic recall
            return self._recall_context(user_id, user_input)

    def _recall_rich_context(
        self,
        user_id: str,
        user_input: str,
        session_type: str
    ) -> str:
        """
        Synchronous wrapper for rich context recall.
        """
        try:
            from app.core.memory.cognee_memory import run_async
            return run_async(
                self._recall_rich_context_async(user_id, user_input, session_type)
            )
        except Exception as e:
            print(f"Rich context sync wrapper failed: {e}")
            return self._recall_context(user_id, user_input)

    async def _save_to_cognee_async(
        self,
        result,
        user_id: str,
        session_type: str,
        user_input: str,
        detected_fields: Dict,
        conversation_history: List[str]
    ):
        """
        Save session data to Cognee's knowledge graph.
        """
        try:
            cognee = self._get_cognee_memory()

            raw_output = str(result)

            # Extract entities
            entities = self._extract_entities_from_input(user_input, detected_fields)

            # Store the conversation turn
            turn_data = {
                "user_message": user_input,
                "agent_response": raw_output[:1000],  # Limit size
                "extracted_entities": entities,
                "timestamp": datetime.now().isoformat()
            }

            await cognee.store_conversation_turn(user_id, turn_data, session_type)

            # Store profile if intake
            if session_type == "intake" and entities:
                await cognee.store_profile(user_id, entities)

            # Store habits if present
            habits = self._extract_habits_from_output(raw_output)
            if habits:
                await cognee.store_habit_plan(user_id, habits)

        except Exception as e:
            print(f"Cognee save error: {e}")
            # Fallback handled by caller

    def _save_to_cognee(
        self,
        result,
        user_id: str,
        session_type: str,
        user_input: str,
        detected_fields: Dict,
        conversation_history: List[str]
    ):
        """Synchronous wrapper for Cognee save."""
        try:
            from app.core.memory.cognee_memory import run_async
            run_async(
                self._save_to_cognee_async(
                    result, user_id, session_type,
                    user_input, detected_fields, conversation_history
                )
            )
        except Exception as e:
            print(f"Cognee save sync wrapper failed: {e}")

    # =========================================================================
    # PHASE 5: Pattern Detection Integration
    # =========================================================================

    def run_session_with_patterns(
        self,
        user_input: str,
        user_id: str,
        session_type: str = "follow_up",
        detected_fields: Optional[Dict] = None,
        conversation_history: Optional[List[str]] = None,
        previous_patterns: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Run session with pattern detection and intervention generation.

        Enhanced version that includes:
        - Pattern analysis from conversation
        - Intervention recommendations
        - Pattern-informed crew execution

        Args:
            user_input: Combined user input
            user_id: User identifier
            session_type: Type of session
            detected_fields: Pre-extracted fields
            conversation_history: List of messages
            previous_patterns: Patterns from earlier sessions

        Returns:
            Dict with crew_result, patterns, and interventions
        """
        from app.services.pattern_detector import get_pattern_detector
        from app.services.intervention_engine import get_intervention_engine

        # Initialize detectors
        pattern_detector = get_pattern_detector()
        intervention_engine = get_intervention_engine()

        # Detect patterns from conversation
        messages = conversation_history or [user_input]
        patterns = pattern_detector.analyze_session(messages)

        # Get habit summary
        habit_summary = pattern_detector.get_habit_summary(messages)

        # Generate interventions
        interventions = intervention_engine.generate_interventions(patterns, habit_summary)

        # Build enhanced context for crew
        pattern_context = ""
        if patterns:
            pattern_context = "\n\nDetected patterns:\n"
            for p in patterns[:3]:
                pattern_context += f"- {p.description}\n"

        # Run crew with enhanced context
        enhanced_input = user_input + pattern_context

        crew_result = self.run_session(
            user_input=enhanced_input,
            user_id=user_id,
            session_type=session_type,
            detected_fields=detected_fields,
            conversation_history=conversation_history
        )

        # Format intervention message
        intervention_message = ""
        if interventions:
            intervention_message = intervention_engine.format_intervention_message(interventions)

        return {
            "crew_result": crew_result,
            "patterns": [p.to_dict() for p in patterns],
            "interventions": [i.to_dict() for i in interventions],
            "intervention_message": intervention_message,
            "habit_summary": {k: {
                "status": v.current_status,
                "trend": v.adherence_trend,
                "barriers": v.barriers
            } for k, v in habit_summary.items()}
        }
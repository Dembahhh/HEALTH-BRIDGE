"""
Response Formatter for HEALTH-BRIDGE

Converts raw CrewAI Pydantic/JSON output into clean, user-friendly markdown.
Collects citations from all intermediate task outputs.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats crew pipeline output into readable markdown for the user."""

    @staticmethod
    def format_crew_output(crew_result: Any) -> str:
        """Convert a CrewAI result into a user-friendly markdown string.

        Handles three output shapes:
        1. SafetyReview pydantic with revised_response
        2. Raw JSON string from crew
        3. Plain text fallback
        """
        # Try pydantic output first (SafetyReview is the final task)
        pydantic_out = getattr(crew_result, "pydantic", None)
        if pydantic_out is not None:
            return ResponseFormatter._format_safety_review(pydantic_out, crew_result)

        # Try parsing raw as JSON
        raw = getattr(crew_result, "raw", str(crew_result))
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                return ResponseFormatter._format_json_output(data, crew_result)
            except (json.JSONDecodeError, TypeError):
                pass

        # Collect citations from tasks even for plain text
        citations = ResponseFormatter._collect_citations_from_tasks(crew_result)
        text = str(raw)
        if citations:
            text = ResponseFormatter._append_citation_section(text, citations)
        return text

    @staticmethod
    def _format_safety_review(review: Any, crew_result: Any) -> str:
        """Format a SafetyReview pydantic object."""
        # Use revised_response if present, otherwise build from earlier tasks
        if hasattr(review, "revised_response") and review.revised_response:
            text = review.revised_response
        else:
            # Fall back to building from tasks_output
            text = ResponseFormatter._build_from_tasks(crew_result)

        if not text:
            text = getattr(review, "explanation", str(review))

        # Collect all citations from intermediate tasks
        citations = ResponseFormatter._collect_citations_from_tasks(crew_result)

        # Also add citations from the safety review itself
        if hasattr(review, "citations") and review.citations:
            for c in review.citations:
                cite_dict = c.model_dump() if hasattr(c, "model_dump") else dict(c)
                if cite_dict not in citations:
                    citations.append(cite_dict)

        if citations:
            text = ResponseFormatter._append_citation_section(text, citations)

        return text

    @staticmethod
    def _format_json_output(data: Dict, crew_result: Any) -> str:
        """Format a JSON dict from crew output."""
        parts = []

        # Risk Assessment
        if "hypertension_risk" in data or "diabetes_risk" in data:
            parts.append(ResponseFormatter._format_risk(data))

        # Habit Plan
        if "habits" in data:
            parts.append(ResponseFormatter._format_habits(data))

        # Safety Review wrapper
        if "revised_response" in data and data["revised_response"]:
            parts.append(data["revised_response"])
        elif "explanation" in data:
            parts.append(data["explanation"])

        if not parts:
            parts.append(json.dumps(data, indent=2))

        text = "\n\n".join(parts)

        # Append citations
        citations = ResponseFormatter._collect_citations_from_tasks(crew_result)
        if citations:
            text = ResponseFormatter._append_citation_section(text, citations)

        return text

    @staticmethod
    def _format_risk(data: Dict) -> str:
        """Format risk assessment data into readable text."""
        lines = []
        if data.get("hypertension_risk"):
            lines.append(f"Hypertension risk: {data['hypertension_risk']}")
        if data.get("diabetes_risk"):
            lines.append(f"Diabetes risk: {data['diabetes_risk']}")
        if data.get("key_drivers"):
            drivers = data["key_drivers"]
            if isinstance(drivers, list):
                lines.append("Key factors: " + ", ".join(drivers))
        if data.get("explanation"):
            lines.append(f"\n{data['explanation']}")
        return "\n".join(lines)

    @staticmethod
    def _format_habits(data: Dict) -> str:
        """Format habit plan into readable text."""
        lines = []
        if data.get("focus_areas"):
            areas = data["focus_areas"]
            if isinstance(areas, list):
                lines.append("Focus areas: " + ", ".join(areas))

        habits = data.get("habits", [])
        for i, h in enumerate(habits, 1):
            if isinstance(h, dict):
                action = h.get("action", "")
                freq = h.get("frequency", "")
                trigger = h.get("trigger", "")
                rationale = h.get("rationale", "")
                lines.append(f"\nHabit {i}: {action}")
                if freq:
                    lines.append(f"  Frequency: {freq}")
                if trigger:
                    lines.append(f"  When: {trigger}")
                if rationale:
                    lines.append(f"  Why: {rationale}")

        if data.get("motivational_message"):
            lines.append(f"\n{data['motivational_message']}")

        return "\n".join(lines)

    @staticmethod
    def _build_from_tasks(crew_result: Any) -> str:
        """Build response text from task outputs when revised_response is empty."""
        tasks_output = getattr(crew_result, "tasks_output", [])
        if not tasks_output:
            return ""

        # Walk backwards to find the most useful task output
        for task_out in reversed(tasks_output):
            pydantic = getattr(task_out, "pydantic", None)
            if pydantic:
                # HabitPlan — most user-facing
                if hasattr(pydantic, "habits") and hasattr(pydantic, "motivational_message"):
                    data = pydantic.model_dump() if hasattr(pydantic, "model_dump") else dict(pydantic)
                    return ResponseFormatter._format_habits(data)
                # RiskAssessment
                if hasattr(pydantic, "explanation"):
                    return pydantic.explanation

            raw = getattr(task_out, "raw", None)
            if raw and len(str(raw)) > 20:
                return str(raw)

        return ""

    @staticmethod
    def _collect_citations_from_tasks(crew_result: Any) -> List[Dict]:
        """Walk all tasks_output and extract citations from pydantic models."""
        citations: List[Dict] = []
        seen_ids = set()

        tasks_output = getattr(crew_result, "tasks_output", [])
        for task_out in tasks_output:
            pydantic = getattr(task_out, "pydantic", None)
            if pydantic and hasattr(pydantic, "citations"):
                for c in pydantic.citations:
                    cite = c.model_dump() if hasattr(c, "model_dump") else dict(c)
                    sid = cite.get("source_id", "")
                    if sid and sid not in seen_ids:
                        seen_ids.add(sid)
                        citations.append(cite)

        return citations

    @staticmethod
    def _append_citation_section(text: str, citations: List[Dict]) -> str:
        """Append a Sources section to the response text."""
        if not citations:
            return text

        lines = ["\n\n---\n**Sources:**"]
        for i, c in enumerate(citations, 1):
            name = c.get("source_name", c.get("source_id", f"Source {i}"))
            condition = c.get("condition", "")
            topic = c.get("topic", "")
            label_parts = [name]
            if condition:
                label_parts.append(condition)
            if topic:
                label_parts.append(topic)
            lines.append(f"{i}. {' — '.join(label_parts)}")

        return text + "\n".join(lines)

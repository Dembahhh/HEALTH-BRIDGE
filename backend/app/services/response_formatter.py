"""
Response Formatter

Converts structured agent output (Pydantic models / raw JSON) into
human-readable markdown text for the chat interface.

The crew pipeline ends with SafetyReview, whose revised_response may contain:
- Plain text (ideal — already formatted by the Safety Agent)
- JSON string (HabitPlan serialised as a string)
- None (legacy: plan was safe but not forwarded)

This module handles all three cases and produces user-friendly markdown.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Transforms raw crew output into user-friendly text."""

    @staticmethod
    def format_crew_output(raw_result: Any) -> str:
        """
        Main entry point: detect output type and format accordingly.

        Handles:
        - SafetyReview pydantic output (most common)
        - HabitPlan pydantic output
        - Raw JSON strings
        - Plain text (pass-through)
        """
        # 1. Try pydantic output first
        pydantic_out = getattr(raw_result, "pydantic", None)
        if pydantic_out:
            return ResponseFormatter._format_pydantic(pydantic_out)

        # 2. Try raw string
        raw_str = str(getattr(raw_result, "raw", raw_result))

        # 3. Attempt to parse as JSON
        try:
            parsed = json.loads(raw_str)
            return ResponseFormatter._format_json(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

        # 4. Check if it's nested JSON inside a SafetyReview-like wrapper
        safety_match = re.search(
            r'"revised_response"\s*:\s*"(.*?)"(?:\s*[,}])',
            raw_str,
            re.DOTALL,
        )
        if safety_match:
            inner = safety_match.group(1).replace('\\"', '"').replace("\\n", "\n")
            try:
                parsed_inner = json.loads(inner)
                return ResponseFormatter._format_json(parsed_inner)
            except (json.JSONDecodeError, TypeError):
                return inner  # Plain text inside revised_response

        # 5. If it looks like JSON but didn't parse, strip syntax
        if raw_str.strip().startswith("{"):
            return ResponseFormatter._clean_json_to_text(raw_str)

        return raw_str

    # ── Pydantic dispatch ──────────────────────────────────────────────

    @staticmethod
    def _format_pydantic(obj: Any) -> str:
        """Format a Pydantic model into readable text."""
        class_name = type(obj).__name__

        if class_name == "SafetyReview":
            return ResponseFormatter._format_safety_review(obj)

        if class_name == "HabitPlan":
            return ResponseFormatter._format_habit_plan(obj.model_dump())

        if class_name == "RiskAssessment":
            return ResponseFormatter._format_risk(obj.model_dump())

        # Generic fallback
        return str(obj)

    @staticmethod
    def _format_safety_review(obj: Any) -> str:
        """Extract the user-facing content from a SafetyReview."""
        if obj.revised_response:
            # revised_response may itself be JSON (legacy path)
            try:
                parsed = json.loads(obj.revised_response)
                return ResponseFormatter._format_json(parsed)
            except (json.JSONDecodeError, TypeError):
                # It's already plain text — ideal case
                return obj.revised_response

        # No revised_response — plan was safe but agent didn't forward it
        if obj.is_safe:
            return (
                "Your plan has been reviewed and is safe to follow. "
                "Please check your habit plan above for details."
            )
        # Unsafe and no rewrite — shouldn't happen but handle gracefully
        issues = "\n".join(f"- {i}" for i in obj.flagged_issues) if obj.flagged_issues else ""
        return f"Some safety concerns were found:\n{issues}\nPlease consult a healthcare provider."

    # ── JSON dispatch ──────────────────────────────────────────────────

    @staticmethod
    def _format_json(data: dict) -> str:
        """Route a JSON dict to the appropriate formatter."""
        if "habits" in data:
            return ResponseFormatter._format_habit_plan(data)
        if "hypertension_risk" in data:
            return ResponseFormatter._format_risk(data)
        if "revised_response" in data:
            revised = data.get("revised_response", "")
            if revised:
                try:
                    inner = json.loads(revised) if isinstance(revised, str) else revised
                    return ResponseFormatter._format_json(inner)
                except (json.JSONDecodeError, TypeError):
                    return revised
        return ResponseFormatter._clean_json_to_text(json.dumps(data))

    # ── Domain formatters ──────────────────────────────────────────────

    @staticmethod
    def _format_citations(citations: list) -> str:
        """Format citations as a Sources section in markdown."""
        if not citations:
            return ""
        
        lines = ["\n---\n📚 **Sources:**"]
        seen = set()
        for c in citations:
            source_id = c.get("source_id", "")
            source_name = c.get("source_name", "Unknown")
            snippet = c.get("content_snippet", "")[:150]
            
            if source_id in seen:
                continue
            seen.add(source_id)
            
            lines.append(f"  [{source_id}] *{source_name}* — \"{snippet}\"")
        
        return "\n".join(lines)

    @staticmethod
    def _format_habit_plan(data: dict) -> str:
        """Format a HabitPlan dict into friendly markdown."""
        lines = []

        weeks = data.get("duration_weeks", 4)
        focus = data.get("focus_areas", [])

        lines.append(f"## Your {weeks}-Week Health Plan\n")

        if focus:
            lines.append("**Focus areas:** " + ", ".join(focus) + "\n")

        habits = data.get("habits", [])
        for i, habit in enumerate(habits, 1):
            action = habit.get("action", "Habit")
            freq = habit.get("frequency", "")
            trigger = habit.get("trigger", "")
            rationale = habit.get("rationale", "")

            lines.append(f"### Habit {i}: {action}")
            if freq:
                lines.append(f"**Frequency:** {freq}")
            if trigger:
                lines.append(f"**When:** {trigger}")
            if rationale:
                lines.append(f"**Why:** {rationale}")
            lines.append("")

        msg = data.get("motivational_message", "")
        if msg:
            lines.append(f"---\n*{msg}*")

        # Add citations if present
        citations = data.get("citations", [])
        if citations:
            lines.append(ResponseFormatter._format_citations(citations))

        return "\n".join(lines)

    @staticmethod
    def _format_risk(data: dict) -> str:
        """Format a RiskAssessment dict into friendly text."""
        lines = ["## Your Risk Profile\n"]

        ht = data.get("hypertension_risk", "unknown")
        db = data.get("diabetes_risk", "unknown")

        lines.append(f"- **Hypertension risk:** {ht.capitalize()}")
        lines.append(f"- **Type 2 diabetes risk:** {db.capitalize()}\n")

        drivers = data.get("key_drivers", [])
        if drivers:
            lines.append("**Key factors:**")
            for d in drivers:
                lines.append(f"  - {d}")

        explanation = data.get("explanation", "")
        if explanation:
            lines.append(f"\n{explanation}")

        # Add citations if present
        citations = data.get("citations", [])
        if citations:
            lines.append(ResponseFormatter._format_citations(citations))

        return "\n".join(lines)

    # ── Fallback ───────────────────────────────────────────────────────

    @staticmethod
    def _clean_json_to_text(raw: str) -> str:
        """Last-resort: strip JSON syntax for readability."""
        text = raw.replace("{", "").replace("}", "").replace('"', "")
        text = re.sub(r",\s*", "\n", text)
        text = re.sub(r":\s*", ": ", text)
        return text.strip()

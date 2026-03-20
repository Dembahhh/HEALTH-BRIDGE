"""
Nudge Service

Handles asynchronous generation of AI nudges based on tracking data.
Instead of spinning up a full CrewAI crew (which takes 30-60s), this
uses the Orchestrator's quick direct LLM approach for fast 2-5s nudges
that appear on the dashboard.
"""

import asyncio
import logging
from datetime import datetime

from app.models.tracking import TrackingLog, NudgeData
from app.agents.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


async def generate_tracking_nudge(log_id: str, user_id: str):
    """
    Generate an AI nudge for a specific tracking log entry.
    Updates the MongoDB document with the generated nudge.
    
    Expected to run as a background task.
    """
    try:
        # 1. Fetch the log entry
        log_entry = await TrackingLog.get(log_id)
        if not log_entry:
            logger.error(f"Nudge generation failed: Log {log_id} not found")
            return
            
        # 2. Build the context prompt based on the log type
        context_prompt = _build_nudge_prompt(log_entry)
        
        # 3. Use the Orchestrator's direct LLM call for a fast response
        # We classify this as 'lifestyle' to get practical, actionable advice.
        orchestrator = get_orchestrator()
        
        # Fetch profile for personalization
        profile_summary, _, _ = await orchestrator._fetch_profile_and_history(user_id, history_limit=0)
        
        loop = asyncio.get_event_loop()
        nudge_text = await loop.run_in_executor(
            None,
            orchestrator._direct_llm_call,
            context_prompt,
            user_id,
            profile_summary,
            "lifestyle",
            [] # No conversation history needed for a standalone nudge
        )
        
        # Clean up formatting for the dashboard (remove markdown, keep to 2-3 sentences max)
        clean_text = _clean_nudge_text(nudge_text)
        
        # Determine action type based on the log
        action_type = log_entry.log_type
        if log_entry.log_type == "bp" and log_entry.bp_classification and log_entry.bp_classification.get("severity", 0) >= 4:
             action_type = "referral" # Crisis levels
             
        # 4. Save back to the tracking log
        log_entry.nudge = NudgeData(
            text=clean_text,
            action_type=action_type,
            generated_at=datetime.utcnow()
        )
        await log_entry.save()
        logger.info(f"Successfully generated nudge for log {log_id}")
        
    except Exception as e:
        logger.error(f"Error generating nudge for log {log_id}: {e}", exc_info=True)


def _build_nudge_prompt(log: TrackingLog) -> str:
    """Build a prompt string describing the user's latest check-in."""
    
    base = (
        "The user just submitted a health check-in on their dashboard. "
        "Generate a very short, encouraging 'nudge' (maximum 2-3 sentences) "
        "to display on their home screen. Do NOT use markdown. Start directly with the message.\n\n"
        "Here is what they logged:\n"
    )
    
    if log.log_type == "bp":
        cat = log.bp_classification.get("category", "unknown") if log.bp_classification else "unknown"
        base += f"- Blood Pressure: {log.systolic}/{log.diastolic} (Classified as: {cat})\n"
        
    elif log.log_type == "glucose":
        cat = log.glucose_classification.get("category", "unknown") if log.glucose_classification else "unknown"
        base += f"- Blood Sugar: {log.glucose_value} {log.glucose_unit} ({log.glucose_test_type} test). Classified as: {cat}.\n"
        
    elif log.log_type == "medication":
        taken = sum(1 for m in log.medications if m.taken)
        skipped = sum(1 for m in log.medications if not m.taken)
        base += f"- Medications: Taken {taken}, Skipped {skipped}.\n"
        
    if log.mood:
        base += f"- Mood: {log.mood}\n"
    if log.notes:
        base += f"- Notes: {log.notes}\n"
        
    return base


def _clean_nudge_text(text: str) -> str:
    """Strip markdown and ensure it's short."""
    # Remove markdown bold/italics
    cleaned = text.replace("**", "").replace("*", "").replace("##", "").strip()
    
    # Take first 3 sentences max
    import re
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    if len(sentences) > 3:
         cleaned = " ".join(sentences[:3])
         
    return cleaned

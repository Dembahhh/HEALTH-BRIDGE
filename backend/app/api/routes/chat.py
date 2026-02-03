"""
Chat API Routes

Endpoints for chat sessions and messaging.
"""

from typing import Optional, List
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import asyncio
import functools

from app.api.deps import CurrentUser
from app.models.chat import ChatSession, ChatMessage
from app.models.plan import HabitPlan, Habit
from datetime import datetime, timedelta

router = APIRouter()


def get_user_id(current_user) -> str:
    """Extract user ID from current_user (dict or User object)."""
    if isinstance(current_user, dict):
        return current_user.get("uid", "unknown")
    return getattr(current_user, "firebase_uid", str(current_user.id))


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""
    session_type: str = "general"  # intake, follow_up, general


class CreateSessionResponse(BaseModel):
    """Response with new session details."""
    session_id: str
    session_type: str
    message: str


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    session_id: str
    content: str


class SendMessageResponse(BaseModel):
    """Response with assistant message."""
    message_id: str
    content: str
    agent_name: Optional[str] = None
    habit_plan_id: Optional[str] = None


class MessageItem(BaseModel):
    """A single message in history."""
    role: str
    content: str
    created_at: str


# Endpoints
@router.post("/session", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: CurrentUser,
):
    """
    Create a new chat session.

    Session types:
    - intake: First-time health assessment
    - follow_up: Returning user check-in
    - general: Educational questions
    """
    user_id = get_user_id(current_user)

    # Create session in database
    session = ChatSession(
        user_id=user_id,
        session_type=request.session_type,
        status="active"
    )
    await session.create()

    return CreateSessionResponse(
        session_id=str(session.id),
        session_type=request.session_type,
        message=f"Session created. Type: {request.session_type}",
    )


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: CurrentUser,
):
    """
    Send a message and get AI response.

    This triggers the multi-agent pipeline.
    """
    from app.services.chat import ChatService

    user_id = get_user_id(current_user)

    # Verify session exists and belongs to user
    session = await ChatSession.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Save user message
    user_message = ChatMessage(
        session_id=request.session_id,
        user_id=user_id,
        role="user",
        content=request.content
    )
    await user_message.create()

    try:
        # Initialize service and execute agent crew
        chat_service = ChatService()

        # Run synchronous CrewAI in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            functools.partial(
                chat_service.run_session,
                request.content,
                user_id,
                session.session_type
            )
        )

        # Extract response content
        response_content = str(result)

        # Save assistant message
        assistant_message = ChatMessage(
            session_id=request.session_id,
            user_id=user_id,
            role="assistant",
            content=response_content,
            agent_name="HealthBridge Crew"
        )
        await assistant_message.create()

        # Save HabitPlan if habits were extracted
        habit_plan_id = None
        if hasattr(result, 'habits') and result.habits:
            habits = []
            for h in result.habits:
                # Map from agent schema (action/trigger/rationale)
                # to plan schema (title/description/category)
                title = h.get("title") or h.get("action", "Habit")
                description = h.get("description") or h.get("rationale", "")
                category = h.get("category") or h.get("trigger", "general")
                habits.append(Habit(
                    title=title[:100] if title else "Habit",
                    description=description,
                    frequency=h.get("frequency", "daily"),
                    category=category,
                    difficulty=h.get("difficulty", "easy")
                ))

            plan = HabitPlan(
                user_id=user_id,
                week_number=1,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(weeks=4),
                habits=habits,
                status="active"
            )
            await plan.create()
            habit_plan_id = str(plan.id)

            # Link plan to session
            session.habit_plan_id = habit_plan_id

        # Update session timestamp
        session.update_timestamp()
        await session.save()

        return SendMessageResponse(
            message_id=str(assistant_message.id),
            content=response_content,
            agent_name="HealthBridge Crew",
            habit_plan_id=habit_plan_id
        )

    except Exception as e:
        # Save error as system message for debugging
        error_message = ChatMessage(
            session_id=request.session_id,
            user_id=user_id,
            role="system",
            content=f"Error: {str(e)}"
        )
        await error_message.create()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: CurrentUser,
):
    """Get all messages in a session."""
    user_id = get_user_id(current_user)

    # Verify session exists and belongs to user
    session = await ChatSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Retrieve messages
    messages = await ChatMessage.find(
        ChatMessage.session_id == session_id
    ).sort("+created_at").to_list()

    return {
        "session_id": session_id,
        "messages": [
            MessageItem(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]
    }


@router.get("/sessions")
async def list_sessions(
    current_user: CurrentUser,
):
    """List all sessions for the current user."""
    user_id = get_user_id(current_user)

    sessions = await ChatSession.find(
        ChatSession.user_id == user_id
    ).sort("-created_at").to_list()

    return {
        "sessions": [
            {
                "session_id": str(s.id),
                "session_type": s.session_type,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat()
            }
            for s in sessions
        ]
    }

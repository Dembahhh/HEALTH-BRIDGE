"""
Chat API Routes

Endpoints for chat sessions and messaging.
"""

import logging
from typing import Optional, List
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.api.deps import CurrentUser
from app.models.chat import ChatSession, ChatMessage
from app.models.plan import HabitPlan, Habit
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""
    session_type: str = Field(
        default="general",
        pattern=r"^(intake|follow_up|general)$",
        description="Session type: intake, follow_up, or general",
    )


class CreateSessionResponse(BaseModel):
    """Response with new session details."""
    session_id: str
    session_type: str
    message: str


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    session_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message content (1-5000 characters)",
    )


class SendMessageResponse(BaseModel):
    """Response with assistant message."""
    message_id: str
    content: str
    agent_name: Optional[str] = None


class MessageItem(BaseModel):
    """A single message in history."""
    role: str
    content: str
    agent_name: Optional[str] = None
    created_at: str


class SessionItem(BaseModel):
    """A session in the list."""
    session_id: str
    session_type: str
    is_active: bool
    created_at: str
    updated_at: str


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a message."""
    message_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=-1, le=1, description="1 = thumbs up, -1 = thumbs down")
    comment: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    """Response confirming feedback was saved."""
    feedback_id: str
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(current_user) -> str:
    """Extract user id from the current_user dependency (dict or User)."""
    if isinstance(current_user, dict):
        return current_user.get("uid")
    return getattr(current_user, "firebase_uid", str(current_user.id))


async def _persist_message(
    session_id: str,
    role: str,
    content: str,
    agent_name: Optional[str] = None,
) -> ChatMessage:
    """Save a chat message to MongoDB and return it."""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        agent_name=agent_name,
    )
    await msg.insert()
    return msg


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/session", response_model=CreateSessionResponse)
@limiter.limit("10/minute")
async def create_session(
    request_body: CreateSessionRequest,
    request: Request,
    current_user: CurrentUser,
):
    """Create a new chat session and persist it."""
    uid = _uid(current_user)
    session_id = str(uuid4())

    session = ChatSession(
        user_id=uid,
        session_id=session_id,
        session_type=request_body.session_type,
    )
    await session.insert()

    return CreateSessionResponse(
        session_id=session_id,
        session_type=request_body.session_type,
        message=f"Session created. Type: {request_body.session_type}",
    )


@router.post("/message", response_model=SendMessageResponse)
@limiter.limit("20/minute")
async def send_message(
    request_body: SendMessageRequest,
    request: Request,
    current_user: CurrentUser,
):
    """
    Send a message and get AI response via the full multi-agent pipeline.
    """
    from app.agents import get_orchestrator

    uid = _uid(current_user)
    orchestrator = get_orchestrator()

    # Persist the user message
    await _persist_message(request_body.session_id, "user", request_body.content)

    # Look up the session to get its type
    session = await ChatSession.find_one(
        ChatSession.session_id == request_body.session_id
    )
    session_type = session.session_type if session else "general"

    try:
        result = await orchestrator.process_message(
            user_id=uid,
            session_id=request_body.session_id,
            message=request_body.content,
            session_type=session_type,
        )

        agent_name = result.get("agent_name", "supervisor")
        content = result["content"]

        # Persist the assistant message
        saved = await _persist_message(
            request_body.session_id, "assistant", content, agent_name
        )

        # Auto-save HabitPlan if the crew extracted habits
        if hasattr(result, "habits") and result.get("habits"):
            habits = []
            for h in result["habits"]:
                title = h.get("title") or h.get("action", "Habit")
                description = h.get("description") or h.get("rationale", "")
                category = h.get("category") or h.get("trigger", "general")
                habits.append(Habit(
                    title=title[:100] if title else "Habit",
                    description=description,
                    frequency=h.get("frequency", "daily"),
                    category=category,
                    difficulty=h.get("difficulty", "easy"),
                ))
            if habits:
                plan = HabitPlan(
                    user_id=uid,
                    week_number=1,
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(weeks=4),
                    habits=habits,
                    status="active",
                )
                await plan.insert()

        # Touch session timestamp
        if session:
            session.update_timestamp()
            await session.save()

        return SendMessageResponse(
            message_id=str(saved.id),
            content=content,
            agent_name=agent_name,
        )
    except Exception as e:
        logger.error(
            "Chat error for user=%s session=%s: %s",
            uid, request_body.session_id, e, exc_info=True,
        )

        fallback = "I'm sorry, I encountered an issue processing your message. Please try again."
        saved = await _persist_message(
            request_body.session_id, "assistant", fallback, "system"
        )
        return SendMessageResponse(
            message_id=str(saved.id),
            content=fallback,
            agent_name="system",
        )


@router.post("/quick", response_model=SendMessageResponse)
@limiter.limit("30/minute")
async def send_quick_message(
    request_body: SendMessageRequest,
    request: Request,
    current_user: CurrentUser,
):
    """
    Quick single-turn response (lighter pipeline, faster).
    """
    from app.agents import get_orchestrator

    uid = _uid(current_user)
    orchestrator = get_orchestrator()

    # Persist the user message
    await _persist_message(request_body.session_id, "user", request_body.content)

    try:
        result = await orchestrator.quick_message(
            user_id=uid,
            session_id=request_body.session_id,
            message=request_body.content,
        )

        agent_name = result.get("agent_name", "quick")
        content = result["content"]

        saved = await _persist_message(
            request_body.session_id, "assistant", content, agent_name
        )

        # Touch session timestamp
        session = await ChatSession.find_one(
            ChatSession.session_id == request_body.session_id
        )
        if session:
            session.update_timestamp()
            await session.save()

        return SendMessageResponse(
            message_id=str(saved.id),
            content=content,
            agent_name=agent_name,
        )
    except Exception as e:
        logger.error(
            "Quick chat error for user=%s session=%s: %s",
            uid, request_body.session_id, e, exc_info=True,
        )

        fallback = "I'm sorry, I encountered an issue. Please try again."
        saved = await _persist_message(
            request_body.session_id, "assistant", fallback, "system"
        )
        return SendMessageResponse(
            message_id=str(saved.id),
            content=fallback,
            agent_name="system",
        )


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("30/minute")
async def submit_feedback(
    request_body: FeedbackRequest,
    request: Request,
    current_user: CurrentUser,
):
    """Submit thumbs up/down feedback on a message."""
    from app.models.chat import MessageFeedback
    
    uid = _uid(current_user)
    
    feedback = MessageFeedback(
        message_id=request_body.message_id,
        session_id=request_body.session_id,
        user_id=uid,
        rating=request_body.rating,
        comment=request_body.comment,
    )
    await feedback.insert()
    
    return FeedbackResponse(
        feedback_id=str(feedback.id),
        message="Feedback recorded. Thank you!",
    )


@router.post("/auto", response_model=SendMessageResponse)
@limiter.limit("20/minute")
async def send_auto_message(
    request_body: SendMessageRequest,
    request: Request,
    current_user: CurrentUser,
):
    """
    Auto-routed message: classifies intent and routes to quick or full pipeline.
    """
    from app.agents import get_orchestrator
    from app.agents.orchestrator import ChatOrchestrator
    
    uid = _uid(current_user)
    orchestrator = get_orchestrator()
    
    # Persist the user message
    await _persist_message(request_body.session_id, "user", request_body.content)
    
    # Classify intent
    route = ChatOrchestrator._classify_intent(request_body.content)
    
    try:
        if route == "quick":
            result = await orchestrator.quick_message(
                user_id=uid,
                session_id=request_body.session_id,
                message=request_body.content,
            )
        else:
            session = await ChatSession.find_one(
                ChatSession.session_id == request_body.session_id
            )
            session_type = session.session_type if session else "general"
            result = await orchestrator.process_message(
                user_id=uid,
                session_id=request_body.session_id,
                message=request_body.content,
                session_type=session_type,
            )
        
        agent_name = result.get("agent_name", "auto")
        content = result["content"]
        
        saved = await _persist_message(
            request_body.session_id, "assistant", content, agent_name
        )
        
        # Touch session timestamp
        session = await ChatSession.find_one(
            ChatSession.session_id == request_body.session_id
        )
        if session:
            session.update_timestamp()
            await session.save()
        
        return SendMessageResponse(
            message_id=str(saved.id),
            content=content,
            agent_name=agent_name,
        )
    except Exception as e:
        logger.error(
            "Auto-route chat error for user=%s session=%s: %s",
            uid, request_body.session_id, e, exc_info=True,
        )
        fallback = "I'm sorry, I encountered an issue. Please try again."
        saved = await _persist_message(
            request_body.session_id, "assistant", fallback, "system"
        )
        return SendMessageResponse(
            message_id=str(saved.id),
            content=fallback,
            agent_name="system",
        )


@router.get("/session/{session_id}/messages")
@limiter.limit("30/minute")
async def get_session_messages(
    session_id: str,
    request: Request,
    current_user: CurrentUser,
):
    """Get all messages in a session from the database."""
    messages = await ChatMessage.find(
        ChatMessage.session_id == session_id
    ).sort("+created_at").to_list()

    return {
        "session_id": session_id,
        "messages": [
            MessageItem(
                role=m.role,
                content=m.content,
                agent_name=m.agent_name,
                created_at=m.created_at.isoformat(),
            ).model_dump()
            for m in messages
        ],
    }


@router.get("/sessions")
@limiter.limit("30/minute")
async def get_sessions(
    request: Request,
    current_user: CurrentUser,
):
    """List all chat sessions for the current user."""
    uid = _uid(current_user)

    sessions = await ChatSession.find(
        ChatSession.user_id == uid
    ).sort("-created_at").to_list()

    return {
        "sessions": [
            SessionItem(
                session_id=s.session_id,
                session_type=s.session_type,
                is_active=s.is_active,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            ).model_dump()
            for s in sessions
        ],
    }

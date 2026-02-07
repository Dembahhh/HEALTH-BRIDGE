"""
Chat API Routes

Endpoints for chat sessions and messaging.
"""

from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.models.chat import ChatSession, ChatMessage

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

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
async def create_session(
    request: CreateSessionRequest,
    current_user: CurrentUser,
):
    """Create a new chat session and persist it."""
    uid = _uid(current_user)
    session_id = str(uuid4())

    session = ChatSession(
        user_id=uid,
        session_id=session_id,
        session_type=request.session_type,
    )
    await session.insert()

    return CreateSessionResponse(
        session_id=session_id,
        session_type=request.session_type,
        message=f"Session created. Type: {request.session_type}",
    )


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: CurrentUser,
):
    """
    Send a message and get AI response via the full multi-agent pipeline.
    """
    from app.agents import get_orchestrator

    uid = _uid(current_user)
    orchestrator = get_orchestrator()

    # Persist the user message
    await _persist_message(request.session_id, "user", request.content)

    # Look up the session to get its type
    session = await ChatSession.find_one(
        ChatSession.session_id == request.session_id
    )
    session_type = session.session_type if session else "general"

    try:
        result = await orchestrator.process_message(
            user_id=uid,
            session_id=request.session_id,
            message=request.content,
            session_type=session_type,
        )

        agent_name = result.get("agent_name", "supervisor")
        content = result["content"]

        # Persist the assistant message
        saved = await _persist_message(
            request.session_id, "assistant", content, agent_name
        )

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
        import traceback
        print(f"Chat error: {e}")
        traceback.print_exc()

        fallback = f"I'm sorry, I encountered an issue processing your message. Error: {str(e)[:100]}"
        saved = await _persist_message(
            request.session_id, "assistant", fallback, "system"
        )
        return SendMessageResponse(
            message_id=str(saved.id),
            content=fallback,
            agent_name="system",
        )


@router.post("/quick", response_model=SendMessageResponse)
async def send_quick_message(
    request: SendMessageRequest,
    current_user: CurrentUser,
):
    """
    Quick single-turn response (lighter pipeline, faster).
    """
    from app.agents import get_orchestrator

    uid = _uid(current_user)
    orchestrator = get_orchestrator()

    # Persist the user message
    await _persist_message(request.session_id, "user", request.content)

    try:
        result = await orchestrator.quick_message(
            user_id=uid,
            session_id=request.session_id,
            message=request.content,
        )

        agent_name = result.get("agent_name", "quick")
        content = result["content"]

        saved = await _persist_message(
            request.session_id, "assistant", content, agent_name
        )

        # Touch session timestamp
        session = await ChatSession.find_one(
            ChatSession.session_id == request.session_id
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
        import traceback
        print(f"Quick chat error: {e}")
        traceback.print_exc()

        fallback = f"I'm sorry, I encountered an issue. Error: {str(e)[:100]}"
        saved = await _persist_message(
            request.session_id, "assistant", fallback, "system"
        )
        return SendMessageResponse(
            message_id=str(saved.id),
            content=fallback,
            agent_name="system",
        )


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
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
async def get_sessions(current_user: CurrentUser):
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

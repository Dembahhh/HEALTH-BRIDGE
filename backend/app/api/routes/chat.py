"""
Chat API Routes

Endpoints for chat sessions and messaging.
"""

from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser

router = APIRouter()


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
    session_id = str(uuid4())

    # TODO: Create session in database (Phase 7)

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
    Send a message and get AI response.

    This triggers the multi-agent pipeline.
    """
    from app.services.chat import ChatService
    
    # Initialize service (in prod, this should be a dependency or singleton)
    chat_service = ChatService()
    
    try:
        # We assume the user ID comes from the auth token
        user_id = current_user.get("uid")
        
        # Execute the agent crew
        result = chat_service.run_intake_session(request.content, user_id)
        
        # Result from CrewAI is typically a string or an object with 'raw'
        response_content = str(result)
        
        return SendMessageResponse(
            message_id=str(uuid4()),
            content=response_content,
            agent_name="HealthBridge Crew"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: CurrentUser,
):
    """Get all messages in a session."""
    # TODO: Retrieve messages from database (Phase 7)

    return {"session_id": session_id, "messages": []}

"""Chat API router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.services.chat_service import ChatService
from src.database.models import Message
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ===== Request/Response Models =====

class ChatSessionResponse(BaseModel):
    """Chat session response model"""
    id: int
    cloneId: str
    startedAt: str
    lastMessageAt: str
    messageCount: int
    status: str

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    id: str
    sessionId: int
    role: str
    content: str
    createdAt: str
    externalUserName: Optional[str] = None
    ragContext: Optional[dict] = None
    tokensUsed: Optional[int] = None
    responseTimeMs: Optional[int] = None
    feedbackRating: Optional[int] = None
    styleRating: Optional[int] = None
    feedbackSource: Optional[str] = None
    feedbackText: Optional[str] = None

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Send message request model"""
    content: str
    externalUserName: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Send message response model"""
    userMessage: ChatMessageResponse
    cloneMessage: ChatMessageResponse


class SubmitFeedbackRequest(BaseModel):
    """Submit feedback request model (owner-only endpoint)

    Enhanced feedback supports:
    - Content rating (required): Was the response accurate? (-1 or 1)
    - Style rating (optional): Does it sound like me? (-1, 0, or 1)
    - Feedback text (optional): Correction text on negative feedback

    Note: feedback_source is derived server-side from authentication context.
    This endpoint requires auth, so feedback_source is always 'owner'.
    External user feedback requires a separate public endpoint (TODO).
    """
    contentRating: int  # Required: -1 (thumbs down) or 1 (thumbs up)
    styleRating: Optional[int] = None  # Optional: -1, 0, or 1
    feedbackText: Optional[str] = None  # Optional: correction text


class CloneInfoResponse(BaseModel):
    """Clone information response model"""
    cloneId: str
    tenantId: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Helper Functions =====

def message_to_response(message: Message) -> ChatMessageResponse:
    """Convert Message model to ChatMessageResponse"""
    return ChatMessageResponse(
        id=str(message.id),
        sessionId=message.session_id,
        role=message.role,
        content=message.content,
        createdAt=message.created_at.isoformat(),
        externalUserName=message.external_user_name,
        ragContext=message.rag_context_json,
        tokensUsed=message.tokens_used,
        responseTimeMs=message.response_time_ms,
        feedbackRating=message.feedback_rating,
        styleRating=message.style_rating,
        feedbackSource=message.feedback_source,
        feedbackText=message.feedback_text,
    )


# ===== API Endpoints =====

@router.get("/info", response_model=CloneInfoResponse)
async def get_clone_info(
    clone_ctx: CloneContext = Depends(get_clone_context),
):
    """
    Get current user's clone information.
    Lightweight endpoint that returns clone ID and basic info without any side effects.
    """
    return CloneInfoResponse(
        cloneId=str(clone_ctx.clone_id),
        tenantId=str(clone_ctx.tenant_id),
        firstName=clone_ctx.clone.first_name,
        lastName=clone_ctx.clone.last_name,
        email=clone_ctx.clone.email,
    )


@router.post("/chat/session", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def create_or_resume_session(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Create or resume a chat session for the clone owner.
    Returns existing active session or creates a new one.
    """
    try:
        chat_service = ChatService(clone_id=clone_ctx.clone_id, tenant_id=clone_ctx.tenant_id, db=db)
        session = chat_service.get_or_create_owner_session()

        return ChatSessionResponse(
            id=session.id,
            cloneId=str(session.clone_id),
            startedAt=session.started_at.isoformat(),
            lastMessageAt=session.last_message_at.isoformat(),
            messageCount=session.message_count,
            status=session.status,
        )
    except Exception as e:
        logger.error("Error creating/resuming session", error=str(e), clone_id=str(clone_ctx.clone_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or resume session"
        )


@router.post("/chat/session/new", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session (closes existing active sessions).
    Used when owner clicks "New Conversation" button.
    """
    try:
        chat_service = ChatService(clone_id=clone_ctx.clone_id, tenant_id=clone_ctx.tenant_id, db=db)
        session = chat_service.create_new_session(close_existing=True)

        return ChatSessionResponse(
            id=session.id,
            cloneId=str(session.clone_id),
            startedAt=session.started_at.isoformat(),
            lastMessageAt=session.last_message_at.isoformat(),
            messageCount=session.message_count,
            status=session.status,
        )
    except Exception as e:
        logger.error("Error creating new session", error=str(e), clone_id=str(clone_ctx.clone_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create new session"
        )


@router.get("/chat/session/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: int,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Get all messages for a chat session"""
    try:
        chat_service = ChatService(clone_id=clone_ctx.clone_id, tenant_id=clone_ctx.tenant_id, db=db)
        messages = chat_service.get_session_messages(session_id)

        return [message_to_response(msg) for msg in messages]
    except ValueError as e:
        logger.warning("Invalid session access", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error getting messages", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.post("/chat/session/{session_id}/message", response_model=SendMessageResponse)
async def send_message(
    session_id: int,
    request: SendMessageRequest,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Send a message and get clone response.
    Uses RAG to retrieve context and LLM to generate response.
    """
    try:
        chat_service = ChatService(clone_id=clone_ctx.clone_id, tenant_id=clone_ctx.tenant_id, db=db)
        user_msg, clone_msg = chat_service.send_message_and_get_response(
            session_id=session_id,
            user_message=request.content,
            external_user_name=request.externalUserName,
        )

        return SendMessageResponse(
            userMessage=message_to_response(user_msg),
            cloneMessage=message_to_response(clone_msg),
        )
    except ValueError as e:
        logger.warning("Invalid message send", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error sending message", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/chat/message/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_message_feedback(
    message_id: str,
    request: SubmitFeedbackRequest,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Submit enhanced feedback for a clone message (owner-only endpoint).

    Supports dual-dimension feedback:
    - Content rating: Was the response accurate? (required)
    - Style rating: Does it sound like me? (optional)

    Owner feedback is weighted 2x for RL chunk scoring.

    Note: This endpoint requires authentication, so feedback_source is always 'owner'.
    TODO: Create separate public endpoint for external user feedback with 1x weight.
    """
    try:
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID format"
        )

    try:
        chat_service = ChatService(clone_id=clone_ctx.clone_id, tenant_id=clone_ctx.tenant_id, db=db)
        chat_service.submit_feedback(
            message_id=message_uuid,
            content_rating=request.contentRating,
            feedback_source="owner",  # Derived from auth - this endpoint is owner-only
            style_rating=request.styleRating,
            feedback_text=request.feedbackText,
        )

        return None
    except ValueError as e:
        logger.warning("Invalid feedback submission", error=str(e), message_id=message_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error submitting feedback", error=str(e), message_id=message_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )

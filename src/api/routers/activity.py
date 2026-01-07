"""Activity API router - tracks clone actions and conversations"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Session as SessionModel, Message
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ===== Request/Response Models =====

class CloneActionResponse(BaseModel):
    """Clone action response model"""
    id: str
    type: str  # "task" | "decision" | "recommendation" | "other"
    description: str
    platform: Optional[str] = None  # "slack" | "email" | "linkedin" | "x" | "other"
    timestamp: str
    outcome: Optional[str] = None
    relatedConversationId: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: str
    platform: str  # "slack" | "email" | "linkedin" | "x" | "granola" | "fathom" | "other"
    participants: List[str]
    preview: str
    messageCount: Optional[int] = None
    timestamp: str
    lastMessageAt: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class ActionsListResponse(BaseModel):
    """Paginated actions response"""
    items: List[CloneActionResponse]
    total: int
    page: int


class ConversationsListResponse(BaseModel):
    """Paginated conversations response"""
    items: List[ConversationResponse]
    total: int
    page: int


class ActivitySearchResponse(BaseModel):
    """Activity search response"""
    actions: List[CloneActionResponse]
    conversations: List[ConversationResponse]


# ===== Helper Functions =====

def session_to_conversation(session: SessionModel) -> ConversationResponse:
    """Convert Session model to ConversationResponse"""
    # Map session platform to conversation platform
    platform_map = {
        'slack': 'slack',
        'email': 'email',
        'web': 'other',
        'api': 'other',
    }
    platform = platform_map.get(session.external_platform, 'other')
    
    # Get participants from messages and session
    participants = set()
    if session.external_user_name:
        participants.add(session.external_user_name)
    
    # Add participants from messages
    for message in session.messages:
        if message.external_user_name:
            participants.add(message.external_user_name)
    
    # Get preview from first message
    preview = ""
    first_message = session.messages[0] if session.messages else None
    if first_message:
        preview = first_message.content[:200]  # First 200 chars
        if len(first_message.content) > 200:
            preview += "..."
    
    return ConversationResponse(
        id=str(session.id),
        platform=platform,
        participants=list(participants) if participants else ["Unknown"],
        preview=preview or "No messages yet",
        messageCount=session.message_count,
        timestamp=session.started_at.isoformat(),
        lastMessageAt=session.last_message_at.isoformat(),
        metadata={
            "external_platform": session.external_platform,
            "external_user_id": session.external_user_id,
            "status": session.status,
        } if session.external_platform or session.external_user_id else None,
    )


# ===== API Endpoints =====

@router.get("/actions", response_model=ActionsListResponse)
async def get_actions(
    type: Optional[str] = Query(None, description="Filter by action type"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    startDate: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    endDate: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    page: Optional[int] = Query(1, ge=1, description="Page number"),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Get clone actions (tasks, decisions, recommendations).
    
    NOTE: Currently returns empty list as there's no CloneAction table yet.
    This endpoint is prepared for future implementation when action tracking is added.
    """
    # TODO: Implement when CloneAction table is created
    # For now, return empty list
    return ActionsListResponse(
        items=[],
        total=0,
        page=page or 1,
    )


@router.get("/conversations", response_model=ConversationsListResponse)
async def get_conversations(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    participant: Optional[str] = Query(None, description="Filter by participant name"),
    startDate: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    endDate: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    page: Optional[int] = Query(1, ge=1, description="Page number"),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Get conversations the clone has had.
    Returns sessions converted to conversation format.
    """
    try:
        # Build query
        query = db.query(SessionModel).filter(
            SessionModel.clone_id == clone_ctx.clone_id
        )
        
        # Apply filters
        if platform:
            # Map frontend platform names to session platform enum values
            platform_map = {
                'slack': 'slack',
                'email': 'email',
                'linkedin': None,  # Not supported in Session model yet
                'x': None,  # Not supported in Session model yet
                'granola': None,  # Not supported in Session model yet
                'fathom': None,  # Not supported in Session model yet
                'other': ['web', 'api'],
            }
            if platform in platform_map:
                mapped_platform = platform_map[platform]
                if mapped_platform is None:
                    # Platform not supported, return empty
                    return ConversationsListResponse(items=[], total=0, page=page or 1)
                elif isinstance(mapped_platform, list):
                    query = query.filter(SessionModel.external_platform.in_(mapped_platform))
                else:
                    query = query.filter(SessionModel.external_platform == mapped_platform)
        
        if participant:
            query = query.filter(SessionModel.external_user_name.ilike(f"%{participant}%"))
        
        if startDate:
            try:
                start_dt = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
                query = query.filter(SessionModel.started_at >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid startDate format. Use ISO format (e.g., 2024-01-01T00:00:00Z)"
                )
        
        if endDate:
            try:
                end_dt = datetime.fromisoformat(endDate.replace('Z', '+00:00'))
                query = query.filter(SessionModel.started_at <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid endDate format. Use ISO format (e.g., 2024-01-01T00:00:00Z)"
                )
        
        # Get total count
        total = query.count()
        
        # Apply pagination (for now, return all - can add limit/offset later)
        # TODO: Add proper pagination with limit/offset
        # Eager load messages to avoid N+1 queries
        sessions = query.options(joinedload(SessionModel.messages)).order_by(SessionModel.started_at.desc()).all()
        
        # Convert to response format
        conversations = [session_to_conversation(session) for session in sessions]
        
        return ConversationsListResponse(
            items=conversations,
            total=total,
            page=page or 1,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching conversations", error=str(e), clone_id=str(clone_ctx.clone_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/activity/search", response_model=ActivitySearchResponse)
async def search_activity(
    q: str = Query(..., description="Search query"),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Search across actions and conversations.
    """
    try:
        # Search conversations (sessions)
        session_query = db.query(SessionModel).filter(
            SessionModel.clone_id == clone_ctx.clone_id
        )
        
        # Search in external user names and message content
        # Join with messages to search content
        sessions = session_query.join(Message).filter(
            or_(
                SessionModel.external_user_name.ilike(f"%{q}%"),
                Message.content.ilike(f"%{q}%")
            )
        ).options(joinedload(SessionModel.messages)).distinct().order_by(SessionModel.started_at.desc()).limit(50).all()
        
        conversations = [session_to_conversation(session) for session in sessions]
        
        # Actions search - empty for now
        actions: List[CloneActionResponse] = []
        
        return ActivitySearchResponse(
            actions=actions,
            conversations=conversations,
        )
        
    except Exception as e:
        logger.error("Error searching activity", error=str(e), clone_id=str(clone_ctx.clone_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search activity"
        )


@router.get("/activity/{id}", response_model=CloneActionResponse | ConversationResponse)
async def get_activity_item(
    id: str,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Get a specific activity item (action or conversation) by ID.
    """
    try:
        # Try to find as session (conversation)
        # Sessions use numeric IDs
        try:
            session_id = int(id)
            session = db.query(SessionModel).options(joinedload(SessionModel.messages)).filter(
                and_(
                    SessionModel.id == session_id,
                    SessionModel.clone_id == clone_ctx.clone_id
                )
            ).first()
            
            if session:
                return session_to_conversation(session)
        except ValueError:
            # Not a numeric ID, skip session lookup
            pass
        
        # Try to find as action (UUID)
        # TODO: Implement when CloneAction table is created
        # For now, return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity item not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching activity item", error=str(e), id=id, clone_id=str(clone_ctx.clone_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity item"
        )


"""Session Manager - manages conversation sessions and messages"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from src.database.models import Session as SessionModel, Message
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages session creation and conversation_json building (on-demand)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(
        self, 
        clone_id: UUID, 
        external_user_name: Optional[str] = None,
        external_user_id: Optional[str] = None,
        external_platform: Optional[str] = None
    ) -> SessionModel:
        """Create new conversation session"""
        session = SessionModel(
            clone_id=clone_id,
            external_user_name=external_user_name,
            external_user_id=external_user_id,
            external_platform=external_platform,
            status='active',
            message_count=0
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        logger.info("Created new session", session_id=session.id, clone_id=str(clone_id))
        return session
    
    def add_message(
        self, 
        session_id: int, 
        role: str, 
        content: str, 
        external_user_name: Optional[str] = None,
        **kwargs
    ) -> Message:
        """Add message to session and update session metadata"""
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Insert message
        message = Message(
            session_id=session_id,
            clone_id=session.clone_id,
            role=role,
            content=content,
            external_user_name=external_user_name if role == "external_user" else None,
            **kwargs
        )
        self.db.add(message)
        self.db.flush()  # Get message.id without committing
        
        # Update session metadata (but NOT conversation_json - built on-demand)
        session.message_count = self.db.query(func.count(Message.id))\
            .filter(Message.session_id == session_id)\
            .scalar()
        session.last_message_at = datetime.utcnow()
        
        self.db.commit()
        logger.debug("Added message to session", session_id=session_id, role=role, message_id=str(message.id))
        return message
    
    def get_conversation(self, session_id: int) -> List[Dict]:
        """Get full conversation JSON (built on-demand from messages table)"""
        messages = self.db.query(Message)\
            .filter(Message.session_id == session_id)\
            .order_by(Message.created_at)\
            .all()
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "external_user_name": msg.external_user_name,
                "timestamp": msg.created_at.isoformat(),
                "feedback_rating": msg.feedback_rating,
                "feedback_comment": msg.feedback_comment,
                "tokens_used": msg.tokens_used,
                "response_time_ms": msg.response_time_ms,
                "rag_context_json": msg.rag_context_json
            }
            for msg in messages
        ]
    
    def get_session_with_conversation(self, session_id: int) -> Optional[Dict]:
        """Get session with conversation_json (built on-demand)"""
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return None
        
        return {
            "id": session.id,
            "clone_id": str(session.clone_id),
            "external_user_name": session.external_user_name,
            "external_user_id": session.external_user_id,
            "external_platform": session.external_platform,
            "started_at": session.started_at.isoformat(),
            "last_message_at": session.last_message_at.isoformat(),
            "message_count": session.message_count,
            "status": session.status,
            "conversation": self.get_conversation(session_id)  # Built on-demand
        }
    
    def close_session(self, session_id: int):
        """Mark session as closed"""
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.status = 'closed'
            self.db.commit()
            logger.info("Closed session", session_id=session_id)

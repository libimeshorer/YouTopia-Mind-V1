"""Chat service for managing conversations between clone owners and their AI clones.

This service handles the core chat functionality including:
- Session management
- Message creation and storage
- RAG-based context retrieval
- LLM response generation
- Feedback collection and RL score updates

See docs/RL_OVERVIEW.md for documentation on the reinforcement learning system.
"""

import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.models import Session as ChatSession, Message, Clone
from src.rag.retriever import RAGRetriever
from src.rag.clone_vector_store import CloneVectorStore
from src.llm.client import LLMClient
from src.services.chunk_score_service import ChunkScoreService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations with RL-based learning."""

    def __init__(
        self,
        clone_id: UUID,
        tenant_id: UUID,
        db: Session,
        rag_retriever: Optional[RAGRetriever] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.clone_id = clone_id
        self.tenant_id = tenant_id
        self.db = db

        # Initialize RAG retriever with clone-specific vector store
        if rag_retriever:
            self.rag_retriever = rag_retriever
        else:
            clone_vector_store = CloneVectorStore(
                clone_id=clone_id,
                tenant_id=tenant_id,
            )
            self.rag_retriever = RAGRetriever(
                clone_vector_store=clone_vector_store,
                top_k=5,
                min_score=0.5,
            )

        # Initialize LLM client
        self.llm_client = llm_client or LLMClient()

        # Initialize chunk score service for RL-based retrieval boosting
        self.chunk_score_service = ChunkScoreService(db)

    def get_or_create_owner_session(self) -> ChatSession:
        """
        Get or create a chat session for the clone owner.
        Owner-only chat has a single persistent session.
        """
        # Try to find an existing active session for this clone owner
        session = (
            self.db.query(ChatSession)
            .filter(
                ChatSession.clone_id == self.clone_id,
                ChatSession.external_platform == 'web',
                ChatSession.status == 'active',
            )
            .order_by(desc(ChatSession.last_message_at))
            .first()
        )

        if session:
            logger.info("Found existing owner session", session_id=session.id, clone_id=str(self.clone_id))
            return session

        # Create new session for owner
        session = ChatSession(
            clone_id=self.clone_id,
            external_platform='web',
            external_user_name='Owner',
            status='active',
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info("Created new owner session", session_id=session.id, clone_id=str(self.clone_id))
        return session

    def create_new_session(self, close_existing: bool = True) -> ChatSession:
        """
        Create a new chat session, optionally closing existing active sessions.
        Used when owner clicks "New Conversation" button.
        """
        if close_existing:
            # Close all active sessions for this clone owner
            active_sessions = (
                self.db.query(ChatSession)
                .filter(
                    ChatSession.clone_id == self.clone_id,
                    ChatSession.external_platform == 'web',
                    ChatSession.status == 'active',
                )
                .all()
            )

            for session in active_sessions:
                session.status = 'closed'

            self.db.commit()
            logger.info(
                "Closed existing owner sessions",
                count=len(active_sessions),
                clone_id=str(self.clone_id)
            )

        # Create new session
        session = ChatSession(
            clone_id=self.clone_id,
            external_platform='web',
            external_user_name='Owner',
            status='active',
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info("Created new conversation", session_id=session.id, clone_id=str(self.clone_id))
        return session

    def get_session_messages(self, session_id: int) -> List[Message]:
        """Get all messages for a session"""
        messages = (
            self.db.query(Message)
            .filter(
                Message.session_id == session_id,
                Message.clone_id == self.clone_id,
            )
            .order_by(Message.created_at.asc())
            .all()
        )

        return messages

    def send_message_and_get_response(
        self,
        session_id: int,
        user_message: str,
        external_user_name: Optional[str] = None,
    ) -> Tuple[Message, Message]:
        """
        Send a user message and generate clone response with RAG.
        Returns tuple of (user_message, clone_message).
        """
        start_time = time.time()

        # Get session
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.clone_id != self.clone_id:
            raise ValueError(f"Session {session_id} does not belong to clone {self.clone_id}")

        # Create user message
        user_msg = Message(
            clone_id=self.clone_id,
            session_id=session_id,
            role='external_user',
            content=user_message,
            external_user_name=external_user_name or 'Owner',
        )
        self.db.add(user_msg)
        self.db.flush()  # Get ID without committing

        logger.info(
            "User message created",
            session_id=session_id,
            message_id=str(user_msg.id),
            preview=user_message[:50]
        )

        # Load learned chunk scores for RL-based retrieval boosting
        # TODO: Cache chunk scores in Redis to avoid loading all scores from DB on every message.
        # Current approach loads ALL scores for clone on each message, which is O(n) where n = scored chunks.
        # For clones with 10,000+ scored chunks, this becomes a performance bottleneck.
        # Options: Redis cache with TTL, or session-level cache invalidated on feedback.
        chunk_scores = self.chunk_score_service.get_score_map(self.clone_id)
        self.rag_retriever.set_chunk_scores(chunk_scores)

        # Retrieve RAG context (with RL boosting if scores exist)
        logger.info("Retrieving RAG context", query_preview=user_message[:50])
        rag_results = self.rag_retriever.retrieve(
            query=user_message,
            top_k=5,
        )

        # Format RAG context for LLM
        rag_context_str = self.rag_retriever.format_context(rag_results)

        # Build RAG context JSON for storage
        rag_context_json = {
            "chunks": [
                {
                    "content": result.get("text", ""),
                    "score": 1.0 - result.get("distance", 0.5),  # Convert distance to similarity score
                    "metadata": result.get("metadata", {}),
                }
                for result in rag_results
            ]
        }

        logger.info("RAG context retrieved", chunks_count=len(rag_results))

        # Get conversation history for context
        conversation_history = self.get_session_messages(session_id)

        # Build messages for LLM
        # Get clone info for personality
        clone = self.db.query(Clone).filter(Clone.id == self.clone_id).first()
        clone_name = (
            f"{clone.first_name} {clone.last_name}".strip()
            if clone and clone.first_name
            else "the AI Clone"
        )

        llm_messages = self._build_llm_messages(
            clone_name=clone_name,
            rag_context=rag_context_str,
            conversation_history=conversation_history,
            current_message=user_message,
        )

        # Generate clone response
        logger.info("Generating clone response")
        llm_response = self.llm_client.generate(
            messages=llm_messages,
            temperature=0.7,
        )

        clone_response_text = llm_response.choices[0].message.content

        # Get token usage
        usage_stats = self.llm_client.get_usage_stats(llm_response)
        tokens_used = usage_stats.get("total_tokens", 0)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Create clone message
        clone_msg = Message(
            clone_id=self.clone_id,
            session_id=session_id,
            role='clone',
            content=clone_response_text,
            rag_context_json=rag_context_json,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
        )
        self.db.add(clone_msg)

        # Update session stats
        # FIX BUG #6: Use current time explicitly instead of clone_msg.created_at
        # (created_at is set by database and won't have a value until after commit)
        current_time = datetime.utcnow()
        session.message_count = session.message_count + 2  # User message + clone message
        session.last_message_at = current_time

        # Commit all changes
        self.db.commit()
        self.db.refresh(user_msg)
        self.db.refresh(clone_msg)
        self.db.refresh(session)

        logger.info(
            "Clone response generated",
            session_id=session_id,
            user_message_id=str(user_msg.id),
            clone_message_id=str(clone_msg.id),
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            rag_chunks=len(rag_results),
        )

        return user_msg, clone_msg

    def submit_feedback(
        self,
        message_id: UUID,
        content_rating: int,
        feedback_source: str,
        style_rating: Optional[int] = None,
        feedback_text: Optional[str] = None,
    ) -> Message:
        """
        Submit feedback for a clone message and update RL chunk scores.

        This method:
        1. Validates the feedback
        2. Updates the message's feedback fields
        3. Updates chunk scores based on which chunks were used in this response
           (owner feedback weighted 2x)

        Args:
            message_id: The clone message to rate
            content_rating: -1 (thumbs down) or 1 (thumbs up) for content quality
            feedback_source: 'owner' or 'external_user'
            style_rating: Optional -1, 0, or 1 for "sounds like me" (owner only)
            feedback_text: Optional correction text on negative feedback

        Returns:
            The updated message

        See docs/RL_OVERVIEW.md for details on how feedback affects chunk scores.
        """
        # Validate content rating
        if content_rating not in [-1, 1]:
            raise ValueError("content_rating must be -1 (thumbs down) or 1 (thumbs up)")

        # Validate feedback source
        if feedback_source not in ['owner', 'external_user']:
            raise ValueError("feedback_source must be 'owner' or 'external_user'")

        # Validate style rating (optional, owner only)
        if style_rating is not None:
            if style_rating not in [-1, 0, 1]:
                raise ValueError("style_rating must be -1, 0, or 1")
            if feedback_source != 'owner':
                raise ValueError("style_rating is only available for owner feedback")

        # Get message
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise ValueError(f"Message {message_id} not found")

        if message.clone_id != self.clone_id:
            raise ValueError(f"Message {message_id} does not belong to clone {self.clone_id}")

        if message.role != 'clone':
            raise ValueError("Can only submit feedback for clone messages")

        # Update feedback fields on the message
        message.feedback_rating = content_rating
        message.feedback_source = feedback_source
        message.style_rating = style_rating
        message.feedback_text = feedback_text
        self.db.commit()
        self.db.refresh(message)

        # Determine weight: owner feedback counts 2x
        weight = 2.0 if feedback_source == 'owner' else 1.0

        # Update chunk scores for RL-based learning
        # This uses the RAG context stored with the message to know which chunks to update
        if message.rag_context_json:
            chunks_updated = self.chunk_score_service.update_scores_from_feedback(
                clone_id=self.clone_id,
                rag_context=message.rag_context_json,
                rating=content_rating,
                weight=weight,
            )
            logger.info(
                "Feedback submitted with RL update",
                message_id=str(message_id),
                content_rating=content_rating,
                style_rating=style_rating,
                feedback_source=feedback_source,
                weight=weight,
                session_id=message.session_id,
                chunks_updated=chunks_updated,
            )
        else:
            logger.info(
                "Feedback submitted (no RAG context for RL)",
                message_id=str(message_id),
                content_rating=content_rating,
                style_rating=style_rating,
                feedback_source=feedback_source,
                session_id=message.session_id,
            )

        return message

    def _build_llm_messages(
        self,
        clone_name: str,
        rag_context: str,
        conversation_history: List[Message],
        current_message: str,
    ) -> List[Dict[str, str]]:
        """Build messages array for LLM API call"""
        messages = []

        # System message with RAG context
        system_prompt = f"""You are {clone_name}, an AI clone assistant. You help your owner by answering questions based on your knowledge.

Your knowledge comes from the following sources:

{rag_context if rag_context else "No specific context available for this query."}

Instructions:
- Answer as {clone_name}, speaking in first person
- Use the provided context to answer questions accurately
- If the context doesn't contain relevant information, say so honestly
- Be helpful, concise, and professional
- Maintain conversation continuity by referencing earlier messages when relevant
"""

        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        # Add conversation history (last 10 messages for context)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        for msg in recent_history:
            role = "user" if msg.role == "external_user" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content,
            })

        # Add current message
        messages.append({
            "role": "user",
            "content": current_message,
        })

        return messages

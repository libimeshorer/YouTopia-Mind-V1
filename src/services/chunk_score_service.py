"""Chunk Score Service - Reinforcement learning for RAG retrieval quality.

This service manages learned quality scores for document chunks based on user feedback.
When users give thumbs up/down on clone responses, we track which chunks were retrieved
and update their scores using an exponential moving average.

See docs/RL_OVERVIEW.md for detailed documentation on the RL system.
"""

from typing import Dict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.database.models import ChunkScore
from src.rag.utils import RL_DECAY, RL_LEARNING_RATE, hash_chunk_content
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChunkScoreService:
    """Service for managing chunk quality scores based on user feedback.

    Key concepts:
    - Each chunk is identified by SHA256 hash of its content
    - Scores are updated using Exponential Moving Average (EMA)
    - Scores are applied as boosts during RAG retrieval

    Constants are defined in src/rag/utils.py (single source of truth):
    - RL_DECAY (0.9): How much to weight historical score vs new feedback
    - RL_LEARNING_RATE (0.1): Weight of new feedback (1 - DECAY)
    - RL_MAX_BOOST (0.3): Maximum score adjustment during retrieval
    """

    def __init__(self, db: Session):
        self.db = db

    def update_scores_from_feedback(
        self,
        clone_id: UUID,
        rag_context: Dict,
        rating: int,
        weight: float = 1.0
    ) -> int:
        """Update chunk scores when user submits feedback on a response.

        Uses PostgreSQL UPSERT to atomically update scores with EMA:
        - New chunks: score = rating * RL_LEARNING_RATE * weight
        - Existing chunks: score = score * RL_DECAY + rating * RL_LEARNING_RATE * weight

        Args:
            clone_id: The clone that generated the response
            rag_context: The rag_context_json from the message (contains chunks)
            rating: +1 (thumbs up) or -1 (thumbs down)
            weight: Feedback weight multiplier (default 1.0, owner feedback uses 2.0)

        Returns:
            Number of chunks updated
        """
        chunks = rag_context.get("chunks", [])
        if not chunks:
            logger.debug("No chunks in rag_context, skipping score update")
            return 0

        updated_count = 0
        weighted_learning_rate = RL_LEARNING_RATE * weight

        for chunk in chunks:
            content = chunk.get("content", "")
            if not content:
                continue

            chunk_hash = hash_chunk_content(content)

            # PostgreSQL UPSERT with exponential moving average (weighted)
            stmt = insert(ChunkScore).values(
                clone_id=clone_id,
                chunk_hash=chunk_hash,
                score=rating * weighted_learning_rate,
                hit_count=1
            ).on_conflict_do_update(
                index_elements=['clone_id', 'chunk_hash'],
                set_={
                    'score': ChunkScore.score * RL_DECAY + rating * weighted_learning_rate,
                    'hit_count': ChunkScore.hit_count + 1
                }
            )
            self.db.execute(stmt)
            updated_count += 1

        self.db.commit()

        logger.info(
            "Chunk scores updated from feedback",
            clone_id=str(clone_id),
            rating=rating,
            weight=weight,
            chunks_updated=updated_count
        )

        return updated_count

    def get_score_map(self, clone_id: UUID) -> Dict[str, float]:
        """Get all chunk scores for a clone as a hash -> score mapping.

        This is called before RAG retrieval to get scores for boosting.
        Returns empty dict if no scores exist (graceful degradation).

        Args:
            clone_id: The clone to get scores for

        Returns:
            Dictionary mapping chunk_hash to score
        """
        rows = self.db.query(ChunkScore).filter(
            ChunkScore.clone_id == clone_id
        ).all()

        score_map = {row.chunk_hash: row.score for row in rows}

        if score_map:
            logger.debug(
                "Chunk scores loaded",
                clone_id=str(clone_id),
                scores_count=len(score_map)
            )

        return score_map

    def get_clone_stats(self, clone_id: UUID) -> Dict:
        """Get statistics about chunk scores for a clone (for debugging/analytics).

        Args:
            clone_id: The clone to get stats for

        Returns:
            Dictionary with score statistics
        """
        from sqlalchemy import func

        stats = self.db.query(
            func.count(ChunkScore.chunk_hash).label('total_chunks'),
            func.avg(ChunkScore.score).label('avg_score'),
            func.min(ChunkScore.score).label('min_score'),
            func.max(ChunkScore.score).label('max_score'),
            func.sum(ChunkScore.hit_count).label('total_hits')
        ).filter(
            ChunkScore.clone_id == clone_id
        ).first()

        return {
            'total_chunks': stats.total_chunks or 0,
            'avg_score': float(stats.avg_score) if stats.avg_score else 0.0,
            'min_score': float(stats.min_score) if stats.min_score else 0.0,
            'max_score': float(stats.max_score) if stats.max_score else 0.0,
            'total_hits': stats.total_hits or 0
        }

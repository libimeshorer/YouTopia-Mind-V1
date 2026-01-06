"""Chunk Score Service - Reinforcement learning for RAG retrieval quality.

This service manages learned quality scores for document chunks based on user feedback.
When users give thumbs up/down on clone responses, we track which chunks were retrieved
and update their scores using an exponential moving average.

See docs/RL_OVERVIEW.md for detailed documentation on the RL system.
"""

import hashlib
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.database.models import ChunkScore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChunkScoreService:
    """Service for managing chunk quality scores based on user feedback.

    Key concepts:
    - Each chunk is identified by SHA256 hash of its content
    - Scores are updated using Exponential Moving Average (EMA)
    - Scores are applied as boosts during RAG retrieval

    Constants (tunable):
    - DECAY (0.9): How much to weight historical score vs new feedback
    - LEARNING_RATE (0.1): Weight of new feedback (1 - DECAY)
    - MAX_BOOST (0.3): Maximum score adjustment during retrieval
    """

    # EMA decay factor: new_score = old_score * DECAY + rating * LEARNING_RATE
    # 0.9 means ~10 recent feedbacks have significant influence
    DECAY = 0.9
    LEARNING_RATE = 0.1  # = 1 - DECAY

    # Maximum boost/penalty to apply during retrieval
    # 0.3 means a perfect score (+1) adds 0.3 to similarity
    MAX_BOOST = 0.3

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def hash_chunk(content: str) -> str:
        """Generate SHA256 hash of chunk content for deduplication.

        Args:
            content: The text content of the chunk

        Returns:
            64-character hex string (SHA256 hash)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def update_scores_from_feedback(
        self,
        clone_id: UUID,
        rag_context: Dict,
        rating: int
    ) -> int:
        """Update chunk scores when user submits feedback on a response.

        Uses PostgreSQL UPSERT to atomically update scores with EMA:
        - New chunks: score = rating * LEARNING_RATE
        - Existing chunks: score = score * DECAY + rating * LEARNING_RATE

        Args:
            clone_id: The clone that generated the response
            rag_context: The rag_context_json from the message (contains chunks)
            rating: +1 (thumbs up) or -1 (thumbs down)

        Returns:
            Number of chunks updated
        """
        chunks = rag_context.get("chunks", [])
        if not chunks:
            logger.debug("No chunks in rag_context, skipping score update")
            return 0

        updated_count = 0

        for chunk in chunks:
            content = chunk.get("content", "")
            if not content:
                continue

            chunk_hash = self.hash_chunk(content)

            # PostgreSQL UPSERT with exponential moving average
            stmt = insert(ChunkScore).values(
                clone_id=clone_id,
                chunk_hash=chunk_hash,
                score=rating * self.LEARNING_RATE,
                hit_count=1
            ).on_conflict_do_update(
                index_elements=['clone_id', 'chunk_hash'],
                set_={
                    'score': ChunkScore.score * self.DECAY + rating * self.LEARNING_RATE,
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

    def get_boost(self, score: float) -> float:
        """Convert a chunk score to a retrieval boost value.

        The boost is capped at ±MAX_BOOST to prevent scores from
        completely overriding semantic similarity.

        Args:
            score: The learned chunk score (roughly -1 to +1)

        Returns:
            Boost value to add to similarity score (±MAX_BOOST max)
        """
        return max(-self.MAX_BOOST, min(self.MAX_BOOST, score * self.MAX_BOOST))

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

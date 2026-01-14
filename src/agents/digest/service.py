"""Digest Service - generates on-demand digests from observations"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.models import AgentObservation, AgentCapability

logger = logging.getLogger(__name__)

# Default limits for digest sections
DEFAULT_INTERESTING_LIMIT = 10
DEFAULT_REVIEW_LIMIT = 10
DEFAULT_SAMPLE_LIMIT = 5


class DigestService:
    """
    Generates on-demand digests from agent observations.
    Groups observations by classification and provides stats.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_digest(
        self,
        clone_id: UUID,
        days: int = 7,
        interesting_limit: int = DEFAULT_INTERESTING_LIMIT,
        review_limit: int = DEFAULT_REVIEW_LIMIT,
        sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    ) -> dict:
        """
        Generate a digest of observations for a clone.

        Args:
            clone_id: The clone to generate digest for
            days: Number of days to look back
            interesting_limit: Max items in "interesting" section
            review_limit: Max items in "review_needed" section
            sample_limit: Max items in "not_interesting" sample

        Returns:
            Dict with categorized observations and stats
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Base query
        base_query = (
            self.db.query(AgentObservation)
            .filter(AgentObservation.clone_id == clone_id)
            .filter(AgentObservation.created_at >= since)
            .order_by(desc(AgentObservation.observed_at))
        )

        # Fetch very_interesting (all of them)
        very_interesting = (
            base_query
            .filter(AgentObservation.classification == "very_interesting")
            .all()
        )

        # Fetch interesting (limited, unreviewed first)
        interesting = (
            base_query
            .filter(AgentObservation.classification == "interesting")
            .order_by(
                AgentObservation.status == "classified",  # Unreviewed first
                desc(AgentObservation.observed_at)
            )
            .limit(interesting_limit)
            .all()
        )

        # Fetch needs_review (limited)
        review_needed = (
            base_query
            .filter(AgentObservation.needs_review == True)
            .filter(AgentObservation.status == "classified")  # Only unreviewed
            .limit(review_limit)
            .all()
        )

        # Fetch not_interesting sample (limited)
        not_interesting_sample = (
            base_query
            .filter(AgentObservation.classification == "not_interesting")
            .filter(AgentObservation.needs_review == False)
            .limit(sample_limit)
            .all()
        )

        # Calculate stats
        total_count = base_query.count()
        pending_count = (
            base_query
            .filter(AgentObservation.status == "classified")
            .count()
        )

        # Get last observation timestamp
        last_observation = base_query.first()
        last_observation_at = last_observation.observed_at if last_observation else None

        # Count totals per category
        interesting_total = (
            base_query
            .filter(AgentObservation.classification == "interesting")
            .count()
        )
        review_total = (
            base_query
            .filter(AgentObservation.needs_review == True)
            .filter(AgentObservation.status == "classified")
            .count()
        )

        return {
            "very_interesting": [self._format_observation(obs) for obs in very_interesting],
            "interesting": [self._format_observation(obs) for obs in interesting],
            "review_needed": [self._format_observation(obs) for obs in review_needed],
            "not_interesting_sample": [self._format_observation(obs) for obs in not_interesting_sample],
            "stats": {
                "total_observations": total_count,
                "pending_review": pending_count,
                "very_interesting_count": len(very_interesting),
                "interesting_count": interesting_total,
                "interesting_shown": len(interesting),
                "review_needed_count": review_total,
                "last_observation_at": last_observation_at.isoformat() if last_observation_at else None,
                "period_days": days,
            },
        }

    def _format_observation(self, obs: AgentObservation) -> dict:
        """Format an observation for the digest response"""
        return {
            "id": str(obs.id),
            "content": obs.content,
            "source_metadata": obs.source_metadata,
            "classification": obs.classification,
            "classification_confidence": obs.classification_confidence,
            "classification_reasoning": obs.classification_reasoning,
            "needs_review": obs.needs_review,
            "user_feedback": obs.user_feedback,
            "status": obs.status,
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
            "created_at": obs.created_at.isoformat() if obs.created_at else None,
        }

    def get_observation(self, clone_id: UUID, observation_id: UUID) -> Optional[AgentObservation]:
        """Get a single observation by ID"""
        return (
            self.db.query(AgentObservation)
            .filter(AgentObservation.id == observation_id)
            .filter(AgentObservation.clone_id == clone_id)
            .first()
        )

    def get_digest_stats(self, clone_id: UUID, days: int = 7) -> dict:
        """Get just the stats without full observations"""
        since = datetime.utcnow() - timedelta(days=days)

        base_query = (
            self.db.query(AgentObservation)
            .filter(AgentObservation.clone_id == clone_id)
            .filter(AgentObservation.created_at >= since)
        )

        return {
            "total": base_query.count(),
            "very_interesting": base_query.filter(AgentObservation.classification == "very_interesting").count(),
            "interesting": base_query.filter(AgentObservation.classification == "interesting").count(),
            "not_interesting": base_query.filter(AgentObservation.classification == "not_interesting").count(),
            "pending_review": base_query.filter(AgentObservation.status == "classified").count(),
            "reviewed": base_query.filter(AgentObservation.status == "reviewed").count(),
        }

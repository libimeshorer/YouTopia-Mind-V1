"""Feedback Service - processes user feedback and updates preferences"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.database.models import AgentObservation, AgentPreference

logger = logging.getLogger(__name__)

# Valid feedback values
VALID_FEEDBACK = ["confirmed", "corrected_to_very_interesting", "corrected_to_interesting", "corrected_to_not_interesting"]


class FeedbackService:
    """
    Processes user feedback on observations.
    Updates preferences with new examples from corrections.
    """

    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(
        self,
        clone_id: UUID,
        observation_id: UUID,
        feedback: str,
        comment: Optional[str] = None,
    ) -> dict:
        """
        Process user feedback on an observation.

        Args:
            clone_id: The clone owner
            observation_id: The observation being reviewed
            feedback: "confirmed" or "corrected_to_{category}"
            comment: Optional user comment explaining the correction

        Returns:
            Dict with success status and whether preference was updated
        """
        # Validate feedback value
        if feedback not in VALID_FEEDBACK:
            raise ValueError(f"Invalid feedback: {feedback}. Must be one of {VALID_FEEDBACK}")

        # Get the observation
        observation = (
            self.db.query(AgentObservation)
            .filter(AgentObservation.id == observation_id)
            .filter(AgentObservation.clone_id == clone_id)
            .first()
        )

        if not observation:
            raise ValueError(f"Observation {observation_id} not found")

        # Update observation
        observation.user_feedback = feedback
        observation.status = "reviewed"

        preference_updated = False

        # If it's a correction, add as example to correct preference
        if feedback.startswith("corrected_to_"):
            correct_category = feedback.replace("corrected_to_", "")
            preference_updated = self._add_example_to_preference(
                clone_id=clone_id,
                category=correct_category,
                observation=observation,
                comment=comment,
            )

        self.db.commit()

        return {
            "success": True,
            "preference_updated": preference_updated,
            "observation_id": str(observation_id),
            "feedback": feedback,
        }

    def _add_example_to_preference(
        self,
        clone_id: UUID,
        category: str,
        observation: AgentObservation,
        comment: Optional[str] = None,
    ) -> bool:
        """Add observation as example to the specified preference category"""
        # Get or create preference
        preference = (
            self.db.query(AgentPreference)
            .filter(AgentPreference.clone_id == clone_id)
            .filter(AgentPreference.capability_type == "observer")
            .filter(AgentPreference.preference_type == category)
            .first()
        )

        if not preference:
            # Create new preference
            preference = AgentPreference(
                clone_id=clone_id,
                capability_type="observer",
                platform=None,  # Universal
                preference_type=category,
                description="",
                keywords=[],
                examples=[],
            )
            self.db.add(preference)

        # Build example
        example = {
            "id": str(uuid4()),
            "text": observation.content[:500],  # Truncate for storage
            "explanation": comment or f"User correction from {observation.classification}",
            "source": "user_feedback",
            "added_at": datetime.utcnow().isoformat(),
            "metadata": observation.source_metadata,
            "original_classification": observation.classification,
        }

        # Add to examples list
        examples = list(preference.examples) if preference.examples else []
        examples.append(example)
        preference.examples = examples

        logger.info(f"Added example to preference {category} for clone {clone_id}")
        return True

    def add_manual_example(
        self,
        clone_id: UUID,
        category: str,
        text: str,
        explanation: str,
    ) -> dict:
        """
        Manually add an example to a preference category.
        Used during setup or when user wants to add examples directly.
        """
        if category not in ["very_interesting", "interesting", "not_interesting"]:
            raise ValueError(f"Invalid category: {category}")

        # Get or create preference
        preference = (
            self.db.query(AgentPreference)
            .filter(AgentPreference.clone_id == clone_id)
            .filter(AgentPreference.capability_type == "observer")
            .filter(AgentPreference.preference_type == category)
            .first()
        )

        if not preference:
            preference = AgentPreference(
                clone_id=clone_id,
                capability_type="observer",
                platform=None,
                preference_type=category,
                description="",
                keywords=[],
                examples=[],
            )
            self.db.add(preference)

        # Build example
        example = {
            "id": str(uuid4()),
            "text": text[:500],
            "explanation": explanation,
            "source": "user_provided",
            "added_at": datetime.utcnow().isoformat(),
        }

        # Add to examples
        examples = list(preference.examples) if preference.examples else []
        examples.append(example)
        preference.examples = examples

        self.db.commit()

        return {
            "success": True,
            "example_id": example["id"],
            "category": category,
        }

    def get_preferences(self, clone_id: UUID) -> list[dict]:
        """Get all preferences for a clone"""
        preferences = (
            self.db.query(AgentPreference)
            .filter(AgentPreference.clone_id == clone_id)
            .filter(AgentPreference.capability_type == "observer")
            .all()
        )

        return [
            {
                "id": str(pref.id),
                "preference_type": pref.preference_type,
                "platform": pref.platform,
                "description": pref.description,
                "keywords": pref.keywords,
                "examples_count": len(pref.examples) if pref.examples else 0,
            }
            for pref in preferences
        ]

    def update_preference_description(
        self,
        clone_id: UUID,
        category: str,
        description: str,
        keywords: Optional[list[str]] = None,
    ) -> dict:
        """Update the description and keywords for a preference"""
        preference = (
            self.db.query(AgentPreference)
            .filter(AgentPreference.clone_id == clone_id)
            .filter(AgentPreference.capability_type == "observer")
            .filter(AgentPreference.preference_type == category)
            .first()
        )

        if not preference:
            preference = AgentPreference(
                clone_id=clone_id,
                capability_type="observer",
                platform=None,
                preference_type=category,
                description=description,
                keywords=keywords or [],
                examples=[],
            )
            self.db.add(preference)
        else:
            preference.description = description
            if keywords is not None:
                preference.keywords = keywords

        self.db.commit()

        return {
            "success": True,
            "preference_type": category,
        }

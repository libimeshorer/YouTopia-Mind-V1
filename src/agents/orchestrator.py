"""Agent Orchestrator - coordinates observation and classification flows"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.database.models import AgentCapability, AgentObservation, Clone
from src.agents.capabilities.slack.observer import SlackObserver
from src.agents.classification.classifier import Classifier

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Coordinates agent capabilities for clones.
    Handles observation → classification → storage flow.
    """

    def __init__(self, db: Session):
        self.db = db

    def run_all_observations(self) -> dict:
        """
        Run observations for all clones with active observer capabilities.
        Called by Celery beat task every 4 hours.
        """
        # Get all active observer capabilities
        capabilities = (
            self.db.query(AgentCapability)
            .filter(AgentCapability.status == "active")
            .filter(AgentCapability.capability_type == "observer")
            .all()
        )

        results = {
            "total_capabilities": len(capabilities),
            "successful": 0,
            "failed": 0,
            "observations_created": 0,
        }

        for capability in capabilities:
            try:
                result = self.run_observation_for_clone(
                    str(capability.clone_id),
                    str(capability.id)
                )
                results["successful"] += 1
                results["observations_created"] += result.get("observations_stored", 0)
            except Exception as e:
                logger.error(f"Failed to run observation for capability {capability.id}: {e}")
                results["failed"] += 1
                # Update capability status to error
                capability.status = "error"
                capability.error_message = str(e)
                self.db.commit()

        return results

    def run_observation_for_clone(self, clone_id: str, capability_id: str) -> dict:
        """
        Run observation and classification for a single clone.

        Flow:
        1. Fetch new messages from Slack
        2. Classify all messages in memory
        3. Store only interesting + 10% sample
        4. Update checkpoints
        """
        capability = (
            self.db.query(AgentCapability)
            .filter(AgentCapability.id == capability_id)
            .filter(AgentCapability.clone_id == clone_id)
            .first()
        )

        if not capability:
            raise ValueError(f"Capability {capability_id} not found for clone {clone_id}")

        if capability.platform != "slack":
            raise ValueError(f"Unsupported platform: {capability.platform}")

        # Initialize observer and classifier
        observer = SlackObserver(self.db, capability)
        classifier = Classifier(self.db, UUID(clone_id))

        # Step 1: Fetch new messages
        logger.info(f"Fetching messages for capability {capability_id}")
        raw_messages = observer.fetch_new_messages()
        logger.info(f"Fetched {len(raw_messages)} new messages")

        if not raw_messages:
            # Update last_run_at even if no messages
            capability.last_run_at = datetime.utcnow()
            self.db.commit()
            return {"messages_fetched": 0, "observations_stored": 0}

        # Step 2: Classify all messages in memory
        logger.info(f"Classifying {len(raw_messages)} messages")
        classified_messages = classifier.classify_batch(raw_messages)
        logger.info(f"Classification complete")

        # Step 3: Store selectively (interesting + sample)
        observations_stored = observer.store_observations(classified_messages)
        logger.info(f"Stored {observations_stored} observations")

        # Step 4: Update capability last_run_at
        capability.last_run_at = datetime.utcnow()
        capability.status = "active"
        capability.error_message = None
        self.db.commit()

        return {
            "messages_fetched": len(raw_messages),
            "observations_stored": observations_stored,
        }

    def get_capability(self, clone_id: UUID, platform: str, capability_type: str) -> Optional[AgentCapability]:
        """Get a specific capability for a clone"""
        return (
            self.db.query(AgentCapability)
            .filter(AgentCapability.clone_id == clone_id)
            .filter(AgentCapability.platform == platform)
            .filter(AgentCapability.capability_type == capability_type)
            .first()
        )

    def create_capability(
        self,
        clone_id: UUID,
        platform: str,
        capability_type: str,
        config: dict,
        integration_id: Optional[UUID] = None,
    ) -> AgentCapability:
        """Create a new capability for a clone"""
        capability = AgentCapability(
            clone_id=clone_id,
            platform=platform,
            capability_type=capability_type,
            config=config,
            integration_id=integration_id,
            status="active",
        )
        self.db.add(capability)
        self.db.commit()
        self.db.refresh(capability)
        return capability

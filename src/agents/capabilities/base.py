"""Base classes for agent capabilities"""

from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session

from src.database.models import AgentCapability


class BaseObserver(ABC):
    """
    Abstract base class for observers.
    Observers fetch data from external systems (Slack, Email, etc.)
    """

    def __init__(self, db: Session, capability: AgentCapability):
        self.db = db
        self.capability = capability
        self.clone_id = capability.clone_id
        self.config = capability.config or {}

    @abstractmethod
    def fetch_new_messages(self) -> list[dict]:
        """
        Fetch new messages from the external system.
        Returns list of raw message dicts with at least:
        - source_id: unique identifier in the source system
        - content: message text
        - observed_at: when the message was created
        - metadata: dict with source-specific info
        """
        pass

    @abstractmethod
    def store_observations(self, classified_messages: list[dict]) -> int:
        """
        Store classified messages as observations.
        Returns count of observations stored.
        """
        pass

    @abstractmethod
    def get_checkpoint(self, channel_id: str) -> Any:
        """Get the checkpoint for a channel"""
        pass

    @abstractmethod
    def update_checkpoint(self, channel_id: str, last_message_ts: str, seen: int, stored: int):
        """Update the checkpoint for a channel"""
        pass

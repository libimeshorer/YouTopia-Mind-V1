"""Slack Observer - fetches messages from Slack channels"""

import logging
import random
import re
from datetime import datetime
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.orm import Session

from src.database.models import (
    AgentCapability,
    AgentObservation,
    Integration,
    ObservationCheckpoint,
)
from src.agents.capabilities.base import BaseObserver

logger = logging.getLogger(__name__)

# Message subtypes to skip (system messages, not user content)
SKIP_SUBTYPES = [
    "channel_join",
    "channel_leave",
    "channel_topic",
    "channel_purpose",
    "channel_name",
    "bot_add",
    "bot_remove",
    "channel_archive",
    "channel_unarchive",
]


class SlackObserver(BaseObserver):
    """
    Fetches messages from configured Slack channels.
    Handles checkpointing and selective storage.
    """

    def __init__(self, db: Session, capability: AgentCapability):
        super().__init__(db, capability)
        self._slack_client: Optional[WebClient] = None
        self._user_cache: dict[str, str] = {}  # user_id -> display_name
        self._channel_cache: dict[str, str] = {}  # channel_id -> channel_name

    @property
    def slack_client(self) -> WebClient:
        """Lazy-load Slack client from integration credentials"""
        if self._slack_client is None:
            if not self.capability.integration_id:
                raise ValueError("No integration linked to capability")

            integration = (
                self.db.query(Integration)
                .filter(Integration.id == self.capability.integration_id)
                .first()
            )

            if not integration:
                raise ValueError("Integration not found")

            if integration.status != "connected":
                raise ValueError(f"Integration not connected: {integration.status}")

            # Get bot token from integration credentials
            # Note: credentials_encrypted should be decrypted here
            # For now, assuming it's stored as JSON with bot_token
            import json
            try:
                creds = json.loads(integration.credentials_encrypted) if integration.credentials_encrypted else {}
            except json.JSONDecodeError:
                creds = {}

            bot_token = creds.get("bot_token") or creds.get("access_token")
            if not bot_token:
                raise ValueError("No bot token in integration credentials")

            self._slack_client = WebClient(token=bot_token)

        return self._slack_client

    def fetch_new_messages(self) -> list[dict]:
        """
        Fetch new messages from all configured channels.
        Returns list of raw message dicts.
        """
        channels = self.config.get("channels", [])
        if not channels:
            logger.warning(f"No channels configured for capability {self.capability.id}")
            return []

        all_messages = []

        for channel_config in channels:
            channel_id = channel_config.get("id") if isinstance(channel_config, dict) else channel_config
            channel_name = channel_config.get("name", channel_id) if isinstance(channel_config, dict) else channel_id

            try:
                messages = self._fetch_channel_messages(channel_id, channel_name)
                all_messages.extend(messages)
            except SlackApiError as e:
                if e.response.get("error") == "channel_not_found":
                    logger.warning(f"Channel {channel_id} not found, skipping")
                elif e.response.get("error") == "not_in_channel":
                    logger.warning(f"Bot not in channel {channel_id}, skipping")
                elif e.response.get("error") == "ratelimited":
                    logger.error(f"Rate limited by Slack API")
                    raise  # Let caller handle retry
                else:
                    logger.error(f"Slack API error for channel {channel_id}: {e}")
                    # Continue with other channels
            except Exception as e:
                logger.error(f"Error fetching channel {channel_id}: {e}")
                # Continue with other channels

        return all_messages

    def _fetch_channel_messages(self, channel_id: str, channel_name: str) -> list[dict]:
        """Fetch messages from a single channel since last checkpoint"""
        checkpoint = self.get_checkpoint(channel_id)
        oldest = checkpoint.last_message_ts if checkpoint else None

        messages = []
        cursor = None
        latest_ts = oldest

        while True:
            try:
                # Fetch conversation history
                kwargs = {
                    "channel": channel_id,
                    "limit": 100,  # Max per request
                }
                if oldest:
                    kwargs["oldest"] = oldest
                if cursor:
                    kwargs["cursor"] = cursor

                response = self.slack_client.conversations_history(**kwargs)

                for msg in response.get("messages", []):
                    # Skip system messages
                    if msg.get("subtype") in SKIP_SUBTYPES:
                        continue

                    # Skip empty messages
                    if not msg.get("text", "").strip():
                        continue

                    # Skip bot messages (optional - could make configurable)
                    if msg.get("bot_id"):
                        continue

                    # Extract text and metadata
                    processed = self._process_message(msg, channel_id, channel_name)
                    if processed:
                        messages.append(processed)

                    # Track latest timestamp for checkpoint
                    if not latest_ts or float(msg["ts"]) > float(latest_ts):
                        latest_ts = msg["ts"]

                # Check for pagination
                if response.get("has_more") and response.get("response_metadata", {}).get("next_cursor"):
                    cursor = response["response_metadata"]["next_cursor"]
                else:
                    break

            except SlackApiError:
                raise

        # Update checkpoint with latest message
        if messages and latest_ts:
            seen = len(messages)
            self.update_checkpoint(channel_id, latest_ts, seen, 0)  # stored count updated after classification

        return messages

    def _process_message(self, msg: dict, channel_id: str, channel_name: str) -> Optional[dict]:
        """Process a raw Slack message into our format"""
        text = msg.get("text", "")
        if not text.strip():
            return None

        # Extract and clean text
        clean_text = self._extract_text(text)
        if not clean_text:
            return None

        # Get author info
        user_id = msg.get("user")
        author_name = self._get_user_name(user_id) if user_id else "Unknown"

        # Parse timestamp
        ts = msg.get("ts", "")
        try:
            observed_at = datetime.fromtimestamp(float(ts))
        except (ValueError, TypeError):
            observed_at = datetime.utcnow()

        return {
            "source_id": ts,
            "content": clean_text,
            "observed_at": observed_at,
            "metadata": {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "author_id": user_id,
                "author_name": author_name,
                "thread_ts": msg.get("thread_ts"),
                "has_thread": msg.get("reply_count", 0) > 0,
            },
        }

    def _extract_text(self, text: str) -> str:
        """Extract plain text from Slack message formatting"""
        # Resolve user mentions: <@U123> → @user
        text = re.sub(r'<@(\w+)>', lambda m: f"@{self._get_user_name(m.group(1))}", text)

        # Resolve channel mentions: <#C123|channel-name> → #channel-name
        text = re.sub(r'<#\w+\|([^>]+)>', r'#\1', text)

        # Clean link formatting: <url|display> → display, <url> → url
        text = re.sub(r'<([^|>]+)\|([^>]+)>', r'\2', text)
        text = re.sub(r'<([^>]+)>', r'\1', text)

        return text.strip()

    def _get_user_name(self, user_id: str) -> str:
        """Get user display name from cache or API"""
        if not user_id:
            return "Unknown"

        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            response = self.slack_client.users_info(user=user_id)
            user = response.get("user", {})
            name = user.get("real_name") or user.get("name") or user_id
            self._user_cache[user_id] = name
            return name
        except SlackApiError:
            self._user_cache[user_id] = user_id
            return user_id

    def get_checkpoint(self, channel_id: str) -> Optional[ObservationCheckpoint]:
        """Get the checkpoint for a channel"""
        return (
            self.db.query(ObservationCheckpoint)
            .filter(ObservationCheckpoint.capability_id == self.capability.id)
            .filter(ObservationCheckpoint.channel_id == channel_id)
            .first()
        )

    def update_checkpoint(self, channel_id: str, last_message_ts: str, seen: int, stored: int):
        """Update or create checkpoint for a channel"""
        checkpoint = self.get_checkpoint(channel_id)

        if checkpoint:
            checkpoint.last_message_ts = last_message_ts
            checkpoint.last_observed_at = datetime.utcnow()
            checkpoint.messages_seen += seen
            checkpoint.messages_stored += stored
        else:
            checkpoint = ObservationCheckpoint(
                capability_id=self.capability.id,
                channel_id=channel_id,
                last_message_ts=last_message_ts,
                last_observed_at=datetime.utcnow(),
                messages_seen=seen,
                messages_stored=stored,
            )
            self.db.add(checkpoint)

        self.db.commit()

    def store_observations(self, classified_messages: list[dict]) -> int:
        """
        Store classified messages as observations.
        Only stores:
        - very_interesting
        - interesting
        - needs_review
        - 10% random sample of not_interesting
        """
        stored_count = 0
        channel_stored_counts: dict[str, int] = {}

        for msg in classified_messages:
            classification = msg.get("classification", "not_interesting")
            needs_review = msg.get("needs_review", False)

            # Decide whether to store
            should_store = (
                classification in ["very_interesting", "interesting"] or
                needs_review or
                (classification == "not_interesting" and random.random() < 0.1)
            )

            if not should_store:
                continue

            # Check for duplicates
            existing = (
                self.db.query(AgentObservation)
                .filter(AgentObservation.clone_id == self.clone_id)
                .filter(AgentObservation.source_type == "slack_message")
                .filter(AgentObservation.source_id == msg["source_id"])
                .first()
            )

            if existing:
                continue

            # Create observation
            observation = AgentObservation(
                clone_id=self.clone_id,
                capability_id=self.capability.id,
                source_type="slack_message",
                source_id=msg["source_id"],
                source_metadata=msg["metadata"],
                content=msg["content"],
                classification=classification,
                classification_confidence=msg.get("confidence"),
                classification_reasoning=msg.get("reasoning"),
                needs_review=needs_review,
                observed_at=msg["observed_at"],
            )
            self.db.add(observation)
            stored_count += 1

            # Track per-channel for checkpoint update
            channel_id = msg["metadata"].get("channel_id")
            if channel_id:
                channel_stored_counts[channel_id] = channel_stored_counts.get(channel_id, 0) + 1

        self.db.commit()

        # Update checkpoint stored counts
        for channel_id, count in channel_stored_counts.items():
            checkpoint = self.get_checkpoint(channel_id)
            if checkpoint:
                checkpoint.messages_stored += count
                self.db.commit()

        return stored_count

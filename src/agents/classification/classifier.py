"""LLM-based classifier for agent observations"""

import json
import logging
from typing import Optional
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.database.models import AgentPreference

logger = logging.getLogger(__name__)

# Maximum examples to include per category in prompt
MAX_EXAMPLES_PER_CATEGORY = 5

# Maximum messages to classify in a single LLM call
MAX_MESSAGES_PER_BATCH = 15

# Confidence threshold below which needs_review is set
CONFIDENCE_THRESHOLD = 0.7


class Classifier:
    """
    LLM-based classifier using few-shot learning from preferences.
    Classifies messages into: very_interesting, interesting, not_interesting
    """

    def __init__(self, db: Session, clone_id: UUID):
        self.db = db
        self.clone_id = clone_id
        self._client: Optional[OpenAI] = None
        self._preferences: Optional[dict] = None

    @property
    def client(self) -> OpenAI:
        """Lazy-load OpenAI client"""
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    @property
    def preferences(self) -> dict:
        """Load preferences for this clone"""
        if self._preferences is None:
            self._preferences = self._load_preferences()
        return self._preferences

    def _load_preferences(self) -> dict:
        """Load preferences from database"""
        prefs = (
            self.db.query(AgentPreference)
            .filter(AgentPreference.clone_id == self.clone_id)
            .filter(AgentPreference.capability_type == "observer")
            .all()
        )

        result = {}
        for pref in prefs:
            result[pref.preference_type] = {
                "description": pref.description,
                "keywords": pref.keywords or [],
                "examples": pref.examples or [],
            }

        # Ensure all categories exist with defaults
        for category in ["very_interesting", "interesting", "not_interesting"]:
            if category not in result:
                result[category] = {
                    "description": self._default_description(category),
                    "keywords": [],
                    "examples": [],
                }

        return result

    def _default_description(self, category: str) -> str:
        """Default descriptions for categories"""
        defaults = {
            "very_interesting": "High-priority opportunities that require immediate attention",
            "interesting": "Worth noting and reviewing, but not urgent",
            "not_interesting": "Routine messages, not relevant to professional goals",
        }
        return defaults.get(category, "")

    def classify_batch(self, messages: list[dict]) -> list[dict]:
        """
        Classify a batch of messages.
        Handles batching for large message sets.
        """
        if not messages:
            return []

        all_results = []

        # Process in batches
        for i in range(0, len(messages), MAX_MESSAGES_PER_BATCH):
            batch = messages[i:i + MAX_MESSAGES_PER_BATCH]
            batch_results = self._classify_batch_internal(batch)
            all_results.extend(batch_results)

        return all_results

    def _classify_batch_internal(self, messages: list[dict]) -> list[dict]:
        """Classify a single batch of messages (max 15)"""
        if not messages:
            return []

        # Build the prompt
        prompt = self._build_classification_prompt(messages)

        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            classifications = result.get("classifications", [])

            # Merge classifications back into messages
            classified_messages = []
            for i, msg in enumerate(messages):
                msg_copy = msg.copy()

                if i < len(classifications):
                    clf = classifications[i]
                    msg_copy["classification"] = clf.get("category", "not_interesting")
                    msg_copy["confidence"] = clf.get("confidence", 0.5)
                    msg_copy["reasoning"] = clf.get("reasoning", "")
                    msg_copy["needs_review"] = clf.get("confidence", 0.5) < CONFIDENCE_THRESHOLD
                else:
                    # Fallback if LLM didn't return enough classifications
                    msg_copy["classification"] = "not_interesting"
                    msg_copy["confidence"] = 0.5
                    msg_copy["reasoning"] = "Classification missing from response"
                    msg_copy["needs_review"] = True

                classified_messages.append(msg_copy)

            return classified_messages

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._fallback_classification(messages)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._fallback_classification(messages)

    def _fallback_classification(self, messages: list[dict]) -> list[dict]:
        """Fallback classification when LLM fails"""
        result = []
        for msg in messages:
            msg_copy = msg.copy()
            msg_copy["classification"] = "not_interesting"
            msg_copy["confidence"] = 0.5
            msg_copy["reasoning"] = "Classification failed, marked for review"
            msg_copy["needs_review"] = True
            result.append(msg_copy)
        return result

    def _system_prompt(self) -> str:
        """System prompt for the classifier"""
        return """You are a message classification assistant. Your job is to classify Slack messages into categories based on the user's preferences.

You must respond with valid JSON in this exact format:
{
    "classifications": [
        {"id": 1, "category": "very_interesting|interesting|not_interesting", "confidence": 0.0-1.0, "reasoning": "brief explanation"}
    ]
}

Guidelines:
- Be consistent in your classifications
- Use confidence scores appropriately: 0.9+ for clear matches, 0.7-0.9 for likely matches, below 0.7 for uncertain
- Keep reasoning brief (1 sentence)
- When in doubt, lean towards "interesting" rather than missing something important"""

    def _build_classification_prompt(self, messages: list[dict]) -> str:
        """Build the classification prompt with preferences and messages"""
        prefs = self.preferences

        # Build preferences section
        pref_lines = []
        for category in ["very_interesting", "interesting", "not_interesting"]:
            pref = prefs.get(category, {})
            desc = pref.get("description", self._default_description(category))
            keywords = pref.get("keywords", [])
            examples = pref.get("examples", [])[:MAX_EXAMPLES_PER_CATEGORY]

            pref_lines.append(f"\n## {category.upper().replace('_', ' ')}")
            pref_lines.append(f"Description: {desc}")

            if keywords:
                pref_lines.append(f"Keywords: {', '.join(keywords)}")

            if examples:
                pref_lines.append("Examples:")
                for ex in examples:
                    text = ex.get("text", "")[:200]  # Truncate long examples
                    explanation = ex.get("explanation", "")
                    if explanation:
                        pref_lines.append(f'- "{text}" ({explanation})')
                    else:
                        pref_lines.append(f'- "{text}"')

        preferences_text = "\n".join(pref_lines)

        # Build messages section
        msg_lines = ["## MESSAGES TO CLASSIFY"]
        for i, msg in enumerate(messages, 1):
            channel = msg.get("metadata", {}).get("channel_name", "unknown")
            author = msg.get("metadata", {}).get("author_name", "unknown")
            content = msg.get("content", "")[:500]  # Truncate long messages

            msg_lines.append(f"""
Message {i}:
- Channel: #{channel}
- Author: {author}
- Content: {content}
""")

        messages_text = "\n".join(msg_lines)

        # Combine into full prompt
        return f"""# CLASSIFICATION PREFERENCES
{preferences_text}

{messages_text}

Classify each message. Respond with JSON containing a "classifications" array with one entry per message in order."""

    def classify_single(self, message: dict) -> dict:
        """Classify a single message (convenience method)"""
        results = self.classify_batch([message])
        return results[0] if results else message

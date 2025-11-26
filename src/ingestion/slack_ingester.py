"""Slack message ingester"""

from typing import List, Dict, Optional
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError as exc:  # pragma: no cover - environment validation
    raise ImportError(
        "slack_sdk is required for Slack ingestion. Install with `pip install slack-sdk`."
    ) from exc

from src.config.settings import settings
from src.utils.logging import get_logger
from src.utils.aws import S3Client
from src.ingestion.chunking import TextChunker

logger = get_logger(__name__)


class SlackIngester:
    """Ingester for Slack messages"""
    
    def __init__(self, bot_token: Optional[str] = None, s3_client: Optional[S3Client] = None):
        self.bot_token = bot_token or settings.slack_bot_token
        self.client = WebClient(token=self.bot_token)
        self.s3_client = s3_client or S3Client()
        self.chunker = TextChunker()
    
    def fetch_channel_messages(
        self,
        channel_id: str,
        limit: int = 1000,
        oldest: Optional[float] = None,
        latest: Optional[float] = None,
    ) -> List[Dict]:
        """Fetch messages from a Slack channel"""
        messages = []
        cursor = None
        
        try:
            while True:
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=min(limit, 200),  # Slack API limit
                    cursor=cursor,
                    oldest=oldest,
                    latest=latest,
                )
                
                if not response["ok"]:
                    logger.error("Error fetching Slack messages", error=response.get("error"))
                    break
                
                messages.extend(response["messages"])
                
                # Check if there are more messages
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                
                if len(messages) >= limit:
                    break
            
            logger.info("Fetched Slack messages", channel=channel_id, count=len(messages))
            return messages
        except SlackApiError as e:
            logger.error("Slack API error", error=str(e))
            raise
    
    def fetch_user_messages(
        self,
        user_id: str,
        limit: int = 1000,
        oldest: Optional[float] = None,
        latest: Optional[float] = None,
    ) -> List[Dict]:
        """Fetch messages from a specific user across all channels"""
        # Note: This requires searching across channels
        # For now, we'll fetch from channels the bot has access to
        messages = []
        
        try:
            # Get list of channels
            channels_response = self.client.conversations_list(types="public_channel,private_channel")
            
            if not channels_response["ok"]:
                logger.error("Error fetching channels", error=channels_response.get("error"))
                return messages
            
            # Search messages in each channel
            for channel in channels_response["channels"]:
                channel_messages = self.fetch_channel_messages(
                    channel["id"],
                    limit=limit,
                    oldest=oldest,
                    latest=latest,
                )
                
                # Filter by user
                user_messages = [
                    msg for msg in channel_messages
                    if msg.get("user") == user_id
                ]
                messages.extend(user_messages)
            
            logger.info("Fetched user messages", user_id=user_id, count=len(messages))
            return messages
        except SlackApiError as e:
            logger.error("Slack API error", error=str(e))
            raise
    
    def format_message(self, message: Dict) -> str:
        """Format a Slack message for ingestion"""
        text = message.get("text", "")
        
        # Add thread replies if available
        if "thread_ts" in message:
            # This is a thread reply, include context
            pass
        
        return text
    
    def ingest_messages(
        self,
        messages: List[Dict],
        source_name: str = "slack",
        user_id: Optional[str] = None,
    ) -> List[Dict]:
        """Ingest Slack messages and return chunks"""
        if not messages:
            return []
        
        logger.info("Ingesting Slack messages", message_count=len(messages))
        
        # Format messages
        formatted_texts = []
        for msg in messages:
            formatted_text = self.format_message(msg)
            if formatted_text.strip():
                formatted_texts.append(formatted_text)
        
        # Combine into chunks (each message or group of messages)
        chunks = []
        for i, text in enumerate(formatted_texts):
            metadata = {
                "source": source_name,
                "message_id": messages[i].get("ts"),
                "user_id": messages[i].get("user") or user_id,
                "channel_id": messages[i].get("channel"),
                "timestamp": messages[i].get("ts"),
            }
            
            # Chunk if message is long
            if len(text) > settings.chunk_size:
                message_chunks = self.chunker.chunk_text(text, metadata)
                chunks.extend(message_chunks)
            else:
                chunks.append({
                    "text": text,
                    "metadata": metadata,
                })
        
        # Save raw messages to S3
        import json
        raw_data = json.dumps(messages, indent=2).encode("utf-8")
        timestamp = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"raw/slack/{timestamp}/messages.json"
        self.s3_client.put_object(s3_key, raw_data, content_type="application/json")
        
        logger.info("Slack messages ingested", chunk_count=len(chunks))
        return chunks


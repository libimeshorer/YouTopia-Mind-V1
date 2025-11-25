"""Message processor for handling Slack messages and generating responses"""

from typing import Optional
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from src.llm.prompt_builder import PromptBuilder
from src.personality.profile import PersonalityProfile
from src.personality.style_analyzer import StyleAnalyzer
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MessageProcessor:
    """Processes Slack messages and generates responses"""
    
    def __init__(
        self,
        prompt_builder: Optional[PromptBuilder] = None,
        style_analyzer: Optional[StyleAnalyzer] = None,
    ):
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.style_analyzer = style_analyzer or StyleAnalyzer()
        self.profile: Optional[PersonalityProfile] = None
        
        # Load profile if available
        self.profile = self.style_analyzer.load_profile()
    
    def process_message(
        self,
        text: str,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> str:
        """Process a message and generate response"""
        try:
            # Remove bot mention if present
            query = text.strip()
            
            logger.info("Processing message", query_preview=query[:50], user_id=user_id)
            
            # Generate response
            response = self.prompt_builder.generate_response(
                query,
                profile=self.profile,
                temperature=0.7,
            )
            
            logger.info("Response generated", response_preview=response[:50])
            return response
        except Exception as e:
            logger.error("Error processing message", error=str(e))
            return "I apologize, but I encountered an error processing your message. Please try again."
    
    def process_message_stream(
        self,
        text: str,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        """Process a message and generate streaming response"""
        try:
            query = text.strip()
            
            logger.info("Processing message (streaming)", query_preview=query[:50], user_id=user_id)
            
            # Generate streaming response
            stream = self.prompt_builder.generate_response(
                query,
                profile=self.profile,
                temperature=0.7,
                stream=True,
            )
            
            return stream
        except Exception as e:
            logger.error("Error processing message stream", error=str(e))
            return None



"""Slack bot event handlers"""

import os
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk.errors import SlackApiError

from src.config.settings import settings
from src.bot.message_processor import MessageProcessor
from src.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Initialize Slack app
app = App(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)

# Initialize message processor
message_processor = MessageProcessor()


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle when bot is mentioned"""
    try:
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        
        logger.info("Bot mentioned", user_id=user_id, channel_id=channel_id)
        
        # Remove bot user ID from text
        try:
            auth_response = client.auth_test()
            bot_user_id = auth_response["user_id"]
        except:
            bot_user_id = None
        
        if bot_user_id:
            query = text.replace(f"<@{bot_user_id}>", "").strip()
        else:
            # Fallback: remove any mention format
            import re
            query = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
        
        if not query:
            say("Hello! How can I help you?", thread_ts=thread_ts)
            return
        
        # Process message
        response = message_processor.process_message(query, user_id=user_id, channel_id=channel_id)
        
        # Send response in thread
        say(response, thread_ts=thread_ts)
        
    except Exception as e:
        logger.error("Error handling mention", error=str(e))
        say("I apologize, but I encountered an error. Please try again.", thread_ts=thread_ts)


@app.event("message")
def handle_message(event, say):
    """Handle direct messages to the bot"""
    try:
        # Only handle direct messages (not channel messages unless mentioned)
        channel_type = event.get("channel_type")
        if channel_type != "im":
            return
        
        text = event.get("text", "")
        user_id = event.get("user")
        channel_id = event.get("channel")
        
        logger.info("Direct message received", user_id=user_id)
        
        if not text.strip():
            return
        
        # Process message
        response = message_processor.process_message(text, user_id=user_id, channel_id=channel_id)
        
        # Send response
        say(response)
        
    except Exception as e:
        logger.error("Error handling message", error=str(e))
        say("I apologize, but I encountered an error. Please try again.")


@app.event("app_home_opened")
def handle_app_home_opened(event, client):
    """Handle app home opened event"""
    try:
        user_id = event["user"]
        
        # You can customize the home tab view here
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Hello! I'm your digital twin. Mention me in a channel or send me a direct message to chat.",
                        },
                    },
                ],
            },
        )
    except Exception as e:
        logger.error("Error handling app home opened", error=str(e))


def handler(event, context):
    """AWS Lambda handler"""
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# For local development
if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    
    if not settings.slack_app_token:
        logger.error("SLACK_APP_TOKEN is required for socket mode")
        exit(1)
    
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()
    logger.info("Slack bot started in socket mode")


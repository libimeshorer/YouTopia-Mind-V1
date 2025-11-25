"""AWS Lambda function entry point for Slack bot"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.bot.slack_handler import handler

# Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler entry point"""
    return handler(event, context)


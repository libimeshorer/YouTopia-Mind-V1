"""Tests for Slack handler"""

import pytest
from unittest.mock import Mock, patch
from src.bot.message_processor import MessageProcessor


@pytest.fixture
def message_processor():
    """Create a test message processor"""
    with patch('src.bot.message_processor.PromptBuilder'):
        with patch('src.bot.message_processor.StyleAnalyzer'):
            return MessageProcessor()


def test_message_processor_initialization(message_processor):
    """Test message processor initialization"""
    assert message_processor is not None
    assert message_processor.prompt_builder is not None



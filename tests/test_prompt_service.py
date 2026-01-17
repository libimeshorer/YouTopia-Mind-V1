"""Tests for PromptService"""

import pytest
from unittest.mock import Mock, MagicMock
from src.llm.prompt_service import PromptService
from src.llm.client import LLMClient
from src.personality.profile import PersonalityProfile, CommunicationStyle


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = Mock(spec=LLMClient)
    return client


@pytest.fixture
def prompt_service(mock_llm_client):
    """Create a PromptService instance with mocked LLM client"""
    return PromptService(llm_client=mock_llm_client)


@pytest.fixture
def sample_message():
    """Create a sample Message object for testing"""
    message = MagicMock()
    message.role = "external_user"
    message.content = "Hello, how are you?"
    return message


@pytest.fixture
def sample_clone_message():
    """Create a sample clone Message object for testing"""
    message = MagicMock()
    message.role = "clone"
    message.content = "I'm doing well, thank you!"
    return message


@pytest.fixture
def sample_personality_profile():
    """Create a sample PersonalityProfile for testing"""
    style = CommunicationStyle(
        formality_level="formal",
        detail_level="high",
        directness="direct",
        decision_making_style="analytical",
        sentence_length_avg=20.5,
        common_phrases=["indeed", "furthermore"],
    )
    return PersonalityProfile(
        person_name="John Doe",
        communication_style=style,
        tone_characteristics={"professional": 0.9, "friendly": 0.3},
    )


class TestPromptServiceBasic:
    """Test basic PromptService functionality"""

    def test_initialization_with_default_client(self):
        """Test PromptService initializes with default LLM client"""
        service = PromptService()
        assert service.llm_client is not None
        assert isinstance(service.llm_client, LLMClient)

    def test_initialization_with_custom_client(self, mock_llm_client):
        """Test PromptService initializes with custom LLM client"""
        service = PromptService(llm_client=mock_llm_client)
        assert service.llm_client == mock_llm_client

    def test_build_messages_minimal(self, prompt_service):
        """Test building messages with minimal required inputs"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name="Test Clone",
        )

        assert len(messages) == 2  # System + user message
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert "Test Clone" in messages[0]["content"]

    def test_build_messages_with_rag_context(self, prompt_service):
        """Test building messages with RAG context"""
        rag_context = "[Source: doc1]\nThis is relevant context."
        
        messages = prompt_service.build_messages(
            current_message="What is this about?",
            rag_context=rag_context,
            clone_name="Test Clone",
        )

        assert len(messages) == 2
        system_content = messages[0]["content"]
        assert rag_context in system_content
        assert "Your knowledge comes from the following sources:" in system_content

    def test_build_messages_without_rag_context(self, prompt_service):
        """Test building messages without RAG context"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            rag_context="",
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert "No specific context available for this query." in system_content

    def test_build_messages_with_style_instructions(self, prompt_service):
        """Test building messages with style instructions"""
        style_instructions = "Be concise and professional."
        
        messages = prompt_service.build_messages(
            current_message="Hello",
            style_instructions=style_instructions,
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert style_instructions in system_content
        assert "Your communication style is:" in system_content

    def test_build_messages_without_style_instructions(self, prompt_service):
        """Test building messages without style instructions"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert "similar to the knowledge provided ealier." in system_content

    def test_build_messages_clone_name_in_system_prompt(self, prompt_service):
        """Test that clone name appears in system prompt"""
        clone_name = "John Doe"
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name=clone_name,
        )

        system_content = messages[0]["content"]
        assert clone_name in system_content
        assert f"You are {clone_name}'s AI clone" in system_content
        assert f"Answer as {clone_name}" in system_content

    def test_build_messages_default_clone_name(self, prompt_service):
        """Test that default clone name is used when None provided"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name=None,
        )

        system_content = messages[0]["content"]
        # Should still work, just with None in the string
        assert "AI clone" in system_content


class TestPromptServiceConversationHistory:
    """Test PromptService conversation history handling"""

    def test_build_messages_with_conversation_history(self, prompt_service, sample_message, sample_clone_message):
        """Test building messages with conversation history"""
        history = [sample_message, sample_clone_message]
        
        messages = prompt_service.build_messages(
            current_message="Follow-up question",
            conversation_history=history,
            clone_name="Test Clone",
        )

        assert len(messages) == 4  # System + 2 history + current
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == sample_message.content
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == sample_clone_message.content
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Follow-up question"

    def test_build_messages_conversation_history_role_conversion(self, prompt_service):
        """Test that conversation history roles are converted correctly"""
        user_msg = MagicMock()
        user_msg.role = "external_user"
        user_msg.content = "User message"
        
        clone_msg = MagicMock()
        clone_msg.role = "clone"
        clone_msg.content = "Clone response"
        
        history = [user_msg, clone_msg]
        messages = prompt_service.build_messages(
            current_message="New message",
            conversation_history=history,
            clone_name="Test Clone",
        )

        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_build_messages_conversation_history_limit(self, prompt_service):
        """Test that conversation history is limited to last 10 messages"""
        # Create 15 messages
        history = []
        for i in range(15):
            msg = MagicMock()
            msg.role = "external_user" if i % 2 == 0 else "clone"
            msg.content = f"Message {i}"
            history.append(msg)
        
        messages = prompt_service.build_messages(
            current_message="New message",
            conversation_history=history,
            clone_name="Test Clone",
        )

        # Should have: system + 10 history messages + current = 12 total
        assert len(messages) == 12
        # First history message should be message 5 (last 10 of 15)
        assert "Message 5" in messages[1]["content"]
        # Last history message should be message 14
        assert "Message 14" in messages[10]["content"]

    def test_build_messages_conversation_history_less_than_10(self, prompt_service):
        """Test that all messages are included when history has less than 10 messages"""
        history = []
        for i in range(5):
            msg = MagicMock()
            msg.role = "external_user" if i % 2 == 0 else "clone"
            msg.content = f"Message {i}"
            history.append(msg)
        
        messages = prompt_service.build_messages(
            current_message="New message",
            conversation_history=history,
            clone_name="Test Clone",
        )

        # Should have: system + 5 history + current = 7 total
        assert len(messages) == 7

    def test_build_messages_without_conversation_history(self, prompt_service):
        """Test building messages without conversation history"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            conversation_history=None,
            clone_name="Test Clone",
        )

        assert len(messages) == 2  # System + user only

    def test_build_messages_with_empty_conversation_history(self, prompt_service):
        """Test building messages with empty conversation history"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            conversation_history=[],
            clone_name="Test Clone",
        )

        assert len(messages) == 2  # System + user only


class TestPromptServiceSystemPrompt:
    """Test PromptService system prompt construction"""

    def test_system_prompt_contains_instructions(self, prompt_service):
        """Test that system prompt contains all required instructions"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert "Answer as" in system_content
        assert "speaking in first person" in system_content
        assert "Use the provided context" in system_content
        assert "Be helpful, concise, and professional" in system_content
        assert "Maintain conversation continuity" in system_content

    def test_system_prompt_rag_context_formatting(self, prompt_service):
        """Test that RAG context is properly formatted in system prompt"""
        rag_context = "[Source: doc1]\nContext line 1\n\n[Source: doc2]\nContext line 2"
        
        messages = prompt_service.build_messages(
            current_message="Question",
            rag_context=rag_context,
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert "Your knowledge comes from the following sources:" in system_content
        assert "[Source: doc1]" in system_content
        assert "Context line 1" in system_content

    def test_system_prompt_style_instructions_section(self, prompt_service):
        """Test that style instructions section is properly formatted"""
        style_instructions = "Be concise. Use bullet points when appropriate."
        
        messages = prompt_service.build_messages(
            current_message="Question",
            style_instructions=style_instructions,
            clone_name="Test Clone",
        )

        system_content = messages[0]["content"]
        assert "Your communication style is:" in system_content
        assert style_instructions in system_content


class TestPromptServiceEdgeCases:
    """Test PromptService edge cases and error handling"""

    def test_build_messages_empty_current_message(self, prompt_service):
        """Test building messages with empty current message"""
        messages = prompt_service.build_messages(
            current_message="",
            clone_name="Test Clone",
        )

        assert len(messages) == 2
        assert messages[1]["content"] == ""

    def test_build_messages_very_long_rag_context(self, prompt_service):
        """Test building messages with very long RAG context"""
        long_context = "A" * 10000  # 10k characters
        
        messages = prompt_service.build_messages(
            current_message="Question",
            rag_context=long_context,
            clone_name="Test Clone",
        )

        assert len(messages) == 2
        assert long_context in messages[0]["content"]

    def test_build_messages_special_characters_in_clone_name(self, prompt_service):
        """Test building messages with special characters in clone name"""
        clone_name = "John O'Brien-Smith"
        
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name=clone_name,
        )

        system_content = messages[0]["content"]
        assert clone_name in system_content

    def test_build_messages_unicode_content(self, prompt_service):
        """Test building messages with unicode content"""
        unicode_message = "Hello 世界 🌍"
        unicode_context = "Context with émojis 🎉"
        
        messages = prompt_service.build_messages(
            current_message=unicode_message,
            rag_context=unicode_context,
            clone_name="Test Clone",
        )

        assert unicode_message in messages[1]["content"]
        assert unicode_context in messages[0]["content"]


class TestPromptServiceMessageStructure:
    """Test PromptService message structure and format"""

    def test_message_structure_is_correct(self, prompt_service):
        """Test that messages have correct structure for OpenAI API"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name="Test Clone",
        )

        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, dict)
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["system", "user", "assistant"]
            assert isinstance(msg["content"], str)

    def test_message_order(self, prompt_service, sample_message):
        """Test that messages are in correct order"""
        history = [sample_message]
        messages = prompt_service.build_messages(
            current_message="New message",
            conversation_history=history,
            clone_name="Test Clone",
        )

        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"  # History message
        assert messages[2]["role"] == "user"  # Current message

    def test_system_message_is_first(self, prompt_service):
        """Test that system message is always first"""
        messages = prompt_service.build_messages(
            current_message="Hello",
            clone_name="Test Clone",
        )

        assert messages[0]["role"] == "system"

    def test_current_message_is_last(self, prompt_service, sample_message):
        """Test that current message is always last"""
        history = [sample_message]
        messages = prompt_service.build_messages(
            current_message="Final message",
            conversation_history=history,
            clone_name="Test Clone",
        )

        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Final message"

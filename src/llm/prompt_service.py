"""Centralized prompt service for building LLM messages with RAG context, personality, and conversation history

This service centralizes all prompt building logic, using the approach from ChatService
where RAG context is placed in the system message.
"""

from typing import List, Dict, Optional
from src.llm.client import LLMClient
from src.config.settings import settings
from src.personality.profile import PersonalityProfile
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PromptService:
    """Centralized service for building LLM prompts with RAG context, personality, and conversation history"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def build_messages(
        self,
        current_message: str,
        rag_context: str = "",
        style_instructions: str = "",
        personality_profile: Optional[PersonalityProfile] = None,
        conversation_history: Optional[List] = None,
        clone_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build messages array for LLM API call.
        
        This method uses the exact logic from ChatService._build_llm_messages():
        - RAG context is placed in the system message
        - Conversation history is limited to last 10 messages
        - Current message is added as user message
        
        Args:
            current_message: The current user message/query
            rag_context: Retrieved RAG context (formatted string)
            conversation_history: List of Message objects from database (optional)
            clone_name: Name of the clone (e.g., "John Doe" or "the AI Clone")
        
        Returns:
            List of message dicts in OpenAI format: [{"role": "system", "content": "..."}, ...]
        """
        messages = []

        # System message with RAG context (copied from ChatService._build_llm_messages)
        # TODO: consider adding personality profile and style to the system prompt.
        system_prompt = f"""You are {clone_name}'s AI clone, that thinks like them and acts like them. 
        You can help {clone_name}'s customers with their professional questions, answering based on your knowledge.

Your knowledge comes from the following sources:

{rag_context if rag_context else "No specific context available for this query."}

Your communication style is:

{style_instructions if style_instructions else "similar to the knowledge provided ealier."}

Instructions:
- Answer as {clone_name}, speaking in first person
- Avoid extenssively using symbols that remind the user you're AI (e.g. em dashes, astrics, etc) unless they are absolutely necessary.
- Replicate {clone_name}'s communication style when possible and relevant
- Use the provided context to answer questions accurately
- If the context doesn't contain relevant information, say so honestly!
- Be helpful, concise, and professional
- Maintain conversation continuity by referencing earlier messages when relevant 
- Ask clarifying questions or follow-up questions when relevant (not EVERY message) to keep the conversation engaging and natural. 
Those questions should be relevant to the conversation and the user's query, and help you to learn more about the user's business and needs, to help them most effectively.
"""

        messages.append({
            "role": "system",
            "content": system_prompt,
        })

        # Add conversation history (last 10 messages for context) - copied from ChatService
        if conversation_history:
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            for msg in recent_history:
                role = "user" if msg.role == "external_user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.content,
                })

        # Add current message
        messages.append({
            "role": "user",
            "content": current_message,
        })

        return messages

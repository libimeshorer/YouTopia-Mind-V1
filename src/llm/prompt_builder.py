"""Prompt builder that combines RAG context with personality profile"""
# TODO: review when starting using bots.

from typing import List, Dict, Optional
from uuid import UUID
from src.llm.client import LLMClient
from src.llm.prompt_service import PromptService
from src.rag.retriever import RAGRetriever
from src.rag.clone_vector_store import CloneVectorStore
from src.personality.profile import PersonalityProfile
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    """Builds context-aware prompts for the digital twin"""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        rag_retriever: Optional[RAGRetriever] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.rag_retriever = rag_retriever or RAGRetriever()
        self.prompt_service = PromptService(llm_client=self.llm_client)
    
    def build_system_prompt(self, profile: Optional[PersonalityProfile] = None) -> str:
        """
        Build system prompt with personality profile.
        
        DEPRECATED: This method is kept for backward compatibility.
        The actual prompt building logic is now in PromptService.
        """
        # Use PromptService to build system prompt
        # Note: PromptService uses clone_name, but this method only has profile
        # For backward compatibility, we'll use a default clone name
        clone_name = profile.person_name if profile and profile.person_name else "professional"
        return self.prompt_service.build_messages(
            current_message="",  # Empty since we only want the system prompt
            rag_context="",
            conversation_history=None,
            clone_name=clone_name,
        )[0]["content"]
    
    def build_messages(
        self,
        user_query: str,
        profile: Optional[PersonalityProfile] = None,
        include_context: bool = True,
        max_context_tokens: Optional[int] = None,
        clone_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        """
        Build messages for LLM with context and personality.
        
        This method now uses PromptService for the actual prompt building.
        It still handles RAG retrieval internally for backward compatibility.
        """
        # Retrieve relevant context (automatically filtered by clone_id/tenant_id if CloneVectorStore is used)
        context = ""
        if include_context:
            # CloneVectorStore automatically filters by clone_id/tenant_id
            context = self.rag_retriever.retrieve_and_format(
                user_query,
                top_k=settings.top_k_retrieval,
            )
        
        # Determine clone name from profile or use default
        clone_name = "professional"
        if profile and profile.person_name:
            clone_name = profile.person_name
        
        # Use PromptService to build messages (uses ChatService logic - context in system message)
        messages = self.prompt_service.build_messages(
            current_message=user_query,
            rag_context=context,
            conversation_history=None,  # PromptBuilder doesn't support conversation history
            clone_name=clone_name,
        )
        
        # Check token limits (maintain backward compatibility)
        max_tokens = max_context_tokens or settings.max_context_tokens
        total_estimated_tokens = sum(self.llm_client.count_tokens(msg["content"]) for msg in messages)
        
        if total_estimated_tokens > max_tokens:
            logger.warning(
                "Message tokens exceed limit",
                estimated_tokens=total_estimated_tokens,
                max_tokens=max_tokens,
            )
            # Truncate context if needed
            if context:
                context_tokens = self.llm_client.count_tokens(context)
                if context_tokens > max_tokens // 2:
                    # Truncate context
                    truncated_length = (max_tokens // 2) * 4  # Rough char estimate
                    truncated_context = context[:truncated_length].rsplit(" ", 1)[0] + "..."
                    
                    # Rebuild messages with truncated context
                    messages = self.prompt_service.build_messages(
                        current_message=user_query,
                        rag_context=truncated_context,
                        conversation_history=None,
                        clone_name=clone_name,
                    )
        
        return messages
    
    def generate_response(
        self,
        user_query: str,
        profile: Optional[PersonalityProfile] = None,
        temperature: float = 0.7,
        stream: bool = False,
        clone_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> str:
        """Generate response using LLM with context and personality"""
        messages = self.build_messages(
            user_query, 
            profile, 
            include_context=True,
            clone_id=clone_id,
            tenant_id=tenant_id
        )
        
        logger.info("Generating response", query_preview=user_query[:50], has_profile=profile is not None)
        
        if stream:
            stream = self.llm_client.generate_stream(messages, temperature=temperature)
            return stream
        else:
            response = self.llm_client.generate(messages, temperature=temperature)
            usage_stats = self.llm_client.get_usage_stats(response)
            logger.info("Response generated", usage=usage_stats)
            return response.choices[0].message.content



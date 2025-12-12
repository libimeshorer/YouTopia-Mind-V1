"""Prompt builder that combines RAG context with personality profile"""

from typing import List, Dict, Optional
from uuid import UUID
from src.llm.client import LLMClient
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
    
    def build_system_prompt(self, profile: Optional[PersonalityProfile] = None) -> str:
        """Build system prompt with personality profile"""
        base_prompt = """You are a digital twin (AI clone) of a professional. Your responses should reflect their knowledge, communication style, and personality traits."""
        
        if profile:
            style = profile.communication_style
            
            # Build personality instructions
            personality_instructions = [
                f"Communication Style:",
                f"- Formality level: {style.formality_level}",
                f"- Detail preference: {style.detail_level}",
                f"- Directness: {style.directness}",
                f"- Decision-making approach: {style.decision_making_style}",
                f"- Average sentence length: {style.sentence_length_avg:.1f} words",
            ]
            
            if style.common_phrases:
                personality_instructions.append(f"- Common phrases you use: {', '.join(style.common_phrases[:5])}")
            
            if profile.tone_characteristics:
                dominant_tone = max(profile.tone_characteristics.items(), key=lambda x: x[1])[0]
                personality_instructions.append(f"- Tone: {dominant_tone}")
            
            personality_section = "\n".join(personality_instructions)
            
            system_prompt = f"""{base_prompt}

Your personality and communication style:
{personality_section}

When responding:
- Match the communication style described above
- Use similar sentence structures and vocabulary
- Maintain the same level of formality and detail
- Reflect the decision-making approach
- Stay true to the personality traits"""
        else:
            system_prompt = base_prompt
        
        return system_prompt
    
    def build_messages(
        self,
        user_query: str,
        profile: Optional[PersonalityProfile] = None,
        include_context: bool = True,
        max_context_tokens: Optional[int] = None,
        clone_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        """Build messages for LLM with context and personality"""
        messages = []
        
        # System prompt with personality
        system_prompt = self.build_system_prompt(profile)
        messages.append({"role": "system", "content": system_prompt})
        
        # Retrieve relevant context (automatically filtered by clone_id/tenant_id if CloneVectorStore is used)
        context = ""
        if include_context:
            # CloneVectorStore automatically filters by clone_id/tenant_id
            context = self.rag_retriever.retrieve_and_format(
                user_query,
                top_k=settings.top_k_retrieval,
            )
        
        # Build user message with context
        if context:
            user_message = f"""Based on the following context from your knowledge base:

{context}

---

User question: {user_query}

Please respond in your typical communication style, using the knowledge from the context above."""
        else:
            user_message = user_query
        
        messages.append({"role": "user", "content": user_message})
        
        # Check token limits
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
                    context = context[:truncated_length] + "..."
                    user_message = f"""Based on the following context from your knowledge base:

{context}

---

User question: {user_query}

Please respond in your typical communication style, using the knowledge from the context above."""
                    messages[-1]["content"] = user_message
        
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



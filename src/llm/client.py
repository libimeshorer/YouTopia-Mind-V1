"""OpenAI client wrapper with retry logic"""

import time
from typing import Optional, Iterator, AsyncIterator
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """OpenAI client wrapper with retry logic and error handling"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = OpenAI(api_key=self.api_key)
    
    def generate(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> ChatCompletion:
        """Generate completion with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                )
                return response
            except Exception as e:
                logger.warning(
                    "OpenAI API call failed",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("OpenAI API call failed after all retries", error=str(e))
                    raise
    
    def generate_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Iterator:
        """Generate streaming completion"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            return stream
        except Exception as e:
            logger.error("Error generating stream", error=str(e))
            raise
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Simple approximation: ~4 characters per token
        return len(text) // 4
    
    def get_usage_stats(self, response: ChatCompletion) -> dict:
        """Extract usage statistics from response"""
        if response.usage:
            return {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return {}


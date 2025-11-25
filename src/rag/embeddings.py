"""Embedding generation using OpenAI API"""

from typing import List, Optional
from openai import OpenAI

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model
        self.client = OpenAI(api_key=self.api_key)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Error generating embedding", error=str(e), text_preview=text[:100])
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                logger.debug("Generated embeddings for batch", batch_size=len(batch), total=len(all_embeddings))
            except Exception as e:
                logger.error("Error generating embeddings for batch", error=str(e), batch_start=i)
                # Continue with next batch
                all_embeddings.extend([[]] * len(batch))
        
        return all_embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model"""
        # text-embedding-3-small has 1536 dimensions
        if "3-small" in self.model:
            return 1536
        elif "3-large" in self.model:
            return 3072
        elif "ada-002" in self.model:
            return 1536
        else:
            # Default to 1536, but could query API if needed
            return 1536


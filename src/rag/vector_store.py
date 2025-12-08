"""Pinecone vector store wrapper (replaces ChromaDB)"""

from typing import List, Dict, Optional
from src.rag.pinecone_store import PineconeStore
from src.rag.embeddings import EmbeddingService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Pinecone vector store wrapper for RAG (maintains backward compatibility)"""
    
    def __init__(
        self,
        collection_name: Optional[str] = None,  # Kept for backward compatibility, not used
        persist_directory: Optional[str] = None,  # Kept for backward compatibility, not used
        embedding_service: Optional[EmbeddingService] = None,
    ):
        # Initialize Pinecone store
        self.pinecone_store = PineconeStore(embedding_service=embedding_service)
        
        logger.info("Vector store initialized (using Pinecone)")
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add texts to the vector store"""
        return self.pinecone_store.add_texts(texts, metadatas, ids)
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search for similar texts"""
        return self.pinecone_store.search(query, n_results, filter_metadata)
    
    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict] = None) -> bool:
        """Delete texts from vector store"""
        # Convert 'where' to filter_metadata for Pinecone
        filter_metadata = where if where else None
        return self.pinecone_store.delete(ids, filter_metadata)
    
    def get_collection_count(self) -> int:
        """Get the number of vectors in the index"""
        return self.pinecone_store.get_collection_count()
    
    def reset(self) -> bool:
        """Reset the index (delete all vectors)"""
        return self.pinecone_store.reset()



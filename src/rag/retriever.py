"""RAG retriever with similarity search and re-ranking"""

from typing import List, Dict, Optional
from src.rag.vector_store import VectorStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """RAG retriever for context retrieval"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ):
        self.vector_store = vector_store or VectorStore()
        self.top_k = top_k
        self.min_score = min_score
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Retrieve relevant context for a query"""
        k = top_k or self.top_k
        
        logger.info("Retrieving context", query_preview=query[:50], top_k=k)
        
        # Search vector store
        results = self.vector_store.search(
            query=query,
            n_results=k,
            filter_metadata=filter_metadata,
        )
        
        # Filter by minimum score (distance threshold)
        # ChromaDB uses cosine distance, lower is better
        # We'll treat distance < 0.5 as good matches (adjustable)
        filtered_results = [
            r for r in results
            if r.get("distance") is None or r["distance"] < (1.0 - self.min_score)
        ]
        
        logger.info(
            "Retrieval completed",
            total_results=len(results),
            filtered_results=len(filtered_results),
        )
        
        return filtered_results
    
    def format_context(self, results: List[Dict]) -> str:
        """Format retrieved results into context string"""
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            # Add source information if available
            source = metadata.get("source", "Unknown")
            context_parts.append(f"[Source: {source}]\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def retrieve_and_format(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> str:
        """Retrieve and format context in one call"""
        results = self.retrieve(query, top_k=top_k, filter_metadata=filter_metadata)
        return self.format_context(results)



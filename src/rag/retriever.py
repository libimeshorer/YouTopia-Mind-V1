"""RAG retriever with similarity search, re-ranking, and RL-based score boosting.

This module handles context retrieval for clone responses. It supports:
- Basic semantic similarity search via Pinecone
- RL-based score boosting from user feedback (see docs/RL_OVERVIEW.md)
- Re-ranking based on learned chunk quality scores
"""

import hashlib
from typing import List, Dict, Optional
from src.rag.vector_store import VectorStore
from src.rag.clone_vector_store import CloneVectorStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """RAG retriever for context retrieval with optional RL-based boosting.

    When chunk_scores are provided (from ChunkScoreService), the retriever will:
    1. Fetch 2x the requested chunks
    2. Apply learned score boosts based on user feedback
    3. Re-rank and return top_k chunks

    This enables the system to learn from feedback and improve retrieval over time.
    """

    # Maximum boost from learned scores (prevents overriding semantic similarity)
    MAX_BOOST = 0.3

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        clone_vector_store: Optional[CloneVectorStore] = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ):
        # Prefer CloneVectorStore if provided (enforces clone isolation)
        if clone_vector_store:
            self.vector_store = clone_vector_store
        else:
            self.vector_store = vector_store or VectorStore()
        self.top_k = top_k
        self.min_score = min_score
        # Chunk scores for RL-based boosting (set via set_chunk_scores)
        self.chunk_scores: Dict[str, float] = {}

    def set_chunk_scores(self, scores: Dict[str, float]) -> None:
        """Set chunk score map for feedback-based boosting.

        Args:
            scores: Dictionary mapping chunk_hash to learned score
        """
        self.chunk_scores = scores or {}
        if self.chunk_scores:
            logger.debug("Chunk scores set for retrieval", scores_count=len(self.chunk_scores))

    def _hash_chunk(self, content: str) -> str:
        """Generate SHA256 hash of chunk content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _apply_score_boosts(self, results: List[Dict]) -> List[Dict]:
        """Apply learned score boosts to retrieval results.

        For each result:
        1. Compute chunk hash
        2. Look up learned score
        3. Add boost to base similarity score
        4. Track boost for logging/debugging

        Args:
            results: List of retrieval results from vector store

        Returns:
            Results with adjusted_score and boost_applied fields added
        """
        for result in results:
            text = result.get("text", "")
            if not text:
                result["adjusted_score"] = 1.0 - result.get("distance", 0.5)
                result["boost_applied"] = 0.0
                continue

            chunk_hash = self._hash_chunk(text)
            base_score = 1.0 - result.get("distance", 0.5)  # Convert distance to similarity

            # Look up learned score and compute boost
            learned_score = self.chunk_scores.get(chunk_hash, 0.0)
            boost = max(-self.MAX_BOOST, min(self.MAX_BOOST, learned_score * self.MAX_BOOST))

            result["adjusted_score"] = base_score + boost
            result["boost_applied"] = boost
            result["chunk_hash"] = chunk_hash

        return results

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Retrieve relevant context for a query with optional RL boosting.

        If chunk_scores are set, fetches 2x chunks and re-ranks based on
        learned quality scores from user feedback.

        Args:
            query: The user's question/query
            top_k: Number of results to return (default: self.top_k)
            filter_metadata: Optional metadata filters

        Returns:
            List of relevant chunks, possibly re-ranked by learned scores
        """
        k = top_k or self.top_k

        # If we have chunk scores, fetch more results for re-ranking
        fetch_k = k * 2 if self.chunk_scores else k

        logger.info(
            "Retrieving context",
            query_preview=query[:50],
            top_k=k,
            fetch_k=fetch_k,
            has_chunk_scores=bool(self.chunk_scores)
        )

        # Search vector store
        results = self.vector_store.search(
            query=query,
            n_results=fetch_k,
            filter_metadata=filter_metadata,
        )

        # Apply RL score boosts if we have chunk scores
        if self.chunk_scores and results:
            results = self._apply_score_boosts(results)

            # Re-rank by adjusted score (descending)
            results.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

            # Take top_k after re-ranking
            results = results[:k]

            # Log boost impact
            boosts_applied = [r.get("boost_applied", 0) for r in results if r.get("boost_applied", 0) != 0]
            if boosts_applied:
                logger.info(
                    "RL score boosts applied",
                    chunks_boosted=len(boosts_applied),
                    avg_boost=sum(boosts_applied) / len(boosts_applied)
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



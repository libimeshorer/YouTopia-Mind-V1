"""Pinecone Serverless vector store wrapper"""

from typing import List, Dict, Optional
import uuid
from pinecone import Pinecone, ServerlessSpec
from src.config.settings import settings
from src.rag.embeddings import EmbeddingService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PineconeStore:
    """Pinecone Serverless vector store wrapper for RAG"""
    
    def __init__(
        self,
        index_name: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.index_name = index_name or settings.pinecone_index_name
        self.api_key = settings.pinecone_api_key
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.api_key)
        
        # Initialize embedding service
        self.embedding_service = embedding_service or EmbeddingService()
        
        # Get embedding dimension
        self.dimension = self.embedding_service.get_embedding_dimension()
        
        # Get or create index
        self.index = self._get_or_create_index()
        
        logger.info(
            "Pinecone store initialized",
            index_name=self.index_name,
            dimension=self.dimension,
        )
    
    def _get_or_create_index(self):
        """Get existing index or create a new one if it doesn't exist"""
        try:
            # Check if index exists
            if self.index_name in [index.name for index in self.pc.list_indexes()]:
                logger.info("Using existing Pinecone index", index_name=self.index_name)
                return self.pc.Index(self.index_name)
            else:
                # Create new index
                logger.info("Creating new Pinecone index", index_name=self.index_name, dimension=self.dimension)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                # Wait a moment for index to be ready
                import time
                time.sleep(2)
                return self.pc.Index(self.index_name)
        except Exception as e:
            logger.error("Error getting or creating Pinecone index", error=str(e))
            raise
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add texts to the vector store"""
        if not texts:
            return []
        
        # Generate embeddings
        logger.info("Generating embeddings", text_count=len(texts))
        embeddings = self.embedding_service.embed_texts(texts)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Prepare vectors for Pinecone (text field + metadata)
        vectors = []
        for i, (text, embedding, metadata, vector_id) in enumerate(zip(texts, embeddings, metadatas, ids)):
            # Pinecone metadata can't contain the text directly, so we store it separately
            # The text will be stored in metadata as a string (Pinecone supports this)
            vector_metadata = {**metadata, "text": text}
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": vector_metadata,
            })
        
        # Upsert to Pinecone
        try:
            self.index.upsert(vectors=vectors)
            logger.info("Texts added to Pinecone", count=len(texts))
            return ids
        except Exception as e:
            logger.error("Error adding texts to Pinecone", error=str(e))
            raise
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search for similar texts"""
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build filter if provided
        filter_dict = None
        if filter_metadata:
            # Pinecone filter format
            filter_dict = {}
            for key, value in filter_metadata.items():
                filter_dict[key] = {"$eq": value}
        
        try:
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                include_metadata=True,
                filter=filter_dict,
            )
            
            # Format results
            formatted_results = []
            if results.matches:
                for match in results.matches:
                    formatted_results.append({
                        "text": match.metadata.get("text", "") if match.metadata else "",
                        "metadata": {k: v for k, v in (match.metadata or {}).items() if k != "text"},
                        "id": match.id,
                        "distance": 1 - match.score if match.score else None,  # Convert similarity to distance
                    })
            
            logger.debug("Search completed", query_preview=query[:50], results_count=len(formatted_results))
            return formatted_results
        except Exception as e:
            logger.error("Error searching Pinecone", error=str(e))
            raise
    
    def delete(self, ids: Optional[List[str]] = None, filter_metadata: Optional[Dict] = None) -> bool:
        """Delete texts from vector store"""
        try:
            if ids:
                self.index.delete(ids=ids)
                logger.info("Texts deleted from Pinecone", ids_count=len(ids))
                return True
            elif filter_metadata:
                # Pinecone doesn't support delete by filter directly
                # We need to query first, then delete by IDs
                # For now, log a warning
                logger.warning("Delete by filter not directly supported in Pinecone. Query first, then delete by IDs.")
                return False
            else:
                logger.warning("No deletion criteria provided")
                return False
        except Exception as e:
            logger.error("Error deleting from Pinecone", error=str(e))
            return False
    
    def get_collection_count(self) -> int:
        """Get the number of vectors in the index"""
        try:
            stats = self.index.describe_index_stats()
            return stats.total_vector_count
        except Exception as e:
            logger.error("Error getting Pinecone index stats", error=str(e))
            return 0
    
    def reset(self) -> bool:
        """Reset the index (delete all vectors)"""
        try:
            # Delete the index and recreate it
            self.pc.delete_index(self.index_name)
            # Wait a moment
            import time
            time.sleep(2)
            # Recreate
            self.index = self._get_or_create_index()
            logger.info("Pinecone index reset", index_name=self.index_name)
            return True
        except Exception as e:
            logger.error("Error resetting Pinecone index", error=str(e))
            return False

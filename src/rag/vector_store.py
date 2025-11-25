"""ChromaDB vector store wrapper"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
from pathlib import Path

from src.config.settings import settings
from src.rag.embeddings import EmbeddingService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """ChromaDB vector store wrapper for RAG"""
    
    def __init__(
        self,
        collection_name: str = "youtopia_mind",
        persist_directory: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        
        # Create directory if it doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        # Initialize embedding service
        self.embedding_service = embedding_service or EmbeddingService()
        
        logger.info(
            "Vector store initialized",
            collection=collection_name,
            persist_directory=self.persist_directory,
        )
    
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
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Add to collection
        try:
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info("Texts added to vector store", count=len(texts))
            return ids
        except Exception as e:
            logger.error("Error adding texts to vector store", error=str(e))
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
        
        # Build query
        where = filter_metadata if filter_metadata else None
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                    })
            
            logger.debug("Search completed", query_preview=query[:50], results_count=len(formatted_results))
            return formatted_results
        except Exception as e:
            logger.error("Error searching vector store", error=str(e))
            raise
    
    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict] = None) -> bool:
        """Delete texts from vector store"""
        try:
            if ids:
                self.collection.delete(ids=ids)
            elif where:
                self.collection.delete(where=where)
            else:
                logger.warning("No deletion criteria provided")
                return False
            
            logger.info("Texts deleted from vector store", ids_count=len(ids) if ids else 0)
            return True
        except Exception as e:
            logger.error("Error deleting from vector store", error=str(e))
            return False
    
    def get_collection_count(self) -> int:
        """Get the number of documents in the collection"""
        return self.collection.count()
    
    def reset(self) -> bool:
        """Reset the collection (delete all documents)"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Vector store reset", collection=self.collection_name)
            return True
        except Exception as e:
            logger.error("Error resetting vector store", error=str(e))
            return False



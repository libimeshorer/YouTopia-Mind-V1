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
        
        # Log environment information for safety
        from src.utils.environment import get_environment, warn_if_production
        env = get_environment()
        logger.info(
            "Pinecone store initialized",
            index_name=self.index_name,
            dimension=self.dimension,
            environment=env,
        )
        
        # Warn if production
        if env == "production":
            logger.warning(
                "⚠️  PineconeStore initialized in PRODUCTION environment",
                index_name=self.index_name,
                environment=env,
                message="All operations will affect production data. Exercise extreme caution."
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
        namespace: Optional[str] = None,
        validate_tenant_clone_ids: bool = False,
        expected_tenant_id: Optional[str] = None,
        expected_clone_id: Optional[str] = None,
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: List of text strings to add
            metadatas: Optional list of metadata dicts
            ids: Optional list of vector IDs
            namespace: Optional namespace for isolation (required when validate_tenant_clone_ids=True)
            validate_tenant_clone_ids: If True, validates metadata includes matching tenant_id/clone_id
            expected_tenant_id: Expected tenant_id for validation (required if validate_tenant_clone_ids=True)
            expected_clone_id: Expected clone_id for validation (required if validate_tenant_clone_ids=True)
        
        Returns:
            List of vector IDs
        """
        if not texts:
            return []
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Validate metadata if requested (used by CloneVectorStore)
        if validate_tenant_clone_ids:
            if not expected_tenant_id or not expected_clone_id:
                raise ValueError(
                    "expected_tenant_id and expected_clone_id are required when validate_tenant_clone_ids=True"
                )
            if not namespace:
                raise ValueError(
                    "namespace is required when validate_tenant_clone_ids=True. "
                    "Use CloneVectorStore to automatically provide namespace and validation."
                )
            
            from src.rag.utils import validate_metadata
            from uuid import UUID
            
            validated_metadatas = []
            for i, metadata in enumerate(metadatas):
                validated_metadata = validate_metadata(
                    metadata,
                    UUID(expected_tenant_id),
                    UUID(expected_clone_id),
                    metadata_index=i,
                )
                validated_metadatas.append(validated_metadata)
            metadatas = validated_metadatas
        
        # Generate embeddings
        logger.info("Generating embeddings", text_count=len(texts))
        embeddings = self.embedding_service.embed_texts(texts)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
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
        
        # Upsert to Pinecone with namespace
        # IMPORTANT: When used through CloneVectorStore, namespace is ALWAYS provided and required.
        # The namespace parameter is optional here only for backward compatibility or direct use.
        # For clone-scoped operations, always use CloneVectorStore which ensures namespace is set.
        try:
            upsert_kwargs = {"vectors": vectors}
            if namespace:
                upsert_kwargs["namespace"] = namespace
            else:
                # Warn if namespace is not provided (should use CloneVectorStore for clone-scoped operations)
                logger.warning(
                    "Adding texts without namespace. For clone-scoped operations, use CloneVectorStore "
                    "which automatically provides the correct namespace."
                )
            self.index.upsert(**upsert_kwargs)
            logger.info("Texts added to Pinecone", count=len(texts), namespace=namespace)
            return ids
        except Exception as e:
            logger.error("Error adding texts to Pinecone", error=str(e))
            raise
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
        namespace: Optional[str] = None,
        validate_tenant_clone_ids: bool = False,
        expected_tenant_id: Optional[str] = None,
        expected_clone_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for similar texts.
        
        Args:
            query: Search query string
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            namespace: Optional namespace for isolation (required when validate_tenant_clone_ids=True)
            validate_tenant_clone_ids: If True, validates filter_metadata includes matching tenant_id/clone_id
            expected_tenant_id: Expected tenant_id for validation (required if validate_tenant_clone_ids=True)
            expected_clone_id: Expected clone_id for validation (required if validate_tenant_clone_ids=True)
        
        Returns:
            List of search results
        """
        # Validate filter_metadata if requested (used by CloneVectorStore)
        if validate_tenant_clone_ids:
            if not expected_tenant_id or not expected_clone_id:
                raise ValueError(
                    "expected_tenant_id and expected_clone_id are required when validate_tenant_clone_ids=True"
                )
            if not namespace:
                raise ValueError(
                    "namespace is required when validate_tenant_clone_ids=True. "
                    "Use CloneVectorStore to automatically provide namespace and validation."
                )
            
            if filter_metadata:
                from src.rag.utils import validate_metadata
                from uuid import UUID
                # Validate that filter_metadata matches expected IDs
                validate_metadata(
                    filter_metadata,
                    UUID(expected_tenant_id),
                    UUID(expected_clone_id),
                )
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build filter if provided
        filter_dict = None
        if filter_metadata:
            filter_dict = {}
            for key, value in filter_metadata.items():
                filter_dict[key] = {"$eq": value}
        
        try:
            # Query Pinecone with namespace
            # IMPORTANT: When used through CloneVectorStore, namespace is ALWAYS provided and required.
            # The namespace parameter is optional here only for backward compatibility or direct use.
            # For clone-scoped operations, always use CloneVectorStore which ensures namespace is set.
            query_kwargs = {
                "vector": query_embedding,
                "top_k": n_results,
                "include_metadata": True,
            }
            if namespace:
                query_kwargs["namespace"] = namespace
            else:
                # Warn if namespace is not provided (should use CloneVectorStore for clone-scoped operations)
                logger.warning(
                    "Searching without namespace. For clone-scoped operations, use CloneVectorStore "
                    "which automatically provides the correct namespace."
                )
            if filter_dict:
                query_kwargs["filter"] = filter_dict
            
            results = self.index.query(**query_kwargs)
            
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
            
            logger.debug("Search completed", query_preview=query[:50], results_count=len(formatted_results), namespace=namespace)
            return formatted_results
        except Exception as e:
            logger.error("Error searching Pinecone", error=str(e))
            raise
    
    def delete(
        self,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict] = None,
        namespace: Optional[str] = None,
        validate_tenant_clone_ids: bool = False,
        expected_tenant_id: Optional[str] = None,
        expected_clone_id: Optional[str] = None,
    ) -> bool:
        """
        Delete texts from vector store.
        
        Args:
            ids: Optional list of vector IDs to delete
            filter_metadata: Optional metadata filters
            namespace: Optional namespace for isolation (required when validate_tenant_clone_ids=True)
            validate_tenant_clone_ids: If True, validates filter_metadata includes matching tenant_id/clone_id
            expected_tenant_id: Expected tenant_id for validation (required if validate_tenant_clone_ids=True)
            expected_clone_id: Expected clone_id for validation (required if validate_tenant_clone_ids=True)
        
        Returns:
            True if deletion was successful
        """
        try:
            # Validate filter_metadata if requested (used by CloneVectorStore)
            if validate_tenant_clone_ids:
                if not expected_tenant_id or not expected_clone_id:
                    raise ValueError(
                        "expected_tenant_id and expected_clone_id are required when validate_tenant_clone_ids=True"
                    )
                if not namespace:
                    raise ValueError(
                        "namespace is required when validate_tenant_clone_ids=True. "
                        "Use CloneVectorStore to automatically provide namespace and validation."
                    )
                
                if filter_metadata:
                    from src.rag.utils import validate_metadata
                    from uuid import UUID
                    # Validate that filter_metadata matches expected IDs
                    validate_metadata(
                        filter_metadata,
                        UUID(expected_tenant_id),
                        UUID(expected_clone_id),
                    )
            
            # WARNING: Delete without namespace affects global index (all namespaces)
            # This is dangerous in production
            if not namespace:
                from src.utils.environment import warn_if_production
                warn_if_production(
                    f"⚠️  DELETE OPERATION WITHOUT NAMESPACE: This will delete vectors globally across all namespaces in index '{self.index_name}'. "
                    "This is extremely dangerous in production. Consider using CloneVectorStore which enforces namespace isolation."
                )
            
            delete_kwargs = {}
            if namespace:
                delete_kwargs["namespace"] = namespace
            
            if ids:
                delete_kwargs["ids"] = ids
                self.index.delete(**delete_kwargs)
                logger.info("Texts deleted from Pinecone", ids_count=len(ids), namespace=namespace)
                return True
            elif filter_metadata:
                # Pinecone doesn't support delete by filter directly
                # We need to query first, then delete by IDs
                # Query to get IDs matching the filter
                from src.rag.embeddings import EmbeddingService
                embedding_service = EmbeddingService()
                # Use a dummy query to get all matching vectors
                dummy_embedding = [0.0] * embedding_service.get_embedding_dimension()
                
                filter_dict = {}
                for key, value in filter_metadata.items():
                    filter_dict[key] = {"$eq": value}
                
                query_kwargs = {
                    "vector": dummy_embedding,
                    "top_k": 10000,  # Maximum reasonable limit
                    "include_metadata": False,
                    "filter": filter_dict,
                }
                if namespace:
                    query_kwargs["namespace"] = namespace
                
                # Query with a very high top_k to get all matching vectors
                results = self.index.query(**query_kwargs)
                
                if results.matches:
                    ids_to_delete = [match.id for match in results.matches]
                    delete_kwargs["ids"] = ids_to_delete
                    self.index.delete(**delete_kwargs)
                    logger.info("Texts deleted from Pinecone by filter", ids_count=len(ids_to_delete), namespace=namespace)
                    return True
                else:
                    logger.info("No vectors found matching filter criteria", namespace=namespace)
                    return True
            else:
                raise ValueError(
                    "Either 'ids' or 'filter_metadata' must be provided."
                )
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
        """
        Reset the index (delete all vectors).
        
        WARNING: This operation is BLOCKED in production for safety.
        This deletes and recreates the entire index, destroying all data across all namespaces.
        """
        from src.utils.environment import require_development
        
        # CRITICAL SAFETY: Block reset in production
        try:
            with require_development(f"PineconeStore.reset() for index '{self.index_name}'"):
                pass
        except RuntimeError as e:
            logger.error(
                "Reset operation blocked in production",
                index_name=self.index_name,
                error=str(e)
            )
            raise
        
        try:
            # Delete the index and recreate it
            logger.warning(
                "Resetting Pinecone index (destructive operation)",
                index_name=self.index_name,
                environment="development"
            )
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

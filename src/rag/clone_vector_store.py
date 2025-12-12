"""Clone-scoped vector store wrapper that enforces tenant_id and clone_id isolation using Pinecone namespaces"""

from typing import List, Dict, Optional
from uuid import UUID
from src.rag.pinecone_store import PineconeStore
from src.rag.utils import validate_metadata
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CloneVectorStore:
    """
    Wrapper around PineconeStore that REQUIRES clone_id and tenant_id for all operations.
    Uses Pinecone namespaces for infrastructure-level isolation: each clone gets its own namespace
    based on tenant_id + clone_id.
    
    This provides better isolation than metadata filtering because:
    - Namespaces are infrastructure-level partitions in Pinecone
    - Impossible to accidentally query across namespaces
    - Better performance (no filter overhead)
    - Clearer separation of data
    """
    
    def __init__(
        self,
        clone_id: UUID,
        tenant_id: UUID,
        base_store: Optional[PineconeStore] = None,
    ):
        """
        Initialize CloneVectorStore with clone and tenant IDs.
        
        Args:
            clone_id: UUID of the clone (required)
            tenant_id: UUID of the tenant (required)
            base_store: Optional PineconeStore instance (creates new one if not provided)
        """
        if not clone_id:
            raise ValueError("clone_id is required")
        if not tenant_id:
            raise ValueError("tenant_id is required")
        
        self.clone_id = clone_id
        self.tenant_id = tenant_id
        self.base_store = base_store or PineconeStore()
        
        # Create namespace from tenant_id and clone_id for infrastructure-level isolation
        # Format: "{tenant_id}_{clone_id}" (UUIDs converted to strings without dashes for cleaner namespace names)
        self.namespace = f"{str(tenant_id).replace('-', '')}_{str(clone_id).replace('-', '')}"
        
        logger.info(
            "CloneVectorStore initialized",
            clone_id=str(clone_id),
            tenant_id=str(tenant_id),
            namespace=self.namespace
        )
    
    def _validate_metadata(self, metadata: Dict, metadata_index: int = None) -> Dict:
        """
        Validate metadata includes tenant_id and clone_id, and that they match this clone's IDs.
        This validation ensures data integrity in addition to namespace isolation.
        
        Args:
            metadata: Metadata dictionary to validate
            metadata_index: Optional index for error messages (when validating a list)
        
        Returns:
            Validated metadata dictionary with tenant_id and clone_id ensured
        """
        return validate_metadata(metadata, self.tenant_id, self.clone_id, metadata_index)
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Search for similar texts within this clone's namespace.
        Namespace isolation ensures only this clone's data is searched.
        Additionally validates filter_metadata matches this clone's IDs.
        
        Args:
            query: Search query string
            n_results: Number of results to return
            filter_metadata: Optional additional metadata filters (for filtering within namespace)
        
        Returns:
            List of search results (all guaranteed to belong to this clone via namespace isolation)
        """
        # Validate filter_metadata if provided (ensures IDs match this clone)
        # This validation ensures we know which namespace to use and verifies data integrity
        if filter_metadata:
            self._validate_metadata(filter_metadata)
        
        logger.debug(
            "Searching in clone namespace",
            clone_id=str(self.clone_id),
            tenant_id=str(self.tenant_id),
            namespace=self.namespace,
            query_preview=query[:50]
        )
        
        # Call base store with namespace ALWAYS provided and validation enabled
        # Namespace ensures infrastructure-level isolation
        # Validation ensures filter_metadata matches expected IDs (double-check)
        return self.base_store.search(
            query=query,
            n_results=n_results,
            filter_metadata=filter_metadata,
            namespace=self.namespace,  # ALWAYS provided - never None
            validate_tenant_clone_ids=True,  # ALWAYS enabled for clone-scoped operations
            expected_tenant_id=str(self.tenant_id),
            expected_clone_id=str(self.clone_id),
        )
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add texts to the vector store in this clone's namespace.
        Namespace isolation ensures vectors are stored only in this clone's namespace.
        Additionally validates that metadata includes matching tenant_id and clone_id.
        
        Args:
            texts: List of text strings to add
            metadatas: Optional list of metadata dicts (tenant_id/clone_id will be validated and added)
            ids: Optional list of vector IDs
        
        Returns:
            List of vector IDs
        """
        if not texts:
            return []
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Validate and ensure tenant_id and clone_id are in each metadata
        # This validation ensures we know which namespace to use and verifies data integrity
        validated_metadatas = []
        for i, metadata in enumerate(metadatas):
            validated_metadata = self._validate_metadata(metadata, metadata_index=i)
            validated_metadatas.append(validated_metadata)
        
        logger.debug(
            "Adding texts to clone namespace",
            clone_id=str(self.clone_id),
            tenant_id=str(self.tenant_id),
            namespace=self.namespace,
            text_count=len(texts)
        )
        
        # Call base store with namespace ALWAYS provided and validation enabled
        # Namespace ensures infrastructure-level isolation
        # Validation ensures metadata matches expected IDs (double-check)
        return self.base_store.add_texts(
            texts=texts,
            metadatas=validated_metadatas,
            ids=ids,
            namespace=self.namespace,  # ALWAYS provided - never None
            validate_tenant_clone_ids=True,  # ALWAYS enabled for clone-scoped operations
            expected_tenant_id=str(self.tenant_id),
            expected_clone_id=str(self.clone_id),
        )
    
    def delete(
        self,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Delete texts from vector store within this clone's namespace.
        Namespace isolation ensures only this clone's vectors can be deleted.
        Additionally validates filter_metadata matches this clone's IDs if provided.
        
        Args:
            ids: Optional list of vector IDs to delete
            filter_metadata: Optional additional metadata filters (for filtering within namespace)
        
        Returns:
            True if deletion was successful
        """
        # Validate filter_metadata if provided (ensures IDs match this clone)
        # This validation ensures we know which namespace to use and verifies data integrity
        if filter_metadata:
            self._validate_metadata(filter_metadata)
        
        logger.debug(
            "Deleting from clone namespace",
            clone_id=str(self.clone_id),
            tenant_id=str(self.tenant_id),
            namespace=self.namespace,
            ids_count=len(ids) if ids else 0
        )
        
        # Call base store with namespace ALWAYS provided and validation enabled
        # Namespace ensures infrastructure-level isolation
        # Validation ensures filter_metadata matches expected IDs (double-check)
        return self.base_store.delete(
            ids=ids,
            filter_metadata=filter_metadata,
            namespace=self.namespace,  # ALWAYS provided - never None
            validate_tenant_clone_ids=True,  # ALWAYS enabled for clone-scoped operations
            expected_tenant_id=str(self.tenant_id),
            expected_clone_id=str(self.clone_id),
        )
    
    def get_collection_count(self) -> int:
        """
        Get the number of vectors in this clone's namespace.
        Note: This requires querying the namespace stats, which may not be directly available.
        For now, returns total index count. Future: implement namespace-specific stats.
        """
        # TODO: Implement namespace-specific count if Pinecone API supports it
        # For now, return total count (namespace isolation ensures queries only return this clone's data)
        return self.base_store.get_collection_count()
    
    def reset(self) -> bool:
        """
        Reset this clone's namespace (delete all vectors in this clone's namespace).
        WARNING: This deletes all vectors in this clone's namespace only.
        Other clones' data remains untouched due to namespace isolation.
        """
        logger.warning(
            "Resetting clone namespace",
            clone_id=str(self.clone_id),
            tenant_id=str(self.tenant_id),
            namespace=self.namespace
        )
        # Delete all vectors in this namespace by querying and deleting
        # Use a dummy query to get all vectors in the namespace
        from src.rag.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        dummy_embedding = [0.0] * embedding_service.get_embedding_dimension()
        
        try:
            # Query all vectors in namespace
            results = self.base_store.index.query(
                vector=dummy_embedding,
                top_k=10000,  # Maximum reasonable limit
                include_metadata=False,
                namespace=self.namespace,
            )
            
            if results.matches:
                ids_to_delete = [match.id for match in results.matches]
                self.base_store.index.delete(ids=ids_to_delete, namespace=self.namespace)
                logger.info("Clone namespace reset", namespace=self.namespace, vectors_deleted=len(ids_to_delete))
                return True
            else:
                logger.info("No vectors found in namespace", namespace=self.namespace)
                return True
        except Exception as e:
            logger.error("Error resetting clone namespace", error=str(e), namespace=self.namespace)
            return False

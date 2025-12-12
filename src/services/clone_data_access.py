"""Clone-scoped data access service with ID validation"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.database.models import Clone, Tenant, Document, Insight
from src.rag.clone_vector_store import CloneVectorStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CloneDataAccessService:
    """
    Central service for all clone-scoped data operations.
    Validates clone_id and tenant_id before any data access to prevent data leakage.
    """
    
    def __init__(self, clone_id: UUID, tenant_id: UUID, db: Session):
        """
        Initialize service with clone and tenant IDs.
        
        Args:
            clone_id: UUID of the clone
            tenant_id: UUID of the tenant
            db: Database session
        """
        self.clone_id = clone_id
        self.tenant_id = tenant_id
        self.db = db
        
        # Validate clone belongs to tenant
        self.validate_clone_access(clone_id, tenant_id)
    
    def validate_clone_access(self, clone_id: UUID, tenant_id: UUID) -> bool:
        """
        Verify that clone belongs to tenant.
        Raises HTTPException if validation fails.
        
        Args:
            clone_id: UUID of the clone
            tenant_id: UUID of the tenant
        
        Returns:
            True if validation passes
        
        Raises:
            HTTPException(403): If clone doesn't belong to tenant
            HTTPException(404): If clone or tenant doesn't exist
        """
        clone = self.db.query(Clone).filter(Clone.id == clone_id).first()
        
        if not clone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clone not found"
            )
        
        if clone.tenant_id != tenant_id:
            logger.warning(
                "Clone access denied - tenant mismatch",
                clone_id=str(clone_id),
                clone_tenant_id=str(clone.tenant_id),
                requested_tenant_id=str(tenant_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clone does not belong to the specified tenant"
            )
        
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return True
    
    def validate_document_access(self, document_id: UUID) -> Document:
        """
        Verify that document belongs to this clone and tenant.
        
        Args:
            document_id: UUID of the document
        
        Returns:
            Document model if access is granted
        
        Raises:
            HTTPException(403): If document doesn't belong to clone
            HTTPException(404): If document doesn't exist
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document.clone_id != self.clone_id:
            logger.warning(
                "Document access denied - clone mismatch",
                document_id=str(document_id),
                document_clone_id=str(document.clone_id),
                requested_clone_id=str(self.clone_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document does not belong to this clone"
            )
        
        # Verify clone belongs to tenant (double-check)
        if document.clone.tenant_id != self.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document does not belong to this tenant"
            )
        
        return document
    
    def validate_insight_access(self, insight_id: UUID) -> Insight:
        """
        Verify that insight belongs to this clone and tenant.
        
        Args:
            insight_id: UUID of the insight
        
        Returns:
            Insight model if access is granted
        
        Raises:
            HTTPException(403): If insight doesn't belong to clone
            HTTPException(404): If insight doesn't exist
        """
        insight = self.db.query(Insight).filter(Insight.id == insight_id).first()
        
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insight not found"
            )
        
        if insight.clone_id != self.clone_id:
            logger.warning(
                "Insight access denied - clone mismatch",
                insight_id=str(insight_id),
                insight_clone_id=str(insight.clone_id),
                requested_clone_id=str(self.clone_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insight does not belong to this clone"
            )
        
        # Verify clone belongs to tenant (double-check)
        if insight.clone.tenant_id != self.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insight does not belong to this tenant"
            )
        
        return insight
    
    def get_documents(self) -> List[Document]:
        """
        Get all documents for this clone.
        Automatically filters by clone_id.
        
        Returns:
            List of Document models
        """
        return self.db.query(Document).filter(
            Document.clone_id == self.clone_id
        ).all()
    
    def get_insights(self) -> List[Insight]:
        """
        Get all insights for this clone.
        Automatically filters by clone_id.
        
        Returns:
            List of Insight models
        """
        return self.db.query(Insight).filter(
            Insight.clone_id == self.clone_id
        ).all()
    
    def get_vector_store(self) -> CloneVectorStore:
        """
        Get a CloneVectorStore instance for this clone.
        All operations will be automatically filtered by clone_id and tenant_id.
        
        Returns:
            CloneVectorStore instance
        """
        return CloneVectorStore(
            clone_id=self.clone_id,
            tenant_id=self.tenant_id
        )

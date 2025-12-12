"""Security validators for clone ownership and data access verification"""

from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.database.models import Clone, Tenant, Document, Insight
from src.utils.logging import get_logger

logger = get_logger(__name__)


def validate_clone_ownership(clone_id: UUID, tenant_id: UUID, db: Session) -> bool:
    """
    Verify that clone belongs to tenant.
    Raises HTTPException if validation fails.
    
    Args:
        clone_id: UUID of the clone
        tenant_id: UUID of the tenant
        db: Database session
    
    Returns:
        True if validation passes
    
    Raises:
        HTTPException(403): If clone doesn't belong to tenant
        HTTPException(404): If clone or tenant doesn't exist
    """
    clone = db.query(Clone).filter(Clone.id == clone_id).first()
    
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
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return True


def validate_document_access(document_id: UUID, clone_id: UUID, tenant_id: UUID, db: Session) -> Document:
    """
    Verify that document belongs to clone and tenant.
    
    Args:
        document_id: UUID of the document
        clone_id: UUID of the clone
        tenant_id: UUID of the tenant
        db: Database session
    
    Returns:
        Document model if access is granted
    
    Raises:
        HTTPException(403): If document doesn't belong to clone
        HTTPException(404): If document doesn't exist
    """
    # First validate clone ownership
    validate_clone_ownership(clone_id, tenant_id, db)
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.clone_id != clone_id:
        logger.warning(
            "Document access denied - clone mismatch",
            document_id=str(document_id),
            document_clone_id=str(document.clone_id),
            requested_clone_id=str(clone_id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document does not belong to this clone"
        )
    
    # Verify clone belongs to tenant (double-check)
    if document.clone.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document does not belong to this tenant"
        )
    
    return document


def validate_insight_access(insight_id: UUID, clone_id: UUID, tenant_id: UUID, db: Session) -> Insight:
    """
    Verify that insight belongs to clone and tenant.
    
    Args:
        insight_id: UUID of the insight
        clone_id: UUID of the clone
        tenant_id: UUID of the tenant
        db: Database session
    
    Returns:
        Insight model if access is granted
    
    Raises:
        HTTPException(403): If insight doesn't belong to clone
        HTTPException(404): If insight doesn't exist
    """
    # First validate clone ownership
    validate_clone_ownership(clone_id, tenant_id, db)
    
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found"
        )
    
    if insight.clone_id != clone_id:
        logger.warning(
            "Insight access denied - clone mismatch",
            insight_id=str(insight_id),
            insight_clone_id=str(insight.clone_id),
            requested_clone_id=str(clone_id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insight does not belong to this clone"
        )
    
    # Verify clone belongs to tenant (double-check)
    if insight.clone.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insight does not belong to this tenant"
        )
    
    return insight


def validate_s3_path(s3_key: str, tenant_id: UUID, clone_id: UUID) -> bool:
    """
    Verify that S3 key path matches expected tenant_id and clone_id structure.
    
    Args:
        s3_key: S3 object key
        tenant_id: Expected tenant ID
        clone_id: Expected clone ID
    
    Returns:
        True if path is valid
    
    Raises:
        HTTPException(403): If path doesn't match expected structure
    """
    expected_prefix = f"documents/{tenant_id}/{clone_id}/"
    insights_prefix = f"insights/{tenant_id}/{clone_id}/"
    
    if not (s3_key.startswith(expected_prefix) or s3_key.startswith(insights_prefix)):
        logger.warning(
            "S3 path validation failed",
            s3_key=s3_key,
            expected_prefix=expected_prefix,
            insights_prefix=insights_prefix
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="S3 path does not match clone/tenant structure"
        )
    
    return True

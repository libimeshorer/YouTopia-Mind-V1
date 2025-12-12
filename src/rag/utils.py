"""Utility functions for RAG operations"""

from typing import Dict
from uuid import UUID
from src.utils.logging import get_logger

logger = get_logger(__name__)


def validate_metadata(
    metadata: Dict,
    tenant_id: UUID,
    clone_id: UUID,
    metadata_index: int = None,
) -> Dict:
    """
    Validate that metadata includes tenant_id and clone_id, and that they match expected values.
    This validation ensures data integrity even though namespaces provide infrastructure-level isolation.
    
    Args:
        metadata: Metadata dictionary to validate
        tenant_id: Expected tenant_id
        clone_id: Expected clone_id
        metadata_index: Optional index for error messages (when validating a list)
    
    Returns:
        Validated metadata dictionary with tenant_id and clone_id ensured
    
    Raises:
        ValueError: If tenant_id or clone_id don't match expected values
    """
    metadata = metadata.copy() if metadata else {}
    
    # Check if metadata contains tenant_id and validate it matches
    if "tenant_id" in metadata:
        if str(metadata["tenant_id"]) != str(tenant_id):
            index_msg = f" at index {metadata_index}" if metadata_index is not None else ""
            raise ValueError(
                f"Metadata{index_msg} tenant_id ({metadata['tenant_id']}) does not match "
                f"expected tenant_id ({tenant_id})"
            )
    
    # Check if metadata contains clone_id and validate it matches
    if "clone_id" in metadata:
        if str(metadata["clone_id"]) != str(clone_id):
            index_msg = f" at index {metadata_index}" if metadata_index is not None else ""
            raise ValueError(
                f"Metadata{index_msg} clone_id ({metadata['clone_id']}) does not match "
                f"expected clone_id ({clone_id})"
            )
    
    # Ensure tenant_id and clone_id are in metadata (for reference/auditing)
    metadata["tenant_id"] = str(tenant_id)
    metadata["clone_id"] = str(clone_id)
    
    return metadata

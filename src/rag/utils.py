"""Utility functions for RAG operations"""

import hashlib
from typing import Dict
from uuid import UUID
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# RL Scoring Constants (Single Source of Truth)
# =============================================================================
# These constants control the reinforcement learning system for chunk scoring.
# See docs/RL_OVERVIEW.md for detailed documentation.

# EMA decay factor: new_score = old_score * DECAY + rating * LEARNING_RATE
# 0.9 means ~10 recent feedbacks have significant influence
RL_DECAY = 0.9
RL_LEARNING_RATE = 0.1  # = 1 - DECAY

# Maximum boost/penalty to apply during retrieval
# 0.3 means a perfect score (+1) adds 0.3 to similarity
RL_MAX_BOOST = 0.3


def hash_chunk_content(content: str) -> str:
    """Generate SHA256 hash of chunk content for scoring/deduplication.

    IMPORTANT: This is the single source of truth for chunk hashing.
    Both score updates and score lookups MUST use this function to ensure
    hash consistency. If hashes don't match, RL learning silently fails.

    Args:
        content: The text content of the chunk

    Returns:
        64-character hex string (SHA256 hash)
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_score_boost(learned_score: float) -> float:
    """Convert a learned chunk score to a retrieval boost value.

    The boost is capped at ±RL_MAX_BOOST to prevent scores from
    completely overriding semantic similarity.

    Args:
        learned_score: The learned chunk score (bounded to roughly -1 to +1 by EMA)

    Returns:
        Boost value to add to similarity score (±RL_MAX_BOOST max)
    """
    return max(-RL_MAX_BOOST, min(RL_MAX_BOOST, learned_score * RL_MAX_BOOST))


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

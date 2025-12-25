"""Integrations API router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Integration
from src.utils.logging import get_logger
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter()


class IntegrationResponse(BaseModel):
    """Integration response model"""
    id: str
    platform: str
    status: str
    lastSyncAt: Optional[str] = None
    createdAt: str
    updatedAt: str
    
    class Config:
        from_attributes = True


@router.get("/integrations", response_model=List[IntegrationResponse])
async def list_integrations(
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    List all integrations for the current clone
    """
    try:
        integrations = db.query(Integration).filter(
            Integration.clone_id == clone_context.clone_id
        ).all()
        
        return [
            IntegrationResponse(
                id=str(integration.id),
                platform=integration.platform.value if hasattr(integration.platform, 'value') else str(integration.platform),
                status=integration.status.value if hasattr(integration.status, 'value') else str(integration.status),
                lastSyncAt=integration.last_sync_at.isoformat() if integration.last_sync_at else None,
                createdAt=integration.created_at.isoformat(),
                updatedAt=integration.updated_at.isoformat(),
            )
            for integration in integrations
        ]
    except Exception as e:
        logger.error("Error listing integrations", error=str(e), clone_id=clone_context.clone_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list integrations"
        )


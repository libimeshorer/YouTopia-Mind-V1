"""Training API router

NOTE: The TrainingStatus table and progress percentage calculation have been deprecated.
The frontend now uses a crystal-based engagement metric calculated client-side from
document/insight/integration counts. The /training/stats endpoint provides all necessary data.

The TrainingStatus table is kept for backwards compatibility but is no longer actively used.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Document, Insight, Integration
from src.utils.logging import get_logger
from pydantic import BaseModel
from typing import Optional

logger = get_logger(__name__)

router = APIRouter()


class TrainingStatsResponse(BaseModel):
    """Training stats response model - primary endpoint for crystal calculation"""
    documentsCount: int
    insightsCount: int
    integrationsCount: int
    dataPoints: int
    lastActivity: Optional[str] = None


@router.get("/training/stats", response_model=TrainingStatsResponse)
async def get_training_stats(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """
    Get training statistics for crystal calculation.

    Returns counts of documents, insights, and integrations which are used
    by the frontend to calculate and display knowledge crystals.
    """
    # Count completed documents
    documents_count = db.query(func.count(Document.id)).filter(
        Document.clone_id == clone_ctx.clone_id,
        Document.status == "complete"
    ).scalar() or 0

    # Count insights
    insights_count = db.query(func.count(Insight.id)).filter(
        Insight.clone_id == clone_ctx.clone_id
    ).scalar() or 0

    # Count connected integrations
    integrations_count = db.query(func.count(Integration.id)).filter(
        Integration.clone_id == clone_ctx.clone_id,
        Integration.status == "connected"
    ).scalar() or 0

    # Get last activity timestamp
    last_doc = db.query(func.max(Document.uploaded_at)).filter(
        Document.clone_id == clone_ctx.clone_id
    ).scalar()

    last_insight = db.query(func.max(Insight.created_at)).filter(
        Insight.clone_id == clone_ctx.clone_id
    ).scalar()

    last_activity = None
    if last_doc and last_insight:
        last_activity = max(last_doc, last_insight).isoformat()
    elif last_doc:
        last_activity = last_doc.isoformat()
    elif last_insight:
        last_activity = last_insight.isoformat()

    # Calculate data points (chunks from documents + insights)
    chunks_count = db.query(func.sum(Document.chunks_count)).filter(
        Document.clone_id == clone_ctx.clone_id,
        Document.status == "complete"
    ).scalar() or 0

    data_points = chunks_count + insights_count

    return TrainingStatsResponse(
        documentsCount=documents_count,
        insightsCount=insights_count,
        integrationsCount=integrations_count,
        dataPoints=data_points,
        lastActivity=last_activity,
    )

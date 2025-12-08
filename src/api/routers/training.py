"""Training API router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from src.api.dependencies import get_current_user, get_db
from src.database.models import User, Document, Insight, TrainingStatus, Integration
from src.utils.logging import get_logger
from pydantic import BaseModel
from typing import List, Dict, Any

logger = get_logger(__name__)

router = APIRouter()


class TrainingStatusResponse(BaseModel):
    """Training status response model"""
    isComplete: bool
    progress: float
    documentsCount: int
    insightsCount: int
    integrationsCount: int
    thresholds: Dict[str, int]
    achievements: List[str]


class TrainingStatsResponse(BaseModel):
    """Training stats response model"""
    documentsCount: int
    insightsCount: int
    integrationsCount: int
    dataPoints: int
    lastActivity: Optional[str] = None


def calculate_training_status(user: User, db: Session) -> TrainingStatus:
    """Calculate or get training status for a user"""
    # Get or create training status
    training_status = db.query(TrainingStatus).filter(
        TrainingStatus.user_id == user.id
    ).first()
    
    # Count actual data
    documents_count = db.query(func.count(Document.id)).filter(
        Document.user_id == user.id,
        Document.status == "complete"
    ).scalar() or 0
    
    insights_count = db.query(func.count(Insight.id)).filter(
        Insight.user_id == user.id
    ).scalar() or 0
    
    integrations_count = db.query(func.count(Integration.id)).filter(
        Integration.user_id == user.id,
        Integration.status == "connected"
    ).scalar() or 0
    
    # Default thresholds
    thresholds = {
        "minDocuments": 1,
        "minInsights": 1,
        "minIntegrations": 1,
    }
    
    if training_status:
        # Update existing status
        training_status.documents_count = documents_count
        training_status.insights_count = insights_count
        training_status.integrations_count = integrations_count
        training_status.thresholds_json = thresholds
        
        # Calculate progress
        progress_items = [
            min(100, (documents_count / thresholds["minDocuments"]) * 100) if thresholds["minDocuments"] > 0 else 100,
            min(100, (insights_count / thresholds["minInsights"]) * 100) if thresholds["minInsights"] > 0 else 100,
            min(100, (integrations_count / thresholds["minIntegrations"]) * 100) if thresholds["minIntegrations"] > 0 else 100,
        ]
        training_status.progress = sum(progress_items) / len(progress_items)
        
        # Check if complete
        training_status.is_complete = (
            documents_count >= thresholds["minDocuments"] and
            insights_count >= thresholds["minInsights"] and
            integrations_count >= thresholds["minIntegrations"]
        )
        
        # Update achievements
        achievements = []
        if documents_count >= thresholds["minDocuments"]:
            achievements.append("Documents uploaded")
        if insights_count >= thresholds["minInsights"]:
            achievements.append("Insights recorded")
        if integrations_count >= thresholds["minIntegrations"]:
            achievements.append("Integrations connected")
        training_status.achievements_json = achievements
        
    else:
        # Create new training status
        progress_items = [
            min(100, (documents_count / thresholds["minDocuments"]) * 100) if thresholds["minDocuments"] > 0 else 100,
            min(100, (insights_count / thresholds["minInsights"]) * 100) if thresholds["minInsights"] > 0 else 100,
            min(100, (integrations_count / thresholds["minIntegrations"]) * 100) if thresholds["minIntegrations"] > 0 else 100,
        ]
        progress = sum(progress_items) / len(progress_items)
        
        is_complete = (
            documents_count >= thresholds["minDocuments"] and
            insights_count >= thresholds["minInsights"] and
            integrations_count >= thresholds["minIntegrations"]
        )
        
        achievements = []
        if documents_count >= thresholds["minDocuments"]:
            achievements.append("Documents uploaded")
        if insights_count >= thresholds["minInsights"]:
            achievements.append("Insights recorded")
        if integrations_count >= thresholds["minIntegrations"]:
            achievements.append("Integrations connected")
        
        training_status = TrainingStatus(
            user_id=user.id,
            is_complete=is_complete,
            progress=progress,
            documents_count=documents_count,
            insights_count=insights_count,
            integrations_count=integrations_count,
            thresholds_json=thresholds,
            achievements_json=achievements,
        )
        db.add(training_status)
    
    db.commit()
    db.refresh(training_status)
    
    return training_status


@router.get("/training/status", response_model=TrainingStatusResponse)
async def get_training_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get training status for the current user"""
    training_status = calculate_training_status(user, db)
    
    return TrainingStatusResponse(
        isComplete=training_status.is_complete,
        progress=training_status.progress,
        documentsCount=training_status.documents_count,
        insightsCount=training_status.insights_count,
        integrationsCount=training_status.integrations_count,
        thresholds=training_status.thresholds_json,
        achievements=training_status.achievements_json,
    )


@router.post("/training/complete", response_model=TrainingStatusResponse)
async def complete_training(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark training as complete"""
    training_status = calculate_training_status(user, db)
    
    if training_status.progress < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Training is not complete. Please complete all required steps."
        )
    
    training_status.is_complete = True
    db.commit()
    db.refresh(training_status)
    
    return TrainingStatusResponse(
        isComplete=training_status.is_complete,
        progress=training_status.progress,
        documentsCount=training_status.documents_count,
        insightsCount=training_status.insights_count,
        integrationsCount=training_status.integrations_count,
        thresholds=training_status.thresholds_json,
        achievements=training_status.achievements_json,
    )


@router.get("/training/stats", response_model=TrainingStatsResponse)
async def get_training_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get training statistics"""
    training_status = calculate_training_status(user, db)
    
    # Get last activity timestamp
    last_doc = db.query(func.max(Document.uploaded_at)).filter(
        Document.user_id == user.id
    ).scalar()
    
    last_insight = db.query(func.max(Insight.created_at)).filter(
        Insight.user_id == user.id
    ).scalar()
    
    last_activity = None
    if last_doc and last_insight:
        last_activity = max(last_doc, last_insight).isoformat()
    elif last_doc:
        last_activity = last_doc.isoformat()
    elif last_insight:
        last_activity = last_insight.isoformat()
    
    # Calculate data points (chunks from documents + insights)
    data_points = (
        db.query(func.sum(Document.chunks_count)).filter(
            Document.user_id == user.id,
            Document.status == "complete"
        ).scalar() or 0
    ) + training_status.insights_count
    
    return TrainingStatsResponse(
        documentsCount=training_status.documents_count,
        insightsCount=training_status.insights_count,
        integrationsCount=training_status.integrations_count,
        dataPoints=data_points,
        lastActivity=last_activity,
    )

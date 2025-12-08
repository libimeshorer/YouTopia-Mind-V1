"""Insights API router"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from src.api.dependencies import get_current_user, get_db
from src.database.models import User, Insight
from src.utils.aws import S3Client
from src.utils.logging import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter()


class InsightResponse(BaseModel):
    """Insight response model"""
    id: str
    content: str
    type: str
    audioUrl: Optional[str] = None
    transcriptionId: Optional[str] = None
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class InsightCreate(BaseModel):
    """Insight creation model"""
    content: str


class InsightUpdate(BaseModel):
    """Insight update model"""
    content: str


@router.get("/insights", response_model=List[InsightResponse])
async def list_insights(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all insights for the current user"""
    insights = db.query(Insight).filter(Insight.user_id == user.id).order_by(Insight.created_at.desc()).all()
    return [
        InsightResponse(
            id=str(insight.id),
            content=insight.content,
            type=insight.type,
            audioUrl=insight.audio_url,
            transcriptionId=insight.transcription_id,
            createdAt=insight.created_at.isoformat(),
            updatedAt=insight.updated_at.isoformat(),
        )
        for insight in insights
    ]


@router.post("/insights", response_model=InsightResponse, status_code=status.HTTP_201_CREATED)
async def create_insight(
    insight_data: InsightCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new text insight"""
    insight = Insight(
        user_id=user.id,
        content=insight_data.content,
        type="text",
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    
    return InsightResponse(
        id=str(insight.id),
        content=insight.content,
        type=insight.type,
        audioUrl=insight.audio_url,
        transcriptionId=insight.transcription_id,
        createdAt=insight.created_at.isoformat(),
        updatedAt=insight.updated_at.isoformat(),
    )


@router.post("/insights/voice", response_model=InsightResponse, status_code=status.HTTP_201_CREATED)
async def upload_voice_insight(
    audio: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a voice recording as an insight"""
    # Validate file type
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file"
        )
    
    # Read audio file
    audio_bytes = await audio.read()
    
    # Upload to S3
    s3_client = S3Client()
    insight_id = uuid.uuid4()
    s3_key = f"insights/{user.id}/{insight_id}/audio.{audio.filename.split('.')[-1] if '.' in audio.filename else 'webm'}"
    
    try:
        s3_client.put_object(s3_key, audio_bytes, content_type=audio.content_type)
        
        # Generate presigned URL
        import boto3
        from src.config.settings import settings
        
        s3_client_boto = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        
        audio_url = s3_client_boto.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
            ExpiresIn=86400 * 7,  # 7 days
        )
    except Exception as e:
        logger.error("Failed to upload audio to S3", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload audio file"
        )
    
    # Create insight record
    insight = Insight(
        id=insight_id,
        user_id=user.id,
        content="[Voice recording]",  # Placeholder, will be updated after transcription
        type="voice",
        audio_url=audio_url,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    
    # TODO: Trigger transcription job asynchronously
    # For now, we'll just return the insight with the audio URL
    
    return InsightResponse(
        id=str(insight.id),
        content=insight.content,
        type=insight.type,
        audioUrl=insight.audio_url,
        transcriptionId=insight.transcription_id,
        createdAt=insight.created_at.isoformat(),
        updatedAt=insight.updated_at.isoformat(),
    )


@router.put("/insights/{insight_id}", response_model=InsightResponse)
async def update_insight(
    insight_id: str,
    insight_data: InsightUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an insight"""
    try:
        insight_uuid = uuid.UUID(insight_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid insight ID format"
        )
    
    insight = db.query(Insight).filter(
        Insight.id == insight_uuid,
        Insight.user_id == user.id
    ).first()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found"
        )
    
    insight.content = insight_data.content
    db.commit()
    db.refresh(insight)
    
    return InsightResponse(
        id=str(insight.id),
        content=insight.content,
        type=insight.type,
        audioUrl=insight.audio_url,
        transcriptionId=insight.transcription_id,
        createdAt=insight.created_at.isoformat(),
        updatedAt=insight.updated_at.isoformat(),
    )


@router.delete("/insights/{insight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insight(
    insight_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an insight"""
    try:
        insight_uuid = uuid.UUID(insight_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid insight ID format"
        )
    
    insight = db.query(Insight).filter(
        Insight.id == insight_uuid,
        Insight.user_id == user.id
    ).first()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found"
        )
    
    # Delete audio from S3 if it's a voice insight
    if insight.audio_url:
        try:
            # Extract S3 key from URL or store it separately
            # For now, we'll skip S3 deletion
            pass
        except Exception as e:
            logger.warning("Failed to delete audio from S3", error=str(e))
    
    db.delete(insight)
    db.commit()
    
    return None


@router.get("/insights/search", response_model=List[InsightResponse])
async def search_insights(
    q: str = Query(..., description="Search query"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search insights by content"""
    insights = db.query(Insight).filter(
        Insight.user_id == user.id,
        Insight.content.ilike(f"%{q}%")
    ).order_by(Insight.created_at.desc()).all()
    
    return [
        InsightResponse(
            id=str(insight.id),
            content=insight.content,
            type=insight.type,
            audioUrl=insight.audio_url,
            transcriptionId=insight.transcription_id,
            createdAt=insight.created_at.isoformat(),
            updatedAt=insight.updated_at.isoformat(),
        )
        for insight in insights
    ]

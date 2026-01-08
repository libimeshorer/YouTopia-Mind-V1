"""Insights API router"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from uuid import UUID
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Insight
from src.services.clone_data_access import CloneDataAccessService
from src.rag.clone_vector_store import CloneVectorStore
from src.ingestion.chunking import TextChunker
from src.config.settings import settings
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


def _store_insight_in_pinecone(
    content: str,
    insight_id: UUID,
    clone_id: UUID,
    tenant_id: UUID,
    insight_type: str,
    vector_store: CloneVectorStore,
    created_at: Optional[datetime] = None,
) -> bool:
    """
    Embed and store an insight in Pinecone.
    
    If content is longer than chunk_size, it will be chunked.
    Otherwise, it will be stored as a single vector.
    
    Uses upsert pattern - if vectors with the same IDs exist, they will be replaced.
    This makes the operation idempotent.
    
    TODO: If we add persistent sync status for Pinecone writes, add a column like
    Insight.pinecone_synced_at and update it after successful upsert to enable retries/observability.
    
    Args:
        content: The insight content text
        insight_id: UUID of the insight
        clone_id: UUID of the clone
        tenant_id: UUID of the tenant
        insight_type: Type of insight ("text" or "voice")
        vector_store: CloneVectorStore instance for this clone
        created_at: Optional datetime for metadata (uses current time if not provided)
    
    Returns:
        True if storage was successful, False otherwise
    """
    if not content or not content.strip():
        logger.warning("Empty insight content, skipping Pinecone storage", insight_id=str(insight_id))
        return False
    
    try:
        chunker = TextChunker()
        chunk_size = settings.chunk_size
        
        # Use provided created_at or current time
        metadata_created_at = created_at if created_at else datetime.utcnow()
        
        # Prepare base metadata
        base_metadata = {
            "insight_id": str(insight_id),
            "source": "insight",
            "type": insight_type,
            "created_at": metadata_created_at.isoformat(),
        }
        
        # Check if content needs chunking
        if len(content) > chunk_size:
            # Chunk the content
            chunks = chunker.chunk_text(content, base_metadata)
            
            if not chunks:
                logger.warning("No chunks generated from insight", insight_id=str(insight_id))
                return False
            
            # Prepare texts, metadatas, and IDs for chunked content
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            ids = [f"insight_{insight_id}_chunk_{i}" for i in range(len(chunks))]
            
            logger.info(
                "Storing chunked insight in Pinecone",
                insight_id=str(insight_id),
                chunk_count=len(chunks)
            )
        else:
            # Store as single vector
            texts = [content]
            metadatas = [base_metadata]
            ids = [f"insight_{insight_id}"]
            
            logger.info(
                "Storing insight in Pinecone",
                insight_id=str(insight_id),
                chunked=False
            )
        
        # Store in Pinecone (upsert - replaces existing vectors with same IDs)
        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        
        logger.info(
            "Insight stored in Pinecone successfully",
            insight_id=str(insight_id),
            vector_count=len(ids)
        )
        return True
    except Exception as e:
        # Log error but don't fail the API call
        logger.error(
            "Failed to store insight in Pinecone",
            error=str(e),
            insight_id=str(insight_id),
            exc_info=True
        )
        return False


def _delete_insight_from_pinecone(
    insight_id: UUID,
    vector_store: CloneVectorStore,
) -> None:
    """
    Delete all vectors associated with an insight from Pinecone.
    
    This handles both single vectors and chunked vectors.
    
    Args:
        insight_id: UUID of the insight
        vector_store: CloneVectorStore instance for this clone
    """
    try:
        # Delete by metadata filter (works for both single and chunked vectors)
        deleted = vector_store.delete(
            filter_metadata={
                "insight_id": str(insight_id),
                "source": "insight",
            }
        )
        
        if deleted:
            logger.info(
                "Insight deleted from Pinecone",
                insight_id=str(insight_id)
            )
        else:
            logger.warning(
                "Failed to delete insight from Pinecone",
                insight_id=str(insight_id)
            )
    except Exception as e:
        # Log error but don't fail the API call
        logger.error(
            "Error deleting insight from Pinecone",
            error=str(e),
            insight_id=str(insight_id),
            exc_info=True
        )


@router.get("/insights", response_model=List[InsightResponse])
async def list_insights(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all insights for the current clone"""
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    insights = data_access.get_insights()
    # Sort by created_at descending
    insights.sort(key=lambda x: x.created_at, reverse=True)
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
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Create a new text insight"""
    insight = Insight(
        clone_id=clone_ctx.clone_id,
        content=insight_data.content,
        type="text",
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    
    # Store in Pinecone for RAG retrieval (upsert pattern - idempotent)
    try:
        data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
        vector_store = data_access.get_vector_store()
        _store_insight_in_pinecone(
            content=insight.content,
            insight_id=insight.id,
            clone_id=clone_ctx.clone_id,
            tenant_id=clone_ctx.tenant_id,
            insight_type=insight.type,
            vector_store=vector_store,
            created_at=insight.created_at,
        )
        # TODO: If we add persistent sync tracking, update pinecone_synced_at here on success/failure.
    except Exception as e:
        # Log error but don't fail the API call - insight is already saved in DB
        logger.error(
            "Failed to store insight in Pinecone after creation",
            error=str(e),
            insight_id=str(insight.id)
        )
    
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
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    # Upload to S3 with tenant_id and clone_id in path
    s3_client = S3Client()
    insight_id = uuid.uuid4()
    file_ext = audio.filename.split('.')[-1] if '.' in audio.filename else 'webm'
    s3_key = f"insights/{clone_ctx.tenant_id}/{clone_ctx.clone_id}/{insight_id}/audio.{file_ext}"
    
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
        clone_id=clone_ctx.clone_id,
        content="[Voice recording]",  # Placeholder, will be updated after transcription
        type="voice",
        audio_url=audio_url,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    
    # TODO: Trigger transcription job asynchronously
    # For now, we'll just return the insight with the audio URL
    # TODO: When transcription is implemented, after transcription updates insight.content,
    #       we should call _store_insight_in_pinecone() to chunk and store the transcribed text
    #       in Pinecone for RAG retrieval. This will enable voice insights to be searchable
    #       and available during chat conversations.
    
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
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    # Validate insight access (ensures insight belongs to this clone)
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    insight = data_access.validate_insight_access(insight_uuid)
    
    insight.content = insight_data.content
    db.commit()
    db.refresh(insight)
    
    # Store updated content in Pinecone (only for text insights)
    # Uses upsert pattern - existing vectors with same IDs will be replaced (idempotent)
    if insight.type == "text":
        try:
            vector_store = data_access.get_vector_store()
            _store_insight_in_pinecone(
                content=insight.content,
                insight_id=insight.id,
                clone_id=clone_ctx.clone_id,
                tenant_id=clone_ctx.tenant_id,
                insight_type=insight.type,
                vector_store=vector_store,
                created_at=insight.created_at,
            )
            # TODO: If we add persistent sync tracking, update pinecone_synced_at here on success/failure.
        except Exception as e:
            # Log error but don't fail the API call - insight is already updated in DB
            logger.error(
                "Failed to store updated insight in Pinecone",
                error=str(e),
                insight_id=str(insight.id)
            )
    
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
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    # Validate insight access (ensures insight belongs to this clone)
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    insight = data_access.validate_insight_access(insight_uuid)
    
    # Delete from Pinecone before deleting from database
    try:
        vector_store = data_access.get_vector_store()
        _delete_insight_from_pinecone(insight.id, vector_store)
    except Exception as e:
        # Log error but continue with deletion - don't fail the API call
        logger.warning(
            "Failed to delete insight from Pinecone",
            error=str(e),
            insight_id=str(insight_id)
        )
    
    # Delete audio from S3 if it's a voice insight
    if insight.audio_url:
        try:
            # Extract S3 key from presigned URL or reconstruct from path
            # S3 key format: insights/{tenant_id}/{clone_id}/{insight_id}/audio.{ext}
            s3_key = f"insights/{clone_ctx.tenant_id}/{clone_ctx.clone_id}/{insight_id}/"
            s3_client = S3Client()
            # List and delete objects with this prefix
            objects = s3_client.list_objects(s3_key)
            for obj_key in objects:
                s3_client.delete_object(obj_key)
        except Exception as e:
            logger.warning("Failed to delete audio from S3", error=str(e))
    
    db.delete(insight)
    db.commit()
    
    return None


@router.get("/insights/search", response_model=List[InsightResponse])
async def search_insights(
    q: str = Query(..., description="Search query"),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Search insights by content"""
    # Search insights filtered by clone_id
    insights = db.query(Insight).filter(
        Insight.clone_id == clone_ctx.clone_id,
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

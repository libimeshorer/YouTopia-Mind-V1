"""Documents API router"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from src.api.dependencies import get_current_user, get_db
from src.database.models import User, Document
from src.ingestion.document_ingester import DocumentIngester
from src.ingestion.pipeline import IngestionPipeline
from src.utils.aws import S3Client
from src.utils.logging import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter()


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str
    name: str
    size: int
    type: str
    status: str
    uploadedAt: str
    chunksExtracted: Optional[int] = None
    errorMessage: Optional[str] = None
    previewUrl: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user"""
    documents = db.query(Document).filter(Document.user_id == user.id).all()
    return [
        DocumentResponse(
            id=str(doc.id),
            name=doc.name,
            size=doc.size,
            type=doc.type,
            status=doc.status,
            uploadedAt=doc.uploaded_at.isoformat(),
            chunksExtracted=doc.chunks_count,
            errorMessage=doc.error_message,
        )
        for doc in documents
    ]


@router.post("/documents", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload one or more documents"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    s3_client = S3Client()
    document_ingester = DocumentIngester(s3_client=s3_client)
    pipeline = IngestionPipeline(document_ingester=document_ingester)
    
    uploaded_documents = []
    
    for file in files:
        try:
            # Validate file type
            allowed_extensions = [".pdf", ".docx", ".doc", ".txt"]
            file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}"
                )
            
            # Read file content
            file_bytes = await file.read()
            file_size = len(file_bytes)
            
            # Generate S3 key
            doc_id = uuid.uuid4()
            s3_key = f"documents/{user.id}/{doc_id}/{file.filename}"
            
            # Create document record
            doc = Document(
                id=doc_id,
                user_id=user.id,
                name=file.filename,
                size=file_size,
                type=file_ext or "application/octet-stream",
                status="pending",
                s3_key=s3_key,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            # Upload to S3
            try:
                s3_client.put_object(s3_key, file_bytes, content_type=file.content_type or "application/octet-stream")
            except Exception as e:
                logger.error("Failed to upload to S3", error=str(e))
                doc.status = "error"
                doc.error_message = f"S3 upload failed: {str(e)}"
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload file to storage"
                )
            
            # Process document asynchronously (in background)
            try:
                # Update status to processing
                doc.status = "processing"
                db.commit()
                
                # Process document
                chunks = document_ingester.ingest_from_bytes(
                    file_bytes,
                    file.filename,
                    source_name=file.filename,
                    additional_metadata={"user_id": str(user.id), "document_id": str(doc.id)}
                )
                
                # Store chunks in vector store
                if chunks:
                    texts = [chunk["text"] for chunk in chunks]
                    metadatas = [chunk["metadata"] for chunk in chunks]
                    pipeline.vector_store.add_texts(texts, metadatas=metadatas)
                    
                    # Update document
                    doc.status = "complete"
                    doc.chunks_count = len(chunks)
                else:
                    doc.status = "error"
                    doc.error_message = "No text extracted from document"
                
                db.commit()
                db.refresh(doc)
                
            except Exception as e:
                logger.error("Error processing document", error=str(e), document_id=str(doc.id))
                doc.status = "error"
                doc.error_message = str(e)
                db.commit()
            
            uploaded_documents.append(
                DocumentResponse(
                    id=str(doc.id),
                    name=doc.name,
                    size=doc.size,
                    type=doc.type,
                    status=doc.status,
                    uploadedAt=doc.uploaded_at.isoformat(),
                    chunksExtracted=doc.chunks_count,
                    errorMessage=doc.error_message,
                )
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error uploading document", error=str(e), filename=file.filename)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    return uploaded_documents


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details by ID"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    doc = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.user_id == user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse(
        id=str(doc.id),
        name=doc.name,
        size=doc.size,
        type=doc.type,
        status=doc.status,
        uploadedAt=doc.uploaded_at.isoformat(),
        chunksExtracted=doc.chunks_count,
        errorMessage=doc.error_message,
    )


@router.get("/documents/{document_id}/preview")
async def get_document_preview(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get S3 presigned URL for document preview"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    doc = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.user_id == user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Generate presigned URL
    s3_client = S3Client()
    try:
        # Use boto3 to generate presigned URL
        import boto3
        from src.config.settings import settings
        
        s3_client_boto = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        
        presigned_url = s3_client_boto.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": doc.s3_key},
            ExpiresIn=3600,  # 1 hour
        )
        
        return {"url": presigned_url}
    except Exception as e:
        logger.error("Error generating presigned URL", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview URL"
        )


@router.get("/documents/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document processing status"""
    return await get_document(document_id, user, db)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    doc = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.user_id == user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete from S3
    try:
        s3_client = S3Client()
        s3_client.delete_object(doc.s3_key)
    except Exception as e:
        logger.warning("Failed to delete from S3", error=str(e), s3_key=doc.s3_key)
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return None


@router.get("/documents/search", response_model=List[DocumentResponse])
async def search_documents(
    q: str = Query(..., description="Search query"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search documents by name"""
    # Simple text search on document names
    documents = db.query(Document).filter(
        Document.user_id == user.id,
        Document.name.ilike(f"%{q}%")
    ).all()
    
    return [
        DocumentResponse(
            id=str(doc.id),
            name=doc.name,
            size=doc.size,
            type=doc.type,
            status=doc.status,
            uploadedAt=doc.uploaded_at.isoformat(),
            chunksExtracted=doc.chunks_count,
            errorMessage=doc.error_message,
        )
        for doc in documents
    ]

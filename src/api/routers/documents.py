"""Documents API router"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import hashlib
from datetime import datetime
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Document
from src.database.db import get_db_session
from src.ingestion.document_ingester import DocumentIngester
from src.services.clone_data_access import CloneDataAccessService
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


def process_document_background(
    doc_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    tenant_id: uuid.UUID,
    clone_id: uuid.UUID,
):
    """
    Background task to process document after upload.

    This runs asynchronously so the upload response returns immediately.
    The frontend can poll /documents/{id}/status to check progress.
    """
    db = get_db_session()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            logger.error("Document not found in background task", document_id=str(doc_id))
            return

        # Update status to processing
        doc.status = "processing"
        db.commit()

        # Set up ingestion
        s3_client = S3Client()
        document_ingester = DocumentIngester(s3_client=s3_client)
        data_access = CloneDataAccessService(clone_id, tenant_id, db)
        vector_store = data_access.get_vector_store()

        # Process document
        chunks = document_ingester.ingest_from_bytes(
            file_bytes,
            filename,
            source_name=filename,
            additional_metadata={
                "tenant_id": str(tenant_id),
                "clone_id": str(clone_id),
                "document_id": str(doc_id)
            }
        )

        # Store chunks in vector store
        if chunks:
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            vector_store.add_texts(texts, metadatas=metadatas)

            doc.status = "complete"
            doc.chunks_count = len(chunks)
        else:
            doc.status = "error"
            doc.error_message = "No text extracted from document"

        db.commit()
        logger.info(
            "Document processing complete",
            document_id=str(doc_id),
            status=doc.status,
            chunks=doc.chunks_count,
        )

    except Exception as e:
        logger.error("Error processing document in background", error=str(e), document_id=str(doc_id))
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.status = "error"
                doc.error_message = str(e)[:500]  # Truncate long errors
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all documents for the current clone"""
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    documents = data_access.get_documents()
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
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Upload one or more documents (processing happens in background)"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )

    s3_client = S3Client()
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
            
            # Calculate file hash for duplicate detection
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            
            # Check for duplicate documents (same hash for this clone)
            existing_doc = db.query(Document).filter(
                Document.clone_id == clone_ctx.clone_id,
                Document.file_hash == file_hash
            ).first()
            
            if existing_doc:
                logger.info("Duplicate document detected", file_hash=file_hash, existing_doc_id=str(existing_doc.id), filename=file.filename)
                # Return existing document instead of creating duplicate
                uploaded_documents.append(
                    DocumentResponse(
                        id=str(existing_doc.id),
                        name=existing_doc.name,
                        size=existing_doc.size,
                        type=existing_doc.type,
                        status=existing_doc.status,
                        uploadedAt=existing_doc.uploaded_at.isoformat(),
                        chunksExtracted=existing_doc.chunks_count,
                        errorMessage=existing_doc.error_message,
                    )
                )
                continue  # Skip to next file
            
            # Generate S3 key with tenant_id and clone_id
            doc_id = uuid.uuid4()
            s3_key = f"documents/{clone_ctx.tenant_id}/{clone_ctx.clone_id}/{doc_id}/{file.filename}"
            
            # Create document record
            doc = Document(
                id=doc_id,
                clone_id=clone_ctx.clone_id,
                name=file.filename,
                size=file_size,
                type=file_ext or "application/octet-stream",
                file_hash=file_hash,
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
            
            # Schedule background processing (returns immediately)
            background_tasks.add_task(
                process_document_background,
                doc_id=doc.id,
                file_bytes=file_bytes,
                filename=file.filename,
                tenant_id=clone_ctx.tenant_id,
                clone_id=clone_ctx.clone_id,
            )

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
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    doc = data_access.validate_document_access(doc_uuid)
    
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
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    # Validate document access (ensures document belongs to this clone)
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    doc = data_access.validate_document_access(doc_uuid)
    
    # Verify S3 key matches tenant_id and clone_id
    expected_prefix = f"documents/{clone_ctx.tenant_id}/{clone_ctx.clone_id}/"
    if not doc.s3_key.startswith(expected_prefix):
        logger.warning(
            "S3 key mismatch detected",
            document_id=str(doc.id),
            s3_key=doc.s3_key,
            expected_prefix=expected_prefix
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document S3 path does not match clone/tenant"
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
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Get document processing status"""
    return await get_document(document_id, clone_ctx, db)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    clone_ctx: CloneContext = Depends(get_clone_context),
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
    
    # Validate document access (ensures document belongs to this clone)
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    doc = data_access.validate_document_access(doc_uuid)
    
    # Delete from S3
    try:
        s3_client = S3Client()
        s3_client.delete_object(doc.s3_key)
    except Exception as e:
        logger.warning("Failed to delete from S3", error=str(e), s3_key=doc.s3_key)
    
    # Delete vectors from vector store (filtered by clone_id/tenant_id)
    try:
        vector_store = data_access.get_vector_store()
        # Delete by document_id in metadata
        vector_store.delete(filter_metadata={"document_id": str(doc.id)})
    except Exception as e:
        logger.warning("Failed to delete vectors", error=str(e), document_id=str(doc.id))
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return None


@router.get("/documents/search", response_model=List[DocumentResponse])
async def search_documents(
    q: str = Query(..., description="Search query"),
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Search documents by name"""
    data_access = CloneDataAccessService(clone_ctx.clone_id, clone_ctx.tenant_id, db)
    # Simple text search on document names, filtered by clone_id
    documents = db.query(Document).filter(
        Document.clone_id == clone_ctx.clone_id,
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

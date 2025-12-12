"""Main ingestion pipeline orchestrator"""

from typing import List, Dict, Optional
from pathlib import Path
from uuid import UUID

from src.rag.vector_store import VectorStore
from src.rag.clone_vector_store import CloneVectorStore
from src.ingestion.document_ingester import DocumentIngester
from src.ingestion.slack_ingester import SlackIngester
from src.ingestion.email_ingester import EmailIngester
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    """Main pipeline for ingesting data from multiple sources"""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        clone_vector_store: Optional[CloneVectorStore] = None,
        document_ingester: Optional[DocumentIngester] = None,
        slack_ingester: Optional[SlackIngester] = None,
        email_ingester: Optional[EmailIngester] = None,
    ):
        # Prefer CloneVectorStore if provided (enforces clone isolation)
        if clone_vector_store:
            self.vector_store = clone_vector_store
        else:
            self.vector_store = vector_store or VectorStore()
        self.document_ingester = document_ingester or DocumentIngester()
        self.slack_ingester = slack_ingester
        self.email_ingester = email_ingester or EmailIngester()
    
    def ingest_documents(
        self,
        file_paths: List[str],
        clone_id: UUID,
        tenant_id: UUID,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
    ) -> int:
        """Ingest multiple document files"""
        # Ensure tenant_id and clone_id are in metadata
        if additional_metadata is None:
            additional_metadata = {}
        additional_metadata["tenant_id"] = str(tenant_id)
        additional_metadata["clone_id"] = str(clone_id)
        
        total_chunks = 0
        
        for file_path in file_paths:
            try:
                chunks = self.document_ingester.ingest_file(
                    file_path,
                    source_name=source_name,
                    additional_metadata=additional_metadata,
                )
                
                if chunks:
                    # Add to vector store (CloneVectorStore will validate IDs)
                    texts = [chunk["text"] for chunk in chunks]
                    metadatas = [chunk["metadata"] for chunk in chunks]
                    self.vector_store.add_texts(texts, metadatas=metadatas)
                    total_chunks += len(chunks)
                
                logger.info("Document ingested", file_path=file_path, chunks=len(chunks))
            except Exception as e:
                logger.error("Error ingesting document", error=str(e), file_path=file_path)
                continue
        
        logger.info("Documents ingestion completed", total_chunks=total_chunks)
        return total_chunks
    
    def ingest_slack_messages(
        self,
        clone_id: UUID,
        tenant_id: UUID,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 1000,
    ) -> int:
        """Ingest Slack messages"""
        if not self.slack_ingester:
            logger.error("Slack ingester not initialized")
            return 0
        
        try:
            if channel_id:
                messages = self.slack_ingester.fetch_channel_messages(channel_id, limit=limit)
            elif user_id:
                messages = self.slack_ingester.fetch_user_messages(user_id, limit=limit)
            else:
                logger.error("Either channel_id or user_id must be provided")
                return 0
            
            chunks = self.slack_ingester.ingest_messages(messages, user_id=user_id)
            
            # Inject tenant_id and clone_id into metadata
            for chunk in chunks:
                chunk["metadata"]["tenant_id"] = str(tenant_id)
                chunk["metadata"]["clone_id"] = str(clone_id)
            
            if chunks:
                texts = [chunk["text"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                self.vector_store.add_texts(texts, metadatas=metadatas)
            
            logger.info("Slack messages ingested", chunk_count=len(chunks))
            return len(chunks)
        except Exception as e:
            logger.error("Error ingesting Slack messages", error=str(e))
            return 0
    
    def ingest_emails(
        self,
        clone_id: UUID,
        tenant_id: UUID,
        file_paths: Optional[List[str]] = None,
        imap_config: Optional[Dict] = None,
    ) -> int:
        """Ingest emails from files or IMAP"""
        total_chunks = 0
        
        if file_paths:
            for file_path in file_paths:
                try:
                    chunks = self.email_ingester.ingest_email_file(file_path)
                    
                    # Inject tenant_id and clone_id into metadata
                    for chunk in chunks:
                        chunk["metadata"]["tenant_id"] = str(tenant_id)
                        chunk["metadata"]["clone_id"] = str(clone_id)
                    
                    if chunks:
                        texts = [chunk["text"] for chunk in chunks]
                        metadatas = [chunk["metadata"] for chunk in chunks]
                        self.vector_store.add_texts(texts, metadatas=metadatas)
                        total_chunks += len(chunks)
                    
                    logger.info("Email ingested", file_path=file_path, chunks=len(chunks))
                except Exception as e:
                    logger.error("Error ingesting email", error=str(e), file_path=file_path)
                    continue
        
        if imap_config:
            try:
                chunks = self.email_ingester.ingest_from_imap(**imap_config)
                
                # Inject tenant_id and clone_id into metadata
                for chunk in chunks:
                    chunk["metadata"]["tenant_id"] = str(tenant_id)
                    chunk["metadata"]["clone_id"] = str(clone_id)
                
                if chunks:
                    texts = [chunk["text"] for chunk in chunks]
                    metadatas = [chunk["metadata"] for chunk in chunks]
                    self.vector_store.add_texts(texts, metadatas=metadatas)
                    total_chunks += len(chunks)
                
                logger.info("Emails ingested from IMAP", chunks=len(chunks))
            except Exception as e:
                logger.error("Error ingesting from IMAP", error=str(e))
        
        logger.info("Email ingestion completed", total_chunks=total_chunks)
        return total_chunks
    
    def ingest_new_document(
        self,
        file_path: str,
        clone_id: UUID,
        tenant_id: UUID,
        source_name: Optional[str] = None,
    ) -> int:
        """Ingest a single new document (for incremental updates)"""
        return self.ingest_documents([file_path], clone_id, tenant_id, source_name=source_name)
    
    def ingest_new_document_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        clone_id: UUID,
        tenant_id: UUID,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
    ) -> int:
        """Ingest a new document from bytes (for uploads)"""
        # Ensure tenant_id and clone_id are in metadata
        if additional_metadata is None:
            additional_metadata = {}
        additional_metadata["tenant_id"] = str(tenant_id)
        additional_metadata["clone_id"] = str(clone_id)
        
        try:
            chunks = self.document_ingester.ingest_from_bytes(
                file_bytes,
                filename,
                source_name=source_name,
                additional_metadata=additional_metadata,
            )
            
            if chunks:
                texts = [chunk["text"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                self.vector_store.add_texts(texts, metadatas=metadatas)
            
            logger.info("Document ingested from bytes", filename=filename, chunks=len(chunks))
            return len(chunks)
        except Exception as e:
            logger.error("Error ingesting document from bytes", error=str(e))
            return 0



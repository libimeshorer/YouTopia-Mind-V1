"""Document ingester for PDF, DOCX, TXT files"""

from typing import List, Dict, Optional
from pathlib import Path

from src.utils.logging import get_logger
from src.utils.aws import S3Client
from src.ingestion.chunking import get_chunker

logger = get_logger(__name__)


class DocumentIngester:
    """Ingester for various document formats"""

    def __init__(self, s3_client: Optional[S3Client] = None):
        self.s3_client = s3_client or S3Client()
        self.chunker = get_chunker()  # Uses strategy from settings
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError as exc:
            raise ImportError(
                "pypdf is required for PDF ingestion. Install with `pip install pypdf`."
            ) from exc
        except Exception as e:
            logger.error("Error extracting text from PDF", error=str(e), file_path=file_path)
            raise
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document  # type: ignore[import-not-found]
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError as exc:
            raise ImportError(
                "python-docx is required for DOCX ingestion. Install with `pip install python-docx`."
            ) from exc
        except Exception as e:
            logger.error("Error extracting text from DOCX", error=str(e), file_path=file_path)
            raise
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error("Error reading TXT file", error=str(e), file_path=file_path)
            raise
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from document based on file extension"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif extension in [".docx", ".doc"]:
            return self.extract_text_from_docx(file_path)
        elif extension == ".txt":
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    
    def ingest_file(
        self,
        file_path: str,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Ingest a document file and return chunks"""
        from datetime import datetime
        
        path = Path(file_path)
        source = source_name or path.name
        
        logger.info("Ingesting document", file_path=file_path, source=source)
        
        # Extract text
        text = self.extract_text(file_path)
        
        if not text or not text.strip():
            logger.warning("No text extracted from document", file_path=file_path)
            return []
        
        # Prepare metadata with timestamps
        ingestion_timestamp = datetime.utcnow().isoformat()
        metadata = {
            "source": source,
            "file_path": str(path),
            "file_type": path.suffix.lower(),
            "ingested_at": ingestion_timestamp,  # When chunks were created and ingested
            **(additional_metadata or {}),
        }
        
        # Chunk text
        chunks = self.chunker.chunk_text(text, metadata)
        
        # Upload raw text to S3
        s3_key = f"raw/documents/{path.name}"
        try:
            with open(file_path, "rb") as f:
                self.s3_client.upload_fileobj(f, s3_key)
            logger.info("Raw document uploaded to S3", s3_key=s3_key)
        except Exception as e:
            logger.warning("Failed to upload raw document to S3", error=str(e))
        
        logger.info("Document ingested", file_path=file_path, chunk_count=len(chunks))
        return chunks
    
    def ingest_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
        document_uploaded_at: Optional[str] = None,
    ) -> List[Dict]:
        """
        Ingest a document from bytes (e.g., from upload).
        
        Args:
            file_bytes: Document file bytes
            filename: Original filename
            source_name: Optional source identifier
            additional_metadata: Optional additional metadata to include
            document_uploaded_at: ISO format timestamp of when document was uploaded (from Document.uploaded_at)
        """
        import tempfile
        
        # Add document upload timestamp to metadata if provided
        if document_uploaded_at and additional_metadata:
            additional_metadata["document_uploaded_at"] = document_uploaded_at
        elif document_uploaded_at:
            additional_metadata = {"document_uploaded_at": document_uploaded_at}
        
        # Save to temporary file
        path = Path(filename)
        extension = path.suffix.lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name
        
        try:
            return self.ingest_file(tmp_path, source_name, additional_metadata)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink()



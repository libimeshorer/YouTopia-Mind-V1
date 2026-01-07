"""Email ingester for processing email data"""

from typing import List, Dict, Optional
from datetime import datetime
import email
from email.header import decode_header

from src.utils.logging import get_logger
from src.utils.aws import S3Client
from src.ingestion.chunking import TextChunker

logger = get_logger(__name__)


class EmailIngester:
    """Ingester for email messages"""

    def __init__(self, s3_client: Optional[S3Client] = None):
        self.s3_client = s3_client or S3Client()
        # TODO: Chunking improvements for emails (when actively used):
        # 1. Consider semantic chunking for long email bodies (use get_chunker())
        # 2. Keep email thread/reply chains together as context
        # 3. Add contextual enrichment with email metadata (subject, sender, recipients)
        # 4. Special handling for forwarded emails and attachments
        # For now, using simple recursive chunking.
        # See: src/ingestion/context_enricher.py for contextual enrichment pattern.
        self.chunker = TextChunker()
    
    def decode_email_header(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or "utf-8")
            else:
                decoded_string += part
        return decoded_string
    
    def extract_email_text(self, email_message: email.message.Message) -> str:
        """Extract text content from email message"""
        text_content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_content += payload.decode(charset, errors="ignore") + "\n"
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                charset = email_message.get_content_charset() or "utf-8"
                text_content = payload.decode(charset, errors="ignore")
        
        return text_content
    
    def parse_email_file(self, file_path: str) -> Dict:
        """Parse an email file (EML format)"""
        try:
            with open(file_path, "rb") as f:
                email_message = email.message_from_bytes(f.read())
            
            subject = self.decode_email_header(email_message.get("Subject", ""))
            from_addr = self.decode_email_header(email_message.get("From", ""))
            to_addr = self.decode_email_header(email_message.get("To", ""))
            date = email_message.get("Date", "")
            text_content = self.extract_email_text(email_message)
            
            return {
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "text": text_content,
                "raw_message": email_message,
            }
        except Exception as e:
            logger.error("Error parsing email file", error=str(e), file_path=file_path)
            raise
    
    def ingest_email_file(
        self,
        file_path: str,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Ingest an email file and return chunks"""
        from pathlib import Path
        
        source = source_name or Path(file_path).name
        
        logger.info("Ingesting email", file_path=file_path, source=source)
        
        # Parse email
        email_data = self.parse_email_file(file_path)
        
        if not email_data["text"] or not email_data["text"].strip():
            logger.warning("No text content in email", file_path=file_path)
            return []
        
        # Prepare metadata
        metadata = {
            "source": source,
            "file_path": file_path,
            "email_subject": email_data["subject"],
            "email_from": email_data["from"],
            "email_to": email_data["to"],
            "email_date": email_data["date"],
            **(additional_metadata or {}),
        }
        
        # Format email text with subject
        email_text = f"Subject: {email_data['subject']}\n\n{email_data['text']}"
        
        # Chunk text
        chunks = self.chunker.chunk_text(email_text, metadata)
        
        # Upload raw email to S3
        s3_key = f"raw/emails/{Path(file_path).name}"
        try:
            with open(file_path, "rb") as f:
                self.s3_client.upload_fileobj(f, s3_key)
            logger.info("Raw email uploaded to S3", s3_key=s3_key)
        except Exception as e:
            logger.warning("Failed to upload raw email to S3", error=str(e))
        
        logger.info("Email ingested", file_path=file_path, chunk_count=len(chunks))
        return chunks
    
    def ingest_from_imap(
        self,
        imap_server: str,
        username: str,
        password: str,
        mailbox: str = "INBOX",
        limit: int = 100,
    ) -> List[Dict]:
        """Ingest emails from IMAP server"""
        import imaplib
        
        chunks = []
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(username, password)
            mail.select(mailbox)
            
            # Search for emails
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()
            
            # Limit number of emails
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                
                if status == "OK":
                    email_message = email.message_from_bytes(msg_data[0][1])
                    text_content = self.extract_email_text(email_message)
                    
                    if text_content.strip():
                        subject = self.decode_email_header(email_message.get("Subject", ""))
                        metadata = {
                            "source": "imap",
                            "email_subject": subject,
                            "email_from": self.decode_email_header(email_message.get("From", "")),
                            "email_date": email_message.get("Date", ""),
                        }
                        
                        email_text = f"Subject: {subject}\n\n{text_content}"
                        email_chunks = self.chunker.chunk_text(email_text, metadata)
                        chunks.extend(email_chunks)
            
            mail.close()
            mail.logout()
            
            logger.info("Emails ingested from IMAP", count=len(chunks))
            return chunks
        except Exception as e:
            logger.error("Error ingesting from IMAP", error=str(e))
            raise



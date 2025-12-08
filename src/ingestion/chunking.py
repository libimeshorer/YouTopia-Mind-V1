"""Text chunking strategies for document ingestion using LangChain"""

from typing import List, Dict, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TextChunker:
    """Text chunking utility using LangChain RecursiveCharacterTextSplitter"""
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Initialize LangChain text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
    
    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text using LangChain RecursiveCharacterTextSplitter"""
        if not text or not text.strip():
            return []
        
        try:
            # Use LangChain to create documents
            documents = self.splitter.create_documents([text])
            
            # Convert to our format with metadata
            chunks = []
            for idx, doc in enumerate(documents):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_index": idx,
                    "chunking_strategy": "recursive_character",
                })
                
                chunks.append({
                    "text": doc.page_content,
                    "metadata": {**chunk_metadata, **(doc.metadata or {})},
                })
            
            logger.debug("Text chunked", original_length=len(text), chunk_count=len(chunks))
            return chunks
        except Exception as e:
            logger.error("Error chunking text with LangChain", error=str(e))
            raise
    
    def chunk_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[Dict]:
        """Chunk multiple texts"""
        all_chunks = []
        
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def chunk_by_sentences(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text by sentences (semantic chunking) - kept for backward compatibility"""
        # Use the main chunk_text method which already handles sentence boundaries
        return self.chunk_text(text, metadata)



"""Text chunking strategies for document ingestion"""

from typing import List, Dict
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TextChunker:
    """Text chunking utility with multiple strategies"""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Chunk text using sliding window approach"""
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Calculate end position
            end = min(start + self.chunk_size, text_length)
            
            # Extract chunk
            chunk_text = text[start:end]
            
            # Create chunk metadata
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.update({
                "chunk_index": len(chunks),
                "chunk_start": start,
                "chunk_end": end,
            })
            
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": chunk_metadata,
            })
            
            # Move start position with overlap
            start += self.chunk_size - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= text_length:
                break
        
        logger.debug("Text chunked", original_length=text_length, chunk_count=len(chunks))
        return chunks
    
    def chunk_texts(self, texts: List[str], metadatas: List[Dict] = None) -> List[Dict]:
        """Chunk multiple texts"""
        all_chunks = []
        
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def chunk_by_sentences(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Chunk text by sentences (semantic chunking)"""
        import re
        
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_index": len(chunks),
                    "chunking_strategy": "sentence",
                })
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                })
                
                # Keep overlap sentences
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.update({
                "chunk_index": len(chunks),
                "chunking_strategy": "sentence",
            })
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata,
            })
        
        logger.debug("Text chunked by sentences", original_length=len(text), chunk_count=len(chunks))
        return chunks



"""Text chunking strategies for document ingestion"""

from typing import List, Dict, Optional, Union
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


class SemanticTextChunker:
    """
    Semantic chunking using chonkie with local embeddings.

    Splits text based on semantic similarity between sentences,
    keeping related content together. Uses a local sentence-transformer
    model (all-MiniLM-L6-v2) for embedding, which is fast and free.
    """

    def __init__(
        self,
        similarity_threshold: Optional[float] = None,
        chunk_size: Optional[int] = None,
    ):
        self.similarity_threshold = similarity_threshold or settings.semantic_similarity_threshold
        self.chunk_size = chunk_size or settings.chunk_size

        try:
            from chonkie import SemanticChunker

            # Use local model - fast, free, no API calls
            self.chunker = SemanticChunker(
                embedding_model="all-MiniLM-L6-v2",
                chunk_size=self.chunk_size,
                similarity_threshold=self.similarity_threshold,
            )
            logger.info(
                "SemanticTextChunker initialized",
                chunk_size=self.chunk_size,
                similarity_threshold=self.similarity_threshold,
            )
        except ImportError as e:
            logger.error("Failed to import chonkie", error=str(e))
            raise ImportError(
                "chonkie is required for semantic chunking. "
                "Install with: pip install chonkie[semantic]"
            ) from e

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text using semantic similarity.

        Args:
            text: The text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunks with text and metadata
        """
        if not text or not text.strip():
            return []

        try:
            # Semantic chunking with chonkie
            chunks = self.chunker.chunk(text)

            # TODO: Consider adding post-processing to merge very small chunks
            # or split very large chunks if retrieval accuracy needs improvement.
            # Options to explore:
            # - Merge chunks smaller than min_chunk_size with adjacent chunks
            # - Split chunks larger than max_chunk_size using recursive splitter
            # - Use chonkie's built-in size constraints if available
            # See: https://docs.chonkie.ai for chunk size tuning options.

            # Format output to match TextChunker interface
            result = []
            for idx, chunk in enumerate(chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_index": idx,
                    "chunking_strategy": "semantic",
                })
                # chonkie returns Chunk objects with .text attribute
                chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
                result.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                })

            logger.debug(
                "Text chunked semantically",
                original_length=len(text),
                chunk_count=len(result),
            )
            return result

        except Exception as e:
            logger.warning(
                "Semantic chunking failed, falling back to recursive",
                error=str(e),
            )
            # Fallback to recursive chunker
            return TextChunker().chunk_text(text, metadata)

    def chunk_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[Dict]:
        """Chunk multiple texts"""
        all_chunks = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        return all_chunks


def get_chunker(strategy: Optional[str] = None) -> Union[TextChunker, SemanticTextChunker]:
    """
    Factory function to get the appropriate chunker based on settings.

    Args:
        strategy: Override strategy ("semantic" or "recursive").
                  If None, uses settings.chunking_strategy.

    Returns:
        TextChunker or SemanticTextChunker instance
    """
    strategy = strategy or settings.chunking_strategy

    if strategy == "semantic":
        try:
            return SemanticTextChunker()
        except ImportError:
            logger.warning("chonkie not available, falling back to recursive chunker")
            return TextChunker()

    return TextChunker()

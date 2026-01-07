"""Text chunking strategies for document ingestion"""

import re
import numpy as np
from typing import List, Dict, Optional, Union
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
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


class SemanticTextChunker:
    """
    Semantic chunking using OpenAI embeddings.

    Splits text based on meaning rather than character count:
    1. Split text into sentences
    2. Embed sentences with text-embedding-3-small (cheap)
    3. Calculate cosine similarity between consecutive sentences
    4. Split where similarity drops below threshold
    5. Merge sentences into chunks respecting size limits
    """

    # Regex pattern to split text into sentences
    SENTENCE_PATTERN = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z])|'  # After .!? followed by space and capital
        r'(?<=[.!?])\s*\n+|'        # After .!? at end of line
        r'\n\n+'                     # Double newlines (paragraph breaks)
    )

    def __init__(
        self,
        similarity_threshold: Optional[float] = None,
        min_chunk_size: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
        embedding_model: Optional[str] = None,
    ):
        self.similarity_threshold = similarity_threshold or settings.semantic_similarity_threshold
        self.min_chunk_size = min_chunk_size or settings.semantic_min_chunk_size
        self.max_chunk_size = max_chunk_size or settings.semantic_max_chunk_size
        self.embedding_model = embedding_model or settings.semantic_embedding_model
        self.client = OpenAI(api_key=settings.openai_api_key)

        # Fallback chunker for edge cases
        self._fallback_chunker = TextChunker(
            chunk_size=self.max_chunk_size,
            chunk_overlap=int(self.max_chunk_size * 0.1),
        )

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Split by sentence boundaries
        sentences = self.SENTENCE_PATTERN.split(text)

        # Clean up and filter empty sentences
        cleaned = []
        for s in sentences:
            s = s.strip()
            if s and len(s) > 10:  # Ignore very short fragments
                cleaned.append(s)

        return cleaned

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings)
        except Exception as e:
            logger.error("Error getting embeddings", error=str(e))
            raise

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _find_split_points(self, embeddings: np.ndarray) -> List[int]:
        """
        Find indices where semantic similarity drops below threshold.
        Returns list of indices where splits should occur.
        """
        split_points = []

        for i in range(len(embeddings) - 1):
            similarity = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            if similarity < self.similarity_threshold:
                split_points.append(i + 1)  # Split after this sentence

        return split_points

    def _merge_sentences_into_chunks(
        self,
        sentences: List[str],
        split_points: List[int],
    ) -> List[str]:
        """
        Merge sentences into chunks based on split points.
        Ensures chunks respect min/max size limits.
        """
        chunks = []
        current_chunk = []
        current_size = 0

        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)

            # Check if we should split here
            should_split = i in split_points

            # If adding this sentence would exceed max size, split first
            if current_chunk and current_size + sentence_size + 1 > self.max_chunk_size:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size + 1  # +1 for space

            # If this is a semantic split point and chunk is big enough
            if should_split and current_size >= self.min_chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            # If last chunk is too small, merge with previous
            if len(chunk_text) < self.min_chunk_size and chunks:
                chunks[-1] = chunks[-1] + " " + chunk_text
            else:
                chunks.append(chunk_text)

        return chunks

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text semantically using embeddings.

        Falls back to recursive chunking if:
        - Text is too short
        - Too few sentences
        - Embedding fails
        """
        if not text or not text.strip():
            return []

        # Split into sentences
        sentences = self._split_into_sentences(text)

        # Fall back to recursive if too few sentences
        if len(sentences) < 3:
            logger.debug("Too few sentences for semantic chunking, using fallback")
            return self._fallback_chunker.chunk_text(text, metadata)

        try:
            # Get embeddings for all sentences
            logger.debug(f"Getting embeddings for {len(sentences)} sentences")
            embeddings = self._get_embeddings(sentences)

            # Find semantic split points
            split_points = self._find_split_points(embeddings)
            logger.debug(f"Found {len(split_points)} semantic split points")

            # Merge sentences into chunks
            chunk_texts = self._merge_sentences_into_chunks(sentences, split_points)

            # Build result with metadata
            chunks = []
            for idx, chunk_text in enumerate(chunk_texts):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "chunk_index": idx,
                    "chunking_strategy": "semantic",
                })
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                })

            logger.info(
                "Semantic chunking complete",
                sentences=len(sentences),
                chunks=len(chunks),
                split_points=len(split_points),
            )
            return chunks

        except Exception as e:
            logger.warning(f"Semantic chunking failed, falling back to recursive: {e}")
            return self._fallback_chunker.chunk_text(text, metadata)

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
    Factory function to get the appropriate chunker based on strategy.

    Args:
        strategy: "recursive" or "semantic". Defaults to settings.chunking_strategy

    Returns:
        TextChunker for recursive strategy, SemanticTextChunker for semantic
    """
    strategy = strategy or settings.chunking_strategy

    if strategy == "semantic":
        logger.info("Using semantic chunking strategy")
        return SemanticTextChunker()
    else:
        logger.debug("Using recursive character chunking strategy")
        return TextChunker()

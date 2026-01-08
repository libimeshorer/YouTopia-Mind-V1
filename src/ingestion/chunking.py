"""Text chunking strategies for document ingestion"""

import re
import time
import numpy as np
from typing import List, Dict, Optional, Union
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Retry configuration for embeddings API
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


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

        # Fallback chunker for edge cases (including oversized sentences)
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

    def _get_embeddings_with_retry(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts using OpenAI API with retry logic."""
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=texts,
                )

                # Log token usage for cost monitoring
                if response.usage:
                    logger.debug(
                        "Embedding tokens used",
                        total_tokens=response.usage.total_tokens,
                        sentence_count=len(texts),
                    )

                embeddings = [item.embedding for item in response.data]
                return np.array(embeddings)

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Embedding API failed, retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        retry_delay=delay,
                    )
                    time.sleep(delay)

        logger.error("Embedding API failed after retries", error=str(last_error))
        raise last_error

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

    def _split_oversized_sentence(self, sentence: str) -> List[str]:
        """
        Split an oversized sentence using the fallback chunker.
        Returns list of sub-chunks.
        """
        chunks = self._fallback_chunker.chunk_text(sentence)
        return [chunk["text"] for chunk in chunks]

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
        pending_small_chunk = None  # Track undersized chunks to merge forward

        for i, sentence in enumerate(sentences):
            sentence_size = len(sentence)

            # Handle oversized single sentences
            if sentence_size > self.max_chunk_size:
                # First, save current chunk if any
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    if pending_small_chunk:
                        chunk_text = pending_small_chunk + " " + chunk_text
                        pending_small_chunk = None
                    chunks.append(chunk_text)
                    current_chunk = []
                    current_size = 0

                # Split the oversized sentence and add as separate chunks
                sub_chunks = self._split_oversized_sentence(sentence)
                chunks.extend(sub_chunks)
                continue

            # Check if we should split here (semantic boundary)
            should_split = i in split_points

            # If adding this sentence would exceed max size, save current chunk first
            if current_chunk and current_size + sentence_size + 1 > self.max_chunk_size:
                chunk_text = " ".join(current_chunk)

                # Prepend any pending small chunk
                if pending_small_chunk:
                    chunk_text = pending_small_chunk + " " + chunk_text
                    pending_small_chunk = None

                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)
                else:
                    # Chunk is too small - save for merging with next chunk
                    pending_small_chunk = chunk_text

                current_chunk = []
                current_size = 0

            # Prepend pending small chunk to current if starting fresh
            if not current_chunk and pending_small_chunk:
                current_chunk.append(pending_small_chunk)
                current_size = len(pending_small_chunk) + 1
                pending_small_chunk = None

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size + 1  # +1 for space

            # If this is a semantic split point and chunk is big enough
            if should_split and current_size >= self.min_chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

        # Handle the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)

            # Prepend any pending small chunk
            if pending_small_chunk:
                chunk_text = pending_small_chunk + " " + chunk_text
                pending_small_chunk = None

            # If last chunk is too small, try to merge with previous
            if len(chunk_text) < self.min_chunk_size and chunks:
                # Check if merging won't exceed max size
                if len(chunks[-1]) + len(chunk_text) + 1 <= self.max_chunk_size:
                    chunks[-1] = chunks[-1] + " " + chunk_text
                else:
                    # Can't merge - keep as separate (small) chunk
                    chunks.append(chunk_text)
            else:
                chunks.append(chunk_text)

        # Handle any remaining pending small chunk
        if pending_small_chunk:
            if chunks and len(chunks[-1]) + len(pending_small_chunk) + 1 <= self.max_chunk_size:
                chunks[-1] = chunks[-1] + " " + pending_small_chunk
            else:
                chunks.append(pending_small_chunk)

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
            # Get embeddings for all sentences (with retry)
            logger.debug(f"Getting embeddings for {len(sentences)} sentences")
            embeddings = self._get_embeddings_with_retry(sentences)

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

"""
Context enrichment for document chunks using LLM.

Adds contextual prefixes to chunks to improve retrieval accuracy.
Based on Anthropic's Contextual Retrieval approach.

This module is designed to run during document ingestion to enhance
each chunk with context that helps it be more discoverable during search.
"""

import asyncio
import time
from typing import List, Dict, Tuple, Optional
from openai import OpenAI, AsyncOpenAI
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Response validation constants
MIN_CONTEXT_LENGTH = 10
MAX_CONTEXT_LENGTH = 300

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

CONTEXT_PROMPT = """<document>
{document}
</document>

Here is a chunk from this document:
<chunk>
{chunk}
</chunk>

In ONE sentence, describe what this chunk is about and where it fits in the document. Be specific and concise.

Context:"""


class ContextEnricher:
    """
    Enriches document chunks with LLM-generated context.

    This improves retrieval by making each chunk self-descriptive,
    so it can be found even when the query doesn't match the exact wording.

    Example:
        Original chunk: "Revenue grew 3% over previous quarter."
        Enriched chunk: "This section discusses Q2 2023 financial results.

                        Revenue grew 3% over previous quarter."
    """

    def __init__(self, model: str = None):
        self.model = model or settings.context_enrichment_model
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.max_document_chars = settings.max_document_chars_for_context
        self.max_chunks = settings.max_chunks_per_document_for_context

    def should_enrich(self, document_length: int, chunk_count: int) -> bool:
        """
        Determine if document should get context enrichment.

        Skips very long documents where truncation would hurt context quality.
        For long documents, the context for later chunks would be generated
        from truncated document text, potentially producing misleading context.

        Args:
            document_length: Length of document in characters
            chunk_count: Number of chunks in document

        Returns:
            True if document should be enriched, False otherwise
        """
        if document_length > self.max_document_chars:
            logger.info(
                "Skipping context enrichment for long document",
                document_length=document_length,
                max_allowed=self.max_document_chars,
            )
            # TODO: Implement smarter context window for long documents:
            # - Include document intro + local context around each chunk
            # - Use document summarization first
            # - Chunk the document into sections and enrich within sections
            # - Use sliding window approach for context
            return False

        if chunk_count > self.max_chunks:
            logger.warning(
                "Document has too many chunks for context enrichment",
                chunk_count=chunk_count,
                max_allowed=self.max_chunks,
            )
            return False

        return True

    def _validate_context(self, context: Optional[str]) -> Tuple[bool, str]:
        """
        Validate LLM-generated context.

        Args:
            context: The generated context string

        Returns:
            Tuple of (is_valid, cleaned_context_or_reason)
        """
        if not context:
            return False, "Empty response"

        # Strip common prefixes the LLM might add
        cleaned = context.strip()
        if cleaned.lower().startswith("context:"):
            cleaned = cleaned[8:].strip()

        # Check length bounds
        if len(cleaned) < MIN_CONTEXT_LENGTH:
            return False, f"Too short ({len(cleaned)} chars)"

        if len(cleaned) > MAX_CONTEXT_LENGTH:
            # Truncate overly long contexts
            cleaned = cleaned[:MAX_CONTEXT_LENGTH].rsplit(" ", 1)[0] + "..."
            logger.warning("Context truncated", original_length=len(context))

        return True, cleaned

    def _enrich_chunk_sync(self, chunk_text: str, full_document: str) -> Tuple[str, bool]:
        """
        Add context prefix to a single chunk (synchronous with retry).

        Args:
            chunk_text: The chunk to enrich
            full_document: The complete document for context

        Returns:
            Tuple of (enriched_text, success_flag)
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": CONTEXT_PROMPT.format(
                                document=full_document,
                                chunk=chunk_text,
                            ),
                        }
                    ],
                    max_tokens=100,
                    temperature=0,
                )
                context = response.choices[0].message.content

                # Log token usage for cost monitoring
                if response.usage:
                    logger.debug(
                        "Context enrichment tokens",
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                    )

                # Validate response
                is_valid, result = self._validate_context(context)
                if not is_valid:
                    logger.warning("Invalid context response", reason=result, attempt=attempt + 1)
                    last_error = result
                    continue

                return f"{result}\n\n{chunk_text}", True

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Context enrichment failed, retrying",
                        error=last_error,
                        attempt=attempt + 1,
                        retry_delay=delay,
                    )
                    time.sleep(delay)

        logger.error("Context enrichment failed after retries", error=last_error)
        return chunk_text, False

    async def _enrich_chunk_async(self, chunk_text: str, full_document: str) -> Tuple[str, bool]:
        """
        Add context prefix to a single chunk (async with retry).

        Args:
            chunk_text: The chunk to enrich
            full_document: The complete document for context

        Returns:
            Tuple of (enriched_text, success_flag)
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": CONTEXT_PROMPT.format(
                                document=full_document,
                                chunk=chunk_text,
                            ),
                        }
                    ],
                    max_tokens=100,
                    temperature=0,
                )
                context = response.choices[0].message.content

                # Log token usage for cost monitoring
                if response.usage:
                    logger.debug(
                        "Context enrichment tokens",
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                    )

                # Validate response
                is_valid, result = self._validate_context(context)
                if not is_valid:
                    logger.warning("Invalid context response", reason=result, attempt=attempt + 1)
                    last_error = result
                    continue

                return f"{result}\n\n{chunk_text}", True

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Context enrichment failed, retrying",
                        error=last_error,
                        attempt=attempt + 1,
                        retry_delay=delay,
                    )
                    await asyncio.sleep(delay)

        logger.error("Context enrichment failed after retries", error=last_error)
        return chunk_text, False

    async def _enrich_chunks_parallel(
        self,
        chunks: List[Dict],
        full_document: str,
    ) -> List[Dict]:
        """
        Enrich chunks in parallel using async API calls.

        Args:
            chunks: List of chunk dicts
            full_document: Complete document text

        Returns:
            List of enriched chunk dicts
        """
        # Create tasks for all chunks
        tasks = [
            self._enrich_chunk_async(chunk["text"], full_document)
            for chunk in chunks
        ]

        # Run all in parallel
        results = await asyncio.gather(*tasks)

        # Build enriched chunks with accurate metadata
        enriched = []
        success_count = 0
        for chunk, (enriched_text, success) in zip(chunks, results):
            if success:
                success_count += 1
            enriched.append({
                "text": enriched_text,
                "metadata": {
                    **chunk["metadata"],
                    "context_enriched": success,
                },
            })

        logger.info(
            "Parallel enrichment complete",
            total=len(chunks),
            successful=success_count,
            failed=len(chunks) - success_count,
        )
        return enriched

    def enrich_chunks(
        self,
        chunks: List[Dict],
        full_document: str,
    ) -> List[Dict]:
        """
        Enrich multiple chunks with context (runs async internally).

        Args:
            chunks: List of chunk dicts with 'text' and 'metadata' keys
            full_document: Complete document text for context generation

        Returns:
            List of enriched chunk dicts with context prefixes added
        """
        if not chunks:
            return chunks

        # Check if we should enrich this document
        if not self.should_enrich(len(full_document), len(chunks)):
            # Mark chunks as not enriched and return as-is
            for chunk in chunks:
                chunk["metadata"]["context_enriched"] = False
            return chunks

        logger.info(f"Enriching {len(chunks)} chunks with context (parallel)")

        # Run async enrichment
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._enrich_chunks_parallel(chunks, full_document)
                    )
                    return future.result()
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(self._enrich_chunks_parallel(chunks, full_document))
        except Exception as e:
            logger.error("Parallel enrichment failed, falling back to sequential", error=str(e))
            return self._enrich_chunks_sequential(chunks, full_document)

    def _enrich_chunks_sequential(
        self,
        chunks: List[Dict],
        full_document: str,
    ) -> List[Dict]:
        """
        Fallback: Enrich chunks sequentially.

        Args:
            chunks: List of chunk dicts
            full_document: Complete document text

        Returns:
            List of enriched chunk dicts
        """
        enriched = []
        success_count = 0

        for i, chunk in enumerate(chunks):
            enriched_text, success = self._enrich_chunk_sync(chunk["text"], full_document)
            if success:
                success_count += 1

            enriched.append({
                "text": enriched_text,
                "metadata": {
                    **chunk["metadata"],
                    "context_enriched": success,
                },
            })

            # Progress logging for larger documents
            if (i + 1) % 10 == 0:
                logger.info(f"Enriched {i + 1}/{len(chunks)} chunks")

        logger.info(
            "Sequential enrichment complete",
            total=len(chunks),
            successful=success_count,
            failed=len(chunks) - success_count,
        )
        return enriched

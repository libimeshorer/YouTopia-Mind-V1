"""
Context enrichment for document chunks using LLM.

Adds contextual prefixes to chunks to improve retrieval accuracy.
Based on Anthropic's Contextual Retrieval approach.

This module is designed to run during document ingestion to enhance
each chunk with context that helps it be more discoverable during search.
"""

from typing import List, Dict
from openai import OpenAI
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

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

    def enrich_chunk(self, chunk_text: str, full_document: str) -> str:
        """
        Add context prefix to a single chunk.

        Args:
            chunk_text: The chunk to enrich
            full_document: The complete document for context

        Returns:
            Enriched chunk with context prefix, or original chunk on failure
        """
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
                max_tokens=100,  # One sentence shouldn't need more
                temperature=0,
            )
            context = response.choices[0].message.content.strip()

            # Log token usage for cost monitoring
            if response.usage:
                logger.debug(
                    "Context enrichment tokens",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                )

            return f"{context}\n\n{chunk_text}"

        except Exception as e:
            logger.error("Error enriching chunk with context", error=str(e))
            return chunk_text  # Return original on failure

    def enrich_chunks(
        self,
        chunks: List[Dict],
        full_document: str,
    ) -> List[Dict]:
        """
        Enrich multiple chunks with context.

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

        logger.info(f"Enriching {len(chunks)} chunks with context")

        enriched = []
        for i, chunk in enumerate(chunks):
            enriched_text = self.enrich_chunk(chunk["text"], full_document)

            enriched.append({
                "text": enriched_text,
                "metadata": {
                    **chunk["metadata"],
                    "context_enriched": True,
                },
            })

            # Progress logging for larger documents
            if (i + 1) % 10 == 0:
                logger.info(f"Enriched {i + 1}/{len(chunks)} chunks")

        logger.info("Context enrichment complete", chunk_count=len(enriched))
        return enriched
